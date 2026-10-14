"""
Integration-тесты раздела менеджера `/manager/` — клиенты своего региона (стори 42.4).

Покрывает:
- AC1 — вход: менеджер и руководитель пускаются, остальные роли, суперпользователь
  (в том числе в группе «Менеджеры»), аноним и заблокированный менеджер — нет;
- AC2 — список и поиск только по своим клиентам, учётные записи сотрудников скрыты,
  `unregistered` — только с фильтром «Учётная запись на портале»;
- AC3 — 404 на чужого клиента по прямым URL, массовые действия его не трогают;
- AC4/AC5 — белый список полей карточки, подделанный POST, инлайны реквизитов
  и адресов только своего клиента;
- AC6 — разблокировка; AC7 — записи AuditLog; AC8 — ссылки и редиректы в разделе;
- AC9 — права внутри раздела при одном `view_user` (долг VG1 стори 42.1);
- AC10 — клиент ушёл к другому менеджеру после правки ИНН;
- AC11 — число запросов списка не зависит от числа клиентов.

Тесты транзакционные (autouse `clear_db_before_test` в `tests/conftest.py`):
правки групп внутри теста стирает `flush`, а следующий тест заново получает
группы из `role_groups`.
"""

from __future__ import annotations

import importlib
import itertools
import threading
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from django.apps import apps as django_apps
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.utils import label_for_field
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connection, connections, transaction
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.common.models import AuditLog, ManagerRoutingRule
from apps.users.manager_admin import ManagerClientAdmin
from apps.users.models import Address, Company, User
from apps.users.staff_roles import MANAGERS_GROUP, MARKETING_GROUP, SUPERVISORS_GROUP
from tests.conftest import get_unique_suffix

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

PASSWORD = "StrongPassword123!"
NEW_PASSWORD = "AnotherStrongPass456!"
INDEX_URL = "/manager/"
CHANGELIST_URL = "/manager/users/user/"

_migration = importlib.import_module("apps.users.migrations.0023_staff_role_groups")
_counter = itertools.count()

# Поля блока «Не показывать» section-contents: в HTML нет ни поля, ни подписи.
HIDDEN_FIELDS = (
    "is_staff",
    "is_superuser",
    "groups",
    "user_permissions",
    "onec_id",
    "onec_guid",
    "onec_price_type_id",
    "onec_link_candidates",
    "sync_status",
    "created_in_1c",
    "needs_1c_export",
    "last_sync_at",
    "last_sync_from_1c",
    "sync_error_message",
    "responsible_manager_manual",
)


@pytest.fixture(autouse=True)
def role_groups():
    """Группы ролей с полным набором прав — через функцию data-миграции 0023."""
    _migration.create_staff_role_groups(django_apps, SimpleNamespace(connection=connection))


@pytest.fixture(autouse=True)
def no_routing_rules():
    """
    Сид правил `0018` в тестовой БД то есть, то стёрт `flush`, а хук 42.2
    назначает ответственного при создании клиента — правила задаёт сам тест.
    """
    ManagerRoutingRule.objects.all().delete()


@pytest.fixture(autouse=True)
def verified_email_task():
    with patch("apps.users.signals.send_user_verified_email") as task:
        yield task


def unique_digits(length: int) -> str:
    value = (time.time_ns() + next(_counter) * 7919) % (10**length)
    return str(value).zfill(length)


def region_tax_id(region: str) -> str:
    return region + unique_digits(8)


def unique_tax_id() -> str:
    return region_tax_id("50")


def make_staff_member(group_name: str | None = MANAGERS_GROUP, **extra: Any) -> User:
    """Сотрудник роли: `is_staff=True`, член группы, не суперпользователь."""
    defaults = {
        "email": f"staff_{get_unique_suffix()}@freesportopt.ru",
        "first_name": "Сотрудник",
        "last_name": f"Тестов{next(_counter)}",
        "is_staff": True,
    }
    defaults.update(extra)
    member = User.objects.create_user(password=PASSWORD, **defaults)
    if group_name:
        member.groups.add(Group.objects.get(name=group_name))
    return User.objects.get(pk=member.pk)


def make_client(manager: User | None, **overrides: Any) -> User:
    """
    Клиент, закреплённый за менеджером.

    Хук 42.2 в `save()` перезаписал бы `responsible_manager` результатом правил,
    поэтому ответственный ставится `update()` после создания. Флаг «назначен
    вручную» по умолчанию стоит: подтверждение заявки и привязка к 1С иначе
    пересчитали бы ответственного по (пустым) правилам и увели клиента из раздела.
    """
    manual = overrides.pop("manual", True) and manager is not None
    defaults = {
        "email": f"client_{get_unique_suffix()}@example.com",
        "first_name": "Клиент",
        "last_name": f"Фамилия{next(_counter)}",
        "role": "wholesale_level1",
        "company_name": f"ООО Клиент {next(_counter)}",
        "tax_id": unique_tax_id(),
        "phone": f"+7900{unique_digits(7)}",
        "verification_status": "verified",
        "is_verified": True,
    }
    defaults.update(overrides)
    client = User.objects.create_user(password=PASSWORD, **defaults)
    User.objects.filter(pk=client.pk).update(responsible_manager=manager, responsible_manager_manual=manual)
    return User.objects.get(pk=client.pk)


