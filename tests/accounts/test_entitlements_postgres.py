from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection

from apps.accounts.entitlements import InsufficientCreditsError, reserve_daily_tokens
from apps.accounts.models import DailyTokenUsage, Subscription


@pytest.mark.django_db(transaction=True)
def test_concurrent_first_reservations_cannot_overspend_daily_limit():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row locking is required for this integration test.")

    user = get_user_model().objects.create_user(username="race-user", password="password-123")
    Subscription.objects.create(
        user=user,
        status=Subscription.Status.ACTIVE,
        daily_token_limit=10,
    )
    barrier = Barrier(2)

    def reserve_once():
        close_old_connections()
        thread_user = get_user_model().objects.get(pk=user.pk)
        barrier.wait(timeout=10)
        try:
            reserve_daily_tokens(thread_user, 7)
            return "reserved"
        except InsufficientCreditsError:
            return "rejected"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: reserve_once(), range(2)))

    assert sorted(results) == ["rejected", "reserved"]
    assert DailyTokenUsage.objects.get(user=user).used_tokens == 7
