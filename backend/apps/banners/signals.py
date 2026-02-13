"""
Сигналы для приложения banners — кэш-инвалидация

Story 32.1 AC3: Saving/deleting a banner invalidates the API cache
for that specific banner type (key pattern: banners:list:{type}:{role})
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Banner
from .services import invalidate_banner_cache


@receiver(post_save, sender=Banner)
def invalidate_banner_cache_on_save(
    sender: type[Banner], instance: Banner, **kwargs: Any
) -> None:
    """
    Инвалидирует кэш при сохранении баннера.

    AC3: cache key pattern banners:list:{type}:{role}
    """
    invalidate_banner_cache(instance.type)


@receiver(post_delete, sender=Banner)
def invalidate_banner_cache_on_delete(
    sender: type[Banner], instance: Banner, **kwargs: Any
) -> None:
    """
    Инвалидирует кэш при удалении баннера.

    AC3: cache key pattern banners:list:{type}:{role}
    """
    invalidate_banner_cache(instance.type)
