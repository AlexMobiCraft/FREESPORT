import pytest
from django.urls import reverse
from rest_framework import status

from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from tests.conftest import ProductFactory, UserFactory, sample_image

pytestmark = pytest.mark.django_db


@pytest.fixture
def product(sample_image):
    return ProductFactory.create(stock_quantity=10, main_image=sample_image)


@pytest.fixture
def authenticated_client(db, api_client):
    user = UserFactory.create()
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    api_client.user = user
    return api_client


@pytest.fixture
def cart_with_item(authenticated_client, product):
    cart = Cart.objects.create(user=authenticated_client.user)
    CartItem.objects.create(cart=cart, product=product, quantity=1)
    return cart


def test_create_order_from_cart(authenticated_client, cart_with_item):
    """Test creating an order from a cart with items."""
    url = reverse("orders:order-list")
    data = {
        "delivery_address": "123 Test St",
        "delivery_method": "courier",
        "payment_method": "card",
    }
    response = authenticated_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Order.objects.count() == 1
    assert OrderItem.objects.count() == 1
    cart_with_item.refresh_from_db()
    assert cart_with_item.items.count() == 0


def test_create_order_with_empty_cart(authenticated_client):
    """Test creating an order with an empty cart fails."""
    url = reverse("orders:order-list")
    data = {
        "delivery_address": "123 Test St",
        "delivery_method": "courier",
        "payment_method": "card",
    }
    response = authenticated_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_get_order_detail(authenticated_client, cart_with_item):
    """Test retrieving an order detail."""
    # First, create an order
    create_url = reverse("orders:order-list")
    order_data = {
        "delivery_address": "123 Test St",
        "delivery_method": "courier",
        "payment_method": "card",
    }
    create_response = authenticated_client.post(create_url, order_data, format="json")
    order_id = create_response.data["id"]

    # Then, get the detail
    detail_url = reverse("orders:order-detail", kwargs={"pk": order_id})
    response = authenticated_client.get(detail_url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == order_id


def test_user_cannot_see_other_users_order(
    api_client, authenticated_client, cart_with_item
):
    """Test that a user cannot see another user's order."""
    # Create an order with the first user
    create_url = reverse("orders:order-list")
    order_data = {
        "delivery_address": "123 Test St",
        "delivery_method": "courier",
        "payment_method": "card",
    }
    create_response = authenticated_client.post(create_url, order_data, format="json")
    order_id = create_response.data["id"]

    # Create and authenticate a second user
    other_user = UserFactory.create()
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    # Try to get the first user's order
    detail_url = reverse("orders:order-detail", kwargs={"pk": order_id})
    response = api_client.get(detail_url)
    assert response.status_code == status.HTTP_404_NOT_FOUND
