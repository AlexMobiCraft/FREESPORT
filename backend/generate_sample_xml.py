import sys
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order, OrderItem
from apps.orders.services import OrderExportService
from apps.products.models import Product, ProductVariant
from apps.users.models import User


def run():
    try:
        with transaction.atomic():
            # Create dummy user
            user = User.objects.create(
                email=f"sample_{timezone.now().timestamp()}@example.com",
                first_name="Иван",
                last_name="Тестов",
                phone="+79001234567",
                tax_id="123456789012",  # Valid request for 1C often implies INN
            )

            # Create dummy product
            product = Product.objects.create(name="Тестовый Спортивный Товар")
            variant = ProductVariant.objects.create(
                product=product,
                sku="TEST-CML-31",
                retail_price=Decimal("1500.00"),
                onec_id="test-variant-guid-123",
            )

            # Create order
            order = Order.objects.create(
                user=user,
                total_amount=Decimal("3000.00"),
                status="new",
                delivery_address="101000, г. Москва, ул. Пушкина, д. Колотушкина",
                delivery_method="courier",
                payment_method="card",
                customer_name="Иван Тестов",
                customer_email=user.email,
                customer_phone=user.phone,
            )

            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                quantity=2,
                unit_price=Decimal("1500.00"),
                total_price=Decimal("3000.00"),
                product_name="Тестовый Спортивный Товар",
                product_sku="TEST-CML-31",
            )

            service = OrderExportService()
            xml = service.generate_xml(Order.objects.filter(id=order.id))

            print("BEGIN_XML_CONTENT")
            print(xml)
            print("END_XML_CONTENT")

            # We rollback to avoid saving junk to DB
            transaction.set_rollback(True)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    run()
