from django.urls import path

from apps.documents.views import DocumentStatusView, DocumentUploadView

urlpatterns = [
    path("upload/", DocumentUploadView.as_view(), name="document-upload"),
    path("status/", DocumentStatusView.as_view(), name="document-status"),
]
