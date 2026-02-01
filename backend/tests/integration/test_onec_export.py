"""
Tests for Story 4.3: View-обработчики mode=query и mode=success.

Tests cover:
- AC1: handle_query for GET /?mode=query
- AC2: XML generation with OrderExportService
- AC3: ZIP compression when zip=yes
- AC4: handle_success for GET /?mode=success
- AC5: Marking orders as sent_to_1c=True
- AC6: Audit log file saving
- AC7: Full cycle integration tests
- AC8: Compatibility with checkauth authentication
"""

import base64
import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.products.models import Brand, Category, Product, ProductVariant

User = get_user_model()


@pytest.fixture
def onec_user(db):
    """Create a 1C exchange user with proper permissions."""
    user = User.objects.create_user(
        email="1c_export@example.com",
        password="secure_pass_123",
        first_name="1C",
        last_name="Export",
        is_staff=True,
    )
    return user


@pytest.fixture
def customer_user(db):
    """Create a customer user for orders."""
    return User.objects.create_user(
        email="customer@example.com",
        password="cust_pass_123",
        first_name="Иван",
        last_name="Петров",
    )


@pytest.fixture
def product_variant(db):
    """Create a product variant with onec_id."""
    brand = Brand.objects.create(name="TestBrand", slug="testbrand")
    category = Category.objects.create(name="TestCat", slug="testcat")
    product = Product.objects.create(
        name="Test Product",
        slug="test-product",
        brand=brand,
        category=category,
    )
    variant = ProductVariant.objects.create(
        product=product,
        onec_id="variant-1c-id-001",
        sku="TEST-SKU-001",
        retail_price=1500,
    )
    return variant


@pytest.fixture
def order_for_export(db, customer_user, product_variant):
    """Create an order ready for 1C export."""
    order = Order.objects.create(
        user=customer_user,
        order_number="FS-TEST-001",
        total_amount=1500,
        sent_to_1c=False,
        delivery_address="ул. Тестовая, 1",
        delivery_method="pickup",
        payment_method="card",
    )
    OrderItem.objects.create(
        order=order,
        product=product_variant.product,
        variant=product_variant,
        product_name="Test Product",
        unit_price=1500,
        quantity=1,
        total_price=1500,
    )
    return order


