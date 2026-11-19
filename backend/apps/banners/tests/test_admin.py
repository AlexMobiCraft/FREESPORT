"""
Тесты Admin-интерфейса Banner — Story 32.1

Покрытие:
- AC2: BannerAdmin list_filter по type
- AC2: Image обязательна для Marketing type
- AC2: target_url (cta_link) доступен в форме
"""

import csv
import importlib
import io
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from django.apps import apps as django_apps
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, RequestFactory
from django.utils import timezone

from apps.banners.admin import BannerAdmin, BannerDailyStatAdmin, BannerRefFilter
from apps.banners.factories import AdvertisementBannerFactory, BannerFactory, generate_test_image
from apps.banners.models import Banner, BannerDailyStat
from apps.users.models import User
from apps.users.staff_roles import MANAGERS_GROUP, MARKETING_GROUP, SUPERVISORS_GROUP
from freesport.admin_site import marketing_site
from tests.conftest import get_unique_suffix

_roles_migration = importlib.import_module("apps.users.migrations.0023_staff_role_groups")
_stat_migration = importlib.import_module("apps.banners.migrations.0009_banner_daily_stat_permissions")

STATS_URL = "/marketing/banners/bannerdailystat/"
BANNERS_URL = "/marketing/banners/banner/"


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

    def test_hero_banner_without_image_is_valid(self):
        """Hero баннер без image теперь валиден (image blank=True)."""
        banner = Banner(
            title="Test Hero",
            subtitle="Test",
            cta_link="/test",
            type=Banner.BannerType.HERO,
        )
        # full_clean не должен бросать ошибку, т.к. image теперь blank=True
        banner.full_clean()


@pytest.mark.django_db
class TestBannerAdminFieldsets:
    """AC2: target_url (cta_link) доступен для Marketing баннеров."""

    def test_cta_link_in_fieldsets(self):
        """cta_link (target_url) присутствует в fieldsets."""
        admin = BannerAdmin(Banner, AdminSite())
        all_fields: list[str] = []
        for _, options in admin.fieldsets:
            all_fields.extend(cast(Any, options["fields"]))
        assert "cta_link" in all_fields

    def test_type_in_fieldsets(self):
        """type присутствует в fieldsets."""
        admin = BannerAdmin(Banner, AdminSite())
        all_fields: list[str] = []
        for _, options in admin.fieldsets:
            all_fields.extend(cast(Any, options["fields"]))
        assert "type" in all_fields


@pytest.mark.unit
class TestBannerAdminAdvertisementFields:
    """Fieldset «Маркировка рекламы» и видимость флага в списке."""

    def _all_fields(self) -> list[str]:
        admin = BannerAdmin(Banner, AdminSite())
        fields: list[str] = []
        for _, options in admin.fieldsets:
            fields.extend(cast(Any, options["fields"]))
        return fields

    @pytest.mark.parametrize("field", ["is_advertisement", "advertiser_name", "advertiser_inn", "erid"])
    def test_advertisement_field_in_fieldsets(self, field):
        """Все четыре поля маркировки доступны в форме админки."""
        assert field in self._all_fields()

    def test_advertisement_fieldset_present(self):
        """Отдельная секция «Маркировка рекламы» существует."""
        admin = BannerAdmin(Banner, AdminSite())
        titles = [title for title, _ in admin.fieldsets]
        assert "Маркировка рекламы" in titles

    def test_is_advertisement_visible_in_list(self):
        """Флаг с юридическими последствиями виден в списке, а не только в фильтре."""
        admin = BannerAdmin(Banner, AdminSite())
        assert "is_advertisement" in admin.list_display
        assert "is_advertisement" in admin.list_filter

    def test_advertiser_name_searchable(self):
        """По рекламодателю можно искать — иначе не найти его баннеры при проверке."""
        admin = BannerAdmin(Banner, AdminSite())
        assert "advertiser_name" in admin.search_fields


# ---------------------------------------------------------------------------
# Статистика показов и кликов для ОРД
# ---------------------------------------------------------------------------


