"""
Integration тесты для Logout API endpoint

Story 30.4: Тесты для Logout функциональности
AC: 2, 3, 5, 6 - Integration-тесты покрывают все сценарии, изолированы,
                проходят в Docker Compose, следуют pytest conventions

Testing Framework: pytest 7.4.3 + pytest-django 4.7.0
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from tests.conftest import get_unique_suffix

User = get_user_model()

pytestmark = pytest.mark.django_db


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def logout_api_client():
    """API клиент для тестов logout."""
    return APIClient()


@pytest.fixture
def create_test_user():
    """Фабрика для создания пользователей с уникальными данными.

    Returns:
        Callable: Функция для создания пользователя с переданными параметрами
    """

    def _create_user(**kwargs):
        email = kwargs.get("email", f"user_{get_unique_suffix()}@freesport.test")
        password = kwargs.get("password", "TestPassword123!")

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=kwargs.get("first_name", "Test"),
            last_name=kwargs.get("last_name", "User"),
            role=kwargs.get("role", "retail"),
            is_active=kwargs.get("is_active", True),
            verification_status=kwargs.get("verification_status", "verified"),
        )
        return user

    return _create_user


@pytest.fixture
def authenticated_user_with_tokens(create_test_user):
    """Создает пользователя и возвращает токены.

    Returns:
        dict: Словарь с user, access token, refresh token и refresh объектом
    """
    user = create_test_user()
    refresh = RefreshToken.for_user(user)

    return {
        "user": user,
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "refresh_obj": refresh,
    }


@pytest.fixture
def get_logout_url():
    """Возвращает URL для logout endpoint."""
    return reverse("users:logout")


@pytest.fixture
def get_refresh_url():
    """Возвращает URL для token refresh endpoint."""
    return reverse("users:token_refresh")


# =============================================================================
# Tests: Successful Logout (AC: 2)
# =============================================================================


@pytest.mark.integration
class TestLogoutAPISuccess:
    """Тесты успешного logout.

    Проверяют корректную работу logout endpoint при валидных данных.
    """

    def test_successful_logout_returns_204(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Успешный logout возвращает 204 No Content.

        Проверяет, что при валидном access токене в заголовке и
        валидном refresh токене в body возвращается статус 204.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": tokens["refresh"]},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""

    def test_token_added_to_blacklist(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Токен добавляется в blacklist после logout.

        Проверяет, что после успешного logout refresh токен
        записывается в таблицу BlacklistedToken.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        jti = tokens["refresh_obj"]["jti"]

        # Act
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": tokens["refresh"]},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Проверяем blacklist
        outstanding = OutstandingToken.objects.get(jti=jti)
        assert BlacklistedToken.objects.filter(token=outstanding).exists()

    def test_blacklisted_token_cannot_refresh(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
        get_refresh_url,
    ):
        """Blacklisted токен не может получить новый access токен.

        Проверяет, что после logout refresh токен больше не может
        использоваться для получения нового access токена.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act - Logout
        logout_api_client.post(
            get_logout_url,
            data={"refresh": tokens["refresh"]},
            format="json",
        )

        # Act - Попытка refresh
        logout_api_client.credentials()  # Убираем auth для refresh endpoint
        response = logout_api_client.post(
            get_refresh_url,
            data={"refresh": tokens["refresh"]},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_with_fresh_token(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Logout работает со свежесозданным токеном.

        Проверяет, что logout можно выполнить сразу после создания токенов.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act - logout сразу после создания токенов
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": tokens["refresh"]},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# Tests: Authentication Errors (AC: 2)
# =============================================================================


@pytest.mark.integration
class TestLogoutAPIAuthenticationErrors:
    """Тесты ошибок аутентификации.

    Проверяют корректную обработку запросов без валидной аутентификации.
    """

    def test_logout_without_auth_returns_401(
        self,
        logout_api_client,
        get_logout_url,
    ):
        """Logout без аутентификации возвращает 401.

        Проверяет, что запрос без заголовка Authorization отклоняется.
        """
        # Arrange - клиент без аутентификации

        # Act
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": "some-token"},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()

    def test_logout_with_invalid_bearer_token(
        self,
        logout_api_client,
        get_logout_url,
    ):
        """Logout с невалидным Bearer токеном возвращает 401.

        Проверяет, что невалидный JWT в заголовке отклоняется.
        """
        # Arrange
        logout_api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")

        # Act
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": "some-token"},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_with_malformed_auth_header(
        self,
        logout_api_client,
        get_logout_url,
    ):
        """Logout с некорректным заголовком возвращает 401.

        Проверяет, что заголовок без "Bearer " prefix отклоняется.
        """
        # Arrange
        logout_api_client.credentials(HTTP_AUTHORIZATION="InvalidFormat token")

        # Act
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": "some-token"},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Tests: Token Validation Errors (AC: 2)
# =============================================================================


@pytest.mark.integration
class TestLogoutAPITokenValidationErrors:
    """Тесты ошибок валидации токенов.

    Проверяют корректную обработку невалидных refresh токенов.
    """

    def test_logout_with_invalid_refresh_token(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Невалидный refresh токен возвращает 400.

        Проверяет, что некорректный JWT в теле запроса вызывает ошибку.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": "invalid-jwt-token"},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    def test_logout_with_already_blacklisted_token(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Уже blacklisted токен возвращает 400.

        Проверяет, что повторный logout с тем же токеном вызывает ошибку.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Blacklist токена
        logout_api_client.post(
            get_logout_url,
            data={"refresh": tokens["refresh"]},
            format="json",
        )

        # Act - повторный logout
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": tokens["refresh"]},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    def test_logout_with_malformed_jwt(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Некорректный JWT формат возвращает 400.

        Проверяет обработку строки, не соответствующей формату JWT.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": "not.a.jwt"},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_without_refresh_field(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Отсутствие поля refresh возвращает 400.

        Проверяет, что пустой body вызывает ошибку валидации сериализатора.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act
        response = logout_api_client.post(
            get_logout_url,
            data={},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "refresh" in response.json()

    def test_logout_with_access_token_instead_refresh(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Использование access token вместо refresh вызывает ошибку.

        Проверяет, что access токен отклоняется при попытке blacklist.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act - передаем access token вместо refresh
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": tokens["access"]},  # access вместо refresh!
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Tests: Edge Cases and Security (AC: 2)
# =============================================================================


@pytest.mark.integration
class TestLogoutAPIEdgeCases:
    """Тесты edge cases и security.

    Проверяют граничные случаи и безопасность logout endpoint.
    """

    def test_logout_own_token(
        self,
        logout_api_client,
        create_test_user,
        get_logout_url,
    ):
        """Пользователь может сделать logout своего токена.

        Проверяет базовый сценарий logout с собственным токеном.
        """
        # Arrange
        user = create_test_user()
        refresh = RefreshToken.for_user(user)

        logout_api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}"
        )

        # Act
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": str(refresh)},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_multiple_logouts_same_token(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Повторный logout того же токена возвращает ошибку.

        Проверяет, что нельзя дважды занести токен в blacklist.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # First logout
        first_response = logout_api_client.post(
            get_logout_url,
            data={"refresh": tokens["refresh"]},
            format="json",
        )
        assert first_response.status_code == status.HTTP_204_NO_CONTENT

        # Act - второй logout
        second_response = logout_api_client.post(
            get_logout_url,
            data={"refresh": tokens["refresh"]},
            format="json",
        )

        # Assert
        assert second_response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_method_not_allowed_get(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """GET запрос возвращает 405 Method Not Allowed."""
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act
        response = logout_api_client.get(get_logout_url)

        # Assert
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_logout_method_not_allowed_put(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """PUT запрос возвращает 405 Method Not Allowed."""
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act
        response = logout_api_client.put(
            get_logout_url,
            data={"refresh": tokens["refresh"]},
        )

        # Assert
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_logout_method_not_allowed_delete(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """DELETE запрос возвращает 405 Method Not Allowed."""
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act
        response = logout_api_client.delete(get_logout_url)

        # Assert
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_logout_with_very_long_token(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Токен с чрезмерной длиной обрабатывается корректно.

        Проверяет, что очень длинный токен не вызывает server error.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        long_token = "a" * 10000  # Очень длинный токен

        # Act
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": long_token},
            format="json",
        )

        # Assert - должен вернуть 400, а не 500
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_does_not_affect_access_token_immediately(
        self,
        logout_api_client,
        authenticated_user_with_tokens,
        get_logout_url,
    ):
        """Access токен остается валидным сразу после logout.

        Примечание: access токен short-lived и продолжает работать
        до истечения срока действия. Это expected behavior JWT.
        После logout нельзя получить НОВЫЙ access токен.
        """
        # Arrange
        tokens = authenticated_user_with_tokens
        logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Act - logout
        response = logout_api_client.post(
            get_logout_url,
            data={"refresh": tokens["refresh"]},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Assert - можем использовать тот же access токен для другого запроса
        # (хотя в реальности клиент должен удалить его после logout)
        profile_response = logout_api_client.get(reverse("users:profile"))
        # Access токен все еще валиден (не expired)
        assert profile_response.status_code == status.HTTP_200_OK
