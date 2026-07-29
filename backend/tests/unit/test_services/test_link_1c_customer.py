"""
Unit-тесты сервиса связывания B2B-заявки с контрагентом 1С.

Покрывают I/O-матрицу спеки: перенос идентификаторов и реквизитов, обе ветки
customer_code, onec_guid=None, отказы и двойную отправку формы.
"""

from __future__ import annotations

import itertools
import time
import uuid
from unittest.mock import patch

import pytest

from apps.common.models import AuditLog
from apps.users.models import Company, User
from apps.users.services.link_1c_customer import (
    LinkCandidateError,
    SourceNotLinkableError,
    TargetAlreadyLinkedError,
    find_link_candidates,
    link_1c_customer,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

_counter = itertools.count()


def unique_suffix() -> str:
    return f"{time.time_ns()}_{next(_counter)}"


def unique_tax_id() -> str:
    return str(1000000000 + ((time.time_ns() + next(_counter) * 7919) % 900000000))


def make_1c_record(tax_id: str, **overrides) -> User:
    """Контрагент, импортированный из 1С и не заведённый на портале."""
    defaults = {
        "email": f"1c_{unique_suffix()}@example.com",
        "first_name": "Контрагент",
        "last_name": "Из1С",
        "company_name": "ООО Импортированное",
        "tax_id": tax_id,
        "role": User.ROLE_UNREGISTERED,
        "created_in_1c": True,
        "verification_status": "unverified",
        "onec_id": f"1C-{unique_suffix()}",
        # Импорт оставляет пустой пароль — войти по такой записи нельзя.
        "password": "",
    }
    defaults.update(overrides)
    record = User(**defaults)
    record.save()
    return record


def make_applicant(tax_id: str, **overrides) -> User:
    """B2B-заявка, созданная регистрацией на портале."""
    defaults = {
        "email": f"applicant_{unique_suffix()}@example.com",
        "first_name": "Заявитель",
        "last_name": "Портальный",
        "role": "wholesale_level1",
        "company_name": "Форма Компани",
        "tax_id": tax_id,
        "verification_status": "pending",
    }
    defaults.update(overrides)
    password = defaults.pop("password", "StrongPassword123!")
    return User.objects.create_user(password=password, **defaults)


class TestFindLinkCandidates:
    def test_returns_unlinked_1c_records_with_same_tax_id(self):
        tax_id = unique_tax_id()
        record = make_1c_record(tax_id)
        applicant = make_applicant(tax_id)

        assert find_link_candidates(applicant) == [record]

    def test_returns_all_candidates_for_shared_tax_id(self):
        """На один ИНН в 1С приходятся десятки контрагентов — нужны все."""
        tax_id = unique_tax_id()
        records = [make_1c_record(tax_id) for _ in range(3)]
        applicant = make_applicant(tax_id)

        assert find_link_candidates(applicant) == records

    def test_empty_tax_id_returns_empty_list(self):
        applicant = make_applicant("")

        assert find_link_candidates(applicant) == []

    def test_excludes_live_accounts(self):
        """Живой аккаунт с тем же ИНН источником быть не может."""
        tax_id = unique_tax_id()
        make_applicant(tax_id)
        applicant = make_applicant(tax_id)

        assert find_link_candidates(applicant) == []

    def test_excludes_deactivated_records(self):
        tax_id = unique_tax_id()
        make_1c_record(tax_id, is_active=False)
        applicant = make_applicant(tax_id)

        assert find_link_candidates(applicant) == []

    def test_excludes_self(self):
        tax_id = unique_tax_id()
        record = make_1c_record(tax_id)

        assert find_link_candidates(record) == []

    def test_includes_record_with_unusable_password(self):
        """create_user(password=None) пишет '!<случайное>' — это тоже «войти нельзя»."""
        tax_id = unique_tax_id()
        record = make_1c_record(tax_id)
        record.set_password(None)
        record.save(update_fields=["password"])
        applicant = make_applicant(tax_id)

        assert find_link_candidates(applicant) == [record]


class TestLink1CCustomer:
    def test_transfers_identifiers_and_requisites(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id, onec_guid=uuid.uuid4())
        Company.objects.create(
            user=source,
            legal_name="ООО Полное Наименование",
            tax_id=tax_id,
            kpp="770101001",
            legal_address="г. Москва, ул. Тестовая, 1",
        )
        target = make_applicant(tax_id)
        onec_id, onec_guid = source.onec_id, source.onec_guid

        linked = link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=onec_id,
        )

        linked.refresh_from_db()
        source.refresh_from_db()
        assert linked.onec_id == onec_id
        assert linked.onec_guid == onec_guid
        assert linked.company_name == "ООО Импортированное"
        assert linked.tax_id == tax_id
        assert linked.company.legal_name == "ООО Полное Наименование"
        assert linked.company.kpp == "770101001"
        assert linked.company.legal_address == "г. Москва, ул. Тестовая, 1"
        assert source.onec_id is None
        assert source.onec_guid is None
        assert source.is_active is False

    def test_survives_null_onec_guid(self):
        """Импорт onec_guid не заполняет — перенос обязан это переживать."""
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id, onec_guid=None)
        target = make_applicant(tax_id)

        linked = link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
        )

        assert linked.onec_guid is None
        assert linked.onec_id == source.onec_id

    def test_writes_audit_log(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        target = make_applicant(tax_id)
        actor = User.objects.create_superuser(
            email=f"manager_{unique_suffix()}@example.com",
            password="StrongPassword123!",
            first_name="Менеджер",
            last_name="Тестов",
        )

        link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
            actor=actor,
            ip_address="10.0.0.1",
            user_agent="pytest",
        )

        entry = AuditLog.objects.get(action="link_1c_customer")
        assert entry.user == actor
        assert entry.resource_type == "User"
        assert entry.resource_id == str(target.pk)
        assert entry.changes["target_id"] == target.pk
        assert entry.changes["source_id"] == source.pk
        assert "onec_id" in entry.changes["transferred_fields"]

    def test_actor_is_optional_for_shell_usage(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        target = make_applicant(tax_id)

        link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
        )

        assert AuditLog.objects.get(action="link_1c_customer").user is None

    def test_creates_company_when_target_has_none(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        Company.objects.create(user=source, legal_name="ИП Тестов", tax_id=tax_id)
        target = make_applicant(tax_id)
        assert Company.objects.filter(user=target).count() == 0

        link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
        )

        assert Company.objects.get(user=target).legal_name == "ИП Тестов"

    def test_empty_source_requisites_do_not_wipe_target(self):
        """
        Выгрузка 1С не заполняет КПП и адрес для ИП и физлиц. Привязка
        необратима, поэтому затирать ими данные заявителя нельзя.
        """
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        Company.objects.create(user=source, legal_name="ИП Из 1С", tax_id=tax_id, kpp="", legal_address="")
        target = make_applicant(tax_id)
        Company.objects.create(
            user=target,
            legal_name="Форма Компани",
            tax_id=tax_id,
            kpp="770101001",
            legal_address="г. Москва, ул. Лесная, 5",
        )

        link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
        )

        company = Company.objects.get(user=target)
        assert company.legal_name == "ИП Из 1С"
        assert company.kpp == "770101001"
        assert company.legal_address == "г. Москва, ул. Лесная, 5"

    def test_audit_log_records_previous_values_and_real_changes(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id, company_name="ООО Из 1С")
        Company.objects.create(user=source, legal_name="ООО Из 1С полное", tax_id=tax_id)
        target = make_applicant(tax_id, company_name="Форма Компани")

        link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
        )

        changes = AuditLog.objects.get(action="link_1c_customer").changes
        assert changes["previous_values"]["company_name"] == "Форма Компани"
        assert "company_name" in changes["transferred_fields"]
        assert "company.legal_name" in changes["transferred_fields"]
        # tax_id совпадал — переносить было нечего, и аудит этого не утверждает.
        assert "tax_id" not in changes["transferred_fields"]

    def test_tax_id_with_whitespace_is_linkable(self):
        """
        Поиск кандидатов и сверка под блокировкой используют одно правило
        нормализации: иначе заявка залипает — кандидат показан, привязка падает.
        """
        tax_id = unique_tax_id()
        source = make_1c_record(f" {tax_id} ")
        target = make_applicant(tax_id)

        assert find_link_candidates(target) == []

        source.tax_id = tax_id
        source.save(update_fields=["tax_id"])
        target.tax_id = f"{tax_id} "
        target.save(update_fields=["tax_id"])

        assert find_link_candidates(target) == [source]
        linked = link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
        )
        assert linked.onec_id == source.onec_id

    def test_source_without_company_leaves_target_company_untouched(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        target = make_applicant(tax_id)

        link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
        )

        assert Company.objects.filter(user=target).count() == 0

    def test_customer_code_transferred_when_target_has_none(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id, customer_code="12345")
        target = make_applicant(tax_id)

        linked = link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
        )

        source.refresh_from_db()
        assert linked.customer_code == "12345"
        assert source.customer_code is None

    def test_customer_code_of_target_is_never_overwritten(self):
        """Код заявителя уже вшит в номера его заказов."""
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id, customer_code="12345")
        target = make_applicant(tax_id, customer_code="54321")

        linked = link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
        )

        source.refresh_from_db()
        assert linked.customer_code == "54321"
        assert source.customer_code == "12345"

    def test_does_not_touch_identity_fields_of_target(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        target = make_applicant(tax_id)
        email, role, status, password = target.email, target.role, target.verification_status, target.password

        linked = link_1c_customer(
            target_id=target.pk,
            source_id=source.pk,
            expected_onec_id=source.onec_id,
        )

        assert (linked.email, linked.role, linked.verification_status) == (email, role, status)
        assert linked.password == password
        assert linked.is_active is target.is_active


class TestLink1CCustomerRefusals:
    def test_target_with_onec_id_is_rejected(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        target = make_applicant(tax_id, onec_id=f"1C-target-{unique_suffix()}")

        with pytest.raises(TargetAlreadyLinkedError):
            link_1c_customer(
                target_id=target.pk,
                source_id=source.pk,
                expected_onec_id=source.onec_id,
            )

        source.refresh_from_db()
        assert source.onec_id is not None
        assert source.is_active is True

    def test_target_with_only_onec_guid_is_rejected(self):
        """Признак «уже несёт идентичность 1С» — любой из двух идентификаторов."""
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        target = make_applicant(tax_id, onec_guid=uuid.uuid4())

        with pytest.raises(TargetAlreadyLinkedError):
            link_1c_customer(
                target_id=target.pk,
                source_id=source.pk,
                expected_onec_id=source.onec_id,
            )

    @pytest.mark.parametrize("role", ["retail", User.ROLE_UNREGISTERED, "admin"])
    def test_non_b2b_target_is_rejected(self, role):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        target = make_applicant(tax_id, role=role)

        with pytest.raises(LinkCandidateError):
            link_1c_customer(
                target_id=target.pk,
                source_id=source.pk,
                expected_onec_id=source.onec_id,
            )

        source.refresh_from_db()
        assert source.onec_id is not None

    def test_live_account_as_source_is_rejected(self):
        tax_id = unique_tax_id()
        source = make_applicant(tax_id, onec_id=f"1C-live-{unique_suffix()}")
        target = make_applicant(tax_id)

        with pytest.raises(SourceNotLinkableError):
            link_1c_customer(
                target_id=target.pk,
                source_id=source.pk,
                expected_onec_id=source.onec_id,
            )

    def test_stale_expected_onec_id_is_rejected(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        target = make_applicant(tax_id)

        with pytest.raises(SourceNotLinkableError):
            link_1c_customer(
                target_id=target.pk,
                source_id=source.pk,
                expected_onec_id="1C-устаревший",
            )

        target.refresh_from_db()
        assert target.onec_id is None

    def test_tax_id_mismatch_is_rejected(self):
        source = make_1c_record(unique_tax_id())
        target = make_applicant(unique_tax_id())

        with pytest.raises(SourceNotLinkableError):
            link_1c_customer(
                target_id=target.pk,
                source_id=source.pk,
                expected_onec_id=source.onec_id,
            )

    def test_double_submit_is_rejected_without_partial_write(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        target = make_applicant(tax_id)
        onec_id = source.onec_id

        link_1c_customer(target_id=target.pk, source_id=source.pk, expected_onec_id=onec_id)

        with pytest.raises(LinkCandidateError):
            link_1c_customer(target_id=target.pk, source_id=source.pk, expected_onec_id=onec_id)

        target.refresh_from_db()
        source.refresh_from_db()
        assert target.onec_id == onec_id
        assert source.onec_id is None
        assert AuditLog.objects.filter(action="link_1c_customer").count() == 1

    def test_failure_mid_transfer_rolls_back_both_rows(self):
        """
        Откат обязан вернуть обе записи в исходное состояние: иначе останется
        источник со снятым onec_id и цель без него — идентичность 1С потеряна.
        """
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id)
        target = make_applicant(tax_id)
        onec_id = source.onec_id

        with patch(
            "apps.users.services.link_1c_customer.AuditLog.log_action",
            side_effect=RuntimeError("сбой на последнем шаге"),
        ):
            with pytest.raises(RuntimeError):
                link_1c_customer(
                    target_id=target.pk,
                    source_id=source.pk,
                    expected_onec_id=onec_id,
                )

        source.refresh_from_db()
        target.refresh_from_db()
        assert source.onec_id == onec_id
        assert source.is_active is True
        assert target.onec_id is None
        assert not AuditLog.objects.filter(action="link_1c_customer").exists()

    def test_self_link_is_rejected(self):
        record = make_1c_record(unique_tax_id())

        with pytest.raises(LinkCandidateError):
            link_1c_customer(
                target_id=record.pk,
                source_id=record.pk,
                expected_onec_id=record.onec_id,
            )

    def test_missing_source_is_rejected(self):
        target = make_applicant(unique_tax_id())

        with pytest.raises(SourceNotLinkableError):
            link_1c_customer(target_id=target.pk, source_id=10**9, expected_onec_id="")

    def test_source_without_identifiers_is_rejected(self):
        tax_id = unique_tax_id()
        source = make_1c_record(tax_id, onec_id=None, onec_guid=None)
        target = make_applicant(tax_id)

        with pytest.raises(SourceNotLinkableError):
            link_1c_customer(target_id=target.pk, source_id=source.pk, expected_onec_id="")