def make_stat(banner: Banner | None = None, **fields: Any) -> BannerDailyStat:
    """Строка статистики; без баннера — как у удалённого (banner=NULL, снимок остаётся)."""
    defaults: dict[str, Any] = {
        "date": timezone.localdate(),
        "views": 0,
        "clicks": 0,
    }
    if banner is not None:
        defaults.update(
            banner=banner,
            banner_ref_id=banner.pk,
            banner_title=banner.title,
            erid=banner.erid if banner.is_advertisement else "",
            advertiser_name=banner.advertiser_name if banner.is_advertisement else "",
            advertiser_inn=banner.advertiser_inn if banner.is_advertisement else "",
        )
    defaults.update(fields)
    return BannerDailyStat.objects.create(**defaults)


def stat_admin() -> BannerDailyStatAdmin:
    return BannerDailyStatAdmin(BannerDailyStat, AdminSite())


def export_rows(queryset: Any) -> list[list[str]]:
    response = stat_admin().export_ord_csv(RequestFactory().get("/"), queryset)
    content = response.content.decode("utf-8")
    assert content.startswith("﻿")
    return list(csv.reader(io.StringIO(content[1:]), delimiter=";"))


@pytest.mark.django_db
class TestBannerAdminStatColumns:
    def _row(self, banner: Banner) -> Banner:
        request = RequestFactory().get("/")
        return BannerAdmin(Banner, AdminSite()).get_queryset(request).get(pk=banner.pk)

    def test_columns_in_list_display(self):
        admin = BannerAdmin(Banner, AdminSite())
        assert {"views_30d", "clicks_30d", "ctr_30d"} <= set(admin.list_display)

    def test_sums_last_thirty_days_only(self):
        banner = AdvertisementBannerFactory()
        today = timezone.localdate()
        make_stat(banner, date=today, views=10, clicks=1)
        make_stat(banner, date=today - timedelta(days=29), views=5, clicks=2)
        make_stat(banner, date=today - timedelta(days=30), views=1000, clicks=500)
        # Смена ERID — вторая строка того же дня, тоже в сумме.
        make_stat(banner, date=today, erid="2VfnxOTHER", views=5, clicks=0)

        row = self._row(banner)
        admin = BannerAdmin(Banner, AdminSite())

        assert (admin.views_30d(row), admin.clicks_30d(row)) == (20, 3)
        assert admin.ctr_30d(row) == "15,00 %"

    def test_ctr_without_views_is_dash(self):
        banner = BannerFactory()
        make_stat(banner, views=0, clicks=2)
        admin = BannerAdmin(Banner, AdminSite())

        row = self._row(banner)

        assert (admin.views_30d(row), admin.clicks_30d(row), admin.ctr_30d(row)) == (0, 2, "—")

    def test_banner_without_stats_has_zeros(self):
        banner = BannerFactory()
        admin = BannerAdmin(Banner, AdminSite())

        row = self._row(banner)

        assert (admin.views_30d(row), admin.clicks_30d(row), admin.ctr_30d(row)) == (0, 0, "—")

    def test_list_has_one_row_per_banner(self):
        banner = BannerFactory()
        for days in range(5):
            make_stat(banner, date=timezone.localdate() - timedelta(days=days), views=1)

        queryset = BannerAdmin(Banner, AdminSite()).get_queryset(RequestFactory().get("/"))

        assert queryset.filter(pk=banner.pk).count() == 1


@pytest.mark.django_db
class TestBannerDailyStatAdminReadOnly:
    def test_no_add_change_delete(self):
        admin = stat_admin()
        request = RequestFactory().get("/")
        stat = make_stat(BannerFactory(), views=1)

        assert admin.has_add_permission(request) is False
        assert admin.has_change_permission(request, stat) is False
        assert admin.has_delete_permission(request, stat) is False

    def test_list_config(self):
        admin = stat_admin()

        assert admin.date_hierarchy == "date"
        assert "export_ord_csv" in admin.actions
        assert len(admin.list_filter) == 2


