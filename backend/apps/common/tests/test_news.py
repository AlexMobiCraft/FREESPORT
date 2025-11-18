"""
Тесты для news endpoint
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.common.models import News


@pytest.fixture
def api_client():
    """Фикстура для API клиента."""
    return APIClient()


@pytest.mark.django_db
class TestNewsListEndpoint:
    """Тесты для GET /api/v1/news endpoint."""

    @pytest.fixture
    def published_news(self):
        """Создание опубликованных новостей для тестов."""
        now = timezone.now()
        return [
            News.objects.create(
                title="Новость 1",
                slug="news-1",
                excerpt="Описание новости 1",
                is_published=True,
                published_at=now - timedelta(days=1),
            ),
            News.objects.create(
                title="Новость 2",
                slug="news-2",
                excerpt="Описание новости 2",
                is_published=True,
                published_at=now - timedelta(days=2),
            ),
            News.objects.create(
                title="Новость 3",
                slug="news-3",
                excerpt="Описание новости 3",
                is_published=True,
                published_at=now - timedelta(days=3),
            ),
        ]

    def test_get_news_list_success(self, api_client: APIClient, published_news):
        """Тест получения списка новостей."""
        url = reverse("common:news-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3
        assert len(response.data["results"]) == 3

        # Проверяем сортировку (новые первые)
        assert response.data["results"][0]["title"] == "Новость 1"
        assert response.data["results"][1]["title"] == "Новость 2"
        assert response.data["results"][2]["title"] == "Новость 3"

    def test_get_news_list_with_pagination(
        self, api_client: APIClient, published_news
    ):
        """Тест pagination для списка новостей."""
        url = reverse("common:news-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Проверяем, что pagination работает (есть поля для pagination)
        assert "results" in response.data
        assert "count" in response.data
        assert "next" in response.data
        assert "previous" in response.data

    def test_get_news_list_only_published(self, api_client: APIClient):
        """Тест фильтрации только опубликованных новостей."""
        now = timezone.now()

        # Опубликованная новость
        News.objects.create(
            title="Опубликованная",
            slug="published",
            excerpt="Описание",
            is_published=True,
            published_at=now - timedelta(days=1),
        )

        # Неопубликованная новость (draft)
        News.objects.create(
            title="Черновик",
            slug="draft",
            excerpt="Описание",
            is_published=False,
            published_at=now - timedelta(days=1),
        )

        url = reverse("common:news-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "Опубликованная"

    def test_get_news_list_exclude_future_news(self, api_client: APIClient):
        """Тест исключения новостей с будущей датой публикации."""
        now = timezone.now()

        # Прошлая новость
        News.objects.create(
            title="Прошлая новость",
            slug="past-news",
            excerpt="Описание",
            is_published=True,
            published_at=now - timedelta(days=1),
        )

        # Будущая новость
        News.objects.create(
            title="Будущая новость",
            slug="future-news",
            excerpt="Описание",
            is_published=True,
            published_at=now + timedelta(days=1),
        )

        url = reverse("common:news-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "Прошлая новость"
