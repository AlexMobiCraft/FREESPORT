"""
Сайты Django-админки FREESPORT: основная `/admin/`, раздел менеджера `/manager/`,
раздел маркетинга `/marketing/` и раздел руководителя `/supervisor/`.

Эпик 42: флаг `is_staff` теперь означает «сотрудник» (менеджер, маркетинг,
руководитель), а не «администратор». Сотрудникам `is_staff` нужен для входа
в их собственные разделы, поэтому основная `/admin/` с логами синхронизации,
привязками к 1С и служебными полями открыта только суперпользователю.
"""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.urls import reverse

from apps.users.staff_roles import MANAGERS_GROUP, MARKETING_GROUP, SUPERVISORS_GROUP


class SuperuserAdminSite(admin.AdminSite):
    """
    Сайт `/admin/`, доступный только активному суперпользователю.

    Отказ — штатное поведение `AdminSite.admin_view`: 302 на страницу входа
    `/admin/login/?next=…`. Подключается как сайт по умолчанию через
    `freesport.apps.FreesportAdminConfig`, поэтому `admin.site` и все
    `@admin.register(...)` продолжают работать с экземпляром этого класса.
    """

    def has_permission(self, request: HttpRequest) -> bool:
        """Пускает только активного суперпользователя, `is_staff` доступа не даёт."""
        user = request.user
        return bool(user.is_active and user.is_superuser)


class StaffSectionAdminSite(admin.AdminSite):
    """
    Общая проверка входа в раздел сотрудника.

    Пускает активного сотрудника (`is_staff`) из групп `section_groups`.
    Суперпользователя раздел не пускает, даже если он состоит в группе:
    у него есть `/admin/` с тем же и большим, а членство в группе не должно
    превращать его в сотрудника с урезанным видом. Отказ — штатный 302 на
    страницу входа раздела.
    """

    section_groups: tuple[str, ...] = ()

    def has_permission(self, request: HttpRequest) -> bool:
        user = request.user
        if not (user.is_active and user.is_staff) or user.is_superuser:
            return False
        # admin_view и each_context зовут has_permission по нескольку раз за
        # запрос — членство в группах читается из БД один раз. Кэш — словарь по
        # имени сайта: один запрос проверяют разные разделы, и общий атрибут
        # отдал бы одному разделу ответ другого.
        access = getattr(request, "_staff_section_access", None)
        if access is None:
            access = {}
            request._staff_section_access = access  # type: ignore[attr-defined]
        if self.name not in access:
            access[self.name] = user.groups.filter(name__in=self.section_groups).exists()
        return bool(access[self.name])


class ManagerAdminSite(StaffSectionAdminSite):
    """
    Раздел менеджера `/manager/`: клиенты, за которых отвечает сотрудник (стори 42.4),
    их заказы и очередь главной (стори 42.5).

    Пускает активного сотрудника (`is_staff`) из группы «Менеджеры» или
    «Руководители» — ровно критерий `RESPONSIBLE_MANAGER_CHOICES` плюс
    `is_active`: в раздел входит тот, кого можно назначить ответственным.
    Суперпользователя раздел не пускает, даже если он состоит в группе:
    у него есть `/admin/` с тем же и большим, а членство в группе не должно
    превращать его в «менеджера» с урезанной видимостью. Отказ — штатный
    302 на `/manager/login/`.
    """

    site_header = "FREESPORT — Менеджер"
    site_title = "FREESPORT — Менеджер"
    index_title = "Раздел менеджера"
    # Без блока «Последние действия»: его ссылки строит LogEntry.get_admin_url()
    # через reverse("admin:…") без current_app, то есть в закрытую /admin/.
    index_template = "admin/manager/index.html"
    section_groups = (MANAGERS_GROUP, SUPERVISORS_GROUP)

    def index(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> TemplateResponse:
        # Очередь главной (стори 42.5). Импорт внутри метода: модуль заказов
        # раздела сам импортирует manager_site, импорт на уровне модуля дал бы цикл.
        from apps.orders.manager_admin import manager_queue

        extra_context = {**(extra_context or {}), "manager_queue": manager_queue(request, self)}
        return super().index(request, extra_context)

    def get_app_list(self, request: HttpRequest, app_label: str | None = None) -> list[dict[str, Any]]:
        # Пользователи раздела — клиенты: так называются и блок, и модель.
        app_list = super().get_app_list(request, app_label)
        for app in app_list:
            if app["app_label"] != "users":
                continue
            for model in app["models"]:
                if model["object_name"] == "User":
                    model["name"] = "Клиенты"
                    app["name"] = "Клиенты"
        return app_list


manager_site = ManagerAdminSite(name="manager")


class MarketingAdminSite(StaffSectionAdminSite):
    """
    Раздел маркетинга `/marketing/` (стори 42.6): баннеры, новости и блог,
    рубрики, метки товаров, бренды и категории главной.

    Пускает активного сотрудника из группы «Маркетинг» или «Руководители»;
    суперпользователя — нет (см. `StaffSectionAdminSite`). Фильтра по региону
    у маркетинга нет, руководитель видит раздел целиком.
    """

    site_header = "FREESPORT — Маркетинг"
    site_title = "FREESPORT — Маркетинг"
    index_title = "Раздел маркетинга"
    # Без блока «Последние действия» — по той же причине, что у раздела менеджера.
    index_template = "admin/marketing/index.html"
    section_groups = (MARKETING_GROUP, SUPERVISORS_GROUP)

    def index(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> TemplateResponse:
        # Плашка подписчиков. Импорт внутри метода: модуль раздела сам
        # импортирует marketing_site, импорт на уровне модуля дал бы цикл.
        from apps.common.marketing_admin import newsletter_stats

        extra_context = {**(extra_context or {}), "newsletter_stats": newsletter_stats()}
        return super().index(request, extra_context)

    def get_app_list(self, request: HttpRequest, app_label: str | None = None) -> list[dict[str, Any]]:
        # «Общие утилиты» в разделе — это новости и блог; их «Категории» —
        # рубрики, иначе рядом с «Категориями для главной» две похожие «Категории».
        app_list = super().get_app_list(request, app_label)
        for app in app_list:
            if app["app_label"] != "common":
                continue
            app["name"] = "Новости и блог"
            for model in app["models"]:
                if model["object_name"] == "Category":
                    model["name"] = "Рубрики"
        return app_list


marketing_site = MarketingAdminSite(name="marketing")


class SupervisorAdminSite(StaffSectionAdminSite):
    """
    Раздел руководителя `/supervisor/` (стори 42.7): сотрудники, правила
    регионов, получатели уведомлений и бонусная программа.

    Пускает активного сотрудника из группы «Руководители»; суперпользователя —
    нет (см. `StaffSectionAdminSite`). Клиентов и заказы руководитель смотрит
    в `/manager/` — там для него снят фильтр по ответственному, — а витрину
    в `/marketing/`: оба раздела пускают «Руководителей».
    """

    site_header = "FREESPORT — Руководитель"
    site_title = "FREESPORT — Руководитель"
    index_title = "Раздел руководителя"
    # Без блока «Последние действия» — по той же причине, что у раздела менеджера.
    index_template = "admin/supervisor/index.html"
    section_groups = (SUPERVISORS_GROUP,)

    def index(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> TemplateResponse:
        sections = [
            {"url": reverse("manager:index"), "name": "Клиенты и заказы — без фильтра по менеджеру"},
            {"url": reverse("marketing:index"), "name": "Маркетинг"},
        ]
        extra_context = {**(extra_context or {}), "supervisor_sections": sections}
        return super().index(request, extra_context)

    def get_app_list(self, request: HttpRequest, app_label: str | None = None) -> list[dict[str, Any]]:
        # Пользователи раздела — сотрудники; «Общие утилиты» — регионы и
        # получатели уведомлений.
        app_list = super().get_app_list(request, app_label)
        for app in app_list:
            if app["app_label"] == "users":
                app["name"] = "Сотрудники"
                for model in app["models"]:
                    if model["object_name"] == "User":
                        model["name"] = "Сотрудники"
            elif app["app_label"] == "common":
                app["name"] = "Регионы и уведомления"
                for model in app["models"]:
                    if model["object_name"] == "ManagerRoutingRule":
                        model["name"] = "Правила регионов"
        return app_list


supervisor_site = SupervisorAdminSite(name="supervisor")
