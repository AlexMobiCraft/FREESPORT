"""
Views для аутентификации пользователей
"""

from django.contrib.auth import get_user_model
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

# User model is used in the code
from ..serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
    ValidateTokenSerializer,
)
from ..tokens import password_reset_token

User = get_user_model()


class UserRegistrationView(APIView):
    """
    Регистрация новых пользователей с ролями
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Регистрация пользователя",
        description=(
            "Создание нового пользователя с указанием роли "
            "(retail, wholesale_level1-3, trainer, federation_rep)"
        ),
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                description="Пользователь успешно зарегистрирован",
                examples=[
                    OpenApiExample(
                        name="successful_registration",
                        value={
                            "message": "Пользователь успешно зарегистрирован",
                            "user": {
                                "id": 1,
                                "email": "user@example.com",
                                "first_name": "Иван",
                                "last_name": "Петров",
                                "role": "retail",
                                "is_verified": True,
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Ошибки валидации",
                examples=[
                    OpenApiExample(
                        name="validation_errors",
                        value={
                            "email": ["Пользователь с таким email уже существует."],
                            "password_confirm": ["Пароли не совпадают."],
                        },
                    )
                ],
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
                examples=[
                    OpenApiExample(
                        name="successful_login",
                        value={
                            "access": ("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."),
                            "refresh": ("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."),
                            "user": {
                                "id": 1,
                                "email": "user@example.com",
                                "first_name": "Иван",
                                "last_name": "Петров",
                                "role": "retail",
                                "is_verified": True,
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Ошибки аутентификации",
                examples=[
                    OpenApiExample(
                        name="authentication_error",
                        value={"non_field_errors": ["Неверный email или пароль."]},
                    )
                ],
            ),
        },
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs):
        """Аутентификация пользователя"""
        serializer = UserLoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]

            # Создаем JWT токены
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)  # type: ignore[attr-defined]

            return Response(
                {
                    "access": access_token,
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


class PasswordResetRequestView(APIView):
    """
    Запрос на сброс пароля
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Запрос на сброс пароля",
        description=(
            "Отправка email с ссылкой для сброса пароля. "
            "Всегда возвращает 200 OK (security best practice)."
        ),
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="Email отправлен (если пользователь существует)",
                examples=[
                    OpenApiExample(
                        name="success",
                        value={"detail": "Password reset email sent."},
                    )
                ],
            ),
        },
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        """Обработка запроса на сброс пароля"""
        serializer = PasswordResetRequestSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data["email"]

            # Ищем пользователя (без раскрытия существования)
            try:
                user = User.objects.get(email=email, is_active=True)

                # Генерируем uid и token
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = password_reset_token.make_token(user)

                # TODO: В production здесь должна быть отправка email
                # Для разработки - логируем в консоль
                reset_url = (
                    f"http://localhost:3000/password-reset/confirm/{uid}/{token}/"
                )
                print(f"Password reset URL for {email}: {reset_url}")

            except User.DoesNotExist:
                # Не раскрываем информацию о существовании пользователя
                pass

            # Всегда возвращаем успех (security best practice)
            return Response(
                {"detail": "Password reset email sent."}, status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ValidateTokenView(APIView):
    """
    Валидация токена сброса пароля
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Валидация токена сброса пароля",
        description="Проверка валидности токена перед сбросом пароля",
        request=ValidateTokenSerializer,
        responses={
            200: OpenApiResponse(
                description="Токен валиден",
                examples=[
                    OpenApiExample(
                        name="valid_token",
                        value={"valid": True},
                    )
                ],
            ),
            404: OpenApiResponse(
                description="Токен не найден",
                examples=[
                    OpenApiExample(
                        name="invalid_token",
                        value={"detail": "Invalid token"},
                    )
                ],
            ),
            410: OpenApiResponse(
                description="Токен истёк",
                examples=[
                    OpenApiExample(
                        name="expired_token",
                        value={"detail": "Token expired"},
                    )
                ],
            ),
        },
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        """Валидация токена"""
        serializer = ValidateTokenSerializer(data=request.data)

        if serializer.is_valid():
            uid = serializer.validated_data["uid"]
            token = serializer.validated_data["token"]

            try:
                # Декодируем uid
                user_id = force_str(urlsafe_base64_decode(uid))
                user = User.objects.get(pk=user_id, is_active=True)

                # Проверяем токен
                if password_reset_token.check_token(user, token):
                    return Response({"valid": True}, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"detail": "Token expired"}, status=status.HTTP_410_GONE
                    )

            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return Response(
                    {"detail": "Invalid token"}, status=status.HTTP_404_NOT_FOUND
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """
    Подтверждение сброса пароля
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Подтверждение сброса пароля",
        description="Установка нового пароля после валидации токена",
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(
                description="Пароль успешно изменён",
                examples=[
                    OpenApiExample(
                        name="success",
                        value={"detail": "Password has been reset successfully."},
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Ошибки валидации",
                examples=[
                    OpenApiExample(
                        name="validation_error",
                        value={"new_password": ["Password is too weak"]},
                    )
                ],
            ),
            404: OpenApiResponse(
                description="Токен не найден",
                examples=[
                    OpenApiExample(
                        name="invalid_token",
                        value={"detail": "Invalid token"},
                    )
                ],
            ),
            410: OpenApiResponse(
                description="Токен истёк",
                examples=[
                    OpenApiExample(
                        name="expired_token",
                        value={"detail": "Token expired"},
                    )
                ],
            ),
        },
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        """Подтверждение сброса пароля"""
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if serializer.is_valid():
            uid = serializer.validated_data["uid"]
            token = serializer.validated_data["token"]
            new_password = serializer.validated_data["new_password"]

            try:
                # Декодируем uid
                user_id = force_str(urlsafe_base64_decode(uid))
                user = User.objects.get(pk=user_id, is_active=True)

                # Проверяем токен
                if not password_reset_token.check_token(user, token):
                    return Response(
                        {"detail": "Token expired"}, status=status.HTTP_410_GONE
                    )

                # Устанавливаем новый пароль
                user.set_password(new_password)
                user.save(update_fields=["password"])

                return Response(
                    {"detail": "Password has been reset successfully."},
                    status=status.HTTP_200_OK,
                )

            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return Response(
                    {"detail": "Invalid token"}, status=status.HTTP_404_NOT_FOUND
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