def make_1c_record(tax_id: str, **overrides: Any) -> User:
    defaults = {
        "email": f"1c_{get_unique_suffix()}@example.com",
        "first_name": "Контрагент",
        "last_name": "Из1С",
        "company_name": "ООО Импортированное",
        "tax_id": tax_id,
        "role": User.ROLE_UNREGISTERED,
        "created_in_1c": True,
        "verification_status": "unverified",
        "onec_id": f"1C-{get_unique_suffix()}",
        "password": "",
    }
    defaults.update(overrides)
    record = User(**defaults)
    record.save()
    return record


def make_company(user: User, **overrides: Any) -> Company:
    defaults = {
        "legal_name": f"ООО Реквизиты {next(_counter)}",
        "tax_id": user.tax_id,
        "kpp": "770101001",
        "legal_address": "г. Москва, ул. Тверская, д. 1",
    }
    defaults.update(overrides)
    return Company.objects.create(user=user, **defaults)


def make_address(user: User, **overrides: Any) -> Address:
    defaults = {
        "full_name": "Получатель Тестов",
        "phone": "+79001234567",
        "city": "Москва",
        "street": "Тверская",
        "building": "1",
        "postal_code": "125009",
    }
    defaults.update(overrides)
    return Address.objects.create(user=user, **defaults)


