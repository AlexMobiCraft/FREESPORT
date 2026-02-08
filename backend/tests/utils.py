"""
Утилиты для тестирования

Общие функции, используемые в тестах проекта FREESPORT.
"""

from __future__ import annotations

import time
import uuid

# Глобальный счетчик для обеспечения уникальности
_unique_counter = 0


def get_unique_suffix() -> str:
    """
    Генерирует абсолютно уникальный суффикс с глобальным счетчиком,
    временной меткой и UUID.

    Используется для создания уникальных имен в тестах,
    чтобы избежать конфликтов при параллельном выполнении.

    Returns:
        Уникальная строка вида: "{timestamp}-{counter}-{uuid_hex}"
    """
    global _unique_counter
    _unique_counter += 1
    return f"{int(time.time() * 1000)}-{_unique_counter}-{uuid.uuid4().hex[:6]}"


def reset_unique_counter() -> None:
    """
    Сбрасывает глобальный счетчик уникальности.

    Вызывается в conftest.py перед каждым тестом для изоляции.
    """
    global _unique_counter
    _unique_counter = 0


# ---------------------------------------------------------------------------
# 1C Exchange helpers (used by test_onec_export.py, test_onec_export_e2e.py, etc.)
# ---------------------------------------------------------------------------

import base64
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rest_framework.test import APIClient


def get_response_content(response) -> bytes:
    """
    Get content from HttpResponse or FileResponse.

    FileResponse uses streaming_content which must be joined.
    Regular HttpResponse uses .content directly.

    Args:
        response: Django HttpResponse or FileResponse

    Returns:
        Response body as bytes
    """
    if hasattr(response, "streaming_content"):
        return b"".join(response.streaming_content)
    return response.content


def parse_commerceml_response(response) -> ET.Element:
    """
    Parse CommerceML XML from response into ElementTree root.

    Handles both HttpResponse and FileResponse (streaming).

    Args:
        response: Django response with XML body

    Returns:
        Root Element of parsed XML
    """
    content = get_response_content(response).decode("utf-8")
    return ET.fromstring(content)


def perform_1c_checkauth(client: "APIClient", email: str, password: str) -> "APIClient":
    """
    Perform 1C checkauth and set session cookie on the client.

    1C exchange uses Basic Auth + session cookie — distinct from JWT.

    Args:
        client: APIClient instance
        email: User email for Basic Auth
        password: User password for Basic Auth

    Returns:
        Same APIClient with session cookie set

    Raises:
        AssertionError: If checkauth fails
    """
    auth_header = "Basic " + base64.b64encode(f"{email}:{password}".encode()).decode(
        "ascii"
    )
    response = client.get(
        "/api/integration/1c/exchange/",
        data={"mode": "checkauth"},
        HTTP_AUTHORIZATION=auth_header,
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert body.startswith("success"), f"checkauth failed: {body}"
    lines = body.replace("\r\n", "\n").split("\n")
    cookie_name = lines[1]
    cookie_value = lines[2]
    client.cookies[cookie_name] = cookie_value
    return client
