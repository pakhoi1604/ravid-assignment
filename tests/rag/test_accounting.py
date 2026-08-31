from types import SimpleNamespace

import pytest

from apps.rag.accounting import RagStageAccounting
from apps.rag.exceptions import RagAccountingError


def test_stage_reservation_allows_only_one_terminal_call():
    calls = []
    accounting = RagStageAccounting(
        reserve=lambda user, tokens: SimpleNamespace(
            usage_id=7,
            reserved_tokens=tokens,
        ),
        finalize=lambda reservation, actual: calls.append(("finalize", actual)),
        refund=lambda reservation: calls.append(("refund", reservation.reserved_tokens)),
    )
    stage = accounting.reserve(object(), 100)

    stage.finalize(42)

    assert calls == [("finalize", 42)]
    assert stage.terminal_attempted is True
    with pytest.raises(RagAccountingError, match="already"):
        stage.refund()


@pytest.mark.parametrize("operation", ["finalize", "refund"])
def test_stage_reservation_wraps_terminal_failure_once(operation):
    calls = []

    def fail(*args):
        calls.append(operation)
        raise RuntimeError("ledger unavailable")

    accounting = RagStageAccounting(
        reserve=lambda user, tokens: SimpleNamespace(usage_id=7, reserved_tokens=tokens),
        finalize=fail if operation == "finalize" else lambda *args: None,
        refund=fail if operation == "refund" else lambda *args: None,
    )
    stage = accounting.reserve(object(), 100)

    with pytest.raises(RagAccountingError) as error:
        getattr(stage, operation)(42) if operation == "finalize" else stage.refund()

    assert isinstance(error.value.__cause__, RuntimeError)
    assert calls == [operation]
    assert stage.terminal_attempted is True


def test_reserve_errors_keep_the_account_domain_contract():
    expected = RuntimeError("reservation rejected")
    accounting = RagStageAccounting(
        reserve=lambda user, tokens: (_ for _ in ()).throw(expected),
    )

    with pytest.raises(RuntimeError) as error:
        accounting.reserve(object(), 100)

    assert error.value is expected
