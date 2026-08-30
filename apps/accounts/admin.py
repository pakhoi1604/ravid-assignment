from django.contrib import admin

from apps.accounts.models import DailyTokenUsage, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "daily_token_limit", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DailyTokenUsage)
class DailyTokenUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "usage_date", "used_tokens", "updated_at")
    list_filter = ("usage_date",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
