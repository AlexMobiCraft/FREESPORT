"""
Тесты сервисного слоя баннеров — Story 32.1

Покрытие:
- 7-1: Cache key включает роль пользователя (предотвращение утечки)
- 7-2: Service layer functions (validate, build_cache_key, get_role_key, invalidate)
"""

from unittest.mock import MagicMock

import pytest
from django.core.cache import cache

from apps.banners.models import Banner
from apps.banners.services import (
    BANNER_CACHE_TTL,
    CACHE_KEY_PATTERN,
    _ALL_ROLE_KEYS,
    build_cache_key,
    cache_banner_response,
    get_cached_banners,
    get_role_key,
    invalidate_banner_cache,
    validate_banner_type,
)
from apps.users.models import User


class TestGetRoleKey:
    """7-1: get_role_key возвращает корректный ключ роли."""

    def test_none_user_returns_guest(self):
        assert get_role_key(None) == "guest"

    def test_anonymous_user_returns_guest(self):
        user = MagicMock()
        user.is_authenticated = False
        assert get_role_key(user) == "guest"

    def test_retail_user(self):
        user = MagicMock()
        user.is_authenticated = True
        user.role = "retail"
        assert get_role_key(user) == "retail"

    def test_wholesale_user(self):
        user = MagicMock()
        user.is_authenticated = True
        user.role = "wholesale_level1"
        assert get_role_key(user) == "wholesale_level1"

    def test_trainer_user(self):
        user = MagicMock()
        user.is_authenticated = True
        user.role = "trainer"
        assert get_role_key(user) == "trainer"

    def test_federation_user(self):
        user = MagicMock()
        user.is_authenticated = True
        user.role = "federation_rep"
        assert get_role_key(user) == "federation_rep"

    def test_admin_user(self):
        user = MagicMock()
        user.is_authenticated = True
        user.role = "admin"
        assert get_role_key(user) == "admin"

    def test_user_without_role_attr_defaults_to_retail(self):
        user = MagicMock(spec=["is_authenticated"])
        user.is_authenticated = True
        assert get_role_key(user) == "retail"


class TestValidateBannerType:
    """7-2: validate_banner_type корректно фильтрует типы."""

    def test_valid_hero(self):
        assert validate_banner_type("hero") == "hero"

    def test_valid_marketing(self):
        assert validate_banner_type("marketing") == "marketing"

    def test_invalid_type_returns_none(self):
        assert validate_banner_type("invalid") is None

    def test_none_returns_none(self):
        assert validate_banner_type(None) is None

    def test_empty_string_returns_none(self):
        assert validate_banner_type("") is None


class TestBuildCacheKey:
    """7-1: Ключ кеша включает тип и роль."""

    def test_hero_guest(self):
        assert build_cache_key("hero", "guest") == "banners:list:hero:guest"

    def test_marketing_wholesale(self):
        assert build_cache_key("marketing", "wholesale_level1") == "banners:list:marketing:wholesale_level1"

    def test_all_types_guest(self):
        assert build_cache_key(None, "guest") == "banners:list:all:guest"

    def test_all_types_retail(self):
        assert build_cache_key(None, "retail") == "banners:list:all:retail"

    def test_different_roles_produce_different_keys(self):
        """Разные роли дают разные ключи — критично для изоляции."""
        key_guest = build_cache_key("hero", "guest")
        key_wholesale = build_cache_key("hero", "wholesale_level1")
        assert key_guest != key_wholesale


class TestCacheFunctions:
    """7-2: Cache get/set через сервисные функции."""

    def setup_method(self):
        cache.clear()

    def test_get_cached_banners_miss(self):
        assert get_cached_banners("banners:list:hero:guest") is None

    def test_cache_and_retrieve(self):
        data = [{"id": 1, "title": "Test"}]
        cache_banner_response("banners:list:hero:guest", data)
        assert get_cached_banners("banners:list:hero:guest") == data


@pytest.mark.django_db
class TestInvalidateBannerCache:
    """7-1/7-2: Инвалидация очищает ключи по всем ролям."""

    def setup_method(self):
        cache.clear()

    def test_invalidate_clears_typed_keys_for_all_roles(self):
        """Инвалидация hero очищает banners:list:hero:{role} для всех ролей."""
        for role in _ALL_ROLE_KEYS:
            cache.set(f"banners:list:hero:{role}", "data")

        invalidate_banner_cache("hero")

        for role in _ALL_ROLE_KEYS:
            assert cache.get(f"banners:list:hero:{role}") is None

    def test_invalidate_clears_all_keys_for_all_roles(self):
        """Инвалидация hero также очищает banners:list:all:{role}."""
        for role in _ALL_ROLE_KEYS:
            cache.set(f"banners:list:all:{role}", "data")

        invalidate_banner_cache("hero")

        for role in _ALL_ROLE_KEYS:
            assert cache.get(f"banners:list:all:{role}") is None

    def test_invalidate_hero_does_not_clear_marketing(self):
        """Инвалидация hero НЕ затрагивает marketing ключи."""
        for role in _ALL_ROLE_KEYS:
            cache.set(f"banners:list:marketing:{role}", "data")

        invalidate_banner_cache("hero")

        for role in _ALL_ROLE_KEYS:
            assert cache.get(f"banners:list:marketing:{role}") == "data"


class TestAllRoleKeysDerivedFromUserModel:
    """8-1: _ALL_ROLE_KEYS импортируется из User.ROLE_CHOICES, не хардкодится."""

    def test_all_role_choices_present(self):
        """Каждая роль из User.ROLE_CHOICES присутствует в _ALL_ROLE_KEYS."""
        for role_value, _ in User.ROLE_CHOICES:
            assert role_value in _ALL_ROLE_KEYS, f"Role '{role_value}' missing from _ALL_ROLE_KEYS"

    def test_guest_role_present(self):
        """'guest' присутствует в _ALL_ROLE_KEYS (не входит в ROLE_CHOICES)."""
        assert "guest" in _ALL_ROLE_KEYS

    def test_no_extra_roles(self):
        """_ALL_ROLE_KEYS содержит ровно ROLE_CHOICES + guest, без лишних."""
        expected = {role for role, _ in User.ROLE_CHOICES} | {"guest"}
        assert set(_ALL_ROLE_KEYS) == expected

    def test_stays_in_sync_with_user_model(self):
        """При добавлении роли в User.ROLE_CHOICES она автоматически появляется в _ALL_ROLE_KEYS."""
        role_choice_values = {role for role, _ in User.ROLE_CHOICES}
        all_role_set = set(_ALL_ROLE_KEYS) - {"guest"}
        assert all_role_set == role_choice_values


class TestCacheKeyPattern:
    """8-2: CACHE_KEY_PATTERN — константа для формирования ключей кеша."""

    def test_pattern_is_string(self):
        assert isinstance(CACHE_KEY_PATTERN, str)

    def test_pattern_contains_type_placeholder(self):
        assert "{type}" in CACHE_KEY_PATTERN

    def test_pattern_contains_role_placeholder(self):
        assert "{role}" in CACHE_KEY_PATTERN

    def test_build_cache_key_uses_pattern(self):
        """build_cache_key формирует ключ по CACHE_KEY_PATTERN."""
        key = build_cache_key("hero", "guest")
        expected = CACHE_KEY_PATTERN.format(type="hero", role="guest")
        assert key == expected

    def test_build_cache_key_none_type_uses_all(self):
        """При type=None подставляется 'all'."""
        key = build_cache_key(None, "retail")
        expected = CACHE_KEY_PATTERN.format(type="all", role="retail")
        assert key == expected