@pytest.mark.django_db
class TestOrdCsvExport:
    def test_header_bom_and_delimiter(self):
        rows = export_rows(BannerDailyStat.objects.none())

        assert rows == [
            [
                "ERID",
                "Рекламодатель",
                "ИНН рекламодателя",
                "Баннер",
                "Начало периода",
                "Конец периода",
                "Показы",
                "Клики",
            ]
        ]

    def test_only_rows_with_erid(self):
        ad = AdvertisementBannerFactory(erid="2VfnxAD")
        plain = BannerFactory(type=Banner.BannerType.HERO)
        make_stat(ad, date=date(2026, 11, 3), views=7, clicks=1)
        make_stat(plain, date=date(2026, 11, 3), views=100, clicks=10)

        rows = export_rows(BannerDailyStat.objects.all())[1:]

        assert len(rows) == 1
        assert rows[0][0] == '="2VfnxAD"'

    def test_one_row_per_erid_and_banner_within_month(self):
        ad = AdvertisementBannerFactory(erid="2VfnxAD", title="Баннер А", advertiser_inn="7718933790")
        make_stat(ad, date=date(2026, 11, 2), views=0, clicks=1)
        make_stat(ad, date=date(2026, 11, 3), views=10, clicks=2)
        make_stat(ad, date=date(2026, 11, 20), views=5, clicks=0)
        make_stat(ad, date=date(2026, 11, 25), views=0, clicks=1)

        rows = export_rows(BannerDailyStat.objects.all())[1:]

        assert rows == [
            [
                '="2VfnxAD"',
                'ООО "Прайм Спорт Рус"',
                '="7718933790"',
                "Баннер А",
                # Период — первая и последняя дата с показами, не с кликами.
                "03.11.2026",
                "20.11.2026",
                "15",
                "4",
            ]
        ]

    def test_selection_across_month_boundary_gives_row_per_month(self):
        ad = AdvertisementBannerFactory(erid="2VfnxAD")
        make_stat(ad, date=date(2026, 10, 30), views=3, clicks=0)
        make_stat(ad, date=date(2026, 10, 31), views=4, clicks=1)
        make_stat(ad, date=date(2026, 11, 1), views=5, clicks=2)

        rows = export_rows(BannerDailyStat.objects.all())[1:]

        assert [(row[4], row[5], row[6], row[7]) for row in rows] == [
            ("30.10.2026", "31.10.2026", "7", "1"),
            ("01.11.2026", "01.11.2026", "5", "2"),
        ]

    def test_same_erid_on_two_banners_gives_two_rows(self):
        first = AdvertisementBannerFactory(erid="2VfnxSAME", title="Первый")
        second = AdvertisementBannerFactory(erid="2VfnxSAME", title="Второй")
        make_stat(first, date=date(2026, 11, 3), views=1)
        make_stat(second, date=date(2026, 11, 3), views=2)

        rows = export_rows(BannerDailyStat.objects.all())[1:]

        assert sorted((row[3], row[6]) for row in rows) == [("Второй", "2"), ("Первый", "1")]

    def test_requisites_from_latest_row_and_title_change_does_not_split(self):
        ad = AdvertisementBannerFactory(erid="2VfnxAD")
        make_stat(ad, date=date(2026, 11, 3), views=1, banner_title="Старое", advertiser_name="ООО Старое")
        make_stat(ad, date=date(2026, 11, 4), views=1, banner_title="Новое", advertiser_name="ООО Новое")

        rows = export_rows(BannerDailyStat.objects.all())[1:]

        assert len(rows) == 1
        assert (rows[0][1], rows[0][3], rows[0][6]) == ("ООО Новое", "Новое", "2")

    def test_inn_with_leading_zero_is_text(self):
        ad = AdvertisementBannerFactory(erid="2VfnxAD", advertiser_inn="0123456789")
        make_stat(ad, date=date(2026, 11, 3), views=1)

        rows = export_rows(BannerDailyStat.objects.all())[1:]

        assert rows[0][2] == '="0123456789"'

    def test_formula_cells_are_escaped(self):
        ad = AdvertisementBannerFactory(erid="2VfnxAD")
        make_stat(
            ad,
            date=date(2026, 11, 3),
            views=1,
            banner_title='=HYPERLINK("http://evil","x")',
            advertiser_name="@SUM(1+1)",
        )

        rows = export_rows(BannerDailyStat.objects.all())[1:]

        assert rows[0][3] == '\'=HYPERLINK("http://evil","x")'
        assert rows[0][1] == "'@SUM(1+1)"

    def test_quote_in_erid_does_not_break_text_cell(self):
        make_stat(None, banner_ref_id=1, date=date(2026, 11, 3), views=1, erid='ab"c', banner_title="Б")

        rows = export_rows(BannerDailyStat.objects.all())[1:]

        assert rows[0][0] == '="ab""c"'

    def test_respects_selection(self):
        ad = AdvertisementBannerFactory(erid="2VfnxAD")
        selected = make_stat(ad, date=date(2026, 11, 3), views=1)
        make_stat(ad, date=date(2026, 11, 4), views=100)

        rows = export_rows(BannerDailyStat.objects.filter(pk=selected.pk))[1:]

        assert (rows[0][4], rows[0][5], rows[0][6]) == ("03.11.2026", "03.11.2026", "1")


