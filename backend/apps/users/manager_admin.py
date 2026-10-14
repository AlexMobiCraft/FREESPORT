"""
Раздел менеджера `/manager/` — клиенты, за которых отвечает сотрудник (стори 42.4).

Урезанный `UserAdmin` на сайте `manager_site`: только свои клиенты
(`scope_clients`), карточка из белого списка полей без служебных данных
интеграции и привилегий, на чужого клиента — 404. Действия и страницы
подтверждения B2B, привязки к 1С и смены пароля — общие с `/admin/`.

Модуль импортируется из `UsersConfig.ready()`: к этому моменту
`admin.autodiscover()` уже загрузил `apps/users/admin.py`.
"""

from __future__ import annotations

from typing import Any, Iterator

from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.db import transaction
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse

from apps.common.models import AuditLog
from apps.users.admin import AddressInline, CompanyInline, Has1CCandidateFilter, UserAdmin
from apps.users.models import User
from apps.users.staff_roles import staff_accounts_q
from freesport.admin_site import manager_site


def scope_clients(request: HttpRequest, queryset: QuerySet[User]) -> QuerySet[User]:
    """
    Единственное правило видимости клиентов в разделе менеджера.

    Видны клиенты, у которых сотрудник — ответственный менеджер, минус
    учётные записи сотрудников (`staff_accounts_q()`): их ответственный
    мог остаться от времени, когда запись ещё была клиентской. Руководитель
    в 42.4 тоже видит только своих; снятие фильтра для него (стори 42.7)
    правится только здесь.
    """
    return queryset.filter(responsible_manager=request.user).exclude(staff_accounts_q())


class PortalAccountFilter(admin.SimpleListFilter):
    """
    «Учётная запись на портале»: по умолчанию записи `unregistered` скрыты.

    Это контрагенты 1С без аккаунта на сайте (на проде их 4600+): они
    заполняют список, но менеджеру нечего с ними делать, пока клиент не
    зарегистрировался. Показать их — значение «Нет» или «Все».
    """

    title = "Учётная запись на портале"
    parameter_name = "portal_account"

    def __init__(self, request: HttpRequest, params: dict[str, Any], model: Any, model_admin: Any) -> None:
        super().__init__(request, params, model, model_admin)
        # Фильтр роли «Не зарегистрирован» без исключения по умолчанию всегда
        # давал бы пустой список: при нём записи без аккаунта видны, как во «Все».
        self.role_is_unregistered = request.GET.get("role__exact") == User.ROLE_UNREGISTERED

    def effective_value(self) -> str | None:
        value = self.value()
        if value is None and self.role_is_unregistered:
            return "all"
        return value

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [("no", "Нет"), ("all", "Все")]

    def choices(self, changelist: ChangeList) -> Iterator[dict[str, Any]]:
        # Пункт по умолчанию — «Есть» без параметра; штатного «Все» с тем же
        # значением нет, иначе в фильтре было бы два пункта на одно состояние.
        value = self.effective_value()
        yield {
            "selected": value not in ("no", "all"),
            "query_string": changelist.get_query_string(remove=[self.parameter_name]),
            "display": "Есть",
        }
        for lookup, title in self.lookup_choices:
            yield {
                "selected": value == lookup,
                "query_string": changelist.get_query_string({self.parameter_name: lookup}),
                "display": title,
            }

    def queryset(self, request: HttpRequest, queryset: QuerySet[User]) -> QuerySet[User]:
        value = self.effective_value()
        if value == "all":
            return queryset
        if value == "no":
            return queryset.filter(role=User.ROLE_UNREGISTERED)
        return queryset.exclude(role=User.ROLE_UNREGISTERED)


