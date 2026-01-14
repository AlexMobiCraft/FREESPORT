---
title: 'Email-уведомления администратору о заказах'
slug: 'order-admin-email-notifications'
created: '2026-01-14'
status: 'in-progress'
stepsCompleted: [1]
tech_stack: ['Django', 'Celery', 'PostgreSQL']
files_to_modify:
  - 'apps/common/models.py'
  - 'apps/common/admin.py'
  - 'apps/orders/signals.py'
  - 'apps/orders/tasks.py'
  - 'apps/users/tasks.py'
  - 'docs/architecture/02-data-models.md'
  - 'docs/architecture/08-workflows.md'
code_patterns: ['Django signals', 'Celery tasks', 'Boolean flags']
test_patterns: ['pytest', 'mock send_mail', 'factory_boy']
---

# Tech-Spec: Email-уведомления администратору о заказах

**Created:** 2026-01-14

## Overview

### Problem Statement

При создании заказа email-уведомление администратору **не отправляется**, хотя это требование указано в AC Story 15.2:
> "...а администратор получает уведомления о новых заказах."

Текущий сигнал `send_order_confirmation_email` в `apps/orders/signals.py` уведомляет **только клиента** (строка 58: `recipient_list=[customer_email]`).

Дополнительно, текущая система использует жёстко заданный `settings.ADMINS` для B2B верификации, что не позволяет гибко управлять списком получателей через Django Admin.

### Solution

Создать универсальную систему уведомлений с управлением получателями через Django Admin:

1. **Модель `NotificationRecipient`** — хранит email получателей с Boolean флагами для типов уведомлений
2. **Django Admin интерфейс** — управление получателями и их подписками
3. **Расширение сигнала заказов** — отправка email получателям с флагом `notify_new_orders=True`
4. **Миграция `settings.ADMINS`** — перенос логики на новую модель

### Scope

**In Scope:**
- Модель `NotificationRecipient` с 6 типами уведомлений (Boolean флаги)
- Django Admin для управления получателями  
- Email-уведомление при создании заказа
- Миграция `user_verification` и `pending_queue_alert` с `settings.ADMINS`
- Unit-тесты для модели, сигнала и задач
- Email template `admin_new_order.html/txt`

**Out of Scope:**
- Уведомления при изменении статуса заказа (shipped, delivered)
- Telegram/SMS уведомления
- Управление email templates через Django Admin

## Context for Development

### Codebase Patterns

**Email отправка:**
- Используется `django.core.mail.send_mail`
- Templates в `backend/templates/emails/`
- Celery tasks для async отправки (retry logic с exponential backoff)

**Signals:**
- `post_save` сигнал в `apps/orders/signals.py`
- Регистрация в `apps.py` через `import apps.orders.signals`

**Тестирование:**
- `@patch("apps.users.tasks.send_mail")` для мокирования
- `UserFactory` для создания тестовых данных
- `pytest.mark.unit` и `pytest.mark.django_db`

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `apps/orders/signals.py` | Текущий сигнал клиентского email |
| `apps/users/tasks.py` | Паттерн Celery email tasks |
| `apps/common/models.py` | Место для новой модели |
| `tests/unit/test_email_tasks.py` | Паттерн тестирования email |
| `templates/emails/admin_new_verification_request.html` | Паттерн email template |

### Technical Decisions

**1. Размещение модели:** `apps/common/models.py`
   - Модуль `common` уже содержит cross-cutting concerns (Newsletter, AuditLog)

**2. Boolean флаги vs JSONB:**
   - Выбран Boolean — проще для Django Admin, 6 типов управляемо
   - Поля: `notify_new_orders`, `notify_order_cancelled`, `notify_user_verification`, `notify_pending_queue`, `notify_low_stock`, `notify_daily_summary`

**3. Celery vs Sync:**
   - Celery task для async отправки (не блокировать request)
   - Retry logic при SMTP ошибках

## Implementation Plan

### Tasks

#### Task 1: Создать модель NotificationRecipient (AC: Модель в БД)

**File:** `apps/common/models.py`

```python
class NotificationRecipient(TimeStampedModel):
    """Получатель email-уведомлений системы."""
    
    email = models.EmailField(_("Email"), unique=True, db_index=True)
    name = models.CharField(_("Имя"), max_length=100, blank=True)
    is_active = models.BooleanField(_("Активен"), default=True, db_index=True)
    
    # Типы уведомлений
    notify_new_orders = models.BooleanField(_("Новые заказы"), default=False)
    notify_order_cancelled = models.BooleanField(_("Отмена заказов"), default=False)
    notify_user_verification = models.BooleanField(_("Верификация B2B"), default=False)
    notify_pending_queue = models.BooleanField(_("Alert очереди"), default=False)
    notify_low_stock = models.BooleanField(_("Малый остаток"), default=False)
    notify_daily_summary = models.BooleanField(_("Ежедневный отчёт"), default=False)
    
    class Meta:
        verbose_name = _("Получатель уведомлений")
        verbose_name_plural = _("Получатели уведомлений")
```

**Subtasks:**
- [ ] Добавить модель в `apps/common/models.py`
- [ ] Создать миграцию: `python manage.py makemigrations common`
- [ ] Применить миграцию: `python manage.py migrate`

---

#### Task 2: Создать Django Admin интерфейс (AC: Управление через админку)

**File:** `apps/common/admin.py`

