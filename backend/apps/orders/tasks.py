"""
Celery tasks для отправки email-уведомлений о заказах.

Реализует асинхронную отправку уведомлений при создании/отмене заказов
получателям, настроенным через NotificationRecipient в Django Admin.
"""

import logging
from smtplib import SMTPException

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.common.models import NotificationRecipient
from apps.orders.models import Order

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(SMTPException, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 минут максимум
)
def send_order_notification_email(self, order_id: int) -> bool:
    """
    Отправить email-уведомление о новом заказе.

    Отправляет уведомление всем получателям с флагом notify_new_orders=True.

    Args:
        order_id: ID заказа

    Returns:
        True если хотя бы один email отправлен успешно
    """
    try:
        order = Order.objects.prefetch_related("items").get(id=order_id)
    except Order.DoesNotExist:
        logger.error(
            "Order not found for notification",
            extra={"order_id": order_id, "action": "order_notification_email"},
        )
        return False

    # Получаем активных получателей с флагом notify_new_orders
    recipients = NotificationRecipient.objects.filter(
        is_active=True,
        notify_new_orders=True,
    ).values_list("email", flat=True)

    if not recipients:
        logger.info(
            "No recipients configured for new order notifications",
            extra={"order_id": order_id, "action": "skip_order_notification"},
        )
        return False

    # Подготавливаем контекст для шаблона
    customer_email = ""
    customer_phone = ""
    customer_name = ""

    if order.user:
        customer_email = getattr(order.user, "email", "") or ""
        customer_phone = getattr(order.user, "phone", "") or ""
        customer_name = order.customer_display_name
    else:
        customer_email = order.customer_email
        customer_phone = order.customer_phone
        customer_name = order.customer_name or order.customer_email

    delivery_methods = {
        "pickup": "Самовывоз",
        "courier": "Курьерская доставка",
        "post": "Почтовая доставка",
        "transport_company": "Транспортная компания",
    }

    context = {
        "order": order,
        "items": order.items.all(),
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "delivery_method": delivery_methods.get(
            order.delivery_method, order.delivery_method
        ),
        "admin_url": f"{settings.SITE_URL}/admin/orders/order/{order.id}/change/",
    }

    # Рендерим шаблоны
    try:
        html_message = render_to_string("emails/admin_new_order.html", context)
        plain_message = render_to_string("emails/admin_new_order.txt", context)
    except Exception as e:
        logger.error(
            "Failed to render order notification template",
            extra={
                "order_id": order_id,
                "exception": str(e),
            },
        )
        # Fallback на простое сообщение
        plain_message = (
            f"Новый заказ #{order.order_number}\n\n"
            f"Клиент: {customer_name}\n"
            f"Email: {customer_email}\n"
            f"Сумма: {order.total_amount} ₽\n\n"
            f"Откройте Django Admin для просмотра деталей."
        )
        html_message = None

    # Отправляем email
    try:
        send_mail(
            subject=f"[FREESPORT] Новый заказ #{order.order_number}",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=list(recipients),
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(
            "Order notification email sent successfully",
            extra={
                "order_id": order_id,
                "order_number": order.order_number,
                "recipients_count": len(recipients),
                "total_amount": str(order.total_amount),
            },
        )
        return True

    except SMTPException as exc:
        logger.error(
            "Failed to send order notification email",
            extra={
                "order_id": order_id,
                "exception": str(exc),
                "retry_count": self.request.retries,
            },
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(SMTPException, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=600,
)
def send_order_cancelled_notification_email(self, order_id: int) -> bool:
    """
    Отправить email-уведомление об отмене заказа.

    Отправляет уведомление всем получателям с флагом notify_order_cancelled=True.

    Args:
        order_id: ID заказа

    Returns:
        True если хотя бы один email отправлен успешно
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error(
            "Order not found for cancellation notification",
            extra={"order_id": order_id},
        )
        return False

    recipients = NotificationRecipient.objects.filter(
        is_active=True,
        notify_order_cancelled=True,
    ).values_list("email", flat=True)

    if not recipients:
        logger.info(
            "No recipients configured for order cancellation notifications",
            extra={"order_id": order_id},
        )
        return False

    customer_name = order.customer_display_name or order.customer_email

    message = (
        f"Заказ #{order.order_number} был отменён.\n\n"
        f"Клиент: {customer_name}\n"
        f"Сумма: {order.total_amount} ₽\n\n"
        f"Подробности в Django Admin: {settings.SITE_URL}/admin/orders/order/{order.id}/change/"
    )

    try:
        send_mail(
            subject=f"[FREESPORT] Заказ #{order.order_number} отменён",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=list(recipients),
            fail_silently=False,
        )

        logger.info(
            "Order cancellation notification sent",
            extra={
                "order_id": order_id,
                "order_number": order.order_number,
                "recipients_count": len(recipients),
            },
        )
        return True

    except SMTPException as exc:
        logger.error(
            "Failed to send order cancellation notification",
            extra={
                "order_id": order_id,
                "exception": str(exc),
            },
        )
        raise self.retry(exc=exc)
