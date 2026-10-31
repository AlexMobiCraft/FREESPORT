---
title: 'Письма о новом заказе: доставка после коммита и получатели региона'
type: 'bugfix'
created: '2026-10-31'
status: 'done'
baseline_commit: '73b54d3b'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-order-email-recipients/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-order-email-recipients/affected-code.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Письма о заказе теряются: задачи ставятся в `post_save` до коммита и не находят заказ (прод, `0000226001`, обе вернули `False` за 23 и 41 мс). Получает письмо один адрес общего списка; ответственный менеджер клиента и руководитель о заказе не узнают. Зависший Redis держит запрос оформления заказа до 170 с.

**Approach:** Ставить обе задачи через `transaction.on_commit(..., robust=True)`; в `send_order_notification_email` добавить к общему списку ответственного менеджера клиента (`User.responsible_manager`); ограничить таймауты Celery в `base.py`; руководителя включает существующий флаг `notify_new_orders` (правка данных прода — после релиза, с подтверждения владельца).

## Boundaries & Constraints

**Always:** Единственный источник менеджера — `order.user.responsible_manager`, и только если он в `responsible_manager_candidates()` и у него есть email. Менеджер добавляется независимо от `notify_new_orders`. Дубли по `email.lower()` убирать. Таймауты Celery — только в `settings/base.py`, одним местом. Колбэк `on_commit` — `lambda` или именованная функция (не `partial`), отдельный колбэк на каждую задачу; номер заказа — в тексте лога (`extra=` в прод-формат не попадает). Комментарии и docstrings — на русском.

**Ask First:** Любое изменение данных прода (включение `notify_new_orders` у `managermsk3@freesportopt.ru`); создание контрольного заказа на проде (запрещено — уйдёт в рабочую 1С).

**Never:** Новая логика региона; outbox, журнал писем, повторы после исчерпания попыток; новый шаблон письма; `help_text` модели (даст миграцию); обёртки вокруг `.delay` и параметры таймаута в отдельных вызовах; таймауты `django-redis`; письма задним числом по `0000126001` и `0000226001`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Постановка после коммита | Мастер создан через `OrderCreateService` | До коммита задач нет; после — по одной на каждую, заказ с позициями виден | Откат — задач нет; субзаказ — не ставятся |
| Сбой брокера | `.delay` бросает исключение | Блок захвата колбэков завершается без исключения, 201, вторая задача поставлена | Лог с номером заказа |
| Зависший сокет | Сокет принял соединение и молчит | `.delay` с настройками проекта падает быстрее 15 с | Исключение |
| Менеджер региона | Клиент с `responsible_manager`-кандидатом | Письмо менеджеру со ссылкой `/manager/`; чужому региону не уходит | — |
| Ручное назначение | `responsible_manager_manual` | Письмо назначенному, не менеджеру правила | — |
| Пустой общий список | Нет `notify_new_orders=True` | Письмо менеджеру, задача `True` | — |
| Адрес в обоих списках | Email в списке и у менеджера, регистр разный | Одно письмо | — |
| Менеджер не годится | Заблокирован / вне групп / не задан / нет клиента | Письмо общему списку, задача не падает | Для заказа с клиентом — warning с номером заказа |
| Руководитель, флаг выкл. | `notify_new_orders=False`, он же ответственный | Письмо о заказе своего клиента; о чужом — нет | — |

</frozen-after-approval>

## Code Map

