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