# ---------------------------------------------------------------------------
# Раздел /marketing/: права, удаление баннера со статистикой, выгрузка
# ---------------------------------------------------------------------------


@pytest.fixture
def role_groups():
    _roles_migration.create_staff_role_groups(django_apps, SimpleNamespace(connection=connection))
    _stat_migration.grant_banner_stat_permissions(django_apps, SimpleNamespace(connection=connection))


def staff_client(group_name: str) -> Client:
    user = User.objects.create_user(
        email=f"staff_{get_unique_suffix()}@example.com", password="StrongPassword123!", is_staff=True
    )
    user.groups.add(Group.objects.get(name=group_name))
    client = Client()
    client.force_login(user)
    return client


def group_has(group_name: str, codename: str) -> bool:
    return Group.objects.get(name=group_name).permissions.filter(codename=codename).exists()


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.usefixtures("role_groups")
class TestMarketingSectionStats:
    def test_migration_grants_view_only(self):
        for group_name in (MARKETING_GROUP, SUPERVISORS_GROUP):
            assert group_has(group_name, "view_bannerdailystat")
            for codename in ("add_bannerdailystat", "change_bannerdailystat", "delete_bannerdailystat"):
                assert not group_has(group_name, codename)
        assert not group_has(MANAGERS_GROUP, "view_bannerdailystat")

    def test_migration_is_idempotent_and_keeps_manual_permissions(self):
        manual = Permission.objects.get(content_type__app_label="banners", codename="change_bannerdailystat")
        Group.objects.get(name=MARKETING_GROUP).permissions.add(manual)

        _stat_migration.grant_banner_stat_permissions(django_apps, SimpleNamespace(connection=connection))

        assert group_has(MARKETING_GROUP, "change_bannerdailystat")
        assert Group.objects.get(name=MARKETING_GROUP).permissions.filter(codename="view_bannerdailystat").count() == 1

    def test_registered_in_marketing_site(self):
        assert BannerDailyStat in marketing_site._registry

    def test_marketer_sees_stats_read_only(self):
        client = staff_client(MARKETING_GROUP)
        stat = make_stat(AdvertisementBannerFactory(erid="2VfnxAD"), views=3)

        listing = client.get(STATS_URL)
        card = client.get(f"{STATS_URL}{stat.pk}/change/")

        assert listing.status_code == 200
        assert f'href="{STATS_URL}add/"' not in listing.content.decode()
        assert card.status_code == 200
        assert 'name="views"' not in card.content.decode()
        assert client.post(f"{STATS_URL}{stat.pk}/change/", {"views": "999"}).status_code == 403
        assert client.post(f"{STATS_URL}{stat.pk}/delete/", {"post": "yes"}).status_code == 403
        stat.refresh_from_db()
        assert stat.views == 3

    def test_marketer_exports_csv(self):
        client = staff_client(MARKETING_GROUP)
        stat = make_stat(AdvertisementBannerFactory(erid="2VfnxAD"), date=date(2026, 11, 3), views=3)

        response = client.post(STATS_URL, {"action": "export_ord_csv", "_selected_action": [str(stat.pk)]})

        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/csv")
        assert '"=""2VfnxAD"""' in response.content.decode("utf-8")

    def test_supervisor_sees_stats(self):
        client = staff_client(SUPERVISORS_GROUP)

        assert client.get(STATS_URL).status_code == 200

    @staticmethod
    def _listed(client: Client, params: dict[str, str]) -> set[int]:
        response = client.get(STATS_URL, params)
        assert response.status_code == 200
        return {row.pk for row in response.context["cl"].result_list}

    def test_banner_filter_keeps_deleted_banner_snapshot(self):
        client = staff_client(MARKETING_GROUP)
        gone = AdvertisementBannerFactory(erid="2VfnxGONE", title="Удалённый")
        gone_pk = gone.pk
        gone_rows = {make_stat(gone, date=date(2026, 11, day), views=1).pk for day in (3, 4)}
        other_row = make_stat(AdvertisementBannerFactory(erid="2VfnxOTHER"), date=date(2026, 11, 3), views=1)
        gone.delete()

        listed = self._listed(client, {"banner_ref": str(gone_pk)})

        assert listed == gone_rows
        assert other_row.pk not in listed
        assert set(BannerDailyStat.objects.filter(pk__in=listed).values_list("banner_id", flat=True)) == {None}

    def test_erid_filter_without_erid(self):
        client = staff_client(MARKETING_GROUP)
        plain_row = make_stat(BannerFactory(type=Banner.BannerType.HERO), date=date(2026, 11, 3), views=1)
        make_stat(AdvertisementBannerFactory(erid="2VfnxAD"), date=date(2026, 11, 3), views=1)

        assert self._listed(client, {"erid": "__none__"}) == {plain_row.pk}

    def test_erid_filter_by_token(self):
        client = staff_client(MARKETING_GROUP)
        ad = AdvertisementBannerFactory(erid="2VfnxAD")
        ad_row = make_stat(ad, date=date(2026, 11, 3), views=1)
        # Тот же баннер с прежним ERID и другой креатив в выдачу не попадают.
        make_stat(ad, date=date(2026, 11, 3), erid="2VfnxOLD", views=1)
        make_stat(AdvertisementBannerFactory(erid="2VfnxOTHER"), date=date(2026, 11, 3), views=1)
        make_stat(BannerFactory(type=Banner.BannerType.HERO), date=date(2026, 11, 3), views=1)

        assert self._listed(client, {"erid": "2VfnxAD"}) == {ad_row.pk}

    def test_banner_filter_lookups_include_deleted_and_latest_title(self):
        gone = AdvertisementBannerFactory(erid="2VfnxGONE")
        gone_pk = gone.pk
        make_stat(gone, date=date(2026, 11, 4), banner_title="Новое название", views=1)
        make_stat(gone, date=date(2026, 11, 3), banner_title="Старое название", views=1)
        alive = BannerFactory(title="Живой")
        make_stat(alive, date=date(2026, 11, 3), views=1)
        gone.delete()

        lookups = dict(
            BannerRefFilter(RequestFactory().get(STATS_URL), {}, BannerDailyStat, stat_admin()).lookups(
                RequestFactory().get(STATS_URL), stat_admin()
            )
        )

        assert lookups == {
            str(gone_pk): f"Новое название (ID {gone_pk})",
            str(alive.pk): f"Живой (ID {alive.pk})",
        }

    def test_banner_columns_render_in_list(self):
        client = staff_client(MARKETING_GROUP)
        banner = AdvertisementBannerFactory()
        make_stat(banner, views=4, clicks=1)

        html = client.get(BANNERS_URL).content.decode()

        assert "Показы за 30 дней" in html
        assert "25,00 %" in html

    def test_delete_banner_with_stats_keeps_snapshot(self):
        client = staff_client(MARKETING_GROUP)
        banner = AdvertisementBannerFactory(erid="2VfnxGONE", title="Удаляемый")
        banner_pk = banner.pk
        make_stat(banner, date=date(2026, 11, 3), views=7, clicks=2)

        confirm = client.get(f"{BANNERS_URL}{banner_pk}/delete/")
        response = client.post(f"{BANNERS_URL}{banner_pk}/delete/", {"post": "yes"})

        assert confirm.status_code == 200
        assert response.status_code == 302
        assert not Banner.objects.filter(pk=banner_pk).exists()
        stat = BannerDailyStat.objects.get()
        assert (stat.banner_id, stat.banner_ref_id) == (None, banner_pk)
        assert (stat.banner_title, stat.erid, stat.advertiser_inn) == ("Удаляемый", "2VfnxGONE", "7718933790")

        rows = export_rows(BannerDailyStat.objects.all())[1:]
        assert rows == [
            [
                '="2VfnxGONE"',
                'ООО "Прайм Спорт Рус"',
                '="7718933790"',
                "Удаляемый",
                "03.11.2026",
                "03.11.2026",
                "7",
                "2",
            ]
        ]