- `backend/apps/orders/signals.py` -- `send_order_confirmation_email`: сейчас `.delay` прямо в `post_save`
- `backend/apps/orders/tasks.py:168` -- `send_order_notification_email`: сбор получателей, `split_by_manager_section`
- `backend/apps/users/staff_roles.py` -- `responsible_manager_candidates`, `split_by_manager_section` (не меняется)
- `backend/apps/users/services/verify_b2b_application.py:376` -- образец `on_commit(lambda: ..., robust=True)`
- `backend/freesport/settings/base.py:243` -- `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`, сюда таймауты
- `backend/apps/common/supervisor_admin.py:96` -- `SupervisorNotificationRecipientAdmin`, подсказка у флага
- `backend/apps/orders/services/order_create.py:31` -- `@transaction.atomic create()`, граница коммита

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/orders/signals.py` -- обе задачи через `transaction.on_commit(lambda: ..., robust=True)`, `try/except` и логи внутрь колбэка -- иначе после коммита исключение не перехватывается
- [x] `backend/apps/orders/tasks.py` -- получатели = общий список + ответственный менеджер без дублей по `email.lower()`; проверка «нет получателей» после объединения; warning с номером заказа -- CAP-3, CAP-4
- [x] `backend/freesport/settings/base.py` -- настройки Celery из `affected-code.md` («Таймауты брокера») -- CAP-2
- [x] `backend/apps/common/supervisor_admin.py` -- подсказка у `notify_new_orders` через `formfield_for_dbfield` («выключение действует только на общий список») -- CAP-4
- [x] `docs/architecture/02-data-models.md`, `AGENTS.md` (строка `orders/` в «Неочевидное в коде») -- обновить по `affected-code.md`
- [x] Тесты (таблица «Тесты» в `affected-code.md`): `test_onec_export.py:736`, `test_orders_api.py:221` (+ сценарий брокера), `test_order_numbering.py:175`, `test_notification_recipient.py` (CAP-3/4, группа «Руководители»), новый тест настроек Celery, новый тест `OrderCreateService` -- CAP-1..4

**Acceptance Criteria:**
- Given заказ создан через `OrderCreateService`, when транзакция зафиксирована, then каждая задача поставлена один раз и находит заказ со всеми позициями
- Given `.delay` бросает исключение, when заказ оформляется, then ответ 201, заказ в БД, вторая задача поставлена, номер заказа в `caplog`
- Given клиент с ответственным-кандидатом и пустым общим списком, when выполняется задача, then письмо уходит менеджеру со ссылкой `/manager/`, результат `True`
- Given фикстуры с заглушками задач (`test_manager_orders_section`, `test_manager_orders_admin`, `test_supervisor_summary`), when прогнаны, then проходят без правок

## Design Notes

Форма колбэка (`robust=True` изолирует сбой одной задачи от другой):

```python
transaction.on_commit(lambda: _enqueue(send_order_confirmation_to_customer, order), robust=True)
```

Номер заказа — в тексте сообщения (`f"... {order.order_number}: {exc}"`). `Order.DoesNotExist` в задачах остаётся.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q tests/unit/test_notification_recipient.py tests/unit/test_order_numbering.py tests/integration/test_orders_api.py tests/integration/test_onec_export.py tests/integration/test_manager_orders_section.py tests/unit/test_manager_orders_admin.py tests/unit/test_supervisor_summary.py` (плюс новые файлы) -- expected: все зелёные
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` и `npx gitnexus check --cycles -r "C:\Users\1\DEV\FREESPORT"` -- expected: затронуты только ожидаемые символы, новых циклов нет
- линтеры бэкенда (навык `backend-lint`) после зачётного pytest, не параллельно -- expected: чисто

**Manual checks:**
- Dev-стек: воркер с новыми настройками простаивает без переподключений и после перезапуска Redis забирает задачи (CAP-2)

## Suggested Review Order

**Доставка после коммита (CAP-1, CAP-2)**

- Точка входа: две отдельные колбэка-функции с `robust=True`, номер заказа в логе.
  [`signals.py:68`](../../backend/apps/orders/signals.py#L68)

- Порядок относительно коммита, откат и состояние заказа на момент постановки.
  [`test_order_create_email_on_commit.py:67`](../../backend/tests/integration/test_order_create_email_on_commit.py#L67)

- Сбой брокера не ломает POST оформления заказа, вторая задача поставлена.
  [`test_orders_api.py:255`](../../backend/tests/integration/test_orders_api.py#L255)

**Получатели (CAP-3, CAP-4)**

- Кого берём: `responsible_manager` только если проходит `responsible_manager_candidates()`.
  [`tasks.py:161`](../../backend/apps/orders/tasks.py#L161)

- Общий список плюс менеджер без дублей по `email.lower()`.
  [`tasks.py:185`](../../backend/apps/orders/tasks.py#L185)

- Подключение в задаче: проверка «нет получателей» теперь после объединения.
  [`tasks.py:235`](../../backend/apps/orders/tasks.py#L235)

- Подсказка у флага руководителя без `AlterField` и миграции.
  [`supervisor_admin.py:96`](../../backend/apps/common/supervisor_admin.py#L96)

**Таймауты брокера**

- Общий блок настроек Celery: повтор, connect/socket-таймауты, бэкенд результатов.
  [`base.py:262`](../../backend/freesport/settings/base.py#L262)

- `.delay` на молчащем сокете падает быстрее 15 с (замер: 9 с).
  [`test_celery_broker_timeouts.py:47`](../../backend/tests/unit/test_celery_broker_timeouts.py#L47)

**Тесты получателей**

- Сценарии CAP-3/4: регион по правилу, ручное назначение, дубль, негодный менеджер.
  [`test_notification_recipient.py:230`](../../backend/tests/unit/test_notification_recipient.py#L230)

- Выключенный флаг руководителя: письмо только по своим клиентам.
  [`test_notification_recipient.py:410`](../../backend/tests/unit/test_notification_recipient.py#L410)
