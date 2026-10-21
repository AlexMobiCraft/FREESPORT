---
title: 'Импорт 1С: категории не гаснут из-за отсутствия в частичном groups.xml'
type: 'bugfix'
created: '2026-10-21'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'a077842e11c7030d3f5c523d554737df28df2c5c'
context:
  - '{project-root}/backend/docs/testing-standards.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-fix-catalog-categories-deactivation.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** На витрине `/catalog` пропадают подкатегории («Обувь для бокса», «Мешки, груши, манекены», «Наборы для бокса», «Легкая атлетика» и др. — 19 на проде, в 11 из них есть активные товары), хотя в БД и в 1С дерево полное. 1С шлёт `groups*.xml` частичными пакетами (с 24.02.2026 из 3287 сессий с groups в 1258 сработал предохранитель), а `deactivate_obsolete_categories` гасит всякую категорию, которой нет в текущем XML. Предохранитель (≥4 детей и >30 %) пропускает малые ветки (3 ребёнка) и потери до 30 %, поэтому состояние категории зависит от последнего пакета: пришла — включилась, не пришла — погасла.

**Approach:** Отсутствие в XML больше не повод гасить категорию. Гасится только группа, о которой 1С сказала явно: она есть в XML и помечена на удаление, либо вынесена из поддерева якоря (в т.ч. потомок такой группы). Возврат группы в дерево включает её, как и сейчас.

## Boundaries & Constraints

**Always:** гасить только категории с `onec_id` из групп, пришедших в XML сессии и отсечённых правилом допуска (пометка удаления у группы или предка, вне поддерева якоря); запись в БД — один раз в `finalize_session` и только при `completed`; якорь не гасится никогда; возврат группы в дерево по-прежнему делает `is_active=True` через `update_or_create`; перед правкой метода — `npx gitnexus impact <метод> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` (для `deactivate_obsolete_categories` уже `HIGH`: один вызывающий `finalize_session`, процессы `import_products_from_1c.handle`).

**Ask First:** любое изменение правила допуска товаров (`_rebuild_admission_tree`, реестр исключённых) и публичного API категорий.

**Never:** не гасить по отсутствию в XML ни при каком пороге; не удалять категории физически; не трогать `CategoryTreeViewSet`, `reactivate_catalog_categories`, `.env*`; не править прод-БД из кода миграцией.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Частичный пакет | у родителя 3 ребёнка, в XML пришёл 1 | два других остаются `is_active=True` | — |
| Малая потеря в большой ветке | у родителя 5 детей, пришло 4 | пятый остаётся активным | — |
| Помеченная группа | в XML `is_deleted=True`, категория активна | после `finalize_session(completed)` `is_active=False`, у нераскрытых соседей без изменений | — |
| Потомок помеченной | группа без пометки, но предок помечен | гасится | — |
| Вынесена из дерева | якорный режим, родитель группы — чужой корень | гасится | — |
| Возврат | погашенная группа снова допущена в XML | `is_active=True`; следующий частичный пакет её не гасит | — |
| Якорь | якорь попал в «исключённые» | остаётся активным | — |
| Сессия не `completed` | `finalize_session(failed)` | категории не меняются | — |
| Несколько groups*.xml | помеченная группа пришла в первом файле, второй её не содержит | гасится по итогам сессии | — |

</frozen-after-approval>

## Code Map

