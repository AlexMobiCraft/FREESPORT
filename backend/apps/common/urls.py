from django.urls import path

from . import views

app_name = "common"

urlpatterns = [
    path("health/", views.health_check, name="health-check"),
    # Monitoring endpoints
    path(
        "monitoring/metrics/operations/",
        views.operation_metrics,
        name="operation-metrics",
    ),
    path(
        "monitoring/metrics/business/", views.business_metrics, name="business-metrics"
    ),
    path(
        "monitoring/metrics/realtime/", views.realtime_metrics, name="realtime-metrics"
    ),
    path("monitoring/health/", views.system_health, name="system-health"),
]
