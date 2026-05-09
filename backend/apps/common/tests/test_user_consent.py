"""
Тесты модели UserConsent.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from apps.common.models import UserConsent
from apps.common.admin import UserConsentAdmin


pytestmark = [pytest.mark.django_db, pytest.mark.unit]


User = get_user_model()


def test_create_pdp_contract_consent_for_user():
    user = User.objects.create_user(
        email="pdp@example.com",
        password="test-password",
    )

    consent = UserConsent.objects.create(
        user=user,
        consent_type="pdp_contract",
        ip_address="192.168.1.10",
        user_agent="pytest",
    )

    assert consent.user == user
    assert consent.consent_type == "pdp_contract"
    assert consent.policy_version == "1.0"
    assert consent.given_at is not None


def test_create_marketing_email_consent_for_user():
    user = User.objects.create_user(
        email="marketing@example.com",
        password="test-password",
    )

    consent = UserConsent.objects.create(
        user=user,
        consent_type="marketing_email",
        ip_address="192.168.1.11",
        user_agent="pytest",
        policy_version="1.1",
    )

    assert consent.user == user
    assert consent.consent_type == "marketing_email"
    assert consent.policy_version == "1.1"


def test_create_anonymous_consent_with_session_key():
    consent = UserConsent.objects.create(
        session_key="anonymous-session-key-1234567890",
        consent_type="pdp_contract",
        ip_address="127.0.0.1",
    )

    assert consent.user is None
    assert consent.session_key == "anonymous-session-key-1234567890"


def test_user_consent_str_for_user():
    user = User.objects.create_user(
        email="str@example.com",
        password="test-password",
    )
    consent = UserConsent.objects.create(
        user=user,
        consent_type="pdp_contract",
    )

    result = str(consent)

    assert "str@example.com" in result
    assert "Согласие на обработку ПДн для исполнения договора" in result


def test_user_consent_requires_consent_type():
    consent = UserConsent(session_key="anonymous", consent_type="")

    with pytest.raises(ValidationError):
        consent.full_clean()


def test_user_consent_admin_is_read_only():
    request = RequestFactory().get("/admin/common/userconsent/")
    request.user = User.objects.create_superuser(
        email="admin@example.com",
        password="test-password",
    )
    model_admin = UserConsentAdmin(UserConsent, admin.site)

    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_change_permission(request) is False
    assert model_admin.has_delete_permission(request) is False
    assert model_admin.readonly_fields == [
        "user",
        "session_key",
        "consent_type",
        "given_at",
        "ip_address",
        "user_agent",
        "policy_version",
    ]
