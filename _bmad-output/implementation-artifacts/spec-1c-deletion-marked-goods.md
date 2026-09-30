---
title: 'Импорт 1С: в БД только товары дерева СПОРТ без пометки удаления'
type: 'bugfix'
created: '2026-09-29'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'c811d506346fa5e74b88250e29961d7058f547f1'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/tz-1c-deletion-marked-goods.md'
  - '{project-root}/backend/docs/testing-standards.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Импорт 1С пишет в БД всю номенклатуру, а не только ветку «СПОРТ»: фильтр `ROOT_CATEGORY_NAME` режет только категории, товар вне дерева попадает в fallback-категорию, `<ПометкаУдаления>` не читается. На проде 8 091 из 9 939 товаров — вне СПОРТ или к удалению (пример: BT45-RU в «Номенклатура к удалению»).

**Approach:** Правило допуска (ТЗ §3) применяется в каждой сессии обмена: недопущенное не создаётся, существующее **скрывается** (`onec_deleted=True`) и заносится в реестр исключённых Ид 1С. Физически удаляет только команда `purge_products_outside_root` (dry-run → `--apply`). Полное ТЗ владельца — `tz-1c-deletion-marked-goods.md` (в `context`); его решения действуют, кроме пересмотренных ниже.

**Решения владельца по ревью спеки (29.09.2026), заменяют ТЗ:**
1. Обмен с 1С ничего не удаляет физически, только скрывает; удаляет `purge_products_outside_root`. Лимит `ONEC_IMPORT_MAX_PRODUCT_DELETIONS` и `--max-deletions` (ТЗ §4.5) **не делаются**. Причина: каждый файл обмена — отдельная сессия ≤ 500 товаров, лимит на сессию не защищает.
2. Допущенный товар, чья категория в БД вне поддерева якоря, переносится в категорию своей группы 1С (узкая синхронизация; полная — по-прежнему вне объёма).
3. Товар с неизвестной группой — недопущенный, как в ТЗ: не создаётся, существующий скрывается, удаляется `purge`.
4. Реестр исключённых Ид 1С (новая модель): offers/prices/rests пропускают исключённые Ид молча (счётчик), WARNING остаётся только для настоящих пропаж.

## Boundaries & Constraints

**Always:**
- Правило допуска — ТЗ §3 (все группы в поддереве якоря по Ид, пометка товара ≠ true, ни одна группа на пути до якоря не помечена; пометка — без учёта регистра и пробелов, нет тега = false). Поддерево — один раз на сессию, логика якоря и `_allowed_category_ids` из `process_categories` переиспользуется.
- Поддерево: для групп из `groups*.xml` сессии решает родитель из XML; БД — только для групп, которых в XML нет. Помеченная или вынесенная из дерева группа попадает в реестр исключений и исключает себя и потомков из поддерева в следующих сессиях.
- Якорь не найден → ничего не скрывается и не создаётся, `logger.error` + строка в отчёт. `ROOT_CATEGORY_NAME` пуст → условие 1 выключено, условия 2–3 работают, `WARNING` один раз.
- Скрытое импортом не активирует ни один путь (`_update_existing_variant`, `_create_new_variant`, `create_default_variants`); цены и остатки скрытым вариантам обновляются.
- Ни один путь импорта не создаёт `Category` вне поддерева якоря.
- `purge`: товар с `OrderItem` и вариант с `OrderItem.variant` не удаляются (`WARNING` с Ид и числом заказов, товар скрывается); категория удаляется только пустой, от листьев к корню, якорь сохраняется; удаление пачками в `transaction.atomic()`, сбой пачки → повтор по одному, ошибка одного объекта не останавливает команду.
- Построчный `INFO` в лог `import_products` по каждому скрытому/удалённому: Ид 1С, артикул, наименование, причина.
- Перед правкой метода — `npx gitnexus impact <метод> --direction upstream -r "C:\Users\1\DEV\FREESPORT"`.

