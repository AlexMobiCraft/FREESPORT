"""
Сигналы для заказов FREESPORT
Отправка email-уведомлений при создании заказа (AC6)
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string

from .models import Order

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def send_order_confirmation_email(sender, instance, created, **kwargs):
    """
    Отправка email-уведомления клиенту при создании нового заказа.

    Args:
        sender: Класс модели (Order)
        instance: Экземпляр заказа
        created: True если заказ только что создан
        **kwargs: Дополнительные аргументы сигнала
    """
    if not created:
        return

    # Определяем email получателя
    customer_email = None
    if instance.user and hasattr(instance.user, "email"):
        customer_email = instance.user.email
    elif instance.customer_email:
        customer_email = instance.customer_email

    if not customer_email:
        logger.warning(
            f"Не удалось отправить email для заказа {instance.order_number}: "
            "email клиента не указан"
        )
        return

    # Формируем содержимое письма
    subject = f"Заказ #{instance.order_number} успешно оформлен - FREESPORT"

    # Простое текстовое письмо
    message = _build_order_email_text(instance)

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer_email],
            fail_silently=False,
        )
        logger.info(
            f"Email-уведомление о заказе {instance.order_number} "
            f"отправлено на {customer_email}"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки email для заказа {instance.order_number}: {e}")


def _build_order_email_text(order):
    """
    Формирование текста email-уведомления о заказе.

    Args:
        order: Экземпляр заказа

    Returns:
        str: Текст письма
    """
    # Получаем имя клиента
    customer_name = order.customer_display_name or "Уважаемый клиент"

    # Получаем способ доставки
    delivery_methods = {
        "pickup": "Самовывоз",
        "courier": "Курьерская доставка",
        "post": "Почтовая доставка",
        "transport": "Транспортная компания",
    }
    delivery_method_name = delivery_methods.get(
        order.delivery_method, order.delivery_method
    )

    # Формируем список товаров
    items_text = ""
    for item in order.items.all():
        items_text += (
            f"  - {item.product_name} × {item.quantity}: {item.total_price} ₽\n"
        )

    message = f"""
Здравствуйте, {customer_name}!

Ваш заказ #{order.order_number} успешно оформлен.

ДЕТАЛИ ЗАКАЗА:
{items_text}
Итого: {order.total_amount} ₽

ДОСТАВКА:
Способ: {delivery_method_name}
Адрес: {order.delivery_address}

ЧТО ДАЛЬШЕ?
Администратор свяжется с вами в течение 24 часов для уточнения:
- Способа оплаты
- Точной стоимости доставки
- Времени доставки

Спасибо за заказ!

С уважением,
Команда FREESPORT
"""
    return message.strip()
