"""
API Views для заказов FREESPORT
Поддерживает создание заказов из корзины и просмотр деталей
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Order, OrderItem
from .serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
)


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления заказами
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action == 'list':
            return OrderListSerializer
        return OrderDetailSerializer
    
    def get_queryset(self):
        """Получить заказы пользователя"""
        return Order.objects.filter(user=self.request.user).select_related(
            'user'
        ).prefetch_related('items__product').order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Создать новый заказ из корзины"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        # Возвращаем детализированную информацию о созданном заказе
        detail_serializer = OrderDetailSerializer(order, context={'request': request})
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Отменить заказ"""
        order = self.get_object()
        
        if order.status not in ['pending', 'confirmed']:
            return Response(
                {'error': 'Заказ не может быть отменен в текущем статусе'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)