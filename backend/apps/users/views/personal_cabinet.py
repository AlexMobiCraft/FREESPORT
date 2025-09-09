"""
Views для личного кабинета пользователя
"""
from dataclasses import dataclass

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Address, Favorite, User
from ..serializers import (
    AddressSerializer,
    FavoriteCreateSerializer,
    FavoriteSerializer,
    OrderHistorySerializer,
    UserDashboardSerializer,
)


@dataclass
class DashboardData:
    user_info: User
    orders_count: int
    favorites_count: int
    addresses_count: int
    total_order_amount: float | None = None
    avg_order_amount: float | None = None
    verification_status: str | None = None


class UserDashboardView(APIView):
    """
    Персональный дашборд пользователя
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Персональный дашборд",
        description="Получение агрегированной информации для личного кабинета пользователя",
        responses={200: UserDashboardSerializer},
        tags=["Users"],
    )
    def get(self, request):
        """Получение данных дашборда"""
        user = request.user

        # Базовые счетчики
        orders_count = 0  # TODO: Будет реализовано после создания Order модели
        favorites_count = user.favorites.count()
        addresses_count = user.addresses.count()

        # Дополнительная статистика для B2B пользователей
        total_order_amount = None
        avg_order_amount = None
        verification_status = None
        if user.is_b2b_user:
            total_order_amount = 0  # TODO: Временно 0, нужна Order модель
            avg_order_amount = 0  # TODO: Временно 0, нужна Order модель
            verification_status = "verified" if user.is_verified else "pending"

        dashboard_data = DashboardData(
            user_info=user,
            orders_count=orders_count,
            favorites_count=favorites_count,
            addresses_count=addresses_count,
            total_order_amount=total_order_amount,
            avg_order_amount=avg_order_amount,
            verification_status=verification_status,
        )

        serializer = UserDashboardSerializer(dashboard_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddressViewSet(viewsets.ModelViewSet):
    """ViewSet для управления адресами пользователя"""

    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(tags=["Users"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Users"])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=["Users"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=["Users"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(tags=["Users"])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(tags=["Users"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class FavoriteViewSet(viewsets.ModelViewSet):
    """ViewSet для управления избранными товарами"""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related("product")

    def get_serializer_class(self):
        if self.action == "create":
            return FavoriteCreateSerializer
        return FavoriteSerializer

    @extend_schema(tags=["Users"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Users"])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=["Users"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class OrderHistoryView(APIView):
    """История заказов пользователя (TODO: заглушка)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="История заказов",
        description="Получение истории заказов пользователя",
        responses={200: OrderHistorySerializer(many=True)},
        tags=["Users"],
    )
    def get(self, request):
        # TODO: заглушка до реализации Order модели
        return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)
