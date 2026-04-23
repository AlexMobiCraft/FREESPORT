---
title: 'Исправить признак учета НДС в CommerceML-экспорте заказа для 1С'
type: 'bugfix'
created: '2026-04-23'
baseline_commit: 'c04316a913cc944307f7ff4d03e22ee1b12a5d33'
status: 'done'
context:
  - '{project-root}/docs/integrations/1c/order-vat-warehouse-routing.md'
  - '{project-root}/docs/integrations/1c/order-import-handler-diagnostics.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Цена строки сайта уже содержит НДС, но в order-export сейчас используется тег `УчтенВСумме` вместо стандартного `УчтеноВСумме`. Из-за этого 1С может трактовать `ЦенаЗаЕдиницу` как цену без НДС и доначислять налог сверху.

**Approach:** Исправить order-export на стандартный тег `УчтеноВСумме`, не меняя текущую математику брутто-цены и суммы НДС, и синхронизировать unit-тесты и `docs/integrations/1c`, чтобы ошибка не вернулась и проверялась по одному контракту.

## Boundaries & Constraints

**Always:** Считать `ЦенаЗаЕдиницу` и `Сумма` брутто-значениями сайта; сохранять текущий расчет `vat_amount` от брутто-суммы строки; опираться на audit XML и существующие CommerceML-фикстуры; обновлять код, тесты и документацию согласованно.

**Ask First:** Если после исправления XML-контракта 1С продолжит добавлять НДС поверх цены, отдельно согласовать вторую фазу: проверку настроек типа цен/НДС в модуле `1С-Битрикс. Управление сайтом` или в конфигурации 1С.

**Never:** Не менять ставки НДС, `vat_group`, split по `(vat_rate, warehouse_name)`, routing `Организация`/`Склад` или математику `unit_price`/`total_price`; не маскировать дефект одной настройкой 1С, пока export XML не приведен к стандартному тегу; не расширять задачу до общего рефакторинга CommerceML.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Gross price, 22% VAT | `OrderItem.unit_price=189.00`, `vat_rate=22`, экспортируется `Документ/Товар` | В XML остается `<ЦенаЗаЕдиницу>189.00</ЦенаЗаЕдиницу>`, а в `Налог` появляется `<УчтеноВСумме>true</УчтеноВСумме>` и сумма НДС `34.08` | N/A |
| Gross price, 5% VAT | `OrderItem.unit_price=995.00`, `vat_rate=5`, экспортируется `Документ/Товар` | В XML остается цена сайта `995.00`, а `Налог` содержит стандартный флаг включения НДС и сумму `47.38` | N/A |
| Docs/sample parity | Разработчик сверяет runtime XML с документацией | В docs/sample показан тот же тег `УчтеноВСумме`, что и в реальном order-export | Если найдено старое имя тега, оно обновляется вместе с кодом |

</frozen-after-approval>

## Code Map

