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
        """
        import re
        auth_header = self._get_auth_header()

        # First authenticate to establish session
        self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        # Subsequent request uses the cookie automatically managed by APIClient
        response = self.client.get(
            self.url, data={"mode": "init"}
        )

        assert response.status_code == status.HTTP_200_OK

        content = response.content.decode("utf-8").splitlines()
        assert len(content) == 4, f"Expected 4 lines, got {len(content)}: {content}"

        # Validate each line format with REGEX (AI-Review LOW priority fix)
        assert re.match(r'^zip=(yes|no)$', content[0]), f"Line 1 format error: {content[0]}"
        assert re.match(r'^file_limit=\d+$', content[1]), f"Line 2 format error: {content[1]}"
        assert re.match(r'^sessid=[a-zA-Z0-9]+$', content[2]), f"Line 3 format error: {content[2]}"
        assert re.match(r'^version=\d+\.\d+$', content[3]), f"Line 4 format error: {content[3]}"
        assert content[3] == "version=3.1"

    def test_init_unauthenticated(self):
        """
        TC2/AC2: Unauthenticated ?mode=init returns 401 Unauthorized.
        """
        # Ensure client is logged out / no cookies
        self.client.logout()
        response = self.client.get(self.url, data={"mode": "init"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # With PlainTextRenderer, it returns "failure\n..."
        assert b"failure" in response.content

    def test_init_basic_auth_no_session(self):
        """
        [AI-Review][HIGH] Verify that calling mode=init with Basic Auth 
        but without a previous checkauth fails (protocol violation).
        """
        auth_header = self._get_auth_header()
        
        # We explicitly DO NOT call checkauth first
        response = self.client.get(
            self.url, data={"mode": "init"}, HTTP_AUTHORIZATION=auth_header
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert b"No session" in response.content

    def test_init_no_permission(self):
        """
        TC3/AC3: User without can_exchange_1c permission returns 403 Forbidden.
        """
        import uuid
        email = f"regular_init_{uuid.uuid4().hex[:8]}@example.com"
        user = User.objects.create_user(
            email=email,
            password="password123",
            is_staff=False,
        )
        
        self.client.force_login(user)

        response = self.client.get(
            self.url, data={"mode": "init"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_init_post_compatibility(self):
        """
        TC4: POST ?mode=init returns same result as GET (1C compatibility).
        """
        auth_header = self._get_auth_header()
        self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )

        response = self.client.post(
            self.url + "?mode=init"
        )

        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8").splitlines()
        assert len(content) == 4

    def test_full_1c_protocol_flow(self):
        """
        [AI-Review][HIGH] Validates the full checkauth -> init sequence.
        """
        auth_header = self._get_auth_header()
        
        # 1. CheckAuth
        resp1 = self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )
        assert resp1.status_code == 200
        lines1 = resp1.content.decode("utf-8").splitlines()
        cookie_name = lines1[1]
        session_id = lines1[2]
        
        # 2. Init
        resp2 = self.client.get(self.url, data={"mode": "init"})
        assert resp2.status_code == 200
        lines2 = resp2.content.decode("utf-8").splitlines()
        assert lines2[2] == f"sessid={session_id}"
        
        # Verify cookie is present in client
        assert self.client.cookies.get(cookie_name).value == session_id

    def test_checkauth_twice_same_session(self):
        """
        [AI-Review][MEDIUM] Calling checkauth twice should preserve/return same session.
        """
        auth_header = self._get_auth_header()
        
        resp1 = self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )
        sessid1 = resp1.content.decode("utf-8").splitlines()[2]
        
        resp2 = self.client.get(
            self.url, data={"mode": "checkauth"}, HTTP_AUTHORIZATION=auth_header
        )
        sessid2 = resp2.content.decode("utf-8").splitlines()[2]
        
        assert sessid1 == sessid2, "Session ID should be stable across consecutive checkauth calls"

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
