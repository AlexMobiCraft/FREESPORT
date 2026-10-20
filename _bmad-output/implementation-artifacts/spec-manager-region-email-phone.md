---
title: 'Телефон клиента в письме менеджеру о новой заявке'
type: 'feature'
created: '2026-10-20'
status: 'done'
route: 'one-shot'
---

# Телефон клиента в письме менеджеру о новой заявке

## Intent

**Problem:** Письмо региональному менеджеру о регистрации нового клиента (`send_manager_region_email`) не содержит телефон, введённый при регистрации, хотя с PR #332 он обязателен, — менеджеру нечем связаться с клиентом без захода в раздел менеджера.

**Approach:** Телефон передаётся в контекст письма и выводится строкой «Телефон» под Email в HTML- и текстовой версиях. Пустое значение (модель допускает `blank`) показывается как «не указан».

## Suggested Review Order

**Письмо менеджеру**

- Телефон пользователя добавлен в контекст шаблона.
  [`tasks.py:440`](../../backend/apps/users/tasks.py#L440)

- Строка «Телефон» в HTML-версии, сразу под Email.
  [`manager_region_notification.html:35`](../../backend/templates/emails/manager_region_notification.html#L35)

- То же в текстовой версии.
  [`manager_region_notification.txt:9`](../../backend/templates/emails/manager_region_notification.txt#L9)

**Тесты**

- Номер в обеих версиях письма и заглушка «не указан» при пустом поле.
  [`test_region_routing.py:180`](../../backend/tests/unit/test_region_routing.py#L180)
