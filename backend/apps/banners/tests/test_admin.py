"""
Тесты Admin-интерфейса Banner — Story 32.1

Покрытие:
- AC2: BannerAdmin list_filter по type
- AC2: Image обязательна для Marketing type
- AC2: target_url (cta_link) доступен в форме
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from apps.banners.admin import BannerAdmin
from apps.banners.factories import BannerFactory, generate_test_image
from apps.banners.models import Banner


@pytest.mark.django_db
class TestBannerAdminListFilter:
    """AC2: Sidebar filter by 'Type' is available."""

    def test_type_in_list_filter(self):
        """type присутствует в list_filter."""
        admin = BannerAdmin(Banner, AdminSite())
        assert "type" in admin.list_filter

    def test_type_in_list_display(self):
        """type отображается в list_display."""
        admin = BannerAdmin(Banner, AdminSite())
        assert "type" in admin.list_display


@pytest.mark.django_db
class TestBannerAdminFormValidation:
    """AC2: Image mandatory for Marketing type."""

    def test_marketing_banner_without_image_raises_error(self):
        """Создание Marketing баннера без image должно вызвать ValidationError."""
        banner = Banner(
            title="Test Marketing",
            subtitle="Test",
            cta_link="/test",
            type=Banner.BannerType.MARKETING,
            # image не указан
        )
        with pytest.raises(ValidationError) as exc_info:
            banner.full_clean()
        assert "image" in exc_info.value.message_dict

    def test_marketing_banner_with_image_passes(self):
        """Marketing баннер с image проходит валидацию."""
        banner = BannerFactory.build(type=Banner.BannerType.MARKETING)
        # build() не сохраняет, но image генерируется через factory
        # full_clean не должен бросить исключение
        banner.full_clean()

    def test_hero_banner_without_image_not_marketing_error(self):
        """Hero баннер без image НЕ получает ошибку о маркетинговых баннерах."""
        banner = Banner(
            title="Test Hero",
            subtitle="Test",
            cta_link="/test",
            type=Banner.BannerType.HERO,
        )
        with pytest.raises(ValidationError) as exc_info:
            banner.full_clean()
        # Ошибка image есть (поле обязательно), но не наша кастомная
        error_messages = str(exc_info.value)
        assert "маркетинговых" not in error_messages


@pytest.mark.django_db
class TestBannerAdminFieldsets:
    """AC2: target_url (cta_link) доступен для Marketing баннеров."""

    def test_cta_link_in_fieldsets(self):
        """cta_link (target_url) присутствует в fieldsets."""
        admin = BannerAdmin(Banner, AdminSite())
        all_fields = []
        for _, options in admin.fieldsets:
            all_fields.extend(options["fields"])
        assert "cta_link" in all_fields

    def test_type_in_fieldsets(self):
        """type присутствует в fieldsets."""
        admin = BannerAdmin(Banner, AdminSite())
        all_fields = []
        for _, options in admin.fieldsets:
            all_fields.extend(options["fields"])
        assert "type" in all_fields
