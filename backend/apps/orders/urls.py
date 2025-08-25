<<<<<<< HEAD

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet

app_name = 'orders'

router = DefaultRouter()
router.register(r'', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
=======
"""
URL маршруты для заказов
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet

# Router для ViewSets
router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="order")

app_name = "orders"

urlpatterns = [
    # Включаем router для всех ViewSets
    path("", include(router.urls)),
>>>>>>> 438d8f8b8c184e00582b93a9cd4f8fdded94036f
]
