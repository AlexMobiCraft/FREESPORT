"""
Ссылка восстановления пароля обязана вести на публичный адрес сайта.

Story 36.3 (tech-debt #7): базовый адрес был захардкожен как
`http://localhost:3000`, поэтому на продакшене письмо сброса пароля уводило
получателя на его собственную машину — восстановить пароль было нельзя.
Тест закрывает регресс: адрес берётся из `settings.SITE_URL`, а путь остаётся
тем, который обслуживает фронт (`/password-reset/confirm/[uid]/[token]`).
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

PASSWORD_RESET_URL = "/api/v1/auth/password-reset/"
PROD_SITE_URL = "https://optisport.ru"


@pytest.fixture
def account() -> User:
    return User.objects.create_user(
        email=f"reset_link_{time.time_ns()}@example.com",
        password="StrongPassword123!",
        role="retail",
    )


def request_reset_link(account: User) -> str:
    """Запрашивает сброс и возвращает ссылку, ушедшую в задачу отправки письма."""
    with patch("apps.users.views.authentication.send_password_reset_email.delay") as send_email:
        response = APIClient().post(PASSWORD_RESET_URL, {"email": account.email}, format="json")

    assert response.status_code == status.HTTP_200_OK
    send_email.assert_called_once()
    return send_email.call_args.args[1]


def test_reset_link_host_comes_from_site_url(settings, account):
    """Хост ссылки — тот, что настроен в окружении, а не машина разработчика."""
    settings.SITE_URL = PROD_SITE_URL

    link = request_reset_link(account)

    assert link.startswith(f"{PROD_SITE_URL}/")
    assert "localhost" not in link


def test_reset_link_path_matches_frontend_route(settings, account):
    """
    Путь обязан совпасть с маршрутом фронта.

    Иначе смена хоста чинит письмо и ломает переход: страница
    `password-reset/confirm/[uid]/[token]` ждёт оба сегмента.
    """
    settings.SITE_URL = PROD_SITE_URL

    link = request_reset_link(account)

    uid = urlsafe_base64_encode(force_bytes(account.pk))
    prefix = f"{PROD_SITE_URL}/password-reset/confirm/{uid}/"
    assert link.startswith(prefix)
    assert link.endswith("/")
    assert link[len(prefix) : -1], "Токен в ссылке пуст"
