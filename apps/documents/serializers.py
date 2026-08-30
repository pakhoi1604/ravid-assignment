from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from apps.documents.models import IngestionJob

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}
INVALID_FORMAT_ERROR = "Invalid file format. Only PDF, TXT, and Markdown files are allowed."
SUCCESS_MESSAGE = "Document successfully parsed, embedded, and indexed in vector storage."


class UploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, uploaded_file):
        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in ALLOWED_UPLOAD_EXTENSIONS:
            raise serializers.ValidationError(INVALID_FORMAT_ERROR)

        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if uploaded_file.size > max_size:
            raise serializers.ValidationError(
                f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB."
            )

        return uploaded_file


def format_status_response(job: IngestionJob) -> dict[str, str]:
    status = job.status
    if status == IngestionJob.Status.PENDING:
        status = IngestionJob.Status.PROCESSING

    response = {
        "task_id": str(job.task_id),
        "status": status,
    }

    if status == IngestionJob.Status.SUCCESS:
        response["message"] = SUCCESS_MESSAGE
    elif status == IngestionJob.Status.FAILURE:
        response["error"] = job.error or "Failed to parse document content."

    return response