- `backend/apps/products/services/variant_import.py` -- `process_categories` (~2580–2800): ШАГ 1 пропускает отсечённые группы `continue`; сбор «раскрытых» родителей; `deactivate_obsolete_categories` (~2800) и константы `MAX_CATEGORY_DEACTIVATION_RATIO`/`MIN_CHILDREN_FOR_DEACTIVATION_RATIO` (~52–58); `finalize_session` (~3140) вызывает деактивацию; поля `_valid_category_onec_ids`, `_expanded_parent_onec_ids`, `_root_category_onec_ids` (~400–416).
- `backend/apps/products/tests/unit/test_category_deactivation.py` -- 14 тестов старой семантики «гасим отсутствующих»; переписываются.
- `backend/apps/products/management/commands/reactivate_catalog_categories.py` -- существующая прод-команда (dry-run, `--execute`); используется для разового восстановления, не меняется.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/products/services/variant_import.py` -- в ШАГ 1 `process_categories` копить `self._excluded_category_onec_ids` для групп, отброшенных обоими `continue` (anchored и unanchored); удалить сбор «раскрытых» родителей и поля `_valid_category_onec_ids`, `_expanded_parent_onec_ids`, `_root_category_onec_ids`, константы порогов и стат `categories_deactivation_skipped` -- отсутствие в XML не сигнал
- [ ] там же -- заменить `deactivate_obsolete_categories` на `deactivate_excluded_categories`: один `update(is_active=False)` по `onec_id__in` исключённых, активных, кроме `self._anchor_id`; INFO с числом; `finalize_session` вызывает новый метод, ошибки по-прежнему логируются и не валят сессию -- явный сигнал вместо вывода из отсутствия
- [x] `backend/apps/products/tests/unit/test_category_deactivation.py` -- переписать под строки I/O-матрицы (anchored и unanchored); тест «возврат + следующий частичный пакет» двумя сессиями -- закрепляет регресс-сценарий прода
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- записи от 2026-08-09 о «корневых категориях никогда не деактивируются» и о константах порога предохранителя пометить снятыми этой спекой (остальные две записи того блока остаются в силе) -- не оставлять висячих долгов

**Acceptance Criteria:**
- Given 3 категории под одним родителем, when приходит groups.xml с одной из них и сессия `completed`, then все три активны.
- Given группа с `ПометкаУдаления=true` и её потомок, when сессия `completed`, then обе неактивны, а категории вне XML не тронуты.
- Given активная категория, погашенная ранее, when она приходит допущенной, then активна и остаётся активной после следующего частичного пакета.

## Design Notes

Деактивацию откладываем до `finalize_session`, чтобы упавшая сессия не прятала витрину; копить id в ШАГ 1 дешевле повторного обхода XML. После выкладки на проде восстановить 19 категорий командой `reactivate_catalog_categories` (dry-run, затем `--execute`) — до выкладки бессмысленно: следующий пакет погасит их снова.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q apps/products/tests/unit/test_category_deactivation.py` -- expected: все зелёные
- `... pytest -q -k "import and categor" apps/products tests` (после зачётного прогона, не параллельно с линтерами) -- expected: без регрессий импорта 1С
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` и `check --cycles` -- expected: затронут только импорт категорий, новых циклов нет

**Manual checks:**
- После выкладки и `--execute`: `curl https://optisport.ru/api/v1/categories-tree/` содержит 19 возвращённых категорий; через 10–15 минут обменов (несколько пакетов groups) их число не уменьшилось.

## Suggested Review Order

**Откуда берётся сигнал «группа исключена»**

- Точка входа: отсечённые правилом допуска группы копятся, а не вычисляются «по отсутствию».
  [`variant_import.py:2645`](../../backend/apps/products/services/variant_import.py#L2645)

- Допущенная группа снимает исключение: последнее слово за последним файлом сессии.
  [`variant_import.py:2655`](../../backend/apps/products/services/variant_import.py#L2655)

- Поле-накопитель вместо трёх удалённых множеств и порогов предохранителя.
  [`variant_import.py:399`](../../backend/apps/products/services/variant_import.py#L399)

**Применение: один раз, только при completed**

- Новый метод: вычитает допущенное, защищает якорь, пишет в отчёт сессии.
  [`variant_import.py:2760`](../../backend/apps/products/services/variant_import.py#L2760)

- Вызов остался в `finalize_session`: упавшая сессия витрину не трогает.
  [`variant_import.py:3023`](../../backend/apps/products/services/variant_import.py#L3023)

- Счётчик для `report_details`, чтобы оператор видел гашение.
  [`variant_import.py:353`](../../backend/apps/products/services/variant_import.py#L353)

**Проверка**

- Инциденты прода: малая ветка и потеря ниже старого порога остаются активными.
  [`test_category_deactivation.py:121`](../../backend/apps/products/tests/unit/test_category_deactivation.py#L121)

- Регресс «вернулась и пережила частичный пакет», реальная выгрузка 1С — последний тест файла.
  [`test_category_deactivation.py`](../../backend/apps/products/tests/unit/test_category_deactivation.py)

**Долги**

- Три отложенные находки ревью и две снятые записи 2026-08-09.
  [`deferred-work.md`](deferred-work.md)
