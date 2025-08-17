"""
URL маршруты для API управления пользователями
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    user_roles_view,
    UserDashboardView,
    AddressViewSet,
    FavoriteViewSet,
    OrderHistoryView,
)

# Router для ViewSets
router = DefaultRouter()
router.register(r"users/addresses", AddressViewSet, basename="address")
router.register(r"users/favorites", FavoriteViewSet, basename="favorite")

app_name = "users"

urlpatterns = [
    # Аутентификация
    path("auth/register/", UserRegistrationView.as_view(), name="register"),
    path("auth/login/", UserLoginView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Профиль пользователя
    path("users/profile/", UserProfileView.as_view(), name="profile"),
    # Личный кабинет
    path("users/profile/dashboard/", UserDashboardView.as_view(), name="dashboard"),
    path("users/orders/", OrderHistoryView.as_view(), name="orders"),
    # Системная информация
    path("users/roles/", user_roles_view, name="roles"),
    # Включаем router для ViewSets
    path("", include(router.urls)),
]
