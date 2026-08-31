from collections.abc import Callable
from typing import Any

from apps.accounts.entitlements import (
    finalize_daily_tokens,
    refund_daily_tokens,
    reserve_daily_tokens,
)
from apps.rag.exceptions import RagAccountingError


class RagStageReservation:
    def __init__(self, reservation, *, finalize: Callable, refund: Callable):
        self._reservation = reservation
        self._finalize = finalize
        self._refund = refund
        self._terminal_attempted = False

    @property
    def reserved_tokens(self) -> int:
        return self._reservation.reserved_tokens

    @property
    def usage_id(self):
        return self._reservation.usage_id

    @property
    def terminal_attempted(self) -> bool:
        return self._terminal_attempted

    def finalize(self, actual_tokens: int) -> None:
        self._begin_terminal_attempt()
        try:
            self._finalize(self._reservation, actual_tokens)
        except Exception as exc:
            raise RagAccountingError("Unable to finalize token usage.") from exc

    def refund(self) -> None:
        self._begin_terminal_attempt()
        try:
            self._refund(self._reservation)
        except Exception as exc:
            raise RagAccountingError("Unable to refund token usage.") from exc

    def _begin_terminal_attempt(self) -> None:
        if self._terminal_attempted:
            raise RagAccountingError("Token reservation was already settled.")
        self._terminal_attempted = True


class RagStageAccounting:
    def __init__(
        self,
        *,
        reserve: Callable[[Any, int], Any] = reserve_daily_tokens,
        finalize: Callable[[Any, int], None] = finalize_daily_tokens,
        refund: Callable[[Any], None] = refund_daily_tokens,
    ):
        self._reserve = reserve
        self._finalize = finalize
        self._refund = refund

    def reserve(self, user, estimated_tokens: int) -> RagStageReservation:
        reservation = self._reserve(user, estimated_tokens)
        return RagStageReservation(
            reservation,
            finalize=self._finalize,
            refund=self._refund,
        )
