"""
Integration-тесты команды recalculate_responsible_managers (стори 42.3, AC4–AC8).

Клиенты, созданные через save(), сразу получают ответственного хуком 42.2,
а создание правила переводит клиентов сигналом. Поэтому «существующих
клиентов без ответственного» тесты получают сбросом через QuerySet.update()
после подготовки правил и клиентов.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.common.models import ManagerRoutingRule
from apps.users.models import User
from apps.users.services.responsible_manager import resolve_responsible
from apps.users.staff_roles import MANAGERS_GROUP, STAFF_ROLE_GROUPS, SUPERVISORS_GROUP
from tests.conftest import get_unique_suffix

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

COMMAND = "recalculate_responsible_managers"
INN_REGION = ManagerRoutingRule.MATCH_INN_REGION
COUNTRY = ManagerRoutingRule.MATCH_COUNTRY
FALLBACK = ManagerRoutingRule.MATCH_FALLBACK
NO_FALLBACK = "Нет активного резервного правила с менеджером"
DRY_RUN_HEADER = "Пересчёт ответственных менеджеров (пробный запуск, изменения не сохранены)"
COUNTER_LINES = (
    "Назначено по коду региона",
    "Назначено по стране",
    "Ушло на резервное правило",
    "Пропущено (назначен вручную)",
    "Без изменений",
    "Без ответственного (нет резервного правила с менеджером)",
)


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


def rule(match_type: str, match_value: str, manager: User | None = None, active: bool = True) -> ManagerRoutingRule:
    return ManagerRoutingRule.objects.create(
        match_type=match_type,
        match_value=match_value,
        manager=manager,
        manager_email="" if manager else f"rule_{get_unique_suffix()}@freesportopt.ru",
        is_active=active,
    )


def reset_responsible(users) -> None:
    """Состояние «до выката 42.2»: ответственного нет, хук и сигналы не срабатывают."""
    User.objects.filter(pk__in=[user.pk for user in users]).update(responsible_manager=None)


def run(*args: str) -> tuple[str, str]:
    stdout, stderr = StringIO(), StringIO()
    call_command(COMMAND, *args, stdout=stdout, stderr=stderr)
    return stdout.getvalue(), stderr.getvalue()


def counter(report: str, label: str) -> int | None:
    for line in report.splitlines():
        if line.startswith(f"{label}: "):
            return int(line.rsplit(": ", 1)[1])
    return None


def assert_sum_matches(report: str) -> None:
    total = sum(counter(report, label) or 0 for label in COUNTER_LINES)
    assert total == counter(report, "Проверено клиентов")


@pytest.fixture
def managers():
    return {
        "region": make_staff(),
        "country": make_staff(),
        "fallback": make_staff(SUPERVISORS_GROUP),
        "manual": make_staff(),
        "other": make_staff(),
    }


@pytest.fixture
def rules(managers):
    rule(INN_REGION, "23", managers["region"])
    rule(INN_REGION, "24")  # только manager_email — ответственного не даёт
    rule(COUNTRY, "Беларусь", managers["country"])
    rule(FALLBACK, "default", managers["fallback"])


@pytest.fixture
def population(managers, rules):
    """Набор клиентов AC4 и сотрудники с ИНН региона."""
    clients = {
        "no_manager": make_client("2311111111"),
        "already_ok": make_client("2322222222"),
        "foreign_manager": make_client("2333333333"),
        "manual": make_client("2344444444"),
        "unregistered": make_client("2355555555", role="unregistered"),
        "no_inn": make_client(""),
        "email_only_region": make_client("2466666666"),
        "moscow_new": make_client("9777777777"),
        "belarus": make_client("2388888888", country="Беларусь"),
        "inactive": make_client("2399999999", is_active=False),
    }
    staff = {
        "is_staff": User.objects.create_user(
            email=f"s_{get_unique_suffix()}@freesportopt.ru",
            password="StrongPassword123!",
            is_staff=True,
            tax_id="2300000001",
        ),
        "superuser": User.objects.create_superuser(
            email=f"su_{get_unique_suffix()}@freesportopt.ru", password="StrongPassword123!", tax_id="2300000002"
        ),
        "admin_role": make_client("2300000003", role="admin"),
    }
    for group in STAFF_ROLE_GROUPS:
        member = make_client("2300000004")
        member.groups.add(Group.objects.get_or_create(name=group)[0])
        staff[f"group_{group}"] = member

    reset_responsible(list(clients.values()) + list(staff.values()))
    User.objects.filter(pk=clients["already_ok"].pk).update(responsible_manager=managers["region"])
    User.objects.filter(pk=clients["foreign_manager"].pk).update(responsible_manager=managers["other"])
    User.objects.filter(pk=clients["manual"].pk).update(
        responsible_manager=managers["manual"], responsible_manager_manual=True
    )
    for user in list(clients.values()) + list(staff.values()):
        user.refresh_from_db()
    return clients, staff


class TestAssignment:
    def test_invariant_for_every_non_manual_client(self, population, managers):
        clients, staff = population
        updated_at = {user.pk: user.updated_at for user in list(clients.values()) + list(staff.values())}

        run()

        for name, client in clients.items():
            client.refresh_from_db()
            assert client.updated_at == updated_at[client.pk], name
            if name == "manual":
                continue
            assert client.responsible_manager == resolve_responsible(client.country, client.tax_id).manager, name
        assert clients["no_manager"].responsible_manager == managers["region"]
        assert clients["foreign_manager"].responsible_manager == managers["region"]
        assert clients["unregistered"].responsible_manager == managers["region"]
        assert clients["inactive"].responsible_manager == managers["region"]
        assert clients["belarus"].responsible_manager == managers["country"]
        assert clients["no_inn"].responsible_manager == managers["fallback"]
        assert clients["moscow_new"].responsible_manager == managers["fallback"]

    def test_manual_and_staff_untouched(self, population, managers):
        clients, staff = population

        run()

        clients["manual"].refresh_from_db()
        assert clients["manual"].responsible_manager == managers["manual"]
        assert clients["manual"].responsible_manager_manual is True
        for name, user in staff.items():
            user.refresh_from_db()
            assert user.responsible_manager is None, name

    def test_email_only_rule_gives_no_manager(self, population, managers):
        clients, _staff = population

        run()

        clients["email_only_region"].refresh_from_db()
        # Правило 24 без учётной записи: клиент уходит на резерв, а не «к правилу».
        assert clients["email_only_region"].responsible_manager == managers["fallback"]


class TestReport:
    def test_counters(self, population):
        clients, _staff = population

        report, _err = run()

        assert report.splitlines()[0] == "Пересчёт ответственных менеджеров"
        assert "Проверено клиентов: 10" in report
        # no_manager, foreign_manager, unregistered, inactive.
        assert "Назначено по коду региона: 4" in report
        assert "Назначено по стране: 1" in report
        # no_inn, email_only_region, moscow_new.
        assert "Ушло на резервное правило: 3" in report
        assert "Пропущено (назначен вручную): 1" in report
        assert "Без изменений: 1" in report
        assert "Без ответственного" not in report
        assert_sum_matches(report)

    def test_fallback_codes_listed(self, population):
        clients, _staff = population
        make_client("9711111111")
        reset_responsible(User.objects.filter(tax_id="9711111111"))

        report, _err = run()

        lines = report.splitlines()
        header = lines.index("Коды без менеджера, клиенты ушли на резерв:")
        assert lines[header + 1 : header + 3] == [
            "  97 — г. Москва (ИНН с 2014 г.): 2",
            "  24 — Красноярский край: 1",
        ]

    def test_codes_sorted_by_count_then_code(self, managers):
        rule(FALLBACK, "default", managers["fallback"])
        users = [make_client("8011111111"), make_client("8511111111"), make_client("8111111111")]
        users.append(make_client("8522222222"))
        reset_responsible(users)

        report, _err = run()

        lines = report.splitlines()
        header = lines.index("Коды без менеджера, клиенты ушли на резерв:")
        assert lines[header + 1 :] == [
            "  85 — Усть-Ордынский Бурятский АО (Иркутская область): 2",
            "  80 — Агинский Бурятский АО (Забайкальский край): 1",
            "  81 — Коми-Пермяцкий АО (Пермский край): 1",
        ]

    def test_unknown_code_listed_as_is(self, managers):
        rule(FALLBACK, "default", managers["fallback"])
        reset_responsible([make_client("9611111111")])

        report, _err = run()

        assert "  96: 1" in report.splitlines()

    def test_no_codes_section_when_all_assigned(self, managers):
        rule(INN_REGION, "23", managers["region"])
        rule(FALLBACK, "default", managers["fallback"])
        reset_responsible([make_client("2311111111"), make_client("")])

        report, _err = run()

        assert "Коды без менеджера" not in report
        assert "Ушло на резервное правило: 1" in report

    def test_foreign_manager_reassigned_and_counted(self, managers):
        rule(INN_REGION, "23", managers["region"])
        rule(FALLBACK, "default", managers["fallback"])
        client = make_client("2311111111")
        User.objects.filter(pk=client.pk).update(responsible_manager=managers["other"])

        report, _err = run()

        client.refresh_from_db()
        assert client.responsible_manager == managers["region"]
        assert "Назначено по коду региона: 1" in report

    def test_second_run_is_idempotent(self, population):
        run()

        report, _err = run()

        assert "Назначено по коду региона: 0" in report
        assert "Назначено по стране: 0" in report
        assert "Ушло на резервное правило: 0" in report
        checked = counter(report, "Проверено клиентов")
        manual = counter(report, "Пропущено (назначен вручную)")
        assert counter(report, "Без изменений") == checked - manual
        assert_sum_matches(report)


class TestDryRun:
    def test_report_matches_real_run_without_updates(self, population):
        clients, _staff = population

        with CaptureQueriesContext(connection) as ctx:
            dry_report, _err = run("--dry-run")

        assert not [q["sql"] for q in ctx.captured_queries if q["sql"].startswith('UPDATE "users"')]
        for client in clients.values():
            before = client.responsible_manager_id
            client.refresh_from_db()
            assert client.responsible_manager_id == before

        real_report, _err = run()

        dry_lines = dry_report.splitlines()
        real_lines = real_report.splitlines()
        assert dry_lines[0] == DRY_RUN_HEADER
        assert real_lines[0] == "Пересчёт ответственных менеджеров"
        assert dry_lines[1:] == real_lines[1:]


class TestNoFallback:
    @pytest.fixture
    def without_fallback(self, managers):
        rule(INN_REGION, "23", managers["region"])
        rule(FALLBACK, "default")  # резерв только с manager_email
        users = [make_client("2311111111"), make_client(""), make_client("9711111111")]
        reset_responsible(users)
        return users

    def test_real_run_raises_and_changes_nothing(self, without_fallback):
        with pytest.raises(CommandError, match=NO_FALLBACK):
            run()

        for user in without_fallback:
            user.refresh_from_db()
            assert user.responsible_manager is None

    def test_inactive_fallback_with_manager_is_not_enough(self, managers):
        rule(FALLBACK, "default", managers["fallback"], active=False)

        with pytest.raises(CommandError, match=NO_FALLBACK):
            run()

    def test_dry_run_reports_and_warns(self, without_fallback, managers):
        report, err = run("--dry-run")

        assert report.splitlines()[0] == DRY_RUN_HEADER
        assert "Назначено по коду региона: 1" in report
        assert "Без ответственного (нет резервного правила с менеджером): 2" in report
        assert NO_FALLBACK in err
        assert_sum_matches(report)
        for user in without_fallback:
            user.refresh_from_db()
            assert user.responsible_manager is None


class TestPerformance:
    def _queries_for(self, count: int) -> int:
        users = [make_client(f"{('23', '50', '77')[index % 3]}{index:08d}") for index in range(count)]
        reset_responsible(users)
        with CaptureQueriesContext(connection) as ctx:
            run()
        assert not User.objects.filter(pk__in=[user.pk for user in users], responsible_manager__isnull=True).exists()
        return len(ctx.captured_queries)

    def test_query_count_independent_of_clients(self, managers):
        rule(INN_REGION, "23", managers["region"])
        rule(INN_REGION, "50", managers["country"])
        rule(FALLBACK, "default", managers["fallback"])

        assert self._queries_for(5) == self._queries_for(50)
