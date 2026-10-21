---
title: 'Письмо «заявка принята»: название компании и реальные контакты'
type: 'bugfix'
created: '2026-10-21'
status: 'done'
route: 'one-shot'
---

# Письмо «заявка принята»: название компании и реальные контакты

## Intent

**Problem:** В HTML-письме о принятой заявке вместо названия компании выводился сырой `{{ company_name }}`: Prettier перенёс тег на две строки, а Django не разбирает многострочные теги. В блоке контактов стояли заглушки `+7 (XXX) XXX-XX-XX` и `support@optisport.ru`.

**Approach:** Тег возвращён на одну строку. Контакты заменены на данные из подвала сайта (`+7 968 273-21-68`, `info@optisport.ru`), как в письме об отклонении заявки. Текстовая часть обёрнута в `{% autoescape off %}`, чтобы кавычки и `&` в названии не превращались в сущности. Добавлены тесты на реальный рендер письма.

## Suggested Review Order

**Название компании**

- Многострочный тег был причиной бага; теперь `{{ company_name }}` на одной строке с пояснением.
  [`user_registration_pending.html:13`](../../backend/templates/emails/user_registration_pending.html#L13)

- Тесты рендерят письмо по-настоящему (прежние мокали `send_mail`): HTML, текст, спецсимволы, пустое название.
  [`test_email_tasks.py:157`](../../backend/tests/unit/test_email_tasks.py#L157)

**Контакты**

- Реальные телефон и email из подвала, с ссылками `tel:` и `mailto:`.
  [`user_registration_pending.html:45`](../../backend/templates/emails/user_registration_pending.html#L45)

- Те же контакты в текстовой версии; весь шаблон под `autoescape off`.
  [`user_registration_pending.txt:16`](../../backend/templates/emails/user_registration_pending.txt#L16)

- Guard от возврата заглушек.
  [`test_email_tasks.py:198`](../../backend/tests/unit/test_email_tasks.py#L198)