def related_snapshot(user: User) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Company и адреса клиента как значения полей — для сравнения «до» и «после»."""
    company = Company.objects.filter(user=user).values().first() or {}
    addresses = list(Address.objects.filter(user=user).order_by("pk").values())
    return company, addresses


def inline_prefixes(response) -> dict[type, str]:
    """Префиксы формсетов инлайнов карточки по модели."""
    return {inline.formset.model: inline.formset.prefix for inline in response.context["inline_admin_formsets"]}


def change_url(user: User) -> str:
    return reverse("manager:users_user_change", args=[user.pk])


def history_url(user: User) -> str:
    return reverse("manager:users_user_history", args=[user.pk])


def verify_url(user: User) -> str:
    return reverse("manager:users_user_verify", args=[user.pk])


def password_url(user: User) -> str:
    return reverse("manager:auth_user_password_change", args=[user.pk])


def post_action(client, action: str, *targets: User, follow: bool = True, **extra: Any):
    payload = {"action": action, "_selected_action": [str(target.pk) for target in targets]}
    payload.update(extra)
    return client.post(CHANGELIST_URL, payload, follow=follow)


def message_texts(response) -> list[str]:
    return [str(message) for message in response.context["messages"]]


def audit_records(user: User, action: str | None = None):
    records = AuditLog.objects.filter(resource_type="User", resource_id=str(user.pk))
    return records.filter(action=action) if action else records


def form_payload(response) -> dict[str, Any]:
    """POST-данные карточки из GET-контекста: поля формы и формсеты инлайнов."""

    def put(data: dict[str, Any], name: str, value: Any) -> None:
        if value is None or value is False:
            return
        data[name] = "on" if value is True else value

    data: dict[str, Any] = {}
    form = response.context["adminform"].form
    for name in form.fields:
        put(data, name, form[name].value())
    for inline in response.context["inline_admin_formsets"]:
        formset = inline.formset
        management = formset.management_form
        for name in management.fields:
            data[f"{formset.prefix}-{name}"] = management[name].value()
        for inline_form in formset.forms:
            for name in inline_form.fields:
                put(data, inline_form.add_prefix(name), inline_form[name].value())
    return data


@pytest.fixture
def manager() -> User:
    return make_staff_member(MANAGERS_GROUP, first_name="Анна", last_name="Менеджерова")


@pytest.fixture
def other_manager() -> User:
    return make_staff_member(MANAGERS_GROUP)


@pytest.fixture
def manager_client(client, manager):
    client.force_login(manager)
    return client


@pytest.fixture(params=[MANAGERS_GROUP, SUPERVISORS_GROUP], ids=["manager", "supervisor"])
def section_member(request) -> User:
    """
    Сотрудник каждой группы, которую пускает раздел.

    Руководитель в 42.4 видит только своих клиентов (решение 3). Негативные
    проверки видимости идут от обеих групп: если `scope_clients` откроет
    руководителю весь queryset раньше 42.7, упадёт вариант `supervisor`.
    """
    return make_staff_member(request.param)


@pytest.fixture
def section_client(client, section_member):
    client.force_login(section_member)
    return client


class TestEntry:
    """AC1 — кто входит в раздел."""

    @pytest.mark.parametrize("group_name", [MANAGERS_GROUP, SUPERVISORS_GROUP])
    def test_manager_and_supervisor_enter(self, client, group_name):
        client.force_login(make_staff_member(group_name))

        for url in (INDEX_URL, CHANGELIST_URL):
            response = client.get(url)
            assert response.status_code == 200, url
            assert "FREESPORT — Менеджер" in response.content.decode()

    @pytest.mark.parametrize(
        "make_user",
        [
            pytest.param(lambda: make_staff_member(MARKETING_GROUP), id="marketing"),
            pytest.param(lambda: make_staff_member(None), id="staff-without-group"),
            pytest.param(
                lambda: User.objects.create_superuser(email=f"su_{get_unique_suffix()}@example.com", password=PASSWORD),
                id="superuser",
            ),
            pytest.param(
                lambda: make_staff_member(MANAGERS_GROUP, is_superuser=True),
                id="superuser-in-managers-group",
            ),
            pytest.param(lambda: make_staff_member(MANAGERS_GROUP, is_active=False), id="blocked-manager"),
            pytest.param(lambda: make_staff_member(MANAGERS_GROUP, is_staff=False), id="manager-without-is-staff"),
            pytest.param(None, id="anonymous"),
        ],
    )
    def test_others_are_redirected_to_login(self, client, make_user):
        if make_user is not None:
            client.force_login(make_user())

        for url in (INDEX_URL, CHANGELIST_URL):
            response = client.get(url)
            assert response.status_code == 302, url
            assert "/manager/login/" in response.url

    def test_superuser_keeps_admin(self, client):
        """Суперпользователь в группе «Менеджеры» по-прежнему работает в /admin/."""
        client.force_login(make_staff_member(MANAGERS_GROUP, is_superuser=True))
        assert client.get("/admin/").status_code == 200


class TestChangelist:
    """AC2 — список и поиск только по своим клиентам."""

    def test_search_finds_only_own_clients(self, section_client, section_member, other_manager):
        own = make_client(section_member, customer_code=unique_digits(5))
        foreign = make_client(
            other_manager,
            customer_code=unique_digits(5),
            last_name="Чужаков",
            company_name="ООО Чужая Компания",
        )

        listed = section_client.get(CHANGELIST_URL).context["cl"].result_list
        assert own in listed
        assert foreign not in listed

        for query in (
            foreign.email,
            foreign.tax_id,
            foreign.phone,
            foreign.last_name,
            foreign.company_name,
            foreign.customer_code,
        ):
            result = section_client.get(CHANGELIST_URL, {"q": query}).context["cl"].result_list
            assert foreign not in result, query

        # Поиск сам по себе работает: те же поля своего клиента находятся.
        for query in (own.email, own.tax_id, own.phone, own.last_name, own.company_name, own.customer_code):
            result = section_client.get(CHANGELIST_URL, {"q": query}).context["cl"].result_list
            assert own in result, query

    def test_staff_accounts_are_hidden(self, manager_client, manager):
        """По одной записи на каждое условие `staff_accounts_q()`."""
        staff = make_client(manager)
        User.objects.filter(pk=staff.pk).update(is_staff=True)
        superuser = make_client(manager)
        User.objects.filter(pk=superuser.pk).update(is_superuser=True)
        robot = make_client(manager)
        User.objects.filter(pk=robot.pk).update(role="admin")
        marketer = make_client(manager)
        marketer.groups.add(Group.objects.get(name=MARKETING_GROUP))
        own = make_client(manager)

        listed = list(manager_client.get(CHANGELIST_URL, {"portal_account": "all"}).context["cl"].result_list)

        assert listed == [own]

    def test_unregistered_hidden_by_default(self, manager_client, manager):
        record = make_client(manager, role=User.ROLE_UNREGISTERED, verification_status="unverified", is_verified=False)
        own = make_client(manager)

        def listed(params: dict[str, str]) -> list[User]:
            return list(manager_client.get(CHANGELIST_URL, params).context["cl"].result_list)

        assert listed({}) == [own]
        assert listed({"portal_account": "no"}) == [record]
        assert set(listed({"portal_account": "all"})) == {own, record}
        assert listed({"role__exact": User.ROLE_UNREGISTERED}) == [record]

    def test_columns_filters_and_title(self, manager_client, manager):
        make_client(manager)

        response = manager_client.get(CHANGELIST_URL)

        cl = response.context["cl"]
        assert list(cl.list_display) == [
            "action_checkbox",
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
        filters = [getattr(spec, "field_path", None) or spec.parameter_name for spec in cl.filter_specs]
        assert filters == ["role", "verification_status", "has_1c_candidate", "is_active", "portal_account"]
        content = response.content.decode()
        assert "<h1>Клиенты</h1>" in content
        assert 'class="addlink"' not in content
        assert "/manager/users/user/add/" not in content

    def test_index_names_block_clients(self, manager_client):
        response = manager_client.get(INDEX_URL)

        users_app = next(app for app in response.context["app_list"] if app["app_label"] == "users")
        assert users_app["name"] == "Клиенты"
        assert [model["name"] for model in users_app["models"]] == ["Клиенты"]


class TestForeignClient:
    """AC3 — 404 на чужого клиента."""

    def test_direct_urls_answer_404(self, section_client, section_member, other_manager):
        own = make_client(section_member, verification_status="pending", is_verified=False, is_active=False)
        foreign = make_client(other_manager, verification_status="pending", is_verified=False, is_active=False)
        source = make_1c_record(foreign.tax_id)

        # Контроль: те же адреса своего клиента открываются — 404 ниже не от отказа во входе.
        for url in (change_url(own), history_url(own), verify_url(own), password_url(own)):
            assert section_client.get(url).status_code == 200, url

        assert section_client.get(change_url(foreign)).status_code == 404
        assert section_client.post(change_url(foreign), {"email": "hacked@example.com"}).status_code == 404
        assert section_client.get(history_url(foreign)).status_code == 404
        assert section_client.get(verify_url(foreign)).status_code == 404
        response = section_client.post(
            verify_url(foreign), {"confirm": "on", "candidate": f"{source.pk}:{source.onec_id}"}
        )
        assert response.status_code == 404
        assert section_client.post(verify_url(foreign), {"_reject": "1"}).status_code == 404
        assert section_client.get(password_url(foreign)).status_code == 404
        response = section_client.post(
            password_url(foreign),
            {"usable_password": "true", "password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
        )
        assert response.status_code == 404

        foreign.refresh_from_db()
        assert foreign.email != "hacked@example.com"
        assert foreign.verification_status == "pending"
        assert not foreign.onec_id
        assert foreign.check_password(PASSWORD)
        assert not audit_records(foreign).exists()

    @pytest.mark.parametrize(
        "action, foreign_state, field, expected",
        [
            (
                "approve_b2b_users",
                {"verification_status": "pending", "is_verified": False},
                "verification_status",
                "pending",
            ),
            (
                "reject_b2b_users",
                {"verification_status": "pending", "is_verified": False},
                "verification_status",
                "pending",
            ),
            ("block_users", {"is_active": True}, "is_active", True),
            ("unblock_users", {"is_active": False}, "is_active", False),
        ],
    )
    def test_mass_action_skips_forged_foreign_id(
        self, manager_client, manager, other_manager, action, foreign_state, field, expected
    ):
        own = make_client(manager, **foreign_state)
        foreign = make_client(other_manager, **foreign_state)

        post_action(manager_client, action, own, foreign)

        foreign.refresh_from_db()
        assert getattr(foreign, field) == expected
        assert not audit_records(foreign).exists()
        # Своего клиента действие при этом обработало.
        assert audit_records(own).count() == 1

    def test_link_action_skips_forged_foreign_id(self, manager_client, other_manager):
        foreign = make_client(other_manager, verification_status="pending", is_verified=False)
        source = make_1c_record(foreign.tax_id)

        post_action(manager_client, "link_1c_customer", foreign, apply="1", candidate=f"{source.pk}:{source.onec_id}")

        foreign.refresh_from_db()
        assert not foreign.onec_id
        assert not audit_records(foreign).exists()


class TestClientCard:
    """AC4, AC5 — белый список полей карточки."""

    def test_card_shows_only_whitelisted_fields(self, manager_client, manager):
        own = make_client(manager)

        response = manager_client.get(change_url(own))

        assert response.status_code == 200
        adminform = response.context["adminform"]
        assert set(adminform.form.fields) == {
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "company_name",
            "tax_id",
            "country",
            "is_active",
        }
        assert set(adminform.readonly_fields) == {
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
        }
        prefixes = {inline.formset.prefix for inline in response.context["inline_admin_formsets"]}
        assert len(prefixes) == 2

        content = response.content.decode()
        for field in HIDDEN_FIELDS:
            assert f'name="{field}"' not in content, field
            # Подпись — как её вывела бы полная карточка /admin/ (поле модели или display-метод).
            label = str(label_for_field(field, User, admin.site._registry[User]))
            assert label not in content, (field, label)
        assert 'class="deletelink"' not in content
        assert reverse("manager:users_user_delete", args=[own.pk]) not in content
        assert 'class="addlink"' not in content

    def test_responsible_manager_is_text_without_link(self, manager_client, manager):
        own = make_client(manager)

        content = manager_client.get(change_url(own)).content.decode()

        assert f"Анна Менеджерова ({manager.email})" in content
        assert f"/manager/users/user/{manager.pk}/" not in content

    def test_forged_post_changes_only_allowed_fields(self, manager_client, manager, other_manager):
        own = make_client(manager, verification_status="pending", is_verified=False, customer_code=unique_digits(5))
        before = User.objects.get(pk=own.pk)
        data = form_payload(manager_client.get(change_url(own)))
        data.update(
            {
                "phone": "+79001112233",
                "role": "wholesale_level3",
                "is_staff": "on",
                "is_superuser": "on",
                "groups": [str(Group.objects.get(name=SUPERVISORS_GROUP).pk)],
                "onec_id": "FORGED-1C",
                "verification_status": "verified",
                "is_verified": "on",
                "customer_code": "99999",
                "responsible_manager": str(other_manager.pk),
                "responsible_manager_manual": "",
                "_save": "Сохранить",
            }
        )

        response = manager_client.post(change_url(own), data)

        assert response.status_code == 302, response.context["adminform"].form.errors if response.context else ""
        own.refresh_from_db()
        assert own.phone == "+79001112233"
        assert own.role == before.role
        assert not own.is_staff
        assert not own.is_superuser
        assert not own.groups.exists()
        assert own.onec_id == before.onec_id
        assert own.verification_status == "pending"
        assert not own.is_verified
        assert own.customer_code == before.customer_code
        assert own.responsible_manager == manager
        assert own.responsible_manager_manual


def form_index(data: dict[str, Any], prefix: str, obj: Any) -> int:
    """Номер формы формсета, которая редактирует `obj`."""
    total = int(data[f"{prefix}-TOTAL_FORMS"])
    return next(index for index in range(total) if str(data.get(f"{prefix}-{index}-id")) == str(obj.pk))


class TestClientInlines:
    """AC4, AC3 — реквизиты и адреса правятся только у своего клиента."""

    def test_own_company_and_addresses_are_saved(self, manager_client, manager):
        own = make_client(manager)
        company = make_company(own)
        kept = make_address(own, city="Москва")
        removed = make_address(own, city="Тула")
        response = manager_client.get(change_url(own))
        prefixes = inline_prefixes(response)
        company_prefix, address_prefix = prefixes[Company], prefixes[Address]
        data = form_payload(response)

        data[f"{company_prefix}-0-legal_name"] = "ООО Новые реквизиты"
        data[f"{company_prefix}-0-kpp"] = "771001001"
        data[f"{address_prefix}-{form_index(data, address_prefix, kept)}-city"] = "Казань"
        data[f"{address_prefix}-{form_index(data, address_prefix, removed)}-DELETE"] = "on"
        added = int(data[f"{address_prefix}-TOTAL_FORMS"])
        data[f"{address_prefix}-TOTAL_FORMS"] = str(added + 1)
        data.update(
            {
                f"{address_prefix}-{added}-address_type": "shipping",
                f"{address_prefix}-{added}-full_name": "Новый Получатель",
                f"{address_prefix}-{added}-phone": "+79007654321",
                f"{address_prefix}-{added}-city": "Сочи",
                f"{address_prefix}-{added}-street": "Морская",
                f"{address_prefix}-{added}-building": "5",
                "_save": "Сохранить",
            }
        )

        response = manager_client.post(change_url(own), data)

        assert response.status_code == 302, response.context["errors"] if response.context else ""
        company.refresh_from_db()
        assert company.legal_name == "ООО Новые реквизиты"
        assert company.kpp == "771001001"
        kept.refresh_from_db()
        assert kept.city == "Казань"
        assert not Address.objects.filter(pk=removed.pk).exists()
        assert sorted(Address.objects.filter(user=own).values_list("city", flat=True)) == ["Казань", "Сочи"]

    @pytest.mark.parametrize("mode", ["change", "delete"])
    def test_forged_foreign_inline_ids_change_nothing(self, manager_client, manager, other_manager, mode):
        own = make_client(manager)
        own_company = make_company(own)
        own_address = make_address(own)
        foreign = make_client(other_manager)
        foreign_company = make_company(foreign)
        foreign_address = make_address(foreign)
        foreign_before = related_snapshot(foreign)
        response = manager_client.get(change_url(own))
        prefixes = inline_prefixes(response)
        company_prefix, address_prefix = prefixes[Company], prefixes[Address]
        data = form_payload(response)
        index = form_index(data, address_prefix, own_address)

        # ID записей чужого клиента вместо своих — в формах, где они уже стоят.
        data[f"{address_prefix}-{index}-id"] = str(foreign_address.pk)
        if mode == "change":
            data[f"{company_prefix}-0-id"] = str(foreign_company.pk)
            data[f"{company_prefix}-0-legal_name"] = "ООО Подмена"
            data[f"{address_prefix}-{index}-city"] = "Подмена"
        else:
            data[f"{address_prefix}-{index}-DELETE"] = "on"
        data["_save"] = "Сохранить"

        response = manager_client.post(change_url(own), data)

        if mode == "change":
            # Чужой ID не входит в queryset формсета — форма с ошибкой, ничего не сохранено.
            assert response.status_code == 200
            assert response.context["errors"]
        assert related_snapshot(foreign) == foreign_before
        own_company.refresh_from_db()
        assert own_company.legal_name != "ООО Подмена"
        assert list(Address.objects.filter(user=own).values_list("pk", "city")) == [(own_address.pk, own_address.city)]
        assert not audit_records(foreign).exists()


class TestUnblock:
    """AC6 — разблокировка."""

    def test_unblock_restores_login(self, manager_client, manager):
        blocked = make_client(manager, is_active=False)
        assert authenticate(email=blocked.email, password=PASSWORD) is None

        post_action(manager_client, "unblock_users", blocked)

        blocked.refresh_from_db()
        assert blocked.is_active
        assert authenticate(email=blocked.email, password=PASSWORD) == blocked
        assert audit_records(blocked, "unblock_user").count() == 1
        assert audit_records(blocked).count() == 1

    def test_pending_application_and_superuser_are_skipped(self, manager_client, manager):
        pending = make_client(manager, is_active=False, verification_status="pending", is_verified=False)
        superuser = User.objects.create_superuser(
            email=f"su_{get_unique_suffix()}@example.com", password=PASSWORD, is_active=False
        )
        User.objects.filter(pk=superuser.pk).update(responsible_manager=manager)

        response = post_action(manager_client, "unblock_users", pending, superuser)

        pending.refresh_from_db()
        superuser.refresh_from_db()
        assert not pending.is_active
        assert not superuser.is_active
        assert not audit_records(pending).exists()
        assert not audit_records(superuser).exists()
        texts = message_texts(response)
        assert any(f"/manager/users/user/{pending.pk}/verify/" in text for text in texts)

    def test_empty_selection_warns(self, manager_client, manager):
        active = make_client(manager)

        response = post_action(manager_client, "unblock_users", active)

        assert any("ни одного заблокированного" in text for text in message_texts(response))
        assert not audit_records(active).exists()


class TestAuditLog:
    """AC7 — на одно действие одна запись своего вида, автор — менеджер."""

    def assert_single(self, client_user: User, action: str, manager: User) -> AuditLog:
        records = list(audit_records(client_user))
        assert [record.action for record in records] == [action]
        assert records[0].user == manager
        return records[0]

    def test_verify_page_decision(self, manager_client, manager):
        applicant = make_client(manager, verification_status="pending", is_verified=False, is_active=False)

        response = manager_client.post(
            verify_url(applicant), {"confirm": "on", "confirm_without_1c": "on", "role": "wholesale_level1"}
        )

        assert response.status_code == 302
        assert response.url == change_url(applicant)
        self.assert_single(applicant, "verify_b2b", manager)

    def test_verify_page_with_link_writes_two_kinds(self, manager_client, manager):
        applicant = make_client(manager, verification_status="pending", is_verified=False, is_active=False)
        source = make_1c_record(applicant.tax_id)

        response = manager_client.post(
            verify_url(applicant),
            {"confirm": "on", "candidate": f"{source.pk}:{source.onec_id}", "role": "wholesale_level1"},
        )

        assert response.status_code == 302
        actions = sorted(audit_records(applicant).values_list("action", flat=True))
        assert actions == ["link_1c_customer", "verify_b2b"]

    def test_verify_page_reject(self, manager_client, manager):
        applicant = make_client(manager, verification_status="pending", is_verified=False, is_active=False)

        response = manager_client.post(verify_url(applicant), {"_reject": "1"})

        assert response.status_code == 302
        assert response.url == change_url(applicant)
        self.assert_single(applicant, "reject_b2b", manager)

    @pytest.mark.parametrize(
        "action, state, expected",
        [
            ("approve_b2b_users", {"verification_status": "pending", "is_verified": False}, "approve_b2b"),
            ("reject_b2b_users", {"verification_status": "pending", "is_verified": False}, "reject_b2b"),
            ("block_users", {}, "block_user"),
            ("unblock_users", {"is_active": False}, "unblock_user"),
        ],
    )
    def test_mass_actions(self, manager_client, manager, action, state, expected):
        target = make_client(manager, **state)

        post_action(manager_client, action, target)

        self.assert_single(target, expected, manager)

    def test_link_action(self, manager_client, manager):
        applicant = make_client(manager, verification_status="pending", is_verified=False)
        source = make_1c_record(applicant.tax_id)

        post_action(manager_client, "link_1c_customer", applicant, apply="1", candidate=f"{source.pk}:{source.onec_id}")

        applicant.refresh_from_db()
        assert applicant.onec_id == source.onec_id
        self.assert_single(applicant, "link_1c_customer", manager)

    def test_password_change(self, manager_client, manager):
        target = make_client(manager)

        response = manager_client.post(
            password_url(target),
            {"usable_password": "true", "password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
        )

        assert response.status_code == 302
        assert response.url == change_url(target)
        target.refresh_from_db()
        assert target.check_password(NEW_PASSWORD)
        self.assert_single(target, "change_password", manager)

    @pytest.mark.parametrize("initially_active, expected", [(True, "block_user"), (False, "unblock_user")])
    def test_card_active_flag(self, manager_client, manager, initially_active, expected):
        target = make_client(manager, is_active=initially_active)
        data = form_payload(manager_client.get(change_url(target)))
        if initially_active:
            data.pop("is_active")
        else:
            data["is_active"] = "on"
        data["_save"] = "Сохранить"

        response = manager_client.post(change_url(target), data)

        assert response.status_code == 302
        target.refresh_from_db()
        assert target.is_active is not initially_active
        record = self.assert_single(target, expected, manager)
        assert record.details["changes"]["source"] == "card"
        assert record.details["changes"]["blocked"] is initially_active

    def test_card_save_without_flag_change_writes_nothing(self, manager_client, manager):
        target = make_client(manager)
        data = form_payload(manager_client.get(change_url(target)))
        data["phone"] = "+79005554433"
        data["_save"] = "Сохранить"

        assert manager_client.post(change_url(target), data).status_code == 302
        assert not audit_records(target).exists()


class TestLinksStayInSection:
    """AC8 — ни одна ссылка и ни один редирект не ведут в /admin/."""

    @staticmethod
    def assert_no_admin_links(response) -> None:
        assert response.status_code == 200
        assert 'href="/admin/' not in response.content.decode()

    def test_pages_have_no_admin_links(self, manager_client, manager):
        applicant = make_client(manager, verification_status="pending", is_verified=False, is_active=False)
        make_1c_record(applicant.tax_id)
        target = make_client(manager)

        # Сохранение карточки создаёт LogEntry: без своей главной (решение 13)
        # блок «Последние действия» вёл бы в /admin/users/user/<id>/change/.
        data = form_payload(manager_client.get(change_url(target)))
        data["_save"] = "Сохранить"
        response = manager_client.post(change_url(target), data)
        assert response.status_code == 302
        assert response.url.startswith("/manager/")
        assert LogEntry.objects.filter(user=manager).exists()

        index = manager_client.get(INDEX_URL)
        self.assert_no_admin_links(index)
        assert "recent-actions-module" not in index.content.decode()

        self.assert_no_admin_links(manager_client.get(CHANGELIST_URL))
        self.assert_no_admin_links(manager_client.get(change_url(applicant)))
        self.assert_no_admin_links(manager_client.get(verify_url(applicant)))
        self.assert_no_admin_links(manager_client.get(password_url(target)))
        link_page = post_action(manager_client, "link_1c_customer", applicant, follow=False)
        self.assert_no_admin_links(link_page)
        assert "/manager/" in link_page.content.decode()

        # Кнопка «Подтвердить заявку» в карточке и ссылка в списке — в разделе.
        assert verify_url(applicant) in manager_client.get(change_url(applicant)).content.decode()
        assert verify_url(applicant) in manager_client.get(CHANGELIST_URL).content.decode()

    def test_change_with_continue_stays_in_section(self, manager_client, manager):
        target = make_client(manager)
        data = form_payload(manager_client.get(change_url(target)))
        data["_continue"] = "1"

        response = manager_client.post(change_url(target), data)

        assert response.status_code == 302
        assert response.url.startswith(change_url(target))

    def test_link_warning_after_approve_points_to_section(self, manager_client, manager):
        applicant = make_client(manager, verification_status="pending", is_verified=False)
        make_1c_record(applicant.tax_id)

        response = post_action(manager_client, "approve_b2b_users", applicant)

        texts = message_texts(response)
        assert any(change_url(applicant) in text for text in texts)
        assert not any("/admin/" in text for text in texts)


class TestViewOnlyPermissions:
    """AC9 — внутренние проверки права change в разделе (долг VG1 стори 42.1)."""

    @pytest.fixture(autouse=True)
    def view_only_group(self):
        group = Group.objects.get(name=MANAGERS_GROUP)
        view_only = [Permission.objects.get(content_type__app_label="users", codename="view_user")]
        full = list(group.permissions.all())
        group.permissions.set(view_only)
        return SimpleNamespace(group=group, full=full, view_only=view_only)

    def test_card_post_is_forbidden(self, manager_client, manager, view_only_group):
        own = make_client(manager)
        make_company(own)
        address = make_address(own)
        # Форма, какую отправил бы менеджер с полными правами, — снята до урезания прав.
        view_only_group.group.permissions.set(view_only_group.full)
        response = manager_client.get(change_url(own))
        prefixes = inline_prefixes(response)
        data = form_payload(response)
        view_only_group.group.permissions.set(view_only_group.view_only)
        before = User.objects.filter(pk=own.pk).values().get()
        related_before = related_snapshot(own)
        data.update(
            {
                "first_name": "Подмена",
                "phone": "+79001112233",
                f"{prefixes[Company]}-0-legal_name": "ООО Подмена",
                f"{prefixes[Address]}-{form_index(data, prefixes[Address], address)}-city": "Подмена",
                "_save": "Сохранить",
            }
        )

        data.pop("is_active", None)  # снятый флаг — попытка заблокировать

        response = manager_client.post(change_url(own), data)

        assert response.status_code == 403
        assert User.objects.filter(pk=own.pk).values().get() == before
        assert related_snapshot(own) == related_before
        assert not audit_records(own).exists()
        assert not LogEntry.objects.filter(object_id=str(own.pk)).exists()

    def test_card_is_read_only_without_verify_button(self, manager_client, manager):
        applicant = make_client(manager, verification_status="pending", is_verified=False, is_active=False)

        response = manager_client.get(change_url(applicant))

        assert response.status_code == 200
        assert response.context["show_verify_b2b_button"] is False
        assert not response.context["has_change_permission"]
        assert verify_url(applicant) not in response.content.decode()

    def test_verify_and_password_are_forbidden(self, manager_client, manager):
        applicant = make_client(manager, verification_status="pending", is_verified=False, is_active=False)

        assert manager_client.get(verify_url(applicant)).status_code == 403
        response = manager_client.post(
            verify_url(applicant), {"confirm": "on", "confirm_without_1c": "on", "role": "wholesale_level1"}
        )
        assert response.status_code == 403
        assert manager_client.post(verify_url(applicant), {"_reject": "1"}).status_code == 403
        assert manager_client.get(password_url(applicant)).status_code == 403
        response = manager_client.post(
            password_url(applicant),
            {"usable_password": "true", "password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
        )
        assert response.status_code == 403

        applicant.refresh_from_db()
        assert applicant.verification_status == "pending"
        assert applicant.check_password(PASSWORD)
        assert not audit_records(applicant).exists()

    @pytest.mark.parametrize(
        "action", ["approve_b2b_users", "reject_b2b_users", "block_users", "unblock_users", "link_1c_customer"]
    )
    def test_actions_are_unavailable(self, manager_client, manager, action):
        target = make_client(manager, verification_status="pending", is_verified=False)

        changelist = manager_client.get(CHANGELIST_URL)
        assert changelist.status_code == 200
        assert not changelist.context["action_form"]

        post_action(manager_client, action, target)

        changed = User.objects.get(pk=target.pk)
        assert changed.is_active == target.is_active
        assert changed.verification_status == "pending"
        assert not audit_records(target).exists()


class TestClientMovedAway:
    """AC10 — клиент ушёл к другому менеджеру после правки ИНН."""

    def test_redirect_to_changelist_with_message(self, manager_client, manager, other_manager):
        ManagerRoutingRule.objects.create(match_type="inn_region", match_value="23", manager=manager)
        ManagerRoutingRule.objects.create(match_type="inn_region", match_value="77", manager=other_manager)
        # Клиент, созданный после правил, получает ответственного хуком 42.2.
        client_user = User.objects.create_user(
            email=f"client_{get_unique_suffix()}@example.com",
            password=PASSWORD,
            role="wholesale_level1",
            company_name="ООО Регион 23",
            tax_id=region_tax_id("23"),
            verification_status="verified",
            is_verified=True,
        )
        assert User.objects.get(pk=client_user.pk).responsible_manager == manager

        data = form_payload(manager_client.get(change_url(client_user)))
        data["tax_id"] = region_tax_id("77")
        data["_continue"] = "1"
        response = manager_client.post(change_url(client_user), data)

        assert response.status_code == 302
        assert response.url == CHANGELIST_URL
        client_user.refresh_from_db()
        assert client_user.tax_id == data["tax_id"]
        assert client_user.responsible_manager == other_manager
        texts = message_texts(manager_client.get(response.url))
        assert any(f"передан менеджеру {other_manager.email} по правилу региона" in text for text in texts)


def in_other_connection(func: Any) -> Any:
    """Выполнить `func` в отдельном потоке — своё соединение и своя транзакция."""
    outcome: dict[str, Any] = {}

    def run() -> None:
        try:
            outcome["result"] = func()
        except BaseException as exc:  # noqa: BLE001 — исключение возвращается в тест
            outcome["error"] = exc
        finally:
            connections.close_all()

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(timeout=30)
    assert not thread.is_alive(), "второе соединение зависло"
    if "error" in outcome:
        raise outcome["error"]
    return outcome["result"]


def row_is_locked(pk: int) -> bool:
    """Строку пользователя держит чужая транзакция: `FOR UPDATE NOWAIT` из второго соединения."""

    def probe() -> bool:
        try:
            with transaction.atomic():
                User.objects.select_for_update(nowait=True).filter(pk=pk).exists()
        except DatabaseError:
            return True
        return False

    return bool(in_other_connection(probe))


@pytest.fixture
def prod_like_requests(monkeypatch):
    """
    Запросы без `ATOMIC_REQUESTS`, как на production.

    Тестовые настройки оборачивают каждый запрос в транзакцию: там блокировка
    строки работала бы и без собственной транзакции раздела.
    """
    monkeypatch.setitem(connections.settings[DEFAULT_DB_ALIAS], "ATOMIC_REQUESTS", False)


@pytest.fixture
def locked_at_save(monkeypatch) -> dict[int, bool]:
    """`{pk: строка заблокирована}` в момент первого `User.save()` этой записи."""
    seen: dict[int, bool] = {}
    original_save = User.save

    def save(self: User, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None and self.pk not in seen:
            seen[self.pk] = row_is_locked(self.pk)
        original_save(self, *args, **kwargs)

    monkeypatch.setattr(User, "save", save)
    return seen


class TestTransferDuringWrite:
    """
    R42.4-1 — передача клиента другому менеджеру между чтением и записью.

    Устаревший объект карточки не должен вернуть прежнего ответственного, а
    действие — изменить клиента, который уже вышел из выборки менеджера.
    """

    def test_card_save_after_transfer_answers_404(self, manager_client, manager, other_manager, prod_like_requests):
        own = make_client(manager, manual=False)
        phone_before = own.phone
        data = form_payload(manager_client.get(change_url(own)))
        data.update({"phone": "+79005556677", "_save": "Сохранить"})
        original_save_form = ManagerClientAdmin.save_form

        def transfer_then_save_form(self: ManagerClientAdmin, request: Any, form: Any, change: bool) -> Any:
            # Карточка уже прочитана (get_object), запись (save_model) впереди:
            # пересчёт передаёт клиента B и фиксирует транзакцию.
            in_other_connection(lambda: User.objects.filter(pk=own.pk).update(responsible_manager=other_manager))
            return original_save_form(self, request, form, change)

        with patch.object(ManagerClientAdmin, "save_form", transfer_then_save_form):
            response = manager_client.post(change_url(own), data)

        assert response.status_code == 404
        own.refresh_from_db()
        assert own.responsible_manager == other_manager
        assert own.phone == phone_before
        assert not audit_records(own).exists()

    def test_card_save_holds_row_lock(self, manager_client, manager, prod_like_requests, locked_at_save):
        own = make_client(manager)
        data = form_payload(manager_client.get(change_url(own)))
        data.update({"phone": "+79005556678", "_save": "Сохранить"})

        response = manager_client.post(change_url(own), data)

        assert response.status_code == 302
        assert locked_at_save[own.pk] is True
        own.refresh_from_db()
        assert own.phone == "+79005556678"

    @pytest.mark.parametrize(
        "action, overrides",
        [
            ("approve_b2b_users", {"verification_status": "pending", "is_verified": False, "is_active": False}),
            ("reject_b2b_users", {"verification_status": "pending", "is_verified": False}),
            ("block_users", {}),
            ("unblock_users", {"is_active": False}),
        ],
    )
    def test_actions_hold_row_lock(
        self, manager_client, manager, prod_like_requests, locked_at_save, action, overrides
    ):
        own = make_client(manager, **overrides)
        before = audit_records(own).count()

        response = post_action(manager_client, action, own)

        assert response.status_code == 200
        assert locked_at_save[own.pk] is True
        assert audit_records(own).count() == before + 1


class TestChangelistQueryCount:
    """AC11 — число SQL-запросов списка не зависит от числа клиентов (NFR-42-04)."""

    def test_query_count_does_not_grow_with_rows(self, manager_client, manager, django_assert_num_queries):
        def add_applicants_with_candidates(count: int) -> None:
            # Каждая строка — заявка с кандидатом 1С: так замер ловит и запросы,
            # которые display-методы `has_1c_candidate`/`verify_b2b_link` делали бы
            # только для таких строк.
            for _ in range(count):
                tax_id = unique_tax_id()
                make_1c_record(tax_id)
                make_client(manager, tax_id=tax_id, verification_status="pending", is_verified=False)

        add_applicants_with_candidates(5)
        with CaptureQueriesContext(connection) as captured:
            first = manager_client.get(CHANGELIST_URL)
        assert first.status_code == 200
        assert len(first.context["cl"].result_list) == 5
        baseline = len(captured)

        add_applicants_with_candidates(45)
        with django_assert_num_queries(baseline):
            second = manager_client.get(CHANGELIST_URL)
        rows = second.context["cl"].result_list
        assert len(rows) == 50
        assert all(row._has_1c_candidate for row in rows)
