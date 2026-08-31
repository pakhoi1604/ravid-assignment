from django.contrib import admin

from apps.documents.models import Document, IngestionDispatch, IngestionGeneration, IngestionJob


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "owner",
        "original_filename",
        "content_type",
        "size_bytes",
        "active_generation",
        "created_at",
    )
    list_filter = ("content_type", "created_at")
    search_fields = ("public_id", "original_filename", "owner__username")
    readonly_fields = ("public_id", "active_generation", "created_at", "updated_at")


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = (
        "task_id",
        "document",
        "status",
        "generation",
        "attempt_count",
        "lease_expires_at",
        "failure_code",
        "started_at",
        "completed_at",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("task_id", "document__public_id", "document__original_filename")
    readonly_fields = (
        "task_id",
        "generation",
        "attempt_count",
        "lease_expires_at",
        "failure_code",
        "created_at",
        "updated_at",
    )


class ReadOnlyOperationalAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(IngestionGeneration)
class IngestionGenerationAdmin(ReadOnlyOperationalAdmin):
    list_display = (
        "document",
        "generation",
        "status",
        "expected_chunk_count",
        "observed_chunk_count",
        "cleanup_after",
        "cleanup_attempts",
        "failure_code",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("document__public_id", "generation")
    readonly_fields = (
        "document",
        "generation",
        "status",
        "expected_chunk_count",
        "observed_chunk_count",
        "cleanup_after",
        "cleanup_attempts",
        "failure_code",
        "created_at",
        "updated_at",
    )


@admin.register(IngestionDispatch)
class IngestionDispatchAdmin(ReadOnlyOperationalAdmin):
    list_display = (
        "job",
        "generation",
        "status",
        "attempts",
        "available_at",
        "claim_expires_at",
        "published_at",
        "failure_code",
    )
    list_filter = ("status", "created_at")
    search_fields = ("job__task_id", "generation")
    readonly_fields = (
        "job",
        "generation",
        "status",
        "attempts",
        "available_at",
        "claim_token",
        "claim_expires_at",
        "published_at",
        "failure_code",
        "created_at",
        "updated_at",
    )
