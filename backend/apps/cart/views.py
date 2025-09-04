"""
Views для корзины покупок
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from .models import Cart, CartItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    CartItemCreateSerializer,
    CartItemUpdateSerializer,
)
from apps.products.models import Product


class CartViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления корзиной пользователя
    """

    permission_classes = [permissions.AllowAny]  # Поддерживаем гостевые корзины
    serializer_class = CartSerializer

    def get_queryset(self):
        """Получить корзину текущего пользователя или гостя"""
        if self.request.user.is_authenticated:
            return Cart.objects.filter(user=self.request.user)
        else:
            # Для гостевых пользователей
            session_key = self.request.session.session_key
            if session_key:
                return Cart.objects.filter(session_key=session_key)
            return Cart.objects.none()

    def get_or_create_cart(self):
        """Получить или создать корзину для пользователя/гостя"""
        if self.request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=self.request.user)
        else:
            # Для гостевых пользователей
            if not self.request.session.session_key:
                self.request.session.create()
            session_key = self.request.session.session_key
            cart, created = Cart.objects.get_or_create(session_key=session_key)
        return cart

    @extend_schema(
        summary="Получить корзину",
        description="Получение содержимого корзины пользователя с ценами",
        tags=["Cart"],
    )
    def list(self, request, *args, **kwargs):
        """Получить содержимое корзины"""
        cart = self.get_or_create_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @extend_schema(
        summary="Очистить корзину",
        description="Удаление всех товаров из корзины",
        tags=["Cart"],
    )
    @action(detail=False, methods=["delete"])
    def clear(self, request):
        """Очистить корзину"""
        cart = self.get_or_create_cart()
        cart.clear()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления элементами корзины
    """

    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Получить элементы корзины текущего пользователя"""
        if self.request.user.is_authenticated:
            try:
                cart = Cart.objects.get(user=self.request.user)
                return CartItem.objects.filter(cart=cart)
            except Cart.DoesNotExist:
                return CartItem.objects.none()
        else:
            session_key = self.request.session.session_key
            if session_key:
                try:
                    cart = Cart.objects.get(session_key=session_key)
                    return CartItem.objects.filter(cart=cart)
                except Cart.DoesNotExist:
                    return CartItem.objects.none()
            return CartItem.objects.none()

    def get_serializer_class(self):
        """Выбор serializer в зависимости от действия"""
        if self.action == "create":
            return CartItemCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CartItemUpdateSerializer
        return CartItemSerializer

    def get_or_create_cart(self):
        """Получить или создать корзину для пользователя/гостя"""
        if self.request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=self.request.user)
        else:
            if not self.request.session.session_key:
                self.request.session.create()
            session_key = self.request.session.session_key
            cart, created = Cart.objects.get_or_create(session_key=session_key)
        return cart

    def perform_create(self, serializer):
        """Добавить товар в корзину с логикой объединения"""
        cart = self.get_or_create_cart()
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        # Проверяем, есть ли уже такой товар в корзине
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            # Если есть, увеличиваем количество
            cart_item.quantity += quantity
            cart_item.save()
            self.cart_item = cart_item
        except CartItem.DoesNotExist:
            # Если нет, создаем новый элемент
            self.cart_item = serializer.save(cart=cart)

    @extend_schema(
        summary="Список товаров в корзине",
        description="Получение списка всех товаров в корзине пользователя",
        responses={200: CartItemSerializer(many=True)},
        tags=["Cart Items"],
    )
    def list(self, request, *args, **kwargs):
        """Получить список товаров в корзине"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Детали товара в корзине",
        description="Получение детальной информации о товаре в корзине",
        responses={
            200: CartItemSerializer,
            404: OpenApiResponse(description="Товар в корзине не найден"),
        },
        tags=["Cart Items"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Получить детали товара в корзине"""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Добавить товар в корзину",
        description="Добавление товара в корзину с автоматическим объединением одинаковых товаров",
        tags=["Cart Items"],
    )
    def create(self, request, *args, **kwargs):
        """Добавить товар в корзину"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Возвращаем сериализованный cart_item
        response_serializer = CartItemSerializer(
            self.cart_item, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Обновить количество товара",
        description="Полное изменение товара в корзине",
        request=CartItemUpdateSerializer,
        responses={
            200: CartItemSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            404: OpenApiResponse(description="Товар в корзине не найден"),
        },
        tags=["Cart Items"],
    )
    def update(self, request, *args, **kwargs):
        """Обновить количество товара в корзине"""
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Частичное обновление товара",
        description="Частичное изменение количества товара в корзине",
        request=CartItemUpdateSerializer,
        responses={
            200: CartItemSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
            404: OpenApiResponse(description="Товар в корзине не найден"),
        },
        tags=["Cart Items"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Частичное обновление товара в корзине"""
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить товар из корзины",
        description="Удаление товара из корзины",
        tags=["Cart Items"],
    )
    def destroy(self, request, *args, **kwargs):
        """Удалить товар из корзины"""
        return super().destroy(request, *args, **kwargs)