**Never:**
- Не удалять физически в `import_products_from_1c` и Celery-обмене.
- Не трогать файлы картинок в `MEDIA_ROOT`, бренды, атрибуты, импорт контрагентов.
- Не добавлять фильтр по активности категории в публичный API; не синхронизировать категорию допущенного товара, если она уже в поддереве.
- Не ослаблять правило ради старых тестов; не править `.env`, `.env.prod`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Недопущенный товар, новый | группа вне СПОРТ / нет группы / неизвестная / пометка товара или предка; в т.ч. сессия без `groups.xml` | `Product` не создан, Ид в реестре, `skipped_products+1` | — |
| Недопущенный, есть в БД | то же, в т.ч. с остатком или заказом; все совпадения по `onec_id`/`parent_onec_id` | `is_active=False`, `onec_deleted=True`, Ид в реестре, `hidden_products+1`; варианты не трогаются | — |
| Возврат | допущенный товар с `onec_deleted=True` | флаг снят, Ид убран из реестра; `is_active=True`, если есть активный вариант; `restored_products+1` | — |
| Категория отстала | допущенный товар, категория в БД вне поддерева | перенесён в категорию своей группы, `recategorized_products+1` | — |
| Ручное выключение | `is_active=False`, `onec_deleted=False` | возврат его не включает | — |
| Предложение помечено | offer товара СПОРТ, `ПометкаУдаления=true` | новый вариант не создан; существующий `is_active=False`, `onec_deleted=True`; Ид в реестре; прочие активны | — |
| Все предложения помечены | у товара нет активных вариантов | товар `is_active=False` (без флага); `create_default_variants` ему дефолтный вариант не создаёт | — |
| offers/prices/rests исключённого | Ид или родитель в реестре, либо родитель `onec_deleted` | пропуск, `skipped_variants+1`, без WARNING | — |
| Порядок пакетов | товар в `goods_1_1` (СПОРТ) и `goods_1_11` (к удалению) | пакеты по номеру (натуральная сортировка), побеждает поздний | — |
| Якорь не найден | «СПОРТ» нет ни в XML, ни в БД | 0 скрытий, 0 созданий | `logger.error` + строка в отчёт |
| Purge dry-run | без `--apply` | количества и первые 50 по каждому виду, БД не меняется | якорь не найден → `CommandError` |
| Purge apply | скрытые импортом; товары с категорией вне поддерева; скрытые варианты; категории вне поддерева | удалены все без заказов (Ид — в реестр), затем пустые категории; с заказом — скрыт, его категория сохранена, WARNING | сбой пачки → по одному |

</frozen-after-approval>

## Code Map

Пути от `backend/`. Индекс GitNexus stale на 1 merge-коммит (только frontend).

