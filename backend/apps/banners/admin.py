"""
Django Admin для приложения banners
"""

from __future__ import annotations

import csv
import unicodedata
from datetime import date, timedelta
from typing import Any, cast

from django.contrib import admin
from django.db.models import IntegerField, OuterRef, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import SafeString

from .models import Banner, BannerDailyStat

# Окно колонок статистики в списке баннеров: сегодня и 29 предыдущих дней.
STATS_WINDOW_DAYS = 30

ORD_CSV_HEADER = (
    "ERID",
    "Рекламодатель",
    "ИНН рекламодателя",
    "Баннер",
    "Начало периода",
    "Конец периода",
    "Показы",
    "Клики",
)
_FORMULA_PREFIXES = ("=", "+", "-", "@", "＝", "＋", "－", "＠")


def _csv_cell(value: Any) -> str:
    """
    Ячейка CSV, которую Excel не выполнит как формулу.

    Значение, у которого после ведущих пробелов и управляющих символов идёт
    `=`, `+`, `-` или `@`, а также начинающееся с табуляции или `\\r`,
    получает в начало апостроф. Та же логика, что у выгрузки заказов менеджера
    (`apps.orders.manager_admin.csv_cell`); импорт оттуда связал бы приложения.
    """
    text = str(value)
    meaningful = text.lstrip()
    while meaningful and unicodedata.category(meaningful[0]).startswith("C"):
        meaningful = meaningful[1:].lstrip()
    if text.startswith(("\t", "\r")) or meaningful.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def _csv_text(value: str) -> str:
    """
    Ячейка, которую Excel покажет текстом как есть: `="…"`.

    Без этого ИНН с ведущим нулём потерял бы его, а 12-значный ИНН ушёл бы
    в экспоненту. Кавычки внутри значения удваиваются по правилам формулы Excel.
    """
    return '="' + value.replace('"', '""') + '"'


def _format_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _ctr(views: int, clicks: int) -> str:
    """CTR в процентах; при нуле показов — «—»."""
    if not views:
        return "—"
    return f"{clicks * 100 / views:.2f} %".replace(".", ",")


