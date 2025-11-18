"""
Тесты для subscribe/unsubscribe endpoints
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.common.models import Newsletter


@pytest.fixture
def api_client():
    """Фикстура для API клиента."""
    return APIClient()


@pytest.mark.django_db
class TestSubscribeEndpoint:
    """Тесты для POST /api/v1/subscribe endpoint."""

    def test_subscribe_success(self, api_client: APIClient):
        """Тест успешной подписки на рассылку."""
        url = reverse("common:subscribe")
        data = {"email": "newuser@example.com"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "Вы успешно подписались на рассылку"
        assert response.data["email"] == "newuser@example.com"

        # Проверяем создание записи в БД
        assert Newsletter.objects.filter(email="newuser@example.com").exists()
        subscription = Newsletter.objects.get(email="newuser@example.com")
        assert subscription.is_active is True

    def test_subscribe_duplicate_email(self, api_client: APIClient):
        """Тест подписки с уже существующим email."""
        # Создаем существующую подписку
        Newsletter.objects.create(email="existing@example.com", is_active=True)

        url = reverse("common:subscribe")
        data = {"email": "existing@example.com"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "уже подписан" in str(response.data["email"][0])

    def test_subscribe_reactivate_unsubscribed(self, api_client: APIClient):
        """Тест реактивации ранее отписавшегося email."""
        from django.utils import timezone

        # Создаем неактивную подписку
        Newsletter.objects.create(
            email="unsubscribed@example.com",
            is_active=False,
            unsubscribed_at=timezone.now(),
        )

        url = reverse("common:subscribe")
        data = {"email": "unsubscribed@example.com"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        # Проверяем реактивацию
        subscription = Newsletter.objects.get(email="unsubscribed@example.com")
        assert subscription.is_active is True
        assert subscription.unsubscribed_at is None

    def test_subscribe_invalid_email(self, api_client: APIClient):
        """Тест с невалидным email адресом."""
        url = reverse("common:subscribe")
        data = {"email": "invalid-email"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_subscribe_email_normalization(self, api_client: APIClient):
        """Тест нормализации email (lowercase)."""
        url = reverse("common:subscribe")
        data = {"email": "TestUser@EXAMPLE.COM"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        # Проверяем сохранение в lowercase
        subscription = Newsletter.objects.get(email="testuser@example.com")
        assert subscription.email == "testuser@example.com"


@pytest.mark.django_db
class TestUnsubscribeEndpoint:
    """Тесты для POST /api/v1/unsubscribe endpoint."""

    def test_unsubscribe_success(self, api_client: APIClient):
        """Тест успешной отписки от рассылки."""
        # Создаем активную подписку
        Newsletter.objects.create(email="subscriber@example.com", is_active=True)

        url = reverse("common:unsubscribe")
        data = {"email": "subscriber@example.com"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Вы успешно отписались от рассылки"
        assert response.data["email"] == "subscriber@example.com"

        # Проверяем деактивацию в БД
        subscription = Newsletter.objects.get(email="subscriber@example.com")
        assert subscription.is_active is False
        assert subscription.unsubscribed_at is not None

    def test_unsubscribe_not_found(self, api_client: APIClient):
        """Тест отписки несуществующего email."""
        url = reverse("common:unsubscribe")
        data = {"email": "nonexistent@example.com"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "не найден" in str(response.data["email"][0])

    def test_unsubscribe_already_unsubscribed(self, api_client: APIClient):
        """Тест отписки уже отписанного email."""
        from django.utils import timezone

        # Создаем неактивную подписку
        Newsletter.objects.create(
            email="unsubscribed@example.com",
            is_active=False,
            unsubscribed_at=timezone.now(),
        )

        url = reverse("common:unsubscribe")
        data = {"email": "unsubscribed@example.com"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "уже отписан" in str(response.data["email"][0])

    def test_unsubscribe_invalid_email(self, api_client: APIClient):
        """Тест отписки с невалидным email."""
        url = reverse("common:unsubscribe")
        data = {"email": "invalid-email"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_unsubscribe_email_normalization(self, api_client: APIClient):
        """Тест нормализации email при отписке."""
        # Создаем подписку в lowercase
        Newsletter.objects.create(email="testuser@example.com", is_active=True)

        url = reverse("common:unsubscribe")
        data = {"email": "TestUser@EXAMPLE.COM"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Проверяем отписку
        subscription = Newsletter.objects.get(email="testuser@example.com")
        assert subscription.is_active is False