- `apps/integrations/onec_exchange/file_type_detection.py:21`, `import_products_from_1c.py:122–185` (`_restrict_to_expected`) -- почему на проде groups, каждый goods_N, offers_N — отдельные сессии; ручной полный импорт обрабатывает всё в одной.
- `apps/products/services/parser.py` -- `GoodsData` (24), `OfferData` (42), `CategoryData` (73), `parse_goods_xml` (245; первый Ид группы — 280), `parse_offers_xml` (341), `parse_groups_xml` (495, `parse_group` 508). Хелперы 151–164.
- `apps/products/services/variant_import.py` -- `__init__` (278; `stats` 311–348, 377–391); копия `CategoryData` (90, её импортирует `test_category_deactivation.py:23`); `process_product_from_goods` (659; поиск `Q(onec_id)|Q(parent_onec_id)).first()` 703–706 — `parent_onec_id` не уникален); `_update_existing_product` (716); `_create_new_product` (788; `None` → skip 803); `process_variant_from_offer` (968; WARNING 1003–1011); `_update_existing_variant` (1070); `_create_new_variant` (1142, 1165); `create_default_variants` (1303; 1315, 1361, 1371); `update_variant_prices` (1383; WARNING 1402–1408), `update_variant_stock` (1468; 1490–1495); `_get_variant_by_onec_id` (1661; fallback по родителю 1671–1674 — отсекать до него); `_get_or_create_category` (1842) и `_get_unresolved_category` (1887) — fallback убрать; `process_categories` (2051: якорь 2103–2126, allowed 2130–2178 — БД сейчас перевешивает XML, root_not_found 2185, шаг 1 `update_or_create` 2243, шаг 2 parent 2290–2321); `log_progress` (2646); `finalize_session` (2667; `report_details` только при COMPLETED — 2672, 2696).
- `apps/products/management/commands/import_products_from_1c.py` -- процессор 478; шаги 491–528; `_collect_xml_files` (1026; сортировка лексикографическая 1063–1068); `_print_stats` (997).
- `apps/products/models.py` -- `Category` (168, `parent` CASCADE), `Product` (265, `category` CASCADE), `ProductVariant` (817). Последняя миграция `0055_product_article.py`.
- `apps/orders/models.py:443` (`OrderItem.product` CASCADE not null), `:447` (`variant` SET_NULL); `apps/cart/models.py:94`, `apps/users/models.py:534` — каскады при purge. `post_delete`-сигналов на Product/Variant/Image нет, `django-cleanup` не подключён — файлы картинок не пострадают.
- `apps/products/admin.py` -- `ProductAdmin` (373), `ProductVariantAdmin` (599).
- `apps/products/management/commands/fix_category_tree_public_roots.py` -- образец стиля команды.
- Другие создатели процессора — `apps/integrations/tasks.py:286`, `import_images_from_1c.py:169` (конструктор не ломать).
- Тесты, которые придётся переписать: `apps/products/tests/unit/test_variant_import_migrated.py:457–600`, `test_exchange_dir_isolation.py`, `tests/integration/test_variant_import.py` (280, 918, 1086), `unit/test_price_logic.py:18`, `integration/test_image_composition_sync.py:38`, `integration/test_image_import.py:32`, `tests/integration/test_import_fallback_brand.py:55,79`, `management/commands/test_import_products_fix.py`, `tests/integration/test_async_import_tasks.py`, `test_import_orchestration*.py`, `test_import_session_report.py`, `test_import_backup_step.py`, `tests/integration/test_onec_import.py`. Причина массовая: `ROOT_CATEGORY_NAME` по умолчанию «СПОРТ», якоря в тестовой БД нет → «якорь не найден» → ничего не создаётся; тесты должны создавать якорь или ставить пустое имя. Корпус `tests/fixtures/1c-data/` (goods — только `import_files/goods.xml`). Фикстура `onec_data_dir` — `tests/conftest.py:418`.
- Данные: BT45-RU — `4be1a200-…` в `goods/goods_1_9_*.xml`, `5cf1d4de-…` в `goods/goods_1_10_*.xml`; товар `3b6971fe…` — в `goods_1_1` (СПОРТ) и `goods_1_11` (к удалению), всего таких 11; групп с пометкой в снимке нет; товаров со всеми помеченными предложениями — 3.

## Tasks & Acceptance

