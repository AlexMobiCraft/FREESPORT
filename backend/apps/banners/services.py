"""
Сервисный слой для баннеров — кеширование, фильтрация, инвалидация.

Story 32.1 Task 7-2: Вынесение логики из view в service layer.
Story 32.1 Task 7-1: Cache key включает роль пользователя для предотвращения утечки данных.
Story 32.1 Task 8-1: _ALL_ROLE_KEYS импортируется из User.ROLE_CHOICES.
Story 32.1 Task 8-2: CACHE_KEY_PATTERN — константа паттерна ключа кеша.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.core.cache import cache
from django.db.models import QuerySet
from django.utils import timezone

from apps.users.models import User

from .models import Banner

logger = logging.getLogger(__name__)

BANNER_CACHE_TTL = 60 * 15  # 15 минут
MIN_CACHE_TTL = 10  # Минимальный TTL — 10 секунд (защита от cache churn)
CACHE_KEY_PATTERN = "banners:list:{type}:{role}"

# Все возможные роли для полной инвалидации кеша — синхронизировано с User.ROLE_CHOICES
_ALL_ROLE_KEYS = tuple(role for role, _ in User.ROLE_CHOICES) + ("guest",)

_VALID_BANNER_TYPES = frozenset(choice.value for choice in Banner.BannerType)


def get_role_key(user: Any) -> str:
    """
    Определяет ключ роли пользователя для кеша.

    Args:
        user: Объект пользователя или None/AnonymousUser для гостей.

    Returns:
        Строка роли: 'guest' для неавторизованных, иначе user.role.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return "guest"
    return getattr(user, "role", "retail")


def validate_banner_type(banner_type: Optional[str]) -> Optional[str]:
    """
    Валидирует тип баннера. Невалидные значения возвращаются как None.

    Args:
        banner_type: Значение query param ?type=

    Returns:
        Валидный тип баннера или None.
    """
    if banner_type and banner_type in _VALID_BANNER_TYPES:
        return banner_type
    return None


def build_cache_key(banner_type: Optional[str], role_key: str) -> str:
    """
    Строит ключ кеша с учётом типа баннера и роли пользователя.

    Формат: banners:list:{type}:{role} — предотвращает утечку данных
    между ролями (Task 7-1).

    Args:
        banner_type: Тип баннера или None для всех.
        role_key: Ключ роли пользователя.

    Returns:
        Строка ключа кеша.
    """
    type_part = banner_type or "all"
    return CACHE_KEY_PATTERN.format(type=type_part, role=role_key)


def get_cached_banners(cache_key: str) -> Any:
    """Получить закешированные данные баннеров. Возвращает None при промахе."""
    return cache.get(cache_key)


def get_active_banners_queryset(
    user: Any, banner_type: Optional[str] = None
) -> QuerySet[Banner]:
    """
    Получить отфильтрованный QuerySet активных баннеров.

    Args:
        user: Пользователь или None для гостей.
        banner_type: Фильтр по типу (уже валидированный).

    Returns:
        QuerySet с баннерами.
    """
    effective_user = user if user and getattr(user, "is_authenticated", False) else None
    queryset = Banner.get_for_user(effective_user)
    if banner_type:
        queryset = queryset.filter(type=banner_type)
    return queryset


def compute_cache_ttl(banner_type: Optional[str] = None) -> int:
    """
    Вычисляет TTL кеша с учётом ближайших временных границ баннеров.

    Предотвращает показ stale data при наступлении start_date/end_date.
    TTL = min(BANNER_CACHE_TTL, seconds_to_nearest_temporal_boundary).

    Args:
        banner_type: Тип баннера для фильтрации или None для всех.

    Returns:
        TTL в секундах (не менее MIN_CACHE_TTL).
    """
    now = timezone.now()
    nearest_seconds = BANNER_CACHE_TTL

    type_filter = {"type": banner_type} if banner_type else {}

    # Ближайший end_date текущих активных баннеров (истечёт раньше TTL)
    nearest_end = (
        Banner.objects.filter(
            is_active=True, end_date__isnull=False, end_date__gt=now, **type_filter
        )
        .order_by("end_date")
        .values_list("end_date", flat=True)
        .first()
    )
    if nearest_end:
        delta = int((nearest_end - now).total_seconds())
        if 0 < delta < nearest_seconds:
            nearest_seconds = delta

    # Ближайший start_date будущих баннеров (появится раньше TTL)
    nearest_start = (
        Banner.objects.filter(
            is_active=True, start_date__isnull=False, start_date__gt=now, **type_filter
        )
        .order_by("start_date")
        .values_list("start_date", flat=True)
        .first()
    )
    if nearest_start:
        delta = int((nearest_start - now).total_seconds())
        if 0 < delta < nearest_seconds:
            nearest_seconds = delta

    return max(nearest_seconds, MIN_CACHE_TTL)


def cache_banner_response(
    cache_key: str, data: Any, ttl: Optional[int] = None
) -> None:
    """Кеширует сериализованные данные баннеров."""
    cache.set(cache_key, data, ttl if ttl is not None else BANNER_CACHE_TTL)


def invalidate_banner_cache(banner_type: str) -> None:
    """
    Инвалидирует все ключи кеша для данного типа баннера по всем ролям.

    Вызывается из сигналов при save/delete баннера.

    Args:
        banner_type: Тип баннера (hero, marketing).
    """
    keys_to_delete = []
    for role_key in _ALL_ROLE_KEYS:
        keys_to_delete.append(build_cache_key(banner_type, role_key))
        keys_to_delete.append(build_cache_key(None, role_key))  # "all" ключ

    cache.delete_many(keys_to_delete)
    logger.debug(
        "Invalidated banner cache for type=%s across %d role keys",
        banner_type,
        len(_ALL_ROLE_KEYS),
    )