```python
@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'is_active', 'notify_new_orders', 'notify_user_verification']
    list_filter = ['is_active', 'notify_new_orders', 'notify_user_verification']
    search_fields = ['email', 'name']
    list_editable = ['is_active', 'notify_new_orders', 'notify_user_verification']
```

**Subtasks:**
- [ ] Добавить admin class в `apps/common/admin.py`
- [ ] Проверить отображение в Django Admin

---

#### Task 3: Создать email template для новых заказов (AC: Email отправляется)

**Files:** 
- `templates/emails/admin_new_order.html`
- `templates/emails/admin_new_order.txt`

Содержит: номер заказа, клиент, товары, сумма, адрес доставки, ссылка на Django Admin.

---

#### Task 4: Создать Celery task для отправки email о заказе (AC: Email отправляется)

**File:** `apps/orders/tasks.py` (новый файл)

```python
@shared_task(bind=True, max_retries=3, ...)
def send_order_notification_email(self, order_id: int) -> bool:
    """Отправить email о новом заказе получателям с флагом notify_new_orders."""
    recipients = NotificationRecipient.objects.filter(
        is_active=True, 
        notify_new_orders=True
    )
    # ... отправка каждому получателю
```

---

#### Task 5: Интегрировать task в сигнал orders (AC: Email отправляется)

**File:** `apps/orders/signals.py`

Добавить вызов Celery task после создания заказа:
```python
from apps.orders.tasks import send_order_notification_email

@receiver(post_save, sender=Order)
def send_order_confirmation_email(sender, instance, created, **kwargs):
    if not created:
        return
    
    # Существующая логика для клиента...
    
    # Новое: уведомление администраторам
    send_order_notification_email.delay(instance.id)
```

---

#### Task 6: Мигрировать user_verification на новую модель (AC: Миграция ADMINS)

**File:** `apps/users/tasks.py`

Изменить `send_admin_verification_email`:
```python
# Было:
admin_emails = [email for name, email in settings.ADMINS]

# Стало:
from apps.common.models import NotificationRecipient
recipients = NotificationRecipient.objects.filter(
    is_active=True, 
    notify_user_verification=True
).values_list('email', flat=True)
```

Аналогично для `monitor_pending_verification_queue`.

---

#### Task 7: Unit-тесты (AC: Тесты покрывают функционал)

**File:** `tests/unit/test_notification_recipient.py` (новый)

Тест-кейсы:
- Создание NotificationRecipient с флагами
- Фильтрация получателей по типу уведомления
- Admin отображение

**File:** `tests/unit/test_order_notifications.py` (новый)

Тест-кейсы:
- `send_order_notification_email` отправляет email получателям с `notify_new_orders=True`
- Пропуск если нет активных получателей
- Сигнал вызывает task при создании заказа

### Acceptance Criteria

1. ✅ Модель `NotificationRecipient` создана и доступна в Django Admin
2. ✅ Администратор может добавлять/удалять получателей через Django Admin
3. ✅ Администратор может настраивать типы уведомлений для каждого получателя
4. ✅ При создании заказа email отправляется всем получателям с `notify_new_orders=True`
5. ✅ Существующая логика `user_verification` работает через новую модель
6. ✅ Unit-тесты покрывают новый функционал
7. ✅ Документация проекта обновлена

---

#### Task 8: Обновление документации проекта (AC: Документация обновлена)

**Файлы для проверки и обновления:**

| Файл | Что проверить/обновить |
| ---- | ---------------------- |
| `docs/architecture/02-data-models.md` | Добавить модель `NotificationRecipient` |
| `docs/architecture/08-workflows.md` | Добавить workflow email-уведомлений о заказах |
| `docs/architecture/06-system-architecture.md` | Обновить секцию Email System |
| `GEMINI.md` | Добавить информацию о NotificationRecipient |

**Subtasks:**
- [ ] Проверить `02-data-models.md` и добавить описание модели `NotificationRecipient`
- [ ] Проверить `08-workflows.md` и добавить workflow уведомлений о заказах
- [ ] Проверить `06-system-architecture.md` и обновить секцию Email
- [ ] Обновить `GEMINI.md` с информацией о системе уведомлений

## Additional Context

### Dependencies

- Django >= 4.2
- Celery (уже настроен)
- PostgreSQL (уже используется)

### Testing Strategy

**1. Unit Tests (Автоматические):**

```bash
# Запуск через Docker (рекомендуется)
docker compose exec backend pytest tests/unit/test_notification_recipient.py tests/unit/test_order_notifications.py -v

# Или локально
cd backend && pytest tests/unit/test_notification_recipient.py tests/unit/test_order_notifications.py -v
```

**2. Integration Test (Ручной через Django Admin):**

1. Открыть Django Admin: `http://localhost:8001/admin/`
2. Перейти в "Получатели уведомлений" (Common → Notification Recipients)
3. Добавить тестового получателя с email и `notify_new_orders=True`
4. Создать тестовый заказ через API или frontend
5. Проверить логи backend на отправку email:
   ```bash
   docker compose logs backend | grep "Email-уведомление о заказе"
   ```

**3. Email Delivery Test (Ручной):**
- В development используется console backend — письмо выводится в логи
- В production проверить доставку на реальный email

### Notes

- После миграции `settings.ADMINS` останется пустым, что ожидаемо
- Для production нужно добавить получателей через Django Admin
- Data migration для переноса существующих ADMINS в NotificationRecipient — опционально
