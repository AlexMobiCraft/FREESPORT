"""
Сигналы для приложения banners — кэш-инвалидация

Story 32.1 AC3: Saving/deleting a banner invalidates the API cache
for that specific banner type (key pattern: banners:list:{type})
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Banner

logger = logging.getLogger(__name__)


def _invalidate_banner_cache(banner_type: str) -> None:
    """
    Инвалидирует кэш списка баннеров для указанного типа.

    Args:
        banner_type: Тип баннера (hero, marketing)
    """
    cache_key = f"banners:list:{banner_type}"
    cache.delete(cache_key)
    logger.debug("Invalidated banner cache: %s", cache_key)


@receiver(post_save, sender=Banner)
def invalidate_banner_cache_on_save(
    sender: type[Banner], instance: Banner, **kwargs: Any
) -> None:
    """
    Инвалидирует кэш при сохранении баннера.

    AC3: cache key pattern banners:list:{type}
    """
    _invalidate_banner_cache(instance.type)


@receiver(post_delete, sender=Banner)
def invalidate_banner_cache_on_delete(
    sender: type[Banner], instance: Banner, **kwargs: Any
) -> None:
    """
    Инвалидирует кэш при удалении баннера.

    AC3: cache key pattern banners:list:{type}
    """
    _invalidate_banner_cache(instance.type)
