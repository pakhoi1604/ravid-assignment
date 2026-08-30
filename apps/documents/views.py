from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document, IngestionJob
from apps.documents.serializers import UploadSerializer, format_status_response
from apps.documents.tasks import enqueue_ingestion


def first_error(serializer: UploadSerializer) -> str:
    errors = serializer.errors
    file_errors = errors.get("file")
    if isinstance(file_errors, list) and file_errors:
        return str(file_errors[0])
    return "Invalid upload request."


class DocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = UploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data["file"]
        with transaction.atomic():
            document = Document.objects.create(
                owner=request.user,
                original_filename=Path(uploaded_file.name).name,
                file=uploaded_file,
                content_type=getattr(uploaded_file, "content_type", "") or "",
                size_bytes=uploaded_file.size,
            )
            job = IngestionJob.objects.create(document=document)
            transaction.on_commit(lambda: enqueue_ingestion(job))

        return Response(
            {
                "message": "Document uploaded and ingestion started",
                "document_id": str(document.public_id),
                "task_id": str(job.task_id),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class DocumentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        task_id = request.query_params.get("task_id")
        if not task_id:
            return Response({"error": "task_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = IngestionJob.objects.select_related("document").get(
                task_id=task_id,
                document__owner=request.user,
            )
        except (ValidationError, ValueError, IngestionJob.DoesNotExist):
            return Response(
                {"error": "Ingestion task not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(format_status_response(job))