- `backend/apps/orders/services/order_export.py` -- формирует CommerceML заказа и сейчас пишет неверное имя тега в блоке `Товар/Налоги/Налог`.
- `backend/tests/unit/test_order_export_service.py` -- регрессия для XML-структуры order export; сейчас закрепляет неправильный тег.
- `docs/integrations/1c/order-vat-warehouse-routing.md` -- каноническая документация по текущей логике order export и VAT.
- `docs/integrations/1c/samples/order-export-org-warehouse-diagnostic.xml` -- образец order XML для ручной сверки с 1С.
- `backend/var/1c_exchange/logs/*.xml` -- runtime-проверка того, что после фикса экспорт пишет правильный тег и не меняет брутто-цену.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/orders/services/order_export.py` -- заменить `УчтенВСумме` на `УчтеноВСумме` в tax block заказа, сохранив текущие `ЦенаЗаЕдиницу`, `Сумма` и расчет НДС -- чтобы 1С получила стандартный признак "налог уже включен в цену".
- [x] `backend/tests/unit/test_order_export_service.py` -- обновить регрессионный тест на точный тег `УчтеноВСумме` и текущее gross-price поведение -- чтобы опечатка в XML-контракте не вернулась незаметно.
- [x] `docs/integrations/1c/order-vat-warehouse-routing.md` и `docs/integrations/1c/samples/order-export-org-warehouse-diagnostic.xml` -- зафиксировать, что сайт экспортирует цену уже с НДС и что корректный флаг для 1С называется `УчтеноВСумме` -- чтобы команда могла проверять проблему без повторного исследования кода.

**Acceptance Criteria:**
- Given строка заказа, в которой цена сайта уже включает НДС, when `OrderExportService.generate_xml()` формирует CommerceML, then `Товар/Налоги/Налог` содержит `УчтеноВСумме=true`, а `ЦенаЗаЕдиницу` остается равной цене сайта.
- Given строка заказа со ставкой 5% или 22%, when экспорт формирует блок `Налог`, then сумма НДС остается рассчитанной из брутто-суммы строки по текущей формуле и не меняется из-за исправления имени тега.
- Given инженер поддержки сравнивает документацию и свежий audit XML заказа, when он проверяет налоговый блок строки товара, then в образце и в runtime XML используется одно и то же имя тега `УчтеноВСумме`.

## Spec Change Log

## Design Notes

- Runtime evidence: свежий `backend/var/1c_exchange/logs/20260423_172536_orders.xml` уже показывает брутто-цены `995.00`, `189.00`, `194.00` и корректно вычисленные суммы НДС, но использует нестандартный тег `УчтенВСумме`.
- Repo evidence: фикстуры `backend/tests/fixtures/1c-data/prices/*.xml` и `backend/tests/fixtures/1c-data/priceLists/priceLists.xml` уже используют стандартное имя `УчтеноВСумме`, поэтому bugfix должен выровнять order export с остальным CommerceML-контрактом проекта.
- Post-fix note (23.04.2026): реальный импорт в 1С показал, что переименование тега в строке товара само по себе недостаточно. Модуль `БУС_ЗагрузкаСервер` выставляет `Цена включает НДС` из `ДокументXML.НДСВСумме`, а этот флаг читается из `Документ/Налоги`, поэтому финальный рабочий фикс добавил налоговый блок и на уровень документа.

## Verification

**Commands:**
- `docker compose --env-file ..\\.env -f ..\\docker\\docker-compose.yml exec -T backend pytest tests/unit/test_order_export_service.py -k "summe or stavka_22_in_item"` -- expected: тесты order export проходят с новым именем тега и без изменения расчетов НДС.
- `rg -n "УчтеноВСумме" apps/orders/services/order_export.py tests/unit/test_order_export_service.py ..\\docs\\integrations\\1c` -- expected: новый тег присутствует в exporter, регрессионном тесте и затронутой 1C-документации.
- `rg -n "УчтенВСумме" apps/orders/services/order_export.py ..\\docs\\integrations\\1c` -- expected: старое имя тега отсутствует в рабочем коде и затронутой документации.

**Manual checks (if no CLI):**
- Выполнить экспорт тестового заказа и открыть свежий `backend/var/1c_exchange/logs/*_orders.xml`: внутри каждого `Товар/Налог` должен быть тег `<УчтеноВСумме>true</УчтеноВСумме>`, а `ЦенаЗаЕдиницу` должна совпадать с ценой на сайте.

## Suggested Review Order

**XML-контракт**

- Точка входа: добавляем документ-level налоговый блок для флага `ЦенаВключаетНДС`.
  [`order_export.py:196`](../../backend/apps/orders/services/order_export.py#L196)

- Документация фиксирует реальную причину инцидента и итоговое решение.
  [`order-vat-warehouse-routing.md:173`](../../docs/integrations/1c/order-vat-warehouse-routing.md#L173)

- Диагностический sample выровнен с фактическим контрактом экспорта.
  [`order-export-org-warehouse-diagnostic.xml:19`](../../docs/integrations/1c/samples/order-export-org-warehouse-diagnostic.xml#L19)

**Регрессия**

- Тест закрепляет новый тег и защищает сохранение брутто-цены.
  [`test_order_export_service.py:2002`](../../backend/tests/unit/test_order_export_service.py#L2002)