**Execution:**
- [x] `apps/products/services/parser.py` -- `is_deleted` в `GoodsData`/`OfferData`/`CategoryData` (+копия в `variant_import.py:90`), `category_ids: list[str]`, `category_id` = первый.
- [x] `apps/products/models.py` + миграция `0056` -- `onec_deleted` у `Product`/`ProductVariant` (`BooleanField("Скрыт импортом 1С", default=False, db_index=True)`); модель реестра `OnecExcludedItem` (`onec_id` unique, `kind` group/product/offer, `reason`, `updated_at`).
- [x] `apps/products/admin.py` -- колонка, фильтр, readonly `onec_deleted`; реестр — только чтение.
- [x] `apps/products/services/variant_import.py` -- поддерево с приоритетом XML и реестром групп; правило допуска; скрытие/возврат/перенос категории; реестр; пропуск исключённых в offers/prices/rests до fallback по родителю; закрытие путей реактивации; `create_default_variants` пропускает `onec_deleted` и товары с помеченными предложениями в реестре; удаление fallback-категорий; счётчики и построчный лог.
- [x] `apps/products/management/commands/import_products_from_1c.py` -- натуральная сортировка пакетов; итоговая строка «Вне СПОРТ / к удалению: …» в `log_progress` после каждого шага (не только при COMPLETED) и в `_print_stats`.
- [x] `apps/products/management/commands/purge_products_outside_root.py` -- новая команда: dry-run по умолчанию, `--apply`, `--root-name`; порядок — товары, варианты, категории.
- [ ] Тесты -- юнит в `apps/products/tests/`, интеграционные в `tests/integration/`; I/O-матрица и AC; переписать тесты из Code Map.
- [x] `docs/integrations/1c/import-process.md` -- правило допуска, реестр, ранбук разовой очистки (ТЗ §6 в новой редакции: бэкап → эталон → полный импорт → `purge` dry-run → `--apply` → проверки); `deferred-work.md` -- фильтр API по активности категории (ТЗ §5).

**Acceptance Criteria:**
- Given подмножество снимка (groups, `goods_1_1`, `1_9`, `1_10`, `1_11` и их offers, `--skip-images`), when импорт в пустую БД, then нет товаров и категорий вне поддерева СПОРТ, BT45-RU нет.
- Given БД с товарами СПОРТ, вне СПОРТ, «к удалению» (в категории СПОРТ), с заказом, when импорт того же подмножества и затем `purge --apply`, then удалено всё недопущенное без заказов, товар с заказом скрыт и заказ цел, товары СПОРТ не тронуты; удалённый не отдаётся `/api/v1/products/` и `/api/v1/products/<slug>/` (404).
- Given любой вход (без группы, неизвестная группа, дельта без `groups.xml`, пустой `ROOT_CATEGORY_NAME`), when импорт, then `Category` вне поддерева не создана; slug `onec-unresolved-category` и `uncategorized` не создаются.
- Given завершённая сессия, then в `report_details` счётчики `skipped/hidden/restored/recategorized` товаров и `skipped/hidden/restored` вариантов, в `report` — итоговая строка.
- Given изменённые файлы, when тесты с `--cov` по каждому файлу, then ≥ 90 %; black/flake8 чисто.

## Design Notes

- **Скрытие товара не трогает варианты:** товар `is_active=False` уже убирает его с витрины, а возврат не должен включать варианты, скрытые их собственной пометкой. `onec_deleted` варианта значит «пометка предложения».
- **Возврат варианта** (предложение снова допущено) включает его и активирует родителя по правилу `_create_new_variant` (если родитель не `onec_deleted`).
- **Дефолтный вариант:** «у товара в 1С нет характеристик» отличается от «все помечены» по реестру: есть offer-запись с Ид `<товар>#…` → дефолтный не создаётся.
- **Реестр** грузится в память один раз на сессию (≈ 20 тыс. строк); запись добавляется при недопуске/удалении, убирается при допуске. Группа в реестре исключает поддерево в сессиях без `groups.xml`.
- **Якорь не найден:** существующие товары обновляются как раньше, без проверки допуска.
- Флаг команды — `--apply`, как в ТЗ.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q apps/products tests/integration` -- expected: зелено, включая `data_dependent`.
- тот же прогон с `--cov=apps.products.services.variant_import --cov=apps.products.services.parser --cov=apps.products.management.commands.purge_products_outside_root --cov-report=term` (по изменённым модулям) -- expected: ≥ 90 % каждый.
- Навык `backend-lint` -- expected: чисто.
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` -- expected: затронуты только символы из Code Map.

## Implementation Notes

## Spec Change Log

## Review Triage Log
