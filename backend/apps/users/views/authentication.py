"""
Views для аутентификации пользователей
"""
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import User
from ..serializers import UserLoginSerializer, UserRegistrationSerializer


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
    def post(self, request, *args, **kwargs):
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
        description="Аутентификация пользователя и получение JWT токенов",
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
                            "is_verified": True,
                        },
                    }
                },
            ),
            400: OpenApiResponse(
                description="Ошибки аутентификации",
                examples={
                    "application/json": {
                        "non_field_errors": ["Неверный email или пароль."]
                    }
                },
            ),
        },
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs):
        """Аутентификация пользователя"""
        serializer = UserLoginSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            user = serializer.validated_data["user"]

            # Создание JWT токенов
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
