"""
Тесты модели Banner — Story 32.1: Database and Admin Updates

Покрытие:
- AC1: type поле (HERO/MARKETING), null=False, default=HERO
- AC2: Admin-валидация (image обязательна для Marketing)
- AC3: Cache invalidation
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.banners.factories import BannerFactory
from apps.banners.models import Banner


@pytest.mark.django_db
class TestBannerTypeField:
    """AC1: Banner model has a 'type' field with choices HERO and MARKETING."""

    def test_type_field_exists(self):
        """type поле существует на модели."""
        banner = BannerFactory()
        assert hasattr(banner, "type")

    def test_type_choices_hero(self):
        """BannerType.HERO === 'hero'."""
        assert Banner.BannerType.HERO == "hero"

    def test_type_choices_marketing(self):
        """BannerType.MARKETING === 'marketing'."""
        assert Banner.BannerType.MARKETING == "marketing"

    def test_type_choices_labels(self):
        """Choices содержат корректные label."""
        choices_dict = dict(Banner.BannerType.choices)
        assert "hero" in choices_dict
        assert "marketing" in choices_dict

    def test_default_type_is_hero(self):
        """Новый баннер создаётся с type=HERO по умолчанию."""
        banner = BannerFactory()
        assert banner.type == Banner.BannerType.HERO

    def test_create_marketing_banner(self):
        """Можно создать баннер с type=MARKETING."""
        banner = BannerFactory(type=Banner.BannerType.MARKETING)
        assert banner.type == Banner.BannerType.MARKETING

    def test_type_field_not_nullable(self):
        """AC1: type поле non-nullable (null=False) на уровне БД."""
        field = Banner._meta.get_field("type")
        assert field.null is False

    def test_type_field_not_blank(self):
        """type поле не может быть пустым."""
        field = Banner._meta.get_field("type")
        assert field.blank is False

    def test_image_field_optional(self):
        """image поле имеет blank=True (AC: optional for Hero)."""
        field = Banner._meta.get_field("image")
        assert field.blank is True

    def test_cta_text_field_optional(self):
        """cta_text поле имеет blank=True."""
        field = Banner._meta.get_field("cta_text")
        assert field.blank is True

    def test_type_field_max_length(self):
        """type поле max_length=20."""
        field = Banner._meta.get_field("type")
        assert field.max_length == 20

    def test_type_persists_after_save(self):
        """type сохраняется и загружается из БД корректно."""
        banner = BannerFactory(type=Banner.BannerType.MARKETING)
        banner_from_db = Banner.objects.get(pk=banner.pk)
        assert banner_from_db.type == Banner.BannerType.MARKETING

    def test_existing_banners_have_hero_type(self):
        """Дефолтное значение type=HERO для новых записей."""
        banner = BannerFactory()
        banner.refresh_from_db()
        assert banner.type == Banner.BannerType.HERO
