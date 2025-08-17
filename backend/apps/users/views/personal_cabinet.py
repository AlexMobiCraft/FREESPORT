"""
Views для личного кабинета пользователя
"""
from rest_framework import status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from ..models import Address, Favorite
from ..serializers import (
    UserDashboardSerializer,
    AddressSerializer,
    FavoriteSerializer,
    FavoriteCreateSerializer,
    OrderHistorySerializer
)


class UserDashboardView(APIView):
    """
    Персональный дашборд пользователя
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Персональный дашборд",
        description="Получение агрегированной информации для личного кабинета пользователя",
        responses={200: UserDashboardSerializer},
        tags=["Users"]
    )
    def get(self, request):
        """Получение данных дашборда"""
        user = request.user
        
        # Базовые счетчики
        dashboard_data = {
            'user_info': user,
            'orders_count': 0,  # TODO: Будет реализовано после создания Order модели
            'favorites_count': user.favorites.count(),
            'addresses_count': user.addresses.count(),
        }
        
        # Дополнительная статистика для B2B пользователей
        if user.is_b2b_user:
            dashboard_data.update({
                'total_order_amount': 0,  # TODO: Временно 0, нужна Order модель
                'avg_order_amount': 0,    # TODO: Временно 0, нужна Order модель
                'verification_status': 'verified' if user.is_verified else 'pending'
            })
        
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
        return Favorite.objects.filter(user=self.request.user).select_related('product')
    
    def get_serializer_class(self):
        if self.action == 'create':
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
        tags=["Users"]
    )
    def get(self, request):
        # TODO: заглушка до реализации Order модели
        return Response({
            'count': 0,
            'results': []
        }, status=status.HTTP_200_OK)