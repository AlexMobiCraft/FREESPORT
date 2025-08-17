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
    OrderCreateSerializer, OrderDetailSerializer, 
    OrderListSerializer
)


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления заказами
    
    create: Создать заказ из корзины (POST /orders/)
    retrieve: Получить детали заказа (GET /orders/{id}/)
    list: Список заказов пользователя (GET /orders/)
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Возвращаем только заказы текущего пользователя"""
        if self.request.user.is_authenticated:
            return Order.objects.filter(user=self.request.user)\
                .prefetch_related(
                    'items__product',
                    'items__product__brand',
                    'items__product__category'
                ).order_by('-created_at')
        
        # Для анонимных пользователей - пустой queryset
        return Order.objects.none()
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action == 'list':
            return OrderListSerializer
        return OrderDetailSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Получение детального вида заказа"""
        instance = self.get_object()
        
        # Проверяем права доступа к заказу
        if instance.user != request.user and not request.user.is_staff:
            return Response(
                {"detail": "У вас нет прав для просмотра этого заказа"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Создание заказа из корзины"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            order = serializer.save()
            return Response(
                serializer.to_representation(order),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": f"Ошибка создания заказа: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['patch'])
    def cancel(self, request, pk=None):
        """Отмена заказа"""
        order = self.get_object()
        
        # Проверяем права и возможность отмены
        if order.user != request.user and not request.user.is_staff:
            return Response(
                {"detail": "У вас нет прав для отмены этого заказа"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not order.can_be_cancelled:
            return Response(
                {"detail": f"Заказ в статусе '{order.get_status_display()}' не может быть отменен"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
