from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.entitlements import (
    InactiveSubscriptionError,
    InsufficientCreditsError,
    finalize_daily_tokens,
    refund_daily_tokens,
    reserve_daily_tokens,
)
from apps.accounts.models import DailyTokenUsage, Subscription


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="subscriber", password="password-123")


@pytest.fixture
def active_subscription(user):
    return Subscription.objects.create(
        user=user,
        status=Subscription.Status.ACTIVE,
        daily_token_limit=1_000,
    )


@pytest.mark.django_db
def test_missing_or_inactive_subscription_fails_without_usage(user):
    with pytest.raises(InactiveSubscriptionError):
        reserve_daily_tokens(user, 10)
    assert DailyTokenUsage.objects.count() == 0

    Subscription.objects.create(user=user, status=Subscription.Status.INACTIVE)
    with pytest.raises(InactiveSubscriptionError):
        reserve_daily_tokens(user, 10)
    assert DailyTokenUsage.objects.count() == 0


@pytest.mark.django_db
def test_reservation_creates_one_daily_row_and_enforces_limit(user, active_subscription):
    first = reserve_daily_tokens(user, 600)
    with pytest.raises(InsufficientCreditsError):
        reserve_daily_tokens(user, 401)

    usage = DailyTokenUsage.objects.get(pk=first.usage_id)
    assert usage.used_tokens == 600
    assert DailyTokenUsage.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_refund_and_finalize_reconcile_reserved_usage(user, active_subscription):
    refunded = reserve_daily_tokens(user, 300)
    refund_daily_tokens(refunded)
    usage = DailyTokenUsage.objects.get(pk=refunded.usage_id)
    assert usage.used_tokens == 0

    finalized = reserve_daily_tokens(user, 300)
    finalize_daily_tokens(finalized, 125)
    usage.refresh_from_db()
    assert usage.used_tokens == 125


@pytest.mark.django_db
def test_quota_mutations_refresh_audit_timestamp(user, active_subscription, monkeypatch):
    reservation = reserve_daily_tokens(user, 300)
    usage = DailyTokenUsage.objects.get(pk=reservation.usage_id)
    future = usage.updated_at + timedelta(minutes=1)
    monkeypatch.setattr("apps.accounts.entitlements.timezone.now", lambda: future)

    refund_daily_tokens(reservation)

    usage.refresh_from_db()
    assert usage.updated_at == future


@pytest.mark.django_db
def test_actual_usage_over_reservation_is_recorded(user, active_subscription, caplog):
    reservation = reserve_daily_tokens(user, 100)
    finalize_daily_tokens(reservation, 140)

    usage = DailyTokenUsage.objects.get(pk=reservation.usage_id)
    assert usage.used_tokens == 140
    assert "exceeded reserved token bound" in caplog.text


@pytest.mark.django_db
@pytest.mark.parametrize("actual_tokens", [-1, True, 1.5])
def test_finalize_rejects_invalid_actual_usage(user, active_subscription, actual_tokens):
    reservation = reserve_daily_tokens(user, 100)

    with pytest.raises(ValueError, match="actual_tokens"):
        finalize_daily_tokens(reservation, actual_tokens)

    assert DailyTokenUsage.objects.get(pk=reservation.usage_id).used_tokens == 100


@pytest.mark.django_db
def test_usage_rolls_over_by_utc_application_day(user, active_subscription):
    yesterday = timezone.localdate() - timedelta(days=1)
    DailyTokenUsage.objects.create(user=user, usage_date=yesterday, used_tokens=900)

    reservation = reserve_daily_tokens(user, 100)

    assert DailyTokenUsage.objects.get(pk=reservation.usage_id).usage_date == timezone.localdate()
    assert DailyTokenUsage.objects.get(user=user, usage_date=yesterday).used_tokens == 900


@pytest.mark.django_db
@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_reservation_rejects_invalid_estimates(user, active_subscription, value):
    with pytest.raises(ValueError, match="estimated_tokens"):
        reserve_daily_tokens(user, value)
