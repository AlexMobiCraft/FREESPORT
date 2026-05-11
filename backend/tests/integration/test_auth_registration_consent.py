from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.common.models import UserConsent
from apps.users.models import User


pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def unique_email(prefix: str) -> str:
    return f"{prefix}_{time.time_ns()}@example.com"


def retail_payload(**overrides):
    payload = {
        "email": unique_email("consent_retail"),
        "password": "StrongPassword123!",
        "password_confirm": "StrongPassword123!",
        "first_name": "Consent",
        "last_name": "Retail",
        "role": "retail",
        "pdp_consent": True,
        "marketing_consent": False,
    }
    payload.update(overrides)
    return payload


def b2b_payload(**overrides):
    payload = {
        "email": unique_email("consent_b2b"),
        "password": "StrongPassword123!",
        "password_confirm": "StrongPassword123!",
        "first_name": "Consent",
        "last_name": "B2B",
        "role": "wholesale_level1",
        "company_name": "Consent Company",
        "tax_id": "1234567890",
        "pdp_consent": True,
        "marketing_consent": False,
    }
    payload.update(overrides)
    return payload


def post_register(client: APIClient, payload: dict, **headers):
    return client.post("/api/v1/auth/register/", payload, format="json", **headers)


def test_registration_requires_pdp_consent():
    client = APIClient()
    payload = retail_payload()
    payload.pop("pdp_consent")

    response = post_register(client, payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "pdp_consent" in response.data
    assert response.data["pdp_consent"] == ["Необходимо согласие на обработку персональных данных."]


def test_registration_rejects_pdp_consent_false():
    client = APIClient()

    response = post_register(client, retail_payload(pdp_consent=False))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "pdp_consent" in response.data


def test_retail_registration_creates_pdp_consent_record():
    client = APIClient()

    response = post_register(
        client,
        retail_payload(marketing_consent=False),
        REMOTE_ADDR="127.0.0.10",
        HTTP_USER_AGENT="ConsentTestAgent/1.0",
    )

    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email=response.data["user"]["email"])
    consents = UserConsent.objects.filter(user=user)
    assert consents.count() == 1
    consent = consents.get()
    assert consent.consent_type == "pdp_contract"
    assert consent.ip_address == "127.0.0.10"
    assert consent.user_agent == "ConsentTestAgent/1.0"


def test_retail_registration_with_marketing_creates_two_records():
    client = APIClient()

    response = post_register(client, retail_payload(marketing_consent=True))

    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email=response.data["user"]["email"])
    assert set(UserConsent.objects.filter(user=user).values_list("consent_type", flat=True)) == {
        "pdp_contract",
        "marketing_email",
    }


@patch("apps.users.serializers.send_admin_verification_email.delay")
@patch("apps.users.serializers.send_user_pending_email.delay")
def test_b2b_registration_creates_pdp_consent_record_for_pending_user(
    mock_user_email,
    mock_admin_email,
):
    client = APIClient()

    response = post_register(client, b2b_payload())

    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email=response.data["user"]["email"])
    assert user.is_active is False
    assert user.is_verified is False
    consent = UserConsent.objects.get(user=user)
    assert consent.consent_type == "pdp_contract"
    mock_admin_email.assert_called_once_with(user.id)
    mock_user_email.assert_called_once_with(user.id)


def test_consent_record_captures_ip_and_user_agent_from_proxy_headers():
    client = APIClient()
    long_user_agent = "A" * 600

    response = post_register(
        client,
        retail_payload(),
        HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8",
        HTTP_USER_AGENT=long_user_agent,
    )

    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email=response.data["user"]["email"])
    consent = UserConsent.objects.get(user=user)
    assert consent.ip_address == "1.2.3.4"
    assert consent.user_agent == "A" * 512


def test_registration_ignores_invalid_forwarded_ip_for_consent_record():
    client = APIClient()

    response = post_register(
        client,
        retail_payload(),
        HTTP_X_FORWARDED_FOR="not-a-valid-ip, 5.6.7.8",
        HTTP_USER_AGENT="ConsentTestAgent/1.0",
    )

    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email=response.data["user"]["email"])
    consent = UserConsent.objects.get(user=user)
    assert consent.ip_address is None


def test_consent_records_have_default_policy_version():
    client = APIClient()

    response = post_register(client, retail_payload(marketing_consent=True))

    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email=response.data["user"]["email"])
    assert set(UserConsent.objects.filter(user=user).values_list("policy_version", flat=True)) == {"1.0"}
