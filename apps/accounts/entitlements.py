import logging
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Case, F, Value, When
from django.utils import timezone

from apps.accounts.models import DailyTokenUsage, Subscription

logger = logging.getLogger(__name__)


class InactiveSubscriptionError(Exception):
    """Raised when a user has no active local RAG subscription."""


class InsufficientCreditsError(Exception):
    """Raised when a request cannot fit within the user's daily token quota."""


@dataclass(frozen=True)
class TokenReservation:
    usage_id: int
    reserved_tokens: int


def _positive_token_count(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def ensure_active_subscription(user) -> Subscription:
    try:
        subscription = Subscription.objects.get(user=user)
    except Subscription.DoesNotExist as exc:
        raise InactiveSubscriptionError("Active subscription required.") from exc

    if subscription.status != Subscription.Status.ACTIVE:
        raise InactiveSubscriptionError("Active subscription required.")
    return subscription


def _lock_or_create_usage(*, user, usage_date) -> DailyTokenUsage:
    usage = (
        DailyTokenUsage.objects.select_for_update().filter(user=user, usage_date=usage_date).first()
    )
    if usage is not None:
        return usage

    try:
        with transaction.atomic():
            return DailyTokenUsage.objects.create(user=user, usage_date=usage_date)
    except IntegrityError:
        return DailyTokenUsage.objects.select_for_update().get(
            user=user,
            usage_date=usage_date,
        )


def reserve_daily_tokens(user, estimated_tokens: int) -> TokenReservation:
    estimated_tokens = _positive_token_count(estimated_tokens, name="estimated_tokens")

    with transaction.atomic():
        try:
            subscription = Subscription.objects.select_for_update().get(user=user)
        except Subscription.DoesNotExist as exc:
            raise InactiveSubscriptionError("Active subscription required.") from exc
        if subscription.status != Subscription.Status.ACTIVE:
            raise InactiveSubscriptionError("Active subscription required.")

        usage = _lock_or_create_usage(user=user, usage_date=timezone.localdate())
        if usage.used_tokens + estimated_tokens > subscription.daily_token_limit:
            raise InsufficientCreditsError("Insufficient daily token credits.")

        DailyTokenUsage.objects.filter(pk=usage.pk).update(
            used_tokens=F("used_tokens") + estimated_tokens,
            updated_at=timezone.now(),
        )
        return TokenReservation(usage_id=usage.pk, reserved_tokens=estimated_tokens)


def _reduce_usage(usage_id: int, tokens: int) -> None:
    DailyTokenUsage.objects.filter(pk=usage_id).update(
        used_tokens=Case(
            When(used_tokens__gte=tokens, then=F("used_tokens") - tokens),
            default=Value(0),
        ),
        updated_at=timezone.now(),
    )


def refund_daily_tokens(reservation: TokenReservation) -> None:
    _positive_token_count(reservation.reserved_tokens, name="reserved_tokens")
    with transaction.atomic():
        DailyTokenUsage.objects.select_for_update().get(pk=reservation.usage_id)
        _reduce_usage(reservation.usage_id, reservation.reserved_tokens)


def finalize_daily_tokens(reservation: TokenReservation, actual_tokens: int) -> None:
    _positive_token_count(reservation.reserved_tokens, name="reserved_tokens")
    if isinstance(actual_tokens, bool) or not isinstance(actual_tokens, int) or actual_tokens < 0:
        raise ValueError("actual_tokens must be a non-negative integer.")

    delta = actual_tokens - reservation.reserved_tokens
    with transaction.atomic():
        DailyTokenUsage.objects.select_for_update().get(pk=reservation.usage_id)
        if delta > 0:
            logger.error(
                "Provider usage exceeded reserved token bound",
                extra={"usage_id": reservation.usage_id, "overage_tokens": delta},
            )
            DailyTokenUsage.objects.filter(pk=reservation.usage_id).update(
                used_tokens=F("used_tokens") + delta,
                updated_at=timezone.now(),
            )
        elif delta < 0:
            _reduce_usage(reservation.usage_id, -delta)
