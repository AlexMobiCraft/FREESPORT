"""
Story 5.3: Интеграционные тесты полного цикла импорта статусов.

Тесты покрывают полный E2E цикл 1С:
checkauth -> query -> success -> file (orders.xml).

Updated for Story 34-3: handle_query exports only sub-orders
(is_master=False, parent_order__isnull=False). _create_order_with_item
now creates master + sub-order structure.
"""

from __future__ import annotations

from datetime import date
from typing import cast

import pytest
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIClient

from apps.orders.models import Order
from tests.conftest import OrderFactory, OrderItemFactory, ProductVariantFactory, UserFactory
from tests.utils import EXCHANGE_URL, ONEC_PASSWORD
from tests.utils import build_orders_xml as _build_orders_xml
from tests.utils import parse_commerceml_response, perform_1c_checkauth

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture
def log_dir(tmp_path, settings):
    """Override EXCHANGE_LOG_DIR -> tmp_path to isolate logs."""
    private_log = tmp_path / "var" / "1c_exchange" / "logs"
    settings.EXCHANGE_LOG_DIR = str(private_log)
    settings.MEDIA_ROOT = str(tmp_path / "media")
    return private_log


@pytest.fixture
def onec_user(db):
    """Staff user for 1C exchange."""
    return UserFactory.create(is_staff=True, password=ONEC_PASSWORD)


@pytest.fixture
def auth_client(onec_user) -> APIClient:
    """Authenticated APIClient after checkauth."""
    client = APIClient()
    return perform_1c_checkauth(client, onec_user.email, ONEC_PASSWORD)


def _post_orders_xml(auth_client: APIClient, xml_data: bytes) -> Response:
    return cast(
        Response,
        auth_client.post(
            f"{EXCHANGE_URL}?mode=file&filename=orders.xml",
            data=xml_data,
            content_type="application/xml",
            CONTENT_LENGTH=str(len(xml_data)),
        ),
    )


def _get_exchange(auth_client: APIClient, mode: str) -> Response:
    return cast(Response, auth_client.get(EXCHANGE_URL, data={"mode": mode}))


def _create_order_with_item(
    *,
    status: str = "pending",
    sent_to_1c: bool = False,
) -> Order:
    """Create master + sub-order + OrderItem for E2E import tests.

    Returns the sub-order (is_master=False), which is the one exported to 1C
    and the one that receives status updates from 1C.
    """
    variant = ProductVariantFactory.create()
    master = Order.objects.create(
        status=status,
        sent_to_1c=False,
        is_master=True,
        total_amount=variant.retail_price,
        delivery_address="ул. Тестовая, 1",
        delivery_method="courier",
        payment_method="card",
    )
    sub = Order.objects.create(
        status=status,
        sent_to_1c=sent_to_1c,
        is_master=False,
        parent_order=master,
        total_amount=variant.retail_price,
        delivery_address="ул. Тестовая, 1",
        delivery_method="courier",
        payment_method="card",
    )
    sub.order_number = f"order-{sub.pk}"
    sub.save(update_fields=["order_number"])
    OrderItemFactory.create(
        order=sub,
        product=variant.product,
        variant=variant,
        product_name=variant.product.name,
        unit_price=variant.retail_price,
        quantity=1,
        total_price=variant.retail_price,
    )
    return sub


def test_full_cycle_export_then_import_updates_status(auth_client, log_dir, db):
    """AC1: export -> success -> import updates shipped status on sub-order."""
    # ARRANGE
    sub = _create_order_with_item()

    # ACT — export query
    resp_query = _get_exchange(auth_client, "query")
    assert resp_query.status_code == 200
    root = parse_commerceml_response(resp_query)
    documents = root.findall(".//Документ")
    assert any(
        doc.findtext("Номер") == sub.order_number for doc in documents
    ), "Exported XML must include the target sub-order"

    # ACT — export success
    resp_success = _get_exchange(auth_client, "success")
    assert resp_success.status_code == 200

    sub.refresh_from_db()
    assert sub.sent_to_1c is True

    xml_data = _build_orders_xml(
        order_id=f"order-{sub.pk}",
        order_number=f"order-{sub.pk}",
        status_1c="Отгружен",
    )

    # ACT — import orders.xml
    resp_file = _post_orders_xml(auth_client, xml_data)
    assert resp_file.status_code == 200
    assert resp_file.content.decode("utf-8").startswith("success")

    # ASSERT
    sub.refresh_from_db()
    assert sub.status == "shipped"
    assert sub.status_1c == "Отгружен"
    assert sub.sent_to_1c is True


@pytest.mark.parametrize(
    "status_1c, expected_status",
    [
        ("ОжидаетОбработки", "processing"),
        ("Отгружен", "shipped"),
        ("Доставлен", "delivered"),
        ("Отменен", "cancelled"),
    ],
)
def test_status_mapping_from_1c(auth_client, log_dir, db, status_1c, expected_status):
    """AC2: 1C status mapping for processing/shipped/delivered/cancelled."""
    # ARRANGE
    sub = _create_order_with_item()
    xml_data = _build_orders_xml(
        order_id=f"order-{sub.pk}",
        order_number=f"order-{sub.pk}",
        status_1c=status_1c,
    )

    # ACT
    response = _post_orders_xml(auth_client, xml_data)
    assert response.status_code == 200
    assert response.content.decode("utf-8").startswith("success")

    # ASSERT
    sub.refresh_from_db()
    assert sub.status == expected_status
    assert sub.status_1c == status_1c


def test_dates_extracted_from_requisites(auth_client, log_dir, db):
    """AC3: paid_at/shipped_at extracted from requisites."""
    # ARRANGE
    sub = _create_order_with_item()
    xml_data = _build_orders_xml(
        order_id=f"order-{sub.pk}",
        order_number=f"order-{sub.pk}",
        status_1c="Отгружен",
        paid_date="2026-02-01",
        shipped_date="2026-02-02",
    )

    # ACT
    response = _post_orders_xml(auth_client, xml_data)
    assert response.status_code == 200
    assert response.content.decode("utf-8").startswith("success")

    # ASSERT
    sub.refresh_from_db()
    assert sub.paid_at is not None
    assert timezone.localdate(sub.paid_at) == date(2026, 2, 1)
    assert sub.shipped_at is not None
    assert timezone.localdate(sub.shipped_at) == date(2026, 2, 2)


def test_invalid_xml_returns_failure(auth_client, log_dir, db):
    """AC4: invalid XML returns failure."""
    # ARRANGE
    xml_data = b"<not valid xml!!!"

    # ACT
    response = _post_orders_xml(auth_client, xml_data)

    # ASSERT
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert content.startswith("failure")
    assert "Malformed XML" in content


def test_unknown_order_returns_failure(auth_client, log_dir, db):
    """AC4: unknown order returns failure and no updates."""
    # ARRANGE
    existing_sub = _create_order_with_item()
    missing_id = existing_sub.pk + 9999
    xml_data = _build_orders_xml(
        order_id=f"order-{missing_id}",
        order_number=f"order-{missing_id}",
        status_1c="Отгружен",
    )

    # ACT
    response = _post_orders_xml(auth_client, xml_data)

    # ASSERT
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert content.startswith("failure")
    existing_sub.refresh_from_db()
    assert existing_sub.status == "pending"
    assert existing_sub.sent_to_1c is False
