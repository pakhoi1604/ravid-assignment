from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.entitlements import InactiveSubscriptionError, InsufficientCreditsError
from apps.rag.exceptions import (
    RagAccountingError,
    RagConfigurationError,
    RagProviderError,
    RagRetrievalError,
)
from apps.rag.serializers import (
    ChatAnswerSerializer,
    ChatErrorSerializer,
    ChatQuerySerializer,
    first_error,
)
from apps.rag.services import RagService


class ChatQueryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChatQuerySerializer,
        responses={
            200: ChatAnswerSerializer,
            400: OpenApiResponse(response=ChatErrorSerializer),
            401: OpenApiResponse(description="Authentication credentials are required."),
            403: OpenApiResponse(response=ChatErrorSerializer),
            429: OpenApiResponse(response=ChatErrorSerializer),
            503: OpenApiResponse(response=ChatErrorSerializer),
        },
    )
    def post(self, request):
        serializer = ChatQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": first_error(serializer)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = RagService().answer_query(
                user=request.user,
                query=serializer.validated_data["query"],
                use_hyde=serializer.validated_data["use_hyde"],
            )
        except InactiveSubscriptionError:
            return Response(
                {"error": "Active subscription required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        except InsufficientCreditsError:
            return Response(
                {"error": "Insufficient daily token credits."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except RagConfigurationError:
            return Response(
                {"error": "LLM provider is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except (RagProviderError, RagRetrievalError):
            return Response(
                {"error": "Unable to generate answer right now."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except RagAccountingError:
            return Response(
                {"error": "Unable to generate answer right now."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(ChatAnswerSerializer(result).data, status=status.HTTP_200_OK)
