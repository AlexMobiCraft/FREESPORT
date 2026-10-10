"""
Integration-тесты событий автоназначения ответственного менеджера (стори 42.2).

Покрывает:
- AC3 — регистрация через API: правило региона, резерв, правило без учётной записи;
- AC4 — смена ИНН или страны: импорт 1С, привязка к 1С, верификация с привязкой,
  карточка админки, API профиля, save(update_fields=...); ручное назначение не меняется;
- AC5 — верификация заявки без привязки к 1С;
- AC6 — смена менеджера правила через форму ManagerRoutingRuleAdmin;
- AC8 — сотрудник с ИНН региона не получает ответственного.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django import forms
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

from apps.common.models import ManagerRoutingRule
from apps.products.models import ImportSession
from apps.users.models import User
from apps.users.services.link_1c_customer import link_1c_customer
from apps.users.services.processor import CustomerDataProcessor
from apps.users.services.verify_b2b_application import verify_b2b_application
from apps.users.staff_roles import MANAGERS_GROUP, SUPERVISORS_GROUP
from tests.conftest import get_unique_suffix
from tests.consent_versions import REGISTRATION_PDP_TEXT_VERSION

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

INN_REGION = ManagerRoutingRule.MATCH_INN_REGION
COUNTRY = ManagerRoutingRule.MATCH_COUNTRY
FALLBACK = ManagerRoutingRule.MATCH_FALLBACK


def make_staff(group: str = MANAGERS_GROUP, **extra) -> User:
    user = User.objects.create_user(
        email=f"staff_{get_unique_suffix()}@freesportopt.ru",
        password="StrongPassword123!",
        is_staff=True,
        **extra,
    )
    user.groups.add(Group.objects.get_or_create(name=group)[0])
    return user


def make_client(tax_id: str, **extra) -> User:
    defaults = {
        "email": f"client_{get_unique_suffix()}@example.com",
        "first_name": "Клиент",
        "last_name": "Тестов",
        "role": "wholesale_level1",
        "company_name": "ООО Клиент",
        "verification_status": "pending",
    }
    defaults.update(extra)
    return User.objects.create_user(password="StrongPassword123!", tax_id=tax_id, **defaults)


def make_1c_record(tax_id: str) -> User:
    record = User(
        email=f"1c_{get_unique_suffix()}@example.com",
        first_name="Контрагент",
        last_name="Из1С",
        company_name="ООО Импортированное",
        tax_id=tax_id,
        role=User.ROLE_UNREGISTERED,
        created_in_1c=True,
        verification_status="unverified",
        onec_id=f"1C-{get_unique_suffix()}",
        password="",
    )
    record.save()
    return record


def responsible_of(user: User) -> User | None:
    return User.objects.get(pk=user.pk).responsible_manager


@pytest.fixture
def team():
    """Правила: 23 → A, 77 → B, Беларусь → C, 24 — без учётной записи, резерв → R (+ резерв без менеджера)."""
    ManagerRoutingRule.objects.all().delete()
    team = {
        "a": make_staff(),
        "b": make_staff(),
        "c": make_staff(),
        "chief": make_staff(SUPERVISORS_GROUP),
    }
    ManagerRoutingRule.objects.create(match_type=INN_REGION, match_value="23", manager=team["a"])
    ManagerRoutingRule.objects.create(match_type=INN_REGION, match_value="77", manager=team["b"])
    ManagerRoutingRule.objects.create(match_type=COUNTRY, match_value="Беларусь", manager=team["c"])
    ManagerRoutingRule.objects.create(match_type=INN_REGION, match_value="24", manager_email="old24@freesportopt.ru")
    team["fallback"] = ManagerRoutingRule.objects.create(
        match_type=FALLBACK, match_value="default", manager=team["chief"]
    )
    ManagerRoutingRule.objects.create(match_type=FALLBACK, match_value="default", manager_email="admin@freesportopt.ru")
    return team


@pytest.fixture
def superuser_client(client):
    client.force_login(
        User.objects.create_superuser(email=f"root_{get_unique_suffix()}@example.com", password="StrongPassword123!")
    )
    return client


@pytest.fixture
def no_mail():
    with (
        patch("apps.users.serializers.send_manager_region_email.delay"),
        patch("apps.users.serializers.send_admin_verification_email.delay"),
        patch("apps.users.serializers.send_user_pending_email.delay"),
        patch("apps.users.signals.send_user_verified_email"),
    ):
        yield


def change_form_payload(client, user: User, **fields) -> dict:
    """POST-данные карточки пользователя: текущие значения полей формы, inline'ы пустые."""
    response = client.get(reverse("admin:users_user_change", args=[user.pk]))
    assert response.status_code == 200
    payload: dict = {}
    for bound in response.context["adminform"].form:
        value = bound.value()
        if bound.field.disabled:
            continue
        if isinstance(bound.field, forms.BooleanField):
            if value:
                payload[bound.html_name] = "on"
        elif isinstance(bound.field.widget, forms.MultiWidget):
            for suffix, part in zip(bound.field.widget.widgets_names, bound.field.widget.decompress(value)):
                payload[f"{bound.html_name}{suffix}"] = "" if part is None else str(part)
        elif isinstance(value, (list, tuple)):
            payload[bound.html_name] = [str(v) for v in value]
        else:
            payload[bound.html_name] = "" if value is None else str(value)
    for inline_admin_formset in response.context["inline_admin_formsets"]:
        management_form = inline_admin_formset.formset.management_form
        for name in management_form.fields:
            payload[management_form.add_prefix(name)] = str(management_form[name].value())
        payload[management_form.add_prefix("TOTAL_FORMS")] = "0"
        payload[management_form.add_prefix("INITIAL_FORMS")] = "0"
    for name, value in fields.items():
        if value is False:
            payload.pop(name, None)
        else:
            payload[name] = "on" if value is True else value
    return payload


