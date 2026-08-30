from django.contrib import admin

from apps.documents.models import Document, IngestionJob


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "owner",
        "original_filename",
        "content_type",
        "size_bytes",
        "created_at",
    )
    list_filter = ("content_type", "created_at")
    search_fields = ("public_id", "original_filename", "owner__username")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ("task_id", "document", "status", "started_at", "completed_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("task_id", "document__public_id", "document__original_filename")
    readonly_fields = ("task_id", "created_at", "updated_at")
