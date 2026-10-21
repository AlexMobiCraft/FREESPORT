---
title: 'Админка: FREESPORT → OPTISPORT в заголовках'
type: 'chore'
created: '2026-10-21'
status: 'done'
route: 'one-shot'
---

# Админка: FREESPORT → OPTISPORT в заголовках

## Intent

**Problem:** В Django-админке (`/admin/`, `/manager/`, `/marketing/`, `/supervisor/`) в заголовках страниц и во вкладке браузера остаётся прежний бренд FREESPORT, хотя сайт переехал на OPTISPORT.

**Approach:** Заменены только видимые пользователю строки `site_header`/`site_title` и обновлены тесты, которые проверяют эти строки. Внутренние идентификаторы (пакет `freesport`, `FREESPORT_1C_SESSION`, `FREESPORT_DISABLE_CELERY`) не тронуты. Письма сотрудникам со словом FREESPORT в тему не входят.

## Suggested Review Order

**Заголовки админки**

- Три раздела персонала: Менеджер, Маркетинг, Руководитель.
  [`admin_site.py:128`](../../backend/freesport/admin_site.py#L128)

- Основная админка `/admin/`.
  [`admin.py:9`](../../backend/apps/integrations/admin.py#L9)

**Тесты**

- Проверки `site_header`/`site_title` в unit-тестах.
  [`test_marketing_admin_site.py:175`](../../backend/tests/unit/test_marketing_admin_site.py#L175)

- Проверки текста в HTML страниц разделов.
  [`test_supervisor_section.py:245`](../../backend/tests/integration/test_supervisor_section.py#L245)