class TestRegistration:
    """AC3."""

    @pytest.mark.parametrize(
        "tax_id,expected",
        [("2301234567", "a"), ("0001234567", "chief"), ("2401234567", "chief")],
    )
    def test_registration_assigns_responsible(self, team, no_mail, tax_id, expected):
        email = f"reg_{get_unique_suffix()}@example.com"
        response = APIClient().post(
            "/api/v1/auth/register/",
            {
                "email": email,
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "first_name": "Регион",
                "last_name": "Покупатель",
                "role": "wholesale_level1",
                "company_name": "ООО Регион",
                "tax_id": tax_id,
                "country": "Россия",
                "pdp_consent": True,
                "pdp_consent_text_version": REGISTRATION_PDP_TEXT_VERSION,
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        user = User.objects.get(email=email)
        assert user.responsible_manager == team[expected]
        assert user.responsible_manager_manual is False


class TestTaxIdOrCountryChange:
    """AC4."""

    @pytest.fixture
    def processor(self):
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CUSTOMERS,
            status=ImportSession.ImportStatus.STARTED,
        )
        return CustomerDataProcessor(session_id=session.pk)

    def test_import_update_customer(self, team, processor):
        client = make_client("2301234567", onec_id=f"1C-{get_unique_suffix()}")
        assert responsible_of(client) == team["a"]
        processor._update_customer(client, {"tax_id": "7701234567", "onec_id": client.onec_id})
        assert responsible_of(client) == team["b"]

    def test_import_keeps_manual(self, team, processor):
        client = make_client("2301234567", onec_id=f"1C-{get_unique_suffix()}")
        User.objects.filter(pk=client.pk).update(responsible_manager=team["c"], responsible_manager_manual=True)
        client.refresh_from_db()
        processor._update_customer(client, {"tax_id": "7701234567", "onec_id": client.onec_id})
        assert responsible_of(client) == team["c"]

    def test_link_1c_customer_writes_responsible(self, team):
        # Импорт пишет ИНН без strip(): у заявки с пробелом региона нет, она на резерве.
        applicant = make_client(" 7701234567")
        assert responsible_of(applicant) == team["chief"]
        source = make_1c_record("7701234567")
        link_1c_customer(target_id=applicant.pk, source_id=source.pk, expected_onec_id=source.onec_id)
        assert responsible_of(applicant) == team["b"]

    def test_link_1c_customer_keeps_manual(self, team):
        applicant = make_client(" 7701234567")
        User.objects.filter(pk=applicant.pk).update(responsible_manager=team["c"], responsible_manager_manual=True)
        source = make_1c_record("7701234567")
        link_1c_customer(target_id=applicant.pk, source_id=source.pk, expected_onec_id=source.onec_id)
        assert responsible_of(applicant) == team["c"]

    def test_verify_with_link(self, team, no_mail):
        applicant = make_client(" 7701234567")
        source = make_1c_record("7701234567")
        verify_b2b_application(
            target_id=applicant.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
            role="wholesale_level1",
            actor=make_staff(SUPERVISORS_GROUP),
        )
        applicant.refresh_from_db()
        assert applicant.is_verified is True
        assert applicant.responsible_manager == team["b"]

    def test_admin_change_form(self, team, superuser_client):
        client = make_client("2301234567")
        payload = change_form_payload(superuser_client, client, tax_id="7701234567")
        response = superuser_client.post(reverse("admin:users_user_change", args=[client.pk]), payload)
        assert response.status_code == 302, response.context["adminform"].form.errors
        assert responsible_of(client) == team["b"]

    def test_admin_change_form_keeps_manual(self, team, superuser_client):
        client = make_client("2301234567")
        payload = change_form_payload(
            superuser_client,
            client,
            tax_id="7701234567",
            responsible_manager=str(team["c"].pk),
            responsible_manager_manual=True,
        )
        response = superuser_client.post(reverse("admin:users_user_change", args=[client.pk]), payload)
        assert response.status_code == 302, response.context["adminform"].form.errors
        client.refresh_from_db()
        assert (client.responsible_manager, client.responsible_manager_manual) == (team["c"], True)

    def test_profile_api(self, team):
        client = make_client("2301234567")
        api = APIClient()
        api.force_authenticate(client)
        response = api.patch("/api/v1/users/profile/", {"tax_id": "7701234567"}, format="json")
        assert response.status_code == 200, response.data
        assert responsible_of(client) == team["b"]

    def test_profile_api_keeps_manual(self, team):
        client = make_client("2301234567")
        User.objects.filter(pk=client.pk).update(responsible_manager_manual=True)
        api = APIClient()
        api.force_authenticate(User.objects.get(pk=client.pk))
        response = api.patch("/api/v1/users/profile/", {"tax_id": "7701234567"}, format="json")
        assert response.status_code == 200, response.data
        assert responsible_of(client) == team["a"]

    def test_country_change(self, team):
        client = make_client("7701234567")
        client.country = "Беларусь"
        client.save()
        assert responsible_of(client) == team["c"]

    def test_save_with_update_fields_writes_responsible(self, team):
        client = make_client("2301234567")
        client.tax_id = "7701234567"
        client.save(update_fields=["tax_id"])
        assert responsible_of(client) == team["b"]

    def test_save_without_region_fields_does_not_reassign(self, team):
        client = make_client("2301234567")
        User.objects.filter(pk=client.pk).update(responsible_manager=team["c"])
        client = User.objects.get(pk=client.pk)
        client.first_name = "Другое"
        client.save()
        assert responsible_of(client) == team["c"]


class TestVerificationWithoutLink:
    """AC5."""

    def test_existing_application_gets_responsible(self, team, no_mail):
        applicant = make_client("2301234567")
        # Заявка подана до выката 42.2 — ответственного нет.
        User.objects.filter(pk=applicant.pk).update(responsible_manager=None)
        verify_b2b_application(
            target_id=applicant.pk,
            source_id=None,
            role="wholesale_level1",
            confirm_without_1c=True,
            actor=make_staff(SUPERVISORS_GROUP),
        )
        applicant.refresh_from_db()
        assert applicant.is_verified is True
        assert applicant.responsible_manager == team["a"]

    def test_manual_untouched(self, team, no_mail):
        applicant = make_client("2301234567")
        User.objects.filter(pk=applicant.pk).update(responsible_manager=None, responsible_manager_manual=True)
        verify_b2b_application(
            target_id=applicant.pk,
            source_id=None,
            role="wholesale_level1",
            confirm_without_1c=True,
            actor=make_staff(SUPERVISORS_GROUP),
        )
        assert responsible_of(applicant) is None


class TestRuleChangeFromAdmin:
    """AC6: смена менеджера правила через форму админки."""

    def test_replace_manager_in_rule(self, team, superuser_client):
        clients = [make_client(f"23{i:08d}") for i in range(3)]
        manual = make_client("2399999999")
        User.objects.filter(pk=manual.pk).update(responsible_manager_manual=True)
        rule = ManagerRoutingRule.objects.get(match_type=INN_REGION, match_value="23")
        new_manager = make_staff()
        response = superuser_client.post(
            reverse("admin:common_managerroutingrule_change", args=[rule.pk]),
            {
                "match_type": INN_REGION,
                "match_value": "23",
                "is_active": "on",
                "manager": str(new_manager.pk),
                "manager_name": "",
                "manager_email": "",
                "federal_district": "",
            },
        )
        assert response.status_code == 302, response.context["adminform"].form.errors
        assert [responsible_of(c) for c in clients] == [new_manager] * 3
        assert responsible_of(manual) == team["a"]

    def test_duplicate_active_rule_rejected_by_form(self, team, superuser_client):
        response = superuser_client.post(
            reverse("admin:common_managerroutingrule_add"),
            {
                "match_type": INN_REGION,
                "match_value": "23",
                "is_active": "on",
                "manager": "",
                "manager_name": "",
                "manager_email": "dup@freesportopt.ru",
                "federal_district": "",
            },
        )
        assert response.status_code == 200
        assert (
            "Для этого кода региона или страны уже есть активное правило. Выключите его или измените."
            in response.context["adminform"].form.non_field_errors()
        )


class TestStaffNeverAssigned:
    """AC8."""

    @pytest.mark.parametrize("extra", [{"is_staff": True}, {"role": "admin"}])
    def test_staff_created_and_changed(self, team, extra):
        user = User.objects.create_user(
            email=f"emp_{get_unique_suffix()}@freesportopt.ru",
            password="StrongPassword123!",
            tax_id="2301234567",
            **extra,
        )
        assert responsible_of(user) is None
        user.tax_id = "7701234567"
        user.save()
        assert responsible_of(user) is None

    @pytest.mark.parametrize("group", [MANAGERS_GROUP, SUPERVISORS_GROUP])
    def test_role_group_member_changed(self, team, group):
        user = make_client("2301234567")
        user.groups.add(Group.objects.get_or_create(name=group)[0])
        User.objects.filter(pk=user.pk).update(responsible_manager=None)
        user = User.objects.get(pk=user.pk)
        user.tax_id = "7701234567"
        user.save()
        assert responsible_of(user) is None

    def test_rule_change_skips_staff(self, team):
        employee = make_staff(tax_id="2301234567")
        rule = ManagerRoutingRule.objects.get(match_type=INN_REGION, match_value="23")
        rule.manager = team["b"]
        rule.save()
        assert responsible_of(employee) is None

    def test_superuser(self, team):
        root = User.objects.create_superuser(
            email=f"root_{get_unique_suffix()}@example.com", password="StrongPassword123!", tax_id="2301234567"
        )
        root.tax_id = "7701234567"
        root.save()
        assert responsible_of(root) is None