@pytest.fixture
def authenticated_client(onec_user):
    """APIClient that performs checkauth first to establish session."""
    client = APIClient()
    auth_header = "Basic " + base64.b64encode(
        b"1c_export@example.com:secure_pass_123"
    ).decode("ascii")
    # Perform checkauth to establish session
    response = client.get(
        "/api/integration/1c/exchange/",
        data={"mode": "checkauth"},
        HTTP_AUTHORIZATION=auth_header,
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert body.startswith("success")
    # Extract session cookie
    lines = body.replace("\r\n", "\n").split("\n")
    cookie_name = lines[1]
    cookie_value = lines[2]
    client.cookies[cookie_name] = cookie_value
    return client


@pytest.fixture
def log_dir(tmp_path, settings):
    """Override MEDIA_ROOT so audit logs go to tmp_path."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
    return Path(settings.MEDIA_ROOT) / "1c_exchange" / "logs"


# ============================================================
# Task 1: Audit log infrastructure tests (AC6)
# ============================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestExchangeLogInfrastructure:
    """Tests for _save_exchange_log helper (Task 1)."""

    def test_save_exchange_log_creates_directory_and_file(self, log_dir):
        from apps.integrations.onec_exchange.views import _save_exchange_log

        _save_exchange_log("test_output.xml", "<xml>data</xml>")
        assert log_dir.exists()
        saved = list(log_dir.glob("*test_output.xml"))
        assert len(saved) == 1
        assert "<xml>data</xml>" in saved[0].read_text(encoding="utf-8")

    def test_save_exchange_log_binary(self, log_dir):
        from apps.integrations.onec_exchange.views import _save_exchange_log

        binary_data = b"\x50\x4b\x03\x04binary"
        _save_exchange_log("test_output.zip", binary_data, is_binary=True)
        saved = list(log_dir.glob("*test_output.zip"))
        assert len(saved) == 1
        assert saved[0].read_bytes() == binary_data


# ============================================================
# Task 2: handle_query tests (AC1, AC2, AC3)
# ============================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestModeQuery:
    """Tests for handle_query (Task 2)."""

    def test_mode_query_returns_xml(
        self, authenticated_client, order_for_export, log_dir
    ):
        """AC1+AC2: GET /?mode=query returns XML with pending orders."""
        response = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query"},
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "application/xml"
        content = response.content.decode("utf-8")
        assert "<?xml" in content
        assert "КоммерческаяИнформация" in content
        assert "Документ" in content
        assert "FS-TEST-001" in content

    def test_mode_query_empty_when_no_orders(
        self, authenticated_client, log_dir
    ):
        """AC2: Returns valid XML even when no pending orders."""
        response = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query"},
        )
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "КоммерческаяИнформация" in content
        assert "Документ" not in content

    def test_mode_query_zip(
        self, authenticated_client, order_for_export, log_dir
    ):
        """AC3: zip=yes returns a ZIP archive containing orders.xml."""
        response = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query", "zip": "yes"},
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        # Verify it's a valid ZIP with orders.xml inside
        buf = io.BytesIO(response.content)
        with zipfile.ZipFile(buf) as zf:
            assert "orders.xml" in zf.namelist()
            xml_content = zf.read("orders.xml").decode("utf-8")
            assert "КоммерческаяИнформация" in xml_content
            assert "FS-TEST-001" in xml_content

    def test_mode_query_excludes_already_sent(
        self, authenticated_client, order_for_export, log_dir
    ):
        """Only orders with sent_to_1c=False are returned."""
        order_for_export.sent_to_1c = True
        order_for_export.save()
        response = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query"},
        )
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Документ" not in content

    def test_mode_query_saves_audit_log(
        self, authenticated_client, order_for_export, log_dir
    ):
        """AC6: Audit log file is saved."""
        authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query"},
        )
        assert log_dir.exists()
        log_files = list(log_dir.glob("*"))
        assert len(log_files) >= 1


# ============================================================
# Task 3: handle_success tests (AC4, AC5)
# ============================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestModeSuccess:
    """Tests for handle_success (Task 3)."""

    def test_mode_success_updates_status(
        self, authenticated_client, order_for_export, log_dir
    ):
        """AC4+AC5: query then success marks orders as sent."""
        # First, perform query to set session timestamp
        authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query"},
        )
        # Then confirm success
        response = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "success"},
        )
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "success" in content

        order_for_export.refresh_from_db()
        assert order_for_export.sent_to_1c is True
        assert order_for_export.sent_to_1c_at is not None

    def test_mode_success_without_prior_query(
        self, authenticated_client, order_for_export, log_dir
    ):
        """AC5: success without prior query should not update orders (race condition protection)."""
        response = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "success"},
        )
        assert response.status_code == 200
        order_for_export.refresh_from_db()
        assert order_for_export.sent_to_1c is False

    def test_mode_success_does_not_mark_new_orders(
        self, authenticated_client, order_for_export, customer_user,
        product_variant, log_dir
    ):
        """AC5: Orders created after query should NOT be marked as sent (race condition)."""
        # Query existing orders
        authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query"},
        )
        # Create a new order AFTER query
        new_order = Order.objects.create(
            user=customer_user,
            order_number="FS-TEST-002",
            total_amount=3000,
            sent_to_1c=False,
            delivery_address="ул. Новая, 2",
            delivery_method="pickup",
            payment_method="card",
        )
        OrderItem.objects.create(
            order=new_order,
            product=product_variant.product,
            variant=product_variant,
            product_name="Test Product 2",
            unit_price=3000,
            quantity=1,
            total_price=3000,
        )
        # Confirm success
        authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "success"},
        )
        order_for_export.refresh_from_db()
        new_order.refresh_from_db()
        assert order_for_export.sent_to_1c is True
        assert new_order.sent_to_1c is False  # Must NOT be marked


# ============================================================
# Task 4: Full cycle integration (AC7, AC8)
# ============================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestFullExportCycle:
    """Full cycle: checkauth -> query -> success (Task 4)."""

    def test_full_cycle_xml(
        self, authenticated_client, order_for_export, log_dir
    ):
        """AC7+AC8: Full XML export cycle."""
        # 1. Query
        resp_query = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query"},
        )
        assert resp_query.status_code == 200
        assert "FS-TEST-001" in resp_query.content.decode("utf-8")

        # 2. Success
        resp_success = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "success"},
        )
        assert resp_success.status_code == 200

        # 3. Verify order marked
        order_for_export.refresh_from_db()
        assert order_for_export.sent_to_1c is True

        # 4. Query again should return no orders
        resp_query2 = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query"},
        )
        assert "Документ" not in resp_query2.content.decode("utf-8")

    def test_full_cycle_zip(
        self, authenticated_client, order_for_export, log_dir
    ):
        """AC7: Full ZIP export cycle."""
        resp_query = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query", "zip": "yes"},
        )
        assert resp_query.status_code == 200
        assert resp_query["Content-Type"] == "application/zip"

        resp_success = authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "success"},
        )
        assert resp_success.status_code == 200
        order_for_export.refresh_from_db()
        assert order_for_export.sent_to_1c is True

    def test_audit_logging(
        self, authenticated_client, order_for_export, log_dir
    ):
        """AC6: Audit files saved to MEDIA_ROOT/1c_exchange/logs/."""
        authenticated_client.get(
            "/api/integration/1c/exchange/",
            data={"mode": "query"},
        )
        assert log_dir.exists()
        log_files = list(log_dir.glob("*"))
        assert len(log_files) >= 1
