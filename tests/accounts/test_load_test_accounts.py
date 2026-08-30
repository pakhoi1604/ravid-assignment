import json
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import DailyTokenUsage, Subscription


def write_accounts(path, accounts):
    normalized = [{"subscription_active": True, **account} for account in accounts]
    path.write_text(json.dumps({"accounts": normalized}), encoding="utf-8")


@pytest.mark.django_db
def test_load_test_accounts_creates_users_from_mock_data(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    accounts_path = tmp_path / "accounts.json"
    write_accounts(
        accounts_path,
        [
            {
                "username": "reviewer",
                "email": "reviewer@example.com",
                "password": "reviewer-password-123",
                "is_staff": False,
                "is_superuser": False,
            },
            {
                "username": "reviewer_alt",
                "email": "reviewer-alt@example.com",
                "password": "reviewer-alt-password-123",
                "is_active": False,
            },
        ],
    )

    stdout = StringIO()
    call_command("load_test_accounts", str(accounts_path), stdout=stdout)

    user_model = get_user_model()
    reviewer = user_model.objects.get(username="reviewer")
    reviewer_alt = user_model.objects.get(username="reviewer_alt")

    assert reviewer.email == "reviewer@example.com"
    assert reviewer.check_password("reviewer-password-123")
    assert reviewer.is_staff is False
    assert reviewer_alt.is_active is False
    assert reviewer_alt.is_staff is False
    assert reviewer_alt.is_superuser is False
    assert reviewer.subscription.status == Subscription.Status.ACTIVE
    assert reviewer_alt.subscription.status == Subscription.Status.ACTIVE
    assert reviewer.subscription.daily_token_limit == 20_000
    assert DailyTokenUsage.objects.count() == 0
    assert "2 created, 0 updated" in stdout.getvalue()


@pytest.mark.django_db
def test_load_test_accounts_is_idempotent_and_updates_existing_users(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    accounts_path = tmp_path / "accounts.json"
    write_accounts(
        accounts_path,
        [
            {
                "username": "reviewer",
                "email": "first@example.com",
                "password": "first-password-123",
            }
        ],
    )
    call_command("load_test_accounts", str(accounts_path))

    write_accounts(
        accounts_path,
        [
            {
                "username": "reviewer",
                "email": "second@example.com",
                "password": "second-password-123",
                "subscription_active": False,
                "daily_token_limit": 12_345,
            }
        ],
    )
    stdout = StringIO()
    call_command("load_test_accounts", str(accounts_path), stdout=stdout)

    user_model = get_user_model()
    reviewer = user_model.objects.get(username="reviewer")

    assert user_model.objects.filter(username="reviewer").count() == 1
    assert reviewer.email == "second@example.com"
    assert reviewer.check_password("second-password-123")
    assert Subscription.objects.filter(user=reviewer).count() == 1
    assert reviewer.subscription.status == Subscription.Status.INACTIVE
    assert reviewer.subscription.daily_token_limit == 12_345
    assert DailyTokenUsage.objects.count() == 0
    assert "0 created, 1 updated" in stdout.getvalue()


@pytest.mark.django_db
def test_load_test_accounts_rolls_back_all_users_on_subscription_failure(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    accounts_path = tmp_path / "accounts.json"
    write_accounts(
        accounts_path,
        [
            {"username": "first", "password": "first-password-123"},
            {"username": "second", "password": "second-password-123"},
        ],
    )
    original_update_or_create = Subscription.objects.update_or_create

    def fail_second_subscription(*args, **kwargs):
        if kwargs["user"].username == "second":
            raise RuntimeError("simulated subscription persistence failure")
        return original_update_or_create(*args, **kwargs)

    monkeypatch.setattr(
        Subscription.objects,
        "update_or_create",
        fail_second_subscription,
    )

    with pytest.raises(RuntimeError, match="simulated subscription persistence failure"):
        call_command("load_test_accounts", str(accounts_path))

    assert get_user_model().objects.count() == 0
    assert Subscription.objects.count() == 0


def test_load_test_accounts_rejects_missing_mock_data_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    with pytest.raises(CommandError, match="Test account mock data not found"):
        call_command("load_test_accounts", str(tmp_path / "missing.json"))


def test_load_test_accounts_rejects_missing_password(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    accounts_path = tmp_path / "accounts.json"
    write_accounts(accounts_path, [{"username": "reviewer"}])

    with pytest.raises(CommandError, match="missing password"):
        call_command("load_test_accounts", str(accounts_path))


def test_load_test_accounts_requires_explicit_seed_permission(tmp_path):
    accounts_path = tmp_path / "accounts.json"
    write_accounts(
        accounts_path,
        [
            {
                "username": "reviewer",
                "password": "reviewer-password-123",
            }
        ],
    )

    with pytest.raises(CommandError, match="Refusing to load test accounts"):
        call_command("load_test_accounts", str(accounts_path))


def test_load_test_accounts_rejects_boolean_strings(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    accounts_path = tmp_path / "accounts.json"
    write_accounts(
        accounts_path,
        [
            {
                "username": "reviewer",
                "password": "reviewer-password-123",
                "is_staff": "false",
            }
        ],
    )

    with pytest.raises(CommandError, match="is_staff must be a boolean"):
        call_command("load_test_accounts", str(accounts_path))


def test_load_test_accounts_rejects_privileged_accounts(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    accounts_path = tmp_path / "accounts.json"
    write_accounts(
        accounts_path,
        [
            {
                "username": "admin",
                "password": "admin-password-123",
                "is_superuser": True,
            }
        ],
    )

    with pytest.raises(CommandError, match="must not be privileged"):
        call_command("load_test_accounts", str(accounts_path))


def test_load_test_accounts_requires_explicit_subscription_state(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    accounts_path = tmp_path / "accounts.json"
    accounts_path.write_text(
        json.dumps({"accounts": [{"username": "reviewer", "password": "reviewer-password-123"}]}),
        encoding="utf-8",
    )

    with pytest.raises(CommandError, match="subscription_active must be a boolean"):
        call_command("load_test_accounts", str(accounts_path))


def test_load_test_accounts_rejects_invalid_daily_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    accounts_path = tmp_path / "accounts.json"
    write_accounts(
        accounts_path,
        [
            {
                "username": "reviewer",
                "password": "reviewer-password-123",
                "daily_token_limit": 0,
            }
        ],
    )

    with pytest.raises(CommandError, match="daily_token_limit must be a positive integer"):
        call_command("load_test_accounts", str(accounts_path))
