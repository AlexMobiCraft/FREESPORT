---
title: 'Команда включения товаров, застрявших неактивными после импорта 1С'
type: 'bugfix'
created: '2026-10-07'
status: 'ready-for-dev'
review_loop_iteration: 0
context:
  - '{project-root}/backend/docs/testing-standards.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** На проде 161 товар без характеристик навсегда выключен: `is_active=False`, `onec_deleted=False`, при этом активный вариант есть. Им создали вариант по умолчанию до коммита `b42a85c7` (26.04.2026), а тогдашний `create_default_variants` товар не включал. Сейчас импорт включает товар только при создании варианта, а вариант уже есть, поэтому товары не включатся никогда. 47 из них с ценой и остатком теряются с витрины (среди них медболы и скакалки ESPADO, самокаты Cosmoride, мячи INGAME). Выборка — `tmp/stuck-inactive-products-2026-10-07.md`.

**Approach:** Разовая management-команда `activate_stuck_products`: по умолчанию dry-run, включение только с `--apply`. Импорт не меняется: дефект закрыт в `b42a85c7`, а правило «вручную выключенный товар импорт не включает» (спека `spec-1c-deletion-marked-goods.md`) остаётся в силе.

## Boundaries & Constraints

**Always:**
- Застрявший товар — это `is_active=False`, `onec_deleted=False` и хотя бы один вариант с `is_active=True` и `onec_deleted=False`.
- Без флагов команда отбирает только товары, у которых активные варианты дают `max(retail_price) > 0` и `sum(stock_quantity) > 0`. Флаг `--include-unpriced` снимает это условие.
- `--ids 1,2,3` ограничивает выборку указанными товарами, но критерий застрявшего применяется всё равно.
- Включение — пачками в `transaction.atomic()` через `QuerySet.update(is_active=True, updated_at=now())`. Условия `is_active=False, onec_deleted=False` повторяются в `WHERE`, чтобы не включить товар, состояние которого изменилось после отбора.
- Dry-run печатает число товаров и первые 50 строк: id, `onec_id`, артикул, наименование, категория, цена, остаток. `--apply` печатает то же и итог «включено N».
- По каждому включённому товару — строка `INFO` в логгер `import_products` (Ид 1С, артикул, наименование), как у `purge_products_outside_root`.

**Ask First:**
- Если при разработке найдётся живой путь импорта, который и сейчас оставляет товар без характеристик выключенным, — остановиться и сообщить: тогда нужна правка импорта, а не только команда.

**Never:**
- Не менять `variant_import.py` и пути активации импорта.
- Не трогать варианты, категории, `onec_deleted` и реестр `OnecExcludedItem`.
- Не включать товары с `onec_deleted=True` и товары без активного варианта.
- Не делать data-миграцию: включение на проде только командой и только по решению владельца.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Застрявший с ценой и остатком | `is_active=False`, `onec_deleted=False`, активный вариант 630 ₽, остаток 889 | dry-run: в списке, БД не меняется; `--apply`: `is_active=True` | — |
| Без цены или без остатка | то же, цена 0 или остаток 0 | без флага не отбирается; с `--include-unpriced` включается | — |
| Скрыт импортом | `onec_deleted=True` | не отбирается ни при каких флагах | — |
| Все варианты скрыты | у вариантов `is_active=False` или `onec_deleted=True` | не отбирается | — |
| Уже активен | `is_active=True` | не отбирается | — |
| `--ids` с чужим id | id активного или скрытого товара | пропущен, в выводе «не подходит: id …» | — |
| Нечего включать | выборка пуста | «Застрявших товаров нет», код возврата 0 | — |
| Состояние изменилось между отбором и UPDATE | товар включили или скрыли параллельно | не попадает в UPDATE; итог считает только реально обновлённые строки | — |

</frozen-after-approval>

## Code Map

Пути от `backend/`.

- `apps/products/management/commands/purge_products_outside_root.py` -- образец: docstring с примерами запуска, `--apply`, `PREVIEW_LIMIT = 50`, `BATCH_SIZE`, `_out`/`_error`, логгер `import_products`.
- `apps/products/models.py` -- `Product` (`is_active`, `onec_deleted`, `article`, `category`), `ProductVariant` (`is_active`, `onec_deleted`, `retail_price`, `stock_quantity`), related name `variants`.
- `apps/products/services/variant_import.py:1643` (`_activate_parent_product`), `:1820` (`create_default_variants`) -- текущие пути включения; читать, не менять.
- `apps/products/tests/unit/test_variant_import_admission.py:438` -- регрессия «новый товар без характеристик включается дефолтным вариантом» уже покрыта, не дублировать.
- `tests/integration/test_purge_products_outside_root.py` -- образец тестов management-команды через `call_command`.
- `docs/integrations/1c/import-process.md:58` -- список команд; `:502` -- раздел `purge_products_outside_root` (рядом добавить новую команду).

## Tasks & Acceptance

**Execution:**
- [ ] `apps/products/management/commands/activate_stuck_products.py` -- новая команда по Boundaries: dry-run, `--apply`, `--include-unpriced`, `--ids` -- вернуть на витрину товары, застрявшие до `b42a85c7`.
- [ ] `tests/integration/test_activate_stuck_products.py` -- все строки I/O-матрицы плюс проверка, что dry-run ничего не пишет в БД -- критерий отбора легко ослабить незаметно.
- [ ] `docs/integrations/1c/import-process.md` -- строка в «Management Commands» и короткий подраздел: зачем команда, запуск на проде (бэкап → dry-run → сверка с `tmp/stuck-inactive-products-2026-10-07.md` → `--apply`) -- ранбук для владельца.

**Acceptance Criteria:**
- Given копия прода (161 застрявший, 47 из них с ценой и остатком), when команда без флагов, then выводит 47 и БД не меняется.
- Given та же БД, when `--apply`, then включено 47; повторный запуск выводит «Застрявших товаров нет».
- Given изменённые файлы, when pytest с `--cov=apps.products.management.commands.activate_stuck_products`, then покрытие ≥ 90 %; навык `backend-lint` чисто.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q tests/integration/test_activate_stuck_products.py --cov=apps.products.management.commands.activate_stuck_products --cov-report=term` -- expected: зелено, ≥ 90 %.
- Навык `backend-lint` -- expected: black и flake8 чисто.
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` -- expected: новые символы только в новой команде, `variant_import.py` не затронут.

## Spec Change Log
