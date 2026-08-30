from django.urls import path

from apps.rag.views import ChatQueryView

urlpatterns = [path("query/", ChatQueryView.as_view(), name="chat-query")]
