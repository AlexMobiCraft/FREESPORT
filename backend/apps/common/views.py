"""Представления для общего приложения."""
from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.services import CustomerSyncMonitor


@extend_schema(
    summary="Health Check",
    description="Проверка состояния API сервера",
    responses={
        200: OpenApiResponse(
            description="API работает корректно",
            examples=[
                OpenApiExample(
                    "Successful Response",
                    value={
                        "status": "healthy",
                        "version": "1.0.0",
                        "environment": "development",
                    },
                    response_only=True,
                )
            ],
        )
    },
    tags=["System"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(_request):
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


# ============================================================================
# Monitoring Views
# ============================================================================


@extend_schema(
    summary="Получить метрики операций синхронизации",
    description=(
        "Возвращает метрики операций за указанный период "
        "(по умолчанию последние 24 часа)"
    ),
    parameters=[
        OpenApiParameter(
            name="start_date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Начало периода (ISO 8601 формат)",
            required=False,
        ),
        OpenApiParameter(
            name="end_date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Конец периода (ISO 8601 формат)",
            required=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Метрики операций успешно получены",
            examples=[
                OpenApiExample(
                    name="success_example",
                    value={
                        "total_operations": 1250,
                        "operations_by_type": {
                            "import_from_1c": 800,
                            "export_to_1c": 300,
                            "conflict_resolution": 150,
                        },
                        "success_count": 1180,
                        "error_count": 70,
                        "success_rate": 94.4,
                        "error_rate": 5.6,
                    },
                )
            ],
        ),
    },
    tags=["Monitoring"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def operation_metrics(request: Request) -> Response:
    """Получить метрики операций синхронизации."""
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    try:
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        else:
            start_date = timezone.now() - timedelta(hours=24)

        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        else:
            end_date = timezone.now()

        if start_date >= end_date:
            return Response(
                {"error": "start_date должна быть меньше " "end_date"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except ValueError as e:
        return Response(
            {"error": f"Некорректный формат даты: " f"{str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    monitor = CustomerSyncMonitor()
    metrics = monitor.get_operation_metrics(start_date, end_date)

    return Response(metrics, status=status.HTTP_200_OK)


@extend_schema(
    summary="Получить бизнес-метрики синхронизации",
    description="Возвращает бизнес-метрики за указанный период",
    parameters=[
        OpenApiParameter(
            name="start_date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Начало периода (ISO 8601 формат)",
            required=False,
        ),
        OpenApiParameter(
            name="end_date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Конец периода (ISO 8601 формат)",
            required=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Бизнес-метрики успешно получены",
            examples=[
                OpenApiExample(
                    name="success_example",
                    value={
                        "synced_customers_count": 450,
                        "conflicts_resolved": {"portal_registration": 120},
                        "auto_resolution_rate": 88.5,
                    },
                )
            ],
        ),
    },
    tags=["Monitoring"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def business_metrics(request: Request) -> Response:
    """Получить бизнес-метрики синхронизации."""
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    try:
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        else:
            start_date = timezone.now() - timedelta(hours=24)

        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        else:
            end_date = timezone.now()

        if start_date >= end_date:
            return Response(
                {"error": "start_date должна быть меньше end_date"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except ValueError as e:
        return Response(
            {"error": f"Некорректный формат даты: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    monitor = CustomerSyncMonitor()
    metrics = monitor.get_business_metrics(start_date, end_date)

    return Response(metrics, status=status.HTTP_200_OK)


@extend_schema(
    summary="Получить статус здоровья системы",
    description="Возвращает текущий статус всех компонентов системы интеграции",
    responses={
        200: OpenApiResponse(
            description="Статус системы успешно получен",
            examples=[
                OpenApiExample(
                    name="healthy_example",
                    value={
                        "is_healthy": True,
                        "components": {
                            "database": {"component": "database", "available": True},
                            "redis": {"component": "redis", "available": True},
                        },
                        "critical_issues": [],
                    },
                )
            ],
        ),
    },
    tags=["Monitoring"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def system_health(request: Request) -> Response:
    """Получить статус здоровья системы интеграции."""
    monitor = CustomerSyncMonitor()
    health_status = monitor.get_system_health()

    http_status = (
        status.HTTP_200_OK
        if health_status["is_healthy"]
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return Response(health_status, status=http_status)


@extend_schema(
    summary="Получить метрики в реальном времени",
    description="Возвращает метрики за последние 5 минут",
    responses={
        200: OpenApiResponse(
            description="Метрики в реальном времени получены",
            examples=[
                OpenApiExample(
                    name="realtime_example",
                    value={
                        "operations_last_5min": 45,
                        "errors_last_5min": 2,
                        "current_error_rate": 4.44,
                        "throughput_per_minute": 9.0,
                    },
                )
            ],
        ),
    },
    tags=["Monitoring"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def realtime_metrics(request: Request) -> Response:
    """Получить метрики в реальном времени (последние 5 минут)."""
    monitor = CustomerSyncMonitor()
    metrics = monitor.get_real_time_metrics()

    return Response(metrics, status=status.HTTP_200_OK)
