"""
Views для API управления пользователями
"""
from drf_spectacular.openapi import OpenApiExample
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Address, Favorite, User
from .serializers import (
    AddressSerializer,
    FavoriteCreateSerializer,
    FavoriteSerializer,
    OrderHistorySerializer,
    UserDashboardSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)


class UserRegistrationView(APIView):
    """
    Регистрация новых пользователей с ролями
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Регистрация пользователя",
        description="Создание нового пользователя с указанием роли (retail, wholesale_level1-3, trainer, federation_rep)",
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                description="Пользователь успешно зарегистрирован",
                examples={
                    "application/json": {
                        "message": "Пользователь успешно зарегистрирован",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "first_name": "Иван",
                            "last_name": "Петров",
                            "role": "retail",
                            "is_verified": True,
                        },
                    }
                },
            ),
            400: OpenApiResponse(
                description="Ошибки валидации",
                examples={
                    "application/json": {
                        "email": ["Пользователь с таким email уже существует."],
                        "password_confirm": ["Пароли не совпадают."],
                    }
                },
            ),
        },
        tags=["Authentication"],
    )
    def post(self, request):
        """Создание нового пользователя"""
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                {
                    "message": "Пользователь успешно зарегистрирован",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role,
                        "is_verified": user.is_verified,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """
    Аутентификация пользователей с JWT токенами
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Вход пользователя",
        description="Аутентификация пользователя и получение JWT access/refresh токенов",
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(
                description="Успешная аутентификация",
                examples={
                    "application/json": {
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "first_name": "Иван",
                            "last_name": "Петров",
                            "role": "retail",
                        },
                    }
                },
            ),
            400: OpenApiResponse(
                description="Ошибка аутентификации",
                examples={
                    "application/json": {
                        "non_field_errors": ["Неверный email или пароль."]
                    }
                },
            ),
        },
        tags=["Authentication"],
    )
    def post(self, request):
        """Аутентификация пользователя"""
        serializer = UserLoginSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            user = serializer.validated_data["user"]

            # Генерируем JWT токены
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role,
                        "is_verified": user.is_verified,
                    },
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Обновление access токена",
    description="Обновление access токена с использованием refresh токена",
    request={
        "application/json": {"refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}
    },
    responses={
        200: OpenApiResponse(
            description="Токен успешно обновлен",
            examples={
                "application/json": {
                    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                }
            },
        ),
        401: OpenApiResponse(
            description="Неверный refresh токен",
            examples={
                "application/json": {
                    "detail": "Token is invalid or expired",
                    "code": "token_not_valid",
                }
            },
        ),
    },
    tags=["Authentication"],
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def refresh_token_view(request):
    """
    Обновление access токена
    Этот view будет переопределен в URLs с помощью TokenRefreshView из simplejwt
    """
    pass


class UserProfileView(RetrieveUpdateAPIView):
    """
    Просмотр и обновление профиля пользователя
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Возвращает профиль текущего пользователя"""
        return self.request.user

    @extend_schema(
        summary="Получить профиль пользователя",
        description="Получение профиля текущего аутентифицированного пользователя",
        responses={
            200: UserProfileSerializer,
            401: OpenApiResponse(
                description="Пользователь не аутентифицирован",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                },
            ),
        },
        tags=["Users"],
    )
    def get(self, request, *args, **kwargs):
        """Получение профиля пользователя"""
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Обновить профиль пользователя",
        description="Частичное обновление профиля пользователя (PATCH)",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(
                description="Ошибки валидации",
                examples={
                    "application/json": {
                        "tax_id": ["ИНН должен содержать 10 или 12 цифр."]
                    }
                },
            ),
            401: OpenApiResponse(description="Пользователь не аутентифицирован"),
        },
        tags=["Users"],
    )
    def patch(self, request, *args, **kwargs):
        """Обновление профиля пользователя"""
        return super().patch(request, *args, **kwargs)


@extend_schema(
    summary="Информация о ролях пользователей",
    description="Получение списка доступных ролей пользователей в системе",
    responses={
        200: OpenApiResponse(
            description="Список ролей пользователей",
            examples={
                "application/json": {
                    "roles": [
                        {"key": "retail", "display": "Розничный покупатель"},
                        {"key": "wholesale_level1", "display": "Оптовик уровень 1"},
                        {"key": "wholesale_level2", "display": "Оптовик уровень 2"},
                        {"key": "wholesale_level3", "display": "Оптовик уровень 3"},
                        {"key": "trainer", "display": "Тренер/Фитнес-клуб"},
                        {"key": "federation_rep", "display": "Представитель федерации"},
                    ]
                }
            },
        )
    },
    tags=["Users"],
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def user_roles_view(request):
    """
    Возвращает список доступных ролей пользователей
    """
    # Исключаем роль admin из публичного API
    public_roles = [choice for choice in User.ROLE_CHOICES if choice[0] != "admin"]

    roles_data = [{"key": role[0], "display": role[1]} for role in public_roles]

    return Response({"roles": roles_data}, status=status.HTTP_200_OK)


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
        dashboard_data = {
            "user_info": user,
            "orders_count": 0,  # TODO: Будет реализовано после создания Order модели
            "favorites_count": user.favorites.count(),
            "addresses_count": user.addresses.count(),
        }

        # Дополнительная статистика для B2B пользователей
        if user.is_b2b_user:
            dashboard_data.update(
                {
                    "total_order_amount": 0,  # TODO: Временно 0, нужна Order модель
                    "avg_order_amount": 0,  # TODO: Временно 0, нужна Order модель
                    "verification_status": "verified"
                    if user.is_verified
                    else "pending",
                }
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
