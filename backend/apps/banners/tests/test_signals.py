"""
Тесты кэш-инвалидации баннеров — Story 32.1

Покрытие:
- AC3: Saving/deleting banner invalidates cache banners:list:{type}
"""

import pytest
from django.core.cache import cache

from apps.banners.factories import BannerFactory
from apps.banners.models import Banner


@pytest.mark.django_db
class TestBannerCacheInvalidation:
    """AC3: Cache invalidation on save/delete."""

    def test_save_hero_banner_invalidates_hero_cache(self):
        """Сохранение Hero баннера инвалидирует ключ banners:list:hero."""
        cache.set("banners:list:hero", "cached_data")
        BannerFactory(type=Banner.BannerType.HERO)
        assert cache.get("banners:list:hero") is None

    def test_save_marketing_banner_invalidates_marketing_cache(self):
        """Сохранение Marketing баннера инвалидирует ключ banners:list:marketing."""
        cache.set("banners:list:marketing", "cached_data")
        BannerFactory(type=Banner.BannerType.MARKETING)
        assert cache.get("banners:list:marketing") is None

    def test_save_hero_does_not_invalidate_marketing_cache(self):
        """Сохранение Hero баннера НЕ инвалидирует marketing кэш."""
        cache.set("banners:list:marketing", "cached_data")
        BannerFactory(type=Banner.BannerType.HERO)
        assert cache.get("banners:list:marketing") == "cached_data"

    def test_save_marketing_does_not_invalidate_hero_cache(self):
        """Сохранение Marketing баннера НЕ инвалидирует hero кэш."""
        cache.set("banners:list:hero", "cached_data")
        BannerFactory(type=Banner.BannerType.MARKETING)
        assert cache.get("banners:list:hero") == "cached_data"

    def test_delete_hero_banner_invalidates_hero_cache(self):
        """Удаление Hero баннера инвалидирует ключ banners:list:hero."""
        banner = BannerFactory(type=Banner.BannerType.HERO)
        cache.set("banners:list:hero", "cached_data")
        banner.delete()
        assert cache.get("banners:list:hero") is None

    def test_delete_marketing_banner_invalidates_marketing_cache(self):
        """Удаление Marketing баннера инвалидирует ключ banners:list:marketing."""
        banner = BannerFactory(type=Banner.BannerType.MARKETING)
        cache.set("banners:list:marketing", "cached_data")
        banner.delete()
        assert cache.get("banners:list:marketing") is None

    def test_update_banner_invalidates_cache(self):
        """Обновление баннера инвалидирует кэш его типа."""
        banner = BannerFactory(type=Banner.BannerType.HERO)
        cache.set("banners:list:hero", "cached_data")
        banner.title = "Updated Title"
        banner.save()
        assert cache.get("banners:list:hero") is None
