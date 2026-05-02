---
title: "mode=info: follow-up доработки (fallback статус + парные теги)"
type: "bugfix"
created: "2026-05-01"
status: "done"
route: "one-shot"
---

## Intent

**Problem:** Реализация `handle_info` содержала три недочёта: (1) при отсутствии или `None` значении `ORDER_DEFAULTS` дефолтный экспортный статус `"Не согласован"` не попадал в XML-справочник, создавая рассинхрон с тем, что сайт реально отправляет в 1С; (2) блок `<ПлатежныеСистемы />` использовал self-closing форму вместо парных тегов, потенциально несовместимую с legacy-парсерами Bitrix; (3) тест `test_info_status_count` зеркалил старую логику с `if default_status and ...`, а не актуальную логику production-кода.

**Approach:** Привести `handle_info` к тому же fallback-паттерну, что и `OrderExportService._get_order_defaults()` (всегда `"Не согласован"` при отсутствии конфига); заменить self-closing тег на парный; добавить два теста на fallback при отсутствующем/None `ORDER_DEFAULTS`; исправить логику подсчёта в `test_info_status_count`.

## Suggested Review Order

**Исправление fallback-логики в production-коде**

- Замена `(... or {}).get("STATUS")` на `(... or {}).get("STATUS", "Не согласован")` + убрана защитная проверка `if default_status`.
  [`backend/apps/integrations/onec_exchange/views.py:374`](../../backend/apps/integrations/onec_exchange/views.py#L374)

**Парный тег `<ПлатежныеСистемы>`**

- Self-closing `<ПлатежныеСистемы />` → `<ПлатежныеСистемы></ПлатежныеСистемы>`.
  [`backend/apps/integrations/onec_exchange/views.py:397`](../../backend/apps/integrations/onec_exchange/views.py#L397)

**Тесты на fallback без `ORDER_DEFAULTS`**

- Два новых теста: `ORDER_DEFAULTS` отсутствует vs. явно `None` — оба должны давать `"Не согласован"` в XML.
  [`backend/tests/integration/test_onec_exchange_info_mode.py:174`](../../backend/tests/integration/test_onec_exchange_info_mode.py#L174)

**Исправление `test_info_status_count`**

- Подсчёт `expected` теперь зеркалит production: `default_status = defaults.get("STATUS", "Не согласован")` без условия `and`.
  [`backend/tests/integration/test_onec_exchange_info_mode.py:207`](../../backend/tests/integration/test_onec_exchange_info_mode.py#L207)