class ManagerClientAdmin(UserAdmin):
    """Клиенты менеджера: только свои, без служебных полей, без добавления и удаления."""

    list_display = [
        "email",
        "full_name",
        "company_name",
        "tax_id",
        "customer_code",
        "role_display",
        "verification_status_display",
        "has_1c_candidate",
        "verify_b2b_link",
        "phone",
        "created_at",
        "is_active",
    ]
    list_filter = ["role", "verification_status", Has1CCandidateFilter, "is_active", PortalAccountFilter]
    actions = ["approve_b2b_users", "reject_b2b_users", "link_1c_customer", "block_users", "unblock_users"]
    # Полей групп и прав в карточке раздела нет.
    filter_horizontal: Any = ()
    inlines = [CompanyInline, AddressInline]

    # Белый список полей: новое поле User само в раздел не попадёт.
    fieldsets: Any = (
        ("Контакты", {"fields": ("email", "password", "first_name", "last_name", "phone")}),
        ("B2B данные", {"fields": ("company_name", "tax_id", "country", "company_legal_address", "customer_code")}),
        ("Статус", {"fields": ("role", "verification_status", "is_verified", "is_active")}),
        ("1С и ответственный", {"fields": ("linked_to_1c", "onec_price_type_name", "responsible_manager_display")}),
        ("Даты", {"fields": ("created_at", "last_login"), "classes": ("collapse",)}),
    )
    # Статус верификации меняют только страница подтверждения и действия (они
    # пишут AuditLog); код клиента вшит в номера заказов и сверяется с 1С.
    readonly_fields: Any = (
        "customer_code",
        "role",
        "verification_status",
        "is_verified",
        "linked_to_1c",
        "onec_price_type_name",
        "responsible_manager_display",
        "company_legal_address",
        "created_at",
        "last_login",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:  # type: ignore[override]
        return scope_clients(request, super().get_queryset(request))

    def _get_obj_does_not_exist_redirect(self, request: HttpRequest, opts: Any, object_id: str) -> HttpResponse:
        # Штатный ответ на объект вне queryset — 302 на главную с «не существует».
        # В разделе чужой клиент неотличим от несуществующего: 404 на карточке,
        # истории и странице подтверждения. Метод приватный (Django 5.2), его
        # контракт страхуют тесты AC3 стори 42.4.
        raise Http404("Клиент не найден")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: User | None = None) -> bool:  # type: ignore[override]
        return False

    def get_fieldsets(self, request: HttpRequest, obj: User | None = None) -> Any:  # type: ignore[override]
        # Без логики UserAdmin: привилегий и кандидатов 1С в белом списке нет,
        # а find_link_candidates на каждом открытии карточки — лишний запрос.
        return self.fieldsets

    def get_readonly_fields(self, request: HttpRequest, obj: User | None = None) -> list[str]:  # type: ignore[override]
        return list(self.readonly_fields)

    @admin.display(description="Связан с 1С", boolean=True)
    def linked_to_1c(self, obj: User) -> bool:
        return bool(obj.onec_id or obj.onec_guid)

    @admin.display(description="Ответственный менеджер")
    def responsible_manager_display(self, obj: User) -> str:
        # Текст без ссылки: readonly-FK Django рисует ссылкой на карточку
        # менеджера в этом же разделе, а менеджер — сотрудник вне scope_clients,
        # то есть ссылка вела бы в 404.
        manager = obj.responsible_manager
        if manager is None:
            return "—"
        name = manager.full_name
        return f"{name} ({manager.email})" if name else str(manager.email or "—")

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> HttpResponse:
        extra_context = {**(extra_context or {}), "title": "Клиенты"}
        return super().changelist_view(request, extra_context)

    def response_action(self, request: HttpRequest, queryset: QuerySet[User]) -> HttpResponse | None:
        # Выбранные строки читаются под блокировкой в одной транзакции с записью:
        # клиент, переданный другому менеджеру до чтения, в выборку не попадёт,
        # а передать его, пока действие пишет, нельзя. Порядок блокировки — по pk,
        # как у пересчёта ответственных. Привязка к 1С пишет через сервис под его
        # блокировкой (source и target по возрастанию pk) — внешняя блокировка
        # target перевернула бы этот порядок.
        if "link_1c_customer" in request.POST.getlist("action"):
            return super().response_action(request, queryset)
        with transaction.atomic():
            return super().response_action(request, queryset.select_for_update(of=("self",)).order_by("pk"))

    def save_model(  # type: ignore[override]
        self, request: HttpRequest, obj: User, form: ModelForm, change: bool
    ) -> None:
        # Карточка прочитана без блокировки. Если клиента за это время передали
        # другому менеджеру, полное save() вернуло бы прежнего ответственного из
        # устаревшего объекта. Принадлежность проверяется под блокировкой строки в
        # той же транзакции, что и запись: changeform_view Django выполняет в
        # transaction.atomic, блокировка держится до конца запроса, включая инлайны.
        if change and not self.get_queryset(request).select_for_update(of=("self",)).filter(pk=obj.pk).exists():
            raise Http404("Клиент не найден")
        super().save_model(request, obj, form, change)  # type: ignore[arg-type]
        # Блокировка и разблокировка флагом в карточке — тоже действие для журнала.
        if change and "is_active" in form.changed_data:
            AuditLog.log_action(
                user=request.user,
                action="unblock_user" if obj.is_active else "block_user",
                resource_type="User",
                resource_id=obj.pk,
                changes={
                    "email": str(obj.email or ""),
                    "role": obj.role,
                    "blocked": not obj.is_active,
                    "source": "card",
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

    def response_change(self, request: HttpRequest, obj: User) -> HttpResponse:  # type: ignore[override]
        # Смена ИНН или страны переназначает ответственного (хук 42.2), и клиент
        # может уйти к другому менеджеру. Штатный редирект на его карточку
        # ответил бы 404 — вместо этого список с объяснением.
        if not self.get_queryset(request).filter(pk=obj.pk).exists():
            manager = obj.responsible_manager
            self.message_user(
                request,
                f"Клиент {obj.email or obj.pk} передан менеджеру "
                f"{manager.email if manager else 'без ответственного'} по правилу региона.",
                level="warning",
            )
            return HttpResponseRedirect(reverse(f"{self.admin_site.name}:users_user_changelist"))
        return super().response_change(request, obj)  # type: ignore[arg-type]


manager_site.register(User, ManagerClientAdmin)
