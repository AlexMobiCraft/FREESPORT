"""
Unit-тесты сервиса ответственного менеджера (стори 42.2).

Покрывает:
- region_key — ключ региона клиента (страна или код субъекта РФ по ИНН);
- resolve_responsible — правило региона, страны, резерв, источник назначения;
- is_staff_account — критерий «сотрудник»;
- assign_responsible_manager — назначение в памяти, ручное назначение, сотрудники;
- reassign_clients_for_key и affected_keys — массовый пересчёт при смене правила (AC6, AC8).
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.common.models import ManagerRoutingRule
from apps.users.models import User
from apps.users.services.responsible_manager import (
    SOURCE_COUNTRY,
    SOURCE_FALLBACK,
    SOURCE_NONE,
    SOURCE_REGION,
    affected_keys,
    assign_responsible_manager,
    is_staff_account,
    reassign_clients_for_key,
    region_key,
    resolve_responsible,
)
from apps.users.staff_roles import MANAGERS_GROUP, MARKETING_GROUP, SUPERVISORS_GROUP
from tests.conftest import get_unique_suffix

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

INN_REGION = ManagerRoutingRule.MATCH_INN_REGION
COUNTRY = ManagerRoutingRule.MATCH_COUNTRY
FALLBACK = ManagerRoutingRule.MATCH_FALLBACK


@pytest.fixture(autouse=True)
def _clear_routing_rules(db):
    """Изолируем тесты от правил, засеянных data-миграцией common/0018."""
    ManagerRoutingRule.objects.all().delete()


def make_staff(group: str = MANAGERS_GROUP, **extra) -> User:
    user = User.objects.create_user(
        email=f"staff_{get_unique_suffix()}@freesportopt.ru",
        password="StrongPassword123!",
        is_staff=True,
        **extra,
    )
    user.groups.add(Group.objects.get_or_create(name=group)[0])
    return user


def make_client(tax_id: str = "", country: str = User.COUNTRY_RUSSIA, **extra) -> User:
    extra.setdefault("role", "wholesale_level1")
    return User.objects.create_user(
        email=f"client_{get_unique_suffix()}@example.com",
        password="StrongPassword123!",
        tax_id=tax_id,
        country=country,
        **extra,
    )


def rule(match_type: str, match_value: str, manager: User | None = None, email: str = "", active: bool = True):
    return ManagerRoutingRule.objects.create(
        match_type=match_type,
        match_value=match_value,
        manager=manager,
        manager_email=email or ("" if manager else f"rule_{get_unique_suffix()}@freesportopt.ru"),
        is_active=active,
    )


def assert_mass_equals_single(users) -> None:
    """Инвариант: после массового пересчёта у клиента тот же ответственный, что даёт поштучное разрешение."""
    for user in users:
        user.refresh_from_db()
        assert user.responsible_manager == resolve_responsible(user.country, user.tax_id).manager, user.tax_id


class TestRegionKey:
    def test_russia_region(self):
        assert region_key("Россия", "2312345678") == (INN_REGION, "23")

    def test_empty_country_is_russia(self):
        assert region_key("", "2312345678") == (INN_REGION, "23")
        assert region_key(None, "2312345678") == (INN_REGION, "23")

    def test_foreign_country_ignores_inn(self):
        assert region_key("Беларусь", "7701234567") == (COUNTRY, "Беларусь")

    @pytest.mark.parametrize("tax_id", ["", None, "7", "AB12345678", " 2312345678", "2a12345678"])
    def test_no_region(self, tax_id):
        assert region_key("Россия", tax_id) is None


class TestResolveResponsible:
    @pytest.fixture
    def chief(self):
        return make_staff(SUPERVISORS_GROUP)

    def test_region_with_manager(self, chief):
        manager = make_staff()
        rule(INN_REGION, "23", manager)
        rule(FALLBACK, "default", chief)
        resolution = resolve_responsible("Россия", "2312345678")
        assert (resolution.manager, resolution.source) == (manager, SOURCE_REGION)

    def test_region_without_manager_goes_to_fallback(self, chief):
        rule(INN_REGION, "23", email="old@freesportopt.ru")
        rule(FALLBACK, "default", chief)
        resolution = resolve_responsible("Россия", "2312345678")
        assert (resolution.manager, resolution.source) == (chief, SOURCE_FALLBACK)

    def test_country(self, chief):
        manager = make_staff()
        rule(COUNTRY, "Беларусь", manager)
        rule(FALLBACK, "default", chief)
        resolution = resolve_responsible("Беларусь", "7701234567")
        assert (resolution.manager, resolution.source) == (manager, SOURCE_COUNTRY)

    def test_no_key_goes_to_fallback(self, chief):
        rule(FALLBACK, "default", chief)
        rule(FALLBACK, "default", email="admin@freesportopt.ru")
        resolution = resolve_responsible("Россия", "")
        assert (resolution.manager, resolution.source) == (chief, SOURCE_FALLBACK)

    def test_no_fallback_with_manager(self):
        rule(FALLBACK, "default", email="admin@freesportopt.ru")
        resolution = resolve_responsible("Россия", "0012345678")
        assert (resolution.manager, resolution.source) == (None, SOURCE_NONE)

    def test_inactive_rule_ignored(self, chief):
        rule(INN_REGION, "23", make_staff(), active=False)
        rule(FALLBACK, "default", chief)
        resolution = resolve_responsible("Россия", "2312345678")
        assert (resolution.manager, resolution.source) == (chief, SOURCE_FALLBACK)


class TestIsStaffAccount:
    @pytest.mark.parametrize(
        "extra",
        [{"is_staff": True}, {"is_superuser": True}, {"role": "admin"}],
    )
    def test_flags(self, extra):
        user = User(email="x@example.com", **extra)
        assert is_staff_account(user)

    @pytest.mark.parametrize("group", [MANAGERS_GROUP, MARKETING_GROUP, SUPERVISORS_GROUP])
    def test_role_groups(self, group):
        user = make_client("2312345678")
        user.groups.add(Group.objects.get_or_create(name=group)[0])
        assert is_staff_account(user)

    def test_b2b_client(self):
        assert not is_staff_account(make_client("2312345678"))

    def test_unregistered(self):
        assert not is_staff_account(make_client("2312345678", role="unregistered"))

    def test_unsaved_without_groups_query(self, django_assert_num_queries):
        with django_assert_num_queries(0):
            assert not is_staff_account(User(email="new@example.com"))


class TestAssignResponsibleManager:
    def test_assigns_and_reports_change(self):
        manager = make_staff()
        rule(INN_REGION, "23", manager)
        user = User(email="new@example.com", tax_id="2312345678")
        assert assign_responsible_manager(user) is True
        assert user.responsible_manager == manager
        assert assign_responsible_manager(user) is False

    def test_manual_untouched(self):
        rule(INN_REGION, "23", make_staff())
        user = User(email="new@example.com", tax_id="2312345678", responsible_manager_manual=True)
        assert assign_responsible_manager(user) is False
        assert user.responsible_manager is None

    def test_staff_untouched(self):
        rule(INN_REGION, "23", make_staff())
        user = User(email="new@example.com", tax_id="2312345678", is_staff=True)
        assert assign_responsible_manager(user) is False
        assert user.responsible_manager is None


class TestReassignClientsForKey:
    """Сценарий AC6: менеджер A ведёт регион 23 и, вручную, клиентов региона 24."""

    @pytest.fixture
    def scene(self):
        chief = make_staff(SUPERVISORS_GROUP)
        manager_a, manager_b = make_staff(), make_staff()
        fallback_rule = rule(FALLBACK, "default", chief)
        rule(FALLBACK, "default", email="admin@freesportopt.ru")
        rule_23 = rule(INN_REGION, "23", manager_a)
        rule_24 = rule(INN_REGION, "24", manager_a)
        region_23 = [make_client(f"23{i:08d}") for i in range(10)]
        for client in region_23[:2]:
            client.responsible_manager_manual = True
            client.save()
        region_24 = [make_client(f"24{i:08d}") for i in range(3)]
        others = [make_client("0012345678"), make_client(""), make_client("7701234567", country="Казахстан")]
        staff_23 = make_staff(tax_id="2399999999")
        return {
            "chief": chief,
            "a": manager_a,
            "b": manager_b,
            "fallback_rule": fallback_rule,
            "rule_23": rule_23,
            "rule_24": rule_24,
            "region_23": region_23,
            "region_24": region_24,
            "others": others,
            "staff_23": staff_23,
        }

    def responsible(self, users):
        return [User.objects.get(pk=u.pk).responsible_manager for u in users]

    def test_initial_assignment(self, scene):
        assert self.responsible(scene["region_23"]) == [scene["a"]] * 10
        assert self.responsible(scene["others"]) == [scene["chief"]] * 3
        assert self.responsible([scene["staff_23"]]) == [None]

    def test_replace_manager_a_with_b(self, scene):
        rule_23 = scene["rule_23"]
        rule_23.manager = scene["b"]
        rule_23.save()
        assert self.responsible(scene["region_23"][2:]) == [scene["b"]] * 8
        # Ручное назначение не перезаписывается.
        assert self.responsible(scene["region_23"][:2]) == [scene["a"]] * 2
        assert self.responsible(scene["region_24"]) == [scene["a"]] * 3
        assert self.responsible([scene["staff_23"]]) == [None]
        assert_mass_equals_single(scene["region_23"][2:] + scene["region_24"] + scene["others"])

    def test_deactivate_rule_moves_clients_to_fallback(self, scene):
        rule_23 = scene["rule_23"]
        rule_23.is_active = False
        rule_23.save()
        assert self.responsible(scene["region_23"][2:]) == [scene["chief"]] * 8
        assert self.responsible(scene["region_23"][:2]) == [scene["a"]] * 2
        assert_mass_equals_single(scene["region_23"][2:] + scene["region_24"] + scene["others"])

    def test_delete_rule_moves_clients_to_fallback(self, scene):
        scene["rule_23"].delete()
        assert self.responsible(scene["region_23"][2:]) == [scene["chief"]] * 8
        assert self.responsible(scene["region_24"]) == [scene["a"]] * 3
        assert_mass_equals_single(scene["region_23"][2:] + scene["region_24"] + scene["others"])

    def test_change_code_recalculates_both_regions(self, scene):
        scene["rule_24"].delete()
        rule_23 = scene["rule_23"]
        rule_23.match_value = "24"
        rule_23.save()
        assert self.responsible(scene["region_23"][2:]) == [scene["chief"]] * 8
        assert self.responsible(scene["region_24"]) == [scene["a"]] * 3
        assert_mass_equals_single(scene["region_23"][2:] + scene["region_24"] + scene["others"])

    def test_change_fallback_manager(self, scene):
        new_chief = make_staff(SUPERVISORS_GROUP)
        fallback_rule = scene["fallback_rule"]
        fallback_rule.manager = new_chief
        fallback_rule.save()
        assert self.responsible(scene["others"]) == [new_chief] * 3
        # Клиентов с региональным менеджером резерв не трогает.
        assert self.responsible(scene["region_23"][2:]) == [scene["a"]] * 8
        assert self.responsible([scene["staff_23"]]) == [None]
        assert_mass_equals_single(scene["region_23"][2:] + scene["region_24"] + scene["others"])

    def test_no_fallback_manager_clears_responsible(self, scene):
        fallback_rule = scene["fallback_rule"]
        fallback_rule.manager = None
        fallback_rule.manager_email = "chief@freesportopt.ru"
        fallback_rule.save()
        assert self.responsible(scene["others"]) == [None] * 3
        assert self.responsible(scene["region_23"][2:]) == [scene["a"]] * 8

    def test_staff_in_region_untouched_by_direct_call(self, scene):
        staff = scene["staff_23"]
        User.objects.filter(pk=staff.pk).update(responsible_manager=scene["b"])
        reassign_clients_for_key((INN_REGION, "23"))
        assert self.responsible([staff]) == [scene["b"]]

    def test_single_update_query(self, scene):
        User.objects.filter(pk__in=[c.pk for c in scene["region_23"][2:]]).update(responsible_manager=scene["b"])
        with CaptureQueriesContext(connection) as ctx:
            updated = reassign_clients_for_key((INN_REGION, "23"))
        assert updated == 8
        updates = [q["sql"] for q in ctx.captured_queries if q["sql"].startswith('UPDATE "users"')]
        assert len(updates) == 1
        # Разрешение ключа (правило региона) + один UPDATE: запросов не по клиенту.
        assert len(ctx.captured_queries) == 2

    def test_fallback_key_single_update_query(self, scene):
        User.objects.filter(pk__in=[c.pk for c in scene["others"]]).update(responsible_manager=None)
        with CaptureQueriesContext(connection) as ctx:
            updated = reassign_clients_for_key(None)
        assert updated == 3
        assert len([q for q in ctx.captured_queries if q["sql"].startswith('UPDATE "users"')]) == 1


class TestAffectedKeys:
    @staticmethod
    def state(match_type=INN_REGION, value="23", active=True, manager_id=1):
        return {"match_type": match_type, "match_value": value, "is_active": active, "manager_id": manager_id}

    def test_manager_change(self):
        assert affected_keys(self.state(), self.state(manager_id=2)) == {(INN_REGION, "23")}

    def test_code_change(self):
        assert affected_keys(self.state(), self.state(value="24")) == {(INN_REGION, "23"), (INN_REGION, "24")}

    def test_deactivate_and_delete(self):
        assert affected_keys(self.state(), self.state(active=False)) == {(INN_REGION, "23")}
        assert affected_keys(self.state(), None) == {(INN_REGION, "23")}

    def test_new_rule(self):
        assert affected_keys(None, self.state(COUNTRY, "Беларусь")) == {(COUNTRY, "Беларусь")}

    def test_fallback_manager_change(self):
        assert affected_keys(self.state(FALLBACK, "default"), self.state(FALLBACK, "default", manager_id=2)) == {None}

    def test_rules_without_manager_affect_nobody(self):
        assert affected_keys(self.state(manager_id=None), self.state(value="24", manager_id=None)) == set()
        assert affected_keys(None, self.state(FALLBACK, "default", manager_id=None)) == set()
        assert affected_keys(self.state(), self.state()) == set()
