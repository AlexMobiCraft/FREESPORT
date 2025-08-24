from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.conf import settings


@extend_schema(
    summary="Health Check",
    description="Проверка состояния API сервера",
    responses={
        200: OpenApiResponse(
            description="API работает корректно",
            examples={
                "application/json": {
                    "status": "healthy",
                    "version": "1.0.0",
                    "environment": "development",
                }
            },
        )
    },
    tags=["System"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Endpoint для проверки состояния API.
    Возвращает информацию о версии и окружении.
    """
    return Response(
        {
            "status": "healthy",
            "version": "1.0.0",
            "environment": getattr(settings, "ENVIRONMENT", "development"),
        },
        status=status.HTTP_200_OK,
    )
