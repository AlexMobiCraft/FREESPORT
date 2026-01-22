"""
Tests for 1C Exchange API endpoints.

Story 1.1: Setup 1C Exchange Endpoint & Auth (checkauth mode)
Story 1.2: Implement Init Mode Configuration (init mode)

These tests cover the 1C HTTP exchange protocol implementation
per https://dev.1c-bitrix.ru/api_help/sale/algorithms/data_2_site.php
"""

import base64

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.integration
class Test1CCheckAuth:
    """
    Tests for Story 1.1: Setup 1C Exchange Endpoint & Auth
    Validates ?mode=checkauth authentication flow.
    """

    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/integration/1c/exchange/"
        self.test_user = User.objects.create_user(
            email="1c@example.com",
            password="secure_password_123",
            first_name="1C",
            last_name="Technical",
            is_staff=True,
        )

    def test_checkauth_success(self):
        """
        AC 1: GET ?mode=checkauth with valid Basic Auth returns 200, text/plain, and success lines.
        """
        auth_header = (
            "Basic "
            + base64.b64encode(b"1c@example.com:secure_password_123").decode("ascii")
        )

        response = self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "text/plain"

        content = response.content.decode("utf-8").splitlines()
        assert len(content) == 3
        assert content[0] == "success"
        # content[1] and content[2] are cookie name and value

    def test_checkauth_invalid_credentials(self):
        """
        AC 2: GET ?mode=checkauth with invalid Basic Auth returns 401.
        """
        auth_header = (
            "Basic " + base64.b64encode(b"wrong_user:wrong_pass").decode("ascii")
        )

        response = self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_checkauth_no_auth(self):
        """
        AC 2: GET ?mode=checkauth without auth returns 401.
        """
        response = self.client.get(self.url, data={"mode": "checkauth"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_checkauth_no_permission(self):
        """
        AC 3: Unauthorized user (no staff/perm) returns 403.
        """
        User.objects.create_user(
            email="regular@example.com",
            password="password123",
            first_name="Regular",
            last_name="User",
            is_staff=False,
        )
        auth_header = (
            "Basic "
            + base64.b64encode(b"regular@example.com:password123").decode("ascii")
        )

        response = self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_checkauth_with_permission_only(self):
        """
        Verify that a non-staff user with 'can_exchange_1c' permission can access the endpoint.
        """
        perm_user = User.objects.create_user(
            email="perm@example.com",
            password="password123",
            first_name="Perm",
            last_name="User",
            is_staff=False,
        )

        # Add permission
        permission = Permission.objects.get(codename="can_exchange_1c")
        perm_user.user_permissions.add(permission)

        auth_header = (
            "Basic "
            + base64.b64encode(b"perm@example.com:password123").decode("ascii")
        )

        response = self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        assert response.status_code == status.HTTP_200_OK
        assert b"success" in response.content


@pytest.mark.django_db
@pytest.mark.integration
class Test1CInitMode:
    """
    Tests for Story 1.2: Implement Init Mode Configuration
    Validates ?mode=init returns server capabilities for 1C data exchange.
    """

    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/integration/1c/exchange/"
        self.test_user = User.objects.create_user(
            email="1c_init@example.com",
            password="secure_password_123",
            first_name="1C",
            last_name="Technical",
            is_staff=True,
        )

    def _get_auth_header(
        self, email="1c_init@example.com", password="secure_password_123"
    ):
        """Helper to create Basic Auth header."""
        credentials = f"{email}:{password}".encode("utf-8")
        return "Basic " + base64.b64encode(credentials).decode("ascii")

    def test_init_success_4_line_response(self):
        """
        TC1/AC1: Authenticated ?mode=init returns 200 OK with 4-line response.
        Response format: zip=yes, file_limit=X, sessid=X, version=3.1
        
        CRITICAL: This test validates the SESSION COOKIE flow. 
        1. Authenticate via Basic Auth (checkauth) -> sets cookie in client
        2. Request init via Cookie (NO Basic Auth header) -> must work
        """
        auth_header = self._get_auth_header()

        # First authenticate to establish session
        self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        # Subsequent request uses the cookie automatically managed by APIClient
        # We explicitly DO NOT send the auth_header here
        response = self.client.get(
            self.url, data={"mode": "init"}
        )

        assert response.status_code == status.HTTP_200_OK

        content = response.content.decode("utf-8").splitlines()
        assert len(content) == 4, f"Expected 4 lines, got {len(content)}: {content}"

        # Validate each line format
        assert content[0].startswith("zip="), f"Line 1 should be zip=, got: {content[0]}"
        assert content[1].startswith(
            "file_limit="
        ), f"Line 2 should be file_limit=, got: {content[1]}"
        assert content[2].startswith(
            "sessid="
        ), f"Line 3 should be sessid=, got: {content[2]}"
        assert content[3].startswith(
            "version="
        ), f"Line 4 should be version=, got: {content[3]}"

    def test_init_unauthenticated(self):
        """
        TC2/AC2: Unauthenticated ?mode=init returns 401 Unauthorized.
        """
        # Ensure client is logged out / no cookies
        self.client.logout()
        response = self.client.get(self.url, data={"mode": "init"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_init_no_permission(self):
        """
        TC3/AC3: User without can_exchange_1c permission returns 403 Forbidden.
        """
        user = User.objects.create_user(
            email="regular_init@example.com",
            password="password123",
            first_name="Regular",
            last_name="User",
            is_staff=False,
        )
        
        # We use force_login to ensure the user IS authenticated but lacks permission.
        # Checkauth would return 403 and prevent login, leading to 401 here, 
        # but we want to test the PERMISSION check (403), not authentication.
        self.client.force_login(user)

        response = self.client.get(
            self.url, data={"mode": "init"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_init_post_compatibility(self):
        """
        TC4: POST ?mode=init returns same result as GET (1C compatibility).
        Must work with Session Auth (Cookie)
        """
        auth_header = self._get_auth_header()

        # First authenticate
        self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        # POST without Basic Auth header, using Cookie
        response = self.client.post(
            self.url + "?mode=init"
        )

        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8").splitlines()
        assert len(content) == 4

    def test_init_sessid_not_empty(self):
        """
        TC5: Response contains valid non-empty sessid.
        """
        auth_header = self._get_auth_header()

        # First authenticate
        self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        response = self.client.get(
            self.url, data={"mode": "init"}
        )

        content = response.content.decode("utf-8").splitlines()
        sessid_line = content[2]
        assert sessid_line.startswith("sessid=")
        sessid_value = sessid_line.split("=", 1)[1]
        assert len(sessid_value) > 0, "sessid value should not be empty"

    def test_init_version_line(self):
        """
        TC6: Response contains version=3.1 (CommerceML version).
        """
        auth_header = self._get_auth_header()

        self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        response = self.client.get(
            self.url, data={"mode": "init"}
        )

        content = response.content.decode("utf-8").splitlines()
        version_line = content[3]
        assert version_line == "version=3.1", f"Expected 'version=3.1', got: {version_line}"

    def test_init_content_type(self):
        """
        TC7: Content-Type header is text/plain.
        """
        auth_header = self._get_auth_header()

        self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        response = self.client.get(
            self.url, data={"mode": "init"}
        )

        assert "text/plain" in response["Content-Type"]