def _stat_total(field: str, since: date) -> Coalesce:
    """Сумма `field` статистики баннера с даты `since` — подзапросом, без JOIN по обратному FK."""
    totals = (
        BannerDailyStat.objects.filter(banner_id=OuterRef("pk"), date__gte=since)
        .order_by()
        .values("banner_id")
        .annotate(total=Sum(field))
        .values("total")[:1]
    )
    return Coalesce(Subquery(totals, output_field=IntegerField()), 0)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    """Admin для модели Banner"""

    list_display = (
        "title",
        "type",
        "image_preview",
        "is_advertisement",
        "get_is_active_display",
        "priority",
        "target_groups_display",
        "start_date",
        "end_date",
        "views_30d",
        "clicks_30d",
        "ctr_30d",
    )
    list_filter = (
        "type",
        "is_active",
        "is_advertisement",
        "show_to_guests",
        "show_to_authenticated",
        "show_to_trainers",
        "show_to_wholesale",
        "show_to_federation",
    )
    search_fields = ("title", "subtitle", "advertiser_name", "advertiser_inn")
    readonly_fields = ("created_at", "updated_at", "image_preview", "mobile_image_preview")

    fieldsets = (
        (
            "Контент",
            {
                "fields": (
                    "type",
                    "title",
                    "subtitle",
                    "image",
                    "image_preview",
                    "mobile_image",
                    "mobile_image_preview",
                    "image_alt",
                    "cta_text",
                    "cta_link",
                ),
            },
        ),
        (
            "Таргетинг",
            {
                "fields": (
                    "show_to_guests",
                    "show_to_authenticated",
                    "show_to_trainers",
                    "show_to_wholesale",
                    "show_to_federation",
                ),
                "description": ("Выберите целевые группы пользователей для показа баннера"),
            },
        ),
        (
            "Маркировка рекламы",
            {
                "fields": (
                    "is_advertisement",
                    "advertiser_name",
                    "advertiser_inn",
                    "erid",
                ),
                "description": (
                    "Включите «Является рекламой», чтобы показать на баннере метку «Реклама» "
                    "с реквизитами. Наименование и ИНН обязательны при включённой маркировке. "
                    "Доступно только для маркетинговых баннеров."
                ),
            },
        ),
        (
            "Управление",
            {
                "fields": (
                    "is_active",
                    "priority",
                    "start_date",
                    "end_date",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Banner]:
        since = timezone.localdate() - timedelta(days=STATS_WINDOW_DAYS - 1)
        queryset = cast(QuerySet[Banner], super().get_queryset(request))
        return queryset.annotate(
            views_30d=_stat_total("views", since),
            clicks_30d=_stat_total("clicks", since),
        )

    @admin.display(description="Показы за 30 дней", ordering="views_30d")
    def views_30d(self, obj: Banner) -> int:
        return int(getattr(obj, "views_30d", 0) or 0)

    @admin.display(description="Клики за 30 дней", ordering="clicks_30d")
    def clicks_30d(self, obj: Banner) -> int:
        return int(getattr(obj, "clicks_30d", 0) or 0)

    @admin.display(description="CTR за 30 дней")
    def ctr_30d(self, obj: Banner) -> str:
        return _ctr(self.views_30d(obj), self.clicks_30d(obj))

    @admin.display(description="Превью")
    def image_preview(self, obj: Banner) -> SafeString:
        """Отображает превью изображения в списке и детальном просмотре"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 100px;" />',
                obj.image.url,
            )
        return format_html('<span style="color: #999;">{}</span>', "Нет изображения")

    @admin.display(description="Превью (мобильное)")
    def mobile_image_preview(self, obj: Banner) -> SafeString:
        """Превью мобильного изображения. Использует format_html() для экранирования."""
        if obj.mobile_image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 100px;" />',
                obj.mobile_image.url,
            )
        return format_html('<span style="color: #999;">{}</span>', "Нет мобильного изображения")

    @admin.display(description="Целевые группы")
    def target_groups_display(self, obj: Banner) -> str:
        """Отображает список целевых групп пользователей"""
        groups = []
        if obj.show_to_guests:
            groups.append("Гости")
        if obj.show_to_authenticated:
            groups.append("Авторизованные")
        if obj.show_to_trainers:
            groups.append("Тренеры")
        if obj.show_to_wholesale:
            groups.append("Оптовики")
        if obj.show_to_federation:
            groups.append("Федерации")

        return ", ".join(groups) if groups else "Не настроено"

    @admin.display(description="Статус (с учетом дат)", boolean=True)
    def get_is_active_display(self, obj: Banner) -> bool:
        """Отображает реальный статус активности с учетом расписания"""
        return obj.is_scheduled_active


class BannerRefFilter(admin.SimpleListFilter):
    """
    Фильтр по баннеру — по `banner_ref_id`, а не по FK.

    Так в списке остаются и удалённые баннеры: их строки статистики держат
    копию id и снимок названия.
    """

    title = "баннер"
    parameter_name = "banner_ref"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        titles: dict[int, str] = {}
        # По возрастанию даты: побеждает самое свежее название баннера.
        stats = BannerDailyStat.objects.order_by("date", "pk").values_list("banner_ref_id", "banner_title")
        for ref_id, title in stats:
            titles[ref_id] = title
        return [(str(ref_id), f"{title or 'Без названия'} (ID {ref_id})") for ref_id, title in sorted(titles.items())]

    def queryset(self, request: HttpRequest, queryset: QuerySet[BannerDailyStat]) -> QuerySet[BannerDailyStat]:
        value = self.value()
        if value and value.isdigit():
            return queryset.filter(banner_ref_id=int(value))
        return queryset


class EridFilter(admin.SimpleListFilter):
    """Фильтр по ERID креатива; «Без ERID» — строки нерекламных баннеров."""

    title = "ERID"
    parameter_name = "erid"
    EMPTY = "__none__"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        erids = BannerDailyStat.objects.exclude(erid="").order_by("erid").values_list("erid", flat=True).distinct()
        return [(self.EMPTY, "Без ERID"), *((erid, erid) for erid in erids)]

    def queryset(self, request: HttpRequest, queryset: QuerySet[BannerDailyStat]) -> QuerySet[BannerDailyStat]:
        value = self.value()
        if value == self.EMPTY:
            return queryset.filter(erid="")
        if value:
            return queryset.filter(erid=value)
        return queryset


@admin.register(BannerDailyStat)
class BannerDailyStatAdmin(admin.ModelAdmin):
    """
    Дневная статистика показов и кликов баннеров — только просмотр и выгрузка для ОРД.

    Строки пишет только счётчик сайта: добавлять, править и удалять их нельзя,
    иначе отчёт в ОРД разойдётся с фактом.
    """

    list_display = (
        "date",
        "banner_title",
        "banner_ref_id",
        "erid",
        "advertiser_name",
        "advertiser_inn",
        "views",
        "clicks",
        "ctr",
    )
    list_filter = (BannerRefFilter, EridFilter)
    search_fields = ("banner_title", "erid", "advertiser_name", "advertiser_inn")
    date_hierarchy = "date"
    actions = ["export_ord_csv"]
    fields = (
        "date",
        "banner",
        "banner_ref_id",
        "banner_title",
        "erid",
        "advertiser_name",
        "advertiser_inn",
        "views",
        "clicks",
    )
    list_per_page = 100

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: BannerDailyStat | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: BannerDailyStat | None = None) -> bool:
        return False

    @admin.display(description="CTR")
    def ctr(self, obj: BannerDailyStat) -> str:
        return _ctr(obj.views, obj.clicks)

    @admin.action(description="Выгрузить CSV для ОРД")
    def export_ord_csv(self, request: HttpRequest, queryset: QuerySet[BannerDailyStat]) -> HttpResponse:
        """
        CSV для ручного переноса в кабинет ОРД: строка на креатив (ERID), баннер и месяц.

        Только строки с ERID — нерекламные баннеры в ОРД не передаются. Выбор через
        границу месяца даёт по строке на каждый месяц. Реквизиты — из самой поздней
        строки группы, период — первая и последняя дата с показами среди выбранных
        строк месяца (если показов в группе нет — первая и последняя выбранная дата).
        """
        rows = (
            queryset.exclude(erid="")
            .annotate(month=TruncMonth("date"))
            .order_by("date", "pk")
            .values(
                "erid",
                "banner_ref_id",
                "month",
                "date",
                "banner_title",
                "advertiser_name",
                "advertiser_inn",
                "views",
                "clicks",
            )
        )
        groups: dict[tuple[date, str, int], dict[str, Any]] = {}
        for row in rows:
            key = (row["month"], row["erid"], row["banner_ref_id"])
            group = groups.setdefault(
                key,
                {"views": 0, "clicks": 0, "first_view": None, "last_view": None, "first": row["date"]},
            )
            group["views"] += row["views"]
            group["clicks"] += row["clicks"]
            group["last"] = row["date"]
            if row["views"]:
                group["first_view"] = group["first_view"] or row["date"]
                group["last_view"] = row["date"]
            # Строки идут по возрастанию даты — последняя перезаписывает реквизиты.
            group["banner_title"] = row["banner_title"]
            group["advertiser_name"] = row["advertiser_name"]
            group["advertiser_inn"] = row["advertiser_inn"]

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="ord_banners_{timezone.localdate():%Y-%m-%d}.csv"'
        # Без BOM Excel на Windows читает UTF-8 как cp1251.
        response.write("﻿")
        writer = csv.writer(response, delimiter=";")
        writer.writerow(ORD_CSV_HEADER)
        for (_month, erid, _ref_id), group in sorted(groups.items(), key=lambda item: item[0]):
            writer.writerow(
                [
                    _csv_text(erid),
                    _csv_cell(group["advertiser_name"]),
                    _csv_text(group["advertiser_inn"]),
                    _csv_cell(group["banner_title"]),
                    _format_date(group["first_view"] or group["first"]),
                    _format_date(group["last_view"] or group["last"]),
                    group["views"],
                    group["clicks"],
                ]
            )
        return response
