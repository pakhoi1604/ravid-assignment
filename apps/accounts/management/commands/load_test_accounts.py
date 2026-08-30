import json
import os
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Subscription


class Command(BaseCommand):
    help = "Load local-only test accounts from mockdata/test-accounts.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            help="Optional path to a JSON file with an accounts list.",
        )

    def handle(self, *args, **options):
        if os.getenv("ALLOW_TEST_ACCOUNT_SEED") != "true":
            raise CommandError(
                "Refusing to load test accounts. Set ALLOW_TEST_ACCOUNT_SEED=true only for "
                "local or reviewer seeding."
            )

        path = Path(options["path"] or settings.BASE_DIR / "mockdata" / "test-accounts.json")
        accounts = load_accounts(path)

        user_model = get_user_model()
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for account in accounts:
                username = account["username"]
                defaults = {
                    "email": account.get("email", ""),
                    "is_staff": False,
                    "is_superuser": False,
                    "is_active": account.get("is_active", True),
                }
                user, created = user_model.objects.get_or_create(
                    username=username,
                    defaults=defaults,
                )

                for field, value in defaults.items():
                    setattr(user, field, value)
                user.set_password(account["password"])
                user.save()

                subscription_status = (
                    Subscription.Status.ACTIVE
                    if account["subscription_active"]
                    else Subscription.Status.INACTIVE
                )
                Subscription.objects.update_or_create(
                    user=user,
                    defaults={
                        "status": subscription_status,
                        "daily_token_limit": account.get(
                            "daily_token_limit",
                            settings.DEFAULT_DAILY_TOKEN_LIMIT,
                        ),
                    },
                )

                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Created test account: {username}"))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"Updated test account: {username}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {len(accounts)} test account(s): "
                f"{created_count} created, {updated_count} updated."
            )
        )


def load_accounts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise CommandError(f"Test account mock data not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CommandError(f"Invalid test account mock data JSON: {path}") from exc

    accounts = payload.get("accounts") if isinstance(payload, dict) else payload
    if not isinstance(accounts, list):
        raise CommandError("Test account mock data must be a list or an object with accounts.")

    for index, account in enumerate(accounts, start=1):
        if not isinstance(account, dict):
            raise CommandError(f"Test account #{index} must be an object.")
        username = account.get("username")
        password = account.get("password")
        email = account.get("email", "")
        if not isinstance(username, str) or not username:
            raise CommandError(f"Test account #{index} is missing username.")
        if not isinstance(password, str) or not password:
            raise CommandError(f"Test account #{index} is missing password.")
        if not isinstance(email, str):
            raise CommandError(f"Test account #{index} email must be a string.")
        for field in ("is_staff", "is_superuser", "is_active"):
            if field in account and not isinstance(account[field], bool):
                raise CommandError(f"Test account #{index} {field} must be a boolean.")
        if account.get("is_staff") or account.get("is_superuser"):
            raise CommandError(f"Test account #{index} must not be privileged.")
        if not isinstance(account.get("subscription_active"), bool):
            raise CommandError(f"Test account #{index} subscription_active must be a boolean.")
        daily_token_limit = account.get("daily_token_limit")
        if daily_token_limit is not None and (
            isinstance(daily_token_limit, bool)
            or not isinstance(daily_token_limit, int)
            or daily_token_limit <= 0
        ):
            raise CommandError(
                f"Test account #{index} daily_token_limit must be a positive integer."
            )

    return accounts
