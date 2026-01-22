import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class Test1CCheckAuth:
    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/integration/1c/exchange/"
        self.test_user = User.objects.create_user(
            email="1c@example.com",
            password="secure_password_123",
            first_name="1C",
            last_name="Technical",
            is_staff=True
        )

    def test_checkauth_success(self):
        """
        AC 1: GET ?mode=checkauth with valid Basic Auth returns 200, text/plain, and success lines.
        """
        import base64
        auth_header = 'Basic ' + base64.b64encode(b'1c@example.com:secure_password_123').decode('ascii')
        
        response = self.client.get(
            self.url,
            data={'mode': 'checkauth'},
            HTTP_AUTHORIZATION=auth_header
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'text/plain'
        
        content = response.content.decode('utf-8').splitlines()
        assert len(content) == 3
        assert content[0] == 'success'
        # content[1] and content[2] are cookie name and value

    def test_checkauth_invalid_credentials(self):
        """
        AC 2: GET ?mode=checkauth with invalid Basic Auth returns 401.
        """
        import base64
        auth_header = 'Basic ' + base64.b64encode(b'wrong_user:wrong_pass').decode('ascii')
        
        response = self.client.get(
            self.url,
            data={'mode': 'checkauth'},
            HTTP_AUTHORIZATION=auth_header
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_checkauth_no_auth(self):
        """
        AC 2: GET ?mode=checkauth without auth returns 401.
        """
        response = self.client.get(self.url, data={'mode': 'checkauth'})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_checkauth_no_permission(self):
        """
        AC 3: Unauthorized user (no staff/perm) returns 403.
        """
        other_user = User.objects.create_user(
            email="regular@example.com",
            password="password123",
            first_name="Regular",
            last_name="User",
            is_staff=False
        )
        import base64
        auth_header = 'Basic ' + base64.b64encode(b'regular@example.com:password123').decode('ascii')
        
        response = self.client.get(
            self.url,
            data={'mode': 'checkauth'},
            HTTP_AUTHORIZATION=auth_header
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_checkauth_with_permission_only(self):
        """
        Verify that a non-staff user with 'can_exchange_1c' permission can access the endpoint.
        """
        from django.contrib.auth.models import Permission
        
        perm_user = User.objects.create_user(
            email="perm@example.com",
            password="password123",
            first_name="Perm",
            last_name="User",
            is_staff=False
        )
        
        # Add permission
        permission = Permission.objects.get(codename='can_exchange_1c')
        perm_user.user_permissions.add(permission)
        
        import base64
        auth_header = 'Basic ' + base64.b64encode(b'perm@example.com:password123').decode('ascii')
        
        response = self.client.get(
            self.url,
            data={'mode': 'checkauth'},
            HTTP_AUTHORIZATION=auth_header
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert b'success' in response.content
