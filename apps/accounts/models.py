from django.conf import settings
from django.db import models
from django.db.models import Q


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INACTIVE,
    )
    daily_token_limit = models.PositiveIntegerField(default=20_000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(daily_token_limit__gt=0),
                name="accounts_subscription_positive_daily_limit",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} ({self.status})"


class DailyTokenUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_token_usages",
    )
    usage_date = models.DateField()
    used_tokens = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "usage_date"],
                name="accounts_unique_daily_token_usage",
            ),
            models.CheckConstraint(
                condition=Q(used_tokens__gte=0),
                name="accounts_daily_usage_nonnegative",
            ),
        ]
        indexes = [models.Index(fields=["user", "-usage_date"])]
        ordering = ["-usage_date"]

    def __str__(self) -> str:
        return f"{self.user} {self.usage_date}: {self.used_tokens}"
