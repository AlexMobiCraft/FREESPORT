# Generated manually for order constraints

from django.db import migrations, models
from django.db.models import CheckConstraint, Q, UniqueConstraint


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        # Check constraints для сумм заказа
        migrations.AddConstraint(
            model_name='order',
            constraint=CheckConstraint(
                check=Q(total_amount__gte=0),
                name='orders_total_amount_positive'
            ),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=CheckConstraint(
                check=Q(discount_amount__gte=0),
                name='orders_discount_amount_positive'
            ),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=CheckConstraint(
                check=Q(delivery_cost__gte=0),
                name='orders_delivery_cost_positive'
            ),
        ),
        
        # Check constraints для элементов заказа
        migrations.AddConstraint(
            model_name='orderitem',
            constraint=CheckConstraint(
                check=Q(quantity__gte=1),
                name='order_items_quantity_positive'
            ),
        ),
        migrations.AddConstraint(
            model_name='orderitem',
            constraint=CheckConstraint(
                check=Q(unit_price__gte=0),
                name='order_items_unit_price_positive'
            ),
        ),
        migrations.AddConstraint(
            model_name='orderitem',
            constraint=CheckConstraint(
                check=Q(total_price__gte=0),
                name='order_items_total_price_positive'
            ),
        ),
        
        # Бизнес-правило: общая цена = единичная цена * количество
        # Удалено, так как это будет проверяться в Django модели через save() метод
    ]