---
title: 'Акционная цена из 1С отдельным видом цен'
type: 'feature'
created: '2026-10-21'
status: 'ready-for-dev'
route: 'dispatch'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Акцию сейчас ведут вручную: менеджер отмечает каждый товар флагом `is_promo` в админке и отдельно проставляет цену. В 1С акция уже есть — это отдельный вид цен («АКЦИЯ ОКТЯБРЬ-26»), который штатно выбирается в белом списке выгрузки БУС («Выгрузка информации о товарах» → «Цены»). Сайт такой вид цен сейчас пропускает с warning.

**Approach:** Сайт распознаёт вид цен, название которого начинается со слова «АКЦИЯ», пишет его цены в новое поле варианта `promo_price`, сам выставляет `is_promo` и применяет акционную цену в каталоге, карточке, корзине и заказе. Клиент видит свою закреплённую цену зачёркнутой и рядом акционную. Доработка 1С и расширения БУС не нужна.

Решения владельца (2026-10-21):
- Акционная цена действует для всех ролей (гость, розница, опт 1–4, тренер, федерация) и применяется всегда, даже если она выше или равна цене клиента.
- Одновременно действует одна акция.
- Название акционного вида цен в 1С всегда начинается со слова «АКЦИЯ».
- Показ: акционная цена, рядом зачёркнутая цена клиента по его роли — только если она выше акционной (`regular_price > promo_price`). Уточнено владельцем 2026-10-21: зачёркнутая цена ниже оплачиваемой выглядит как повышение цены под видом скидки.
- Снимки цен в корзине не пересчитываются (решение владельца 2026-10-21, см. Design Notes).
- Флаг `is_promo` ставится только автоматически. Ручные действия убрать, поле только для чтения.
- Конец акции в 1С — пометка удаления на виде цен. Новая акция — новый вид цен.
- Экспорт заказа в 1С не меняется. БУС 8.1.0.40 и 8.1.0.45 при загрузке заказа `<ВидЦены>` строки не читает, цену берёт из `ЦенаЗаЕдиницу` (`БУС_ЗагрузкаСервер`, стр. 519, 2167).

## Boundaries & Constraints

**Always:**
- **Распознавание.** `onec_name.strip().lower().startswith("акция")` → `promo_price`. Ветка проверяется первой.
- **Текущая акция** — не более одного `PriceType(product_field="promo_price", is_active=True)`. Гарантия — частичный `UniqueConstraint`.
- **Правило активности при импорте.**
  - Новый акционный тип (запись создана или `product_field` перешёл в `promo_price`) без пометки удаления становится текущим, если он новее текущего по времени создания в 1С. Время берётся из GUID: UUID v1, `uuid.UUID(onec_id).time`. Если GUID не v1, считается новее.
  - Прежний текущий тип и все акционные кроме нового получают `is_active=False`.
  - Несколько новых в одном файле — побеждает самый новый.
  - Уже известный тип импорт никогда не делает активным.
  - Пометка удаления деактивирует тип. Пришедший сразу с пометкой создаётся неактивным.
- **Смена текущей акции** (стала другой или не стало никакой) → `promo_price=NULL` у всех вариантов, затем `sync_promo_flags`. Пометка у неактивного типа ничего не обнуляет.
- **`sync_promo_flags`:** `is_promo = есть активный вариант с promo_price > 0`. Обновляются только расходящиеся строки. Запускается после каждого применения цен и после смены акции.
- **Снятие товара с акции.** Если идёт текущая акция и предложение пришло в пакете цен без цены этой акции, у варианта ставится `promo_price=NULL`. Предложения, которых в пакете нет, не трогаются. Основание: БУС выгружает у предложения все положительные цены белого списка (`&Прайсы` из сохранённых настроек каталога, `ГДЕ Цена > 0`; `БУС_ВыгрузкаСервер`, стр. 6140, 6289), а изменение цены в 1С регистрирует товар к выгрузке. Решение владельца 2026-10-21.
- **`promo_price`:** `≤ 0` → NULL, правило только для этого поля. Это защита: нулевые цены БУС не выгружает.
- **Цены неактивного акционного типа** пропускаются молча. Неизвестный GUID — warning один раз за сессию.
- **Админка** — любое сохранение или удаление акционного `PriceType` и любая смена `product_field`/`is_active` идёт через `apps/products/services/promo.py`. Включение второго акционного типа выключает прежний и обнуляет цены. `promo_price` и `is_promo` в админках только для чтения.
- **API:**
  - `promo_price` — decimal-строка или null, видна всем ролям; null, если у варианта нет акционной цены.
  - `regular_price` — цена по роли без акции (гостю розница).
  - `current_price` — то, что платит клиент: `promo_price`, если есть, иначе `regular_price`.
  - Список отдаёт эти поля по первому варианту.

**Never:**
- Не править 1С и БУС.
- Не трогать ценовые фильтры и сортировку (`visible_price_q`, `min_retail_price`).
- Не трогать тему `/electric`.
- Не пересчитывать уже лежащие в корзине снимки цен.
- Не использовать сегменты номенклатуры.
- Не трогать `discount_percent` и `determineBadge`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Старт акции | Новый «АКЦИЯ НОЯБРЬ-26» + его цены | Тип текущий, октябрь неактивен, `promo_price` обнулён и записан заново, `is_promo` пересчитан | N/A |
| Старый тип в полной выгрузке | «ОКТЯБРЬ» без пометки, текущий «НОЯБРЬ» | Ничего не меняется, цены октября пропущены молча | N/A |
| Пометка неактивного | «ОКТЯБРЬ» с пометкой, текущий «НОЯБРЬ» | Ничего не обнуляется | N/A |
| Товар снят с акции | Текущая акция, предложение пришло в `prices.xml` без её цены | У варианта `promo_price=NULL`, `is_promo` пересчитан, остальные варианты без изменений | N/A |
| Предложение не пришло | Текущая акция, предложения нет в пакете | `promo_price` не меняется | N/A |
| Конец акции | Текущий тип с пометкой | `promo_price=NULL` везде, `is_promo=False` | N/A |
| Два новых в файле | «А» и «Б» новые | Текущий — более новый по GUID | N/A |
| Цены раньше типа | GUID не в `PriceType` | Цена пропущена | Warning с подсказкой о полной выгрузке |
| Акция ниже цены | Опт 2 = 1000, акция 800 | Платит 800, 1000 зачёркнуто | N/A |
| Акция выше цены | Опт 1 = 700, акция 800 | Платит 800, зачёркнутой цены нет | N/A |
| Акция равна цене | Опт 3 = 800, акция 800 | Платит 800, зачёркнутой цены нет | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/products/models.py:721,832,1230` -- `PriceType`: choice и constraint. `ProductVariant.promo_price`. `get_price_for_user` → акция поверх `get_regular_price_for_user` (нынешняя логика).
- `backend/apps/products/migrations/0058_*` -- поле, choice, data-шаг на `RunPython` тем же правилом, что парсер (`onec_name.strip().lower().startswith("акция")`) → `promo_price`, активной остаётся самая новая по GUID; затем constraint. Не SQL `ILIKE`: dev-БД создана с `--lc-ctype=C` (`docker/docker-compose.yml`), и там Postgres кириллицу по регистру не сворачивает.
- `backend/apps/products/services/parser.py:71,497,571` -- `PriceTypeData.is_deleted`, `ПометкаУдаления`, ветка «акция».
- `backend/apps/products/services/variant_import.py:1898,2502` -- `update_variant_prices`: кэш всех `PriceType`, сбрасывается в `process_price_types` (шаги 1 и 4 идут в одном процессоре, `import_products_from_1c.py:518-542`). `process_price_types` применяет правило активности через `promo.py`. В `update_variant_prices`: если есть текущая акция, а её GUID нет среди цен предложения, в `price_updates` добавляется `promo_price=None`. Неакционные типы — как прежде (`is_active=True`).
- новый `backend/apps/products/services/promo.py` -- `is_newer`, `activate`, `deactivate_promo`, `sync_promo_flags`.
- `backend/apps/products/management/commands/import_products_from_1c.py:785` -- `sync_promo_flags()` в конце `_import_variant_prices`. Покрывает сессии `all`/`prices`/`offers` и Celery (`tasks.py:543`).
- `backend/apps/products/admin.py:55,385-471,540-548,589` -- `promo_price` readonly в варианте и инлайне. `is_promo` readonly. Удалить `mark/unmark_as_promo`. `PriceTypeAdmin.save_model`/`delete_model`/`delete_queryset` → `promo.py`. Если сохранение сбросило акционные цены, показать `messages.warning`: «Акционные цены сброшены. Они вернутся после полной выгрузки из 1С».
- `backend/apps/products/marketing_admin.py:30,98-127` -- `LABEL_FIELDS` разделить на редактируемые (без `is_promo`) и показываемые.
- `backend/apps/products/serializers.py:52,439,525,555` -- поля API. `_get_first_variant` предпочитает вариант с `promo_price`.
- `backend/apps/products/views.py:80-92` -- `first_variant_list`: порядок `promo_price IS NULL`, затем `retail_price`.
- Затронуты без правок: `apps/cart/views.py:142`, `apps/cart/models.py:152`, `apps/orders/services/order_create.py:138`, `order_export.py:359` — берут `get_price_for_user`. GitNexus корзину не видит.
- `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` (`npm run generate:types`, гейт `api-contract.yml`), `frontend/src/types/api.ts:38,345`, `services/productsService.ts:25,127`.
- `frontend/src/components/business/ProductCard/ProductCard.tsx:112,307,445,573` -- при `promo_price`: жирная `current_price` во всех трёх раскладках (list/grid/compact), рядом зачёркнутая `regular_price` — только при `regular_price > promo_price`. Ветка `is_sale` действует, только когда акции нет.
- `frontend/src/components/product/ProductInfo.tsx:27-30,143` -- то же по `selectedVariant`. Без выбранного варианта — по полям списка. JSON-LD (`ProductPageClient.tsx:109`) уже берёт `current_price`.

## Tasks & Acceptance

**Execution:**
- [ ] `models.py` + `0058` -- поле, choice, data-шаг, constraint.
- [ ] `parser.py` -- распознавание и пометка удаления.
- [ ] `services/promo.py` -- правило активности, сброс, флаги.
- [ ] `variant_import.py`, `import_products_from_1c.py` -- кэш типов, ≤0, вызовы `promo.py`.
- [ ] `models.py` -- `get_price_for_user` / `get_regular_price_for_user`.
- [ ] `serializers.py`, `views.py`, `openapi.yaml` -- поля и первый вариант.
- [ ] `admin.py`, `marketing_admin.py` -- readonly, удаление действий, хуки `PriceTypeAdmin`.
- [ ] frontend: `api.generated.ts`, `api.ts`, `productsService.ts`, `ProductCard.tsx`, `ProductInfo.tsx`.
- [ ] тесты:
  - backend новые: `apps/products/tests/test_promo_price.py` (все строки матрицы, миграция, админ-хуки, constraint, отсутствие ложного warning);
  - backend правка: `test_parser_helpers.py`, `test_price_logic.py`, `tests/integration/test_variant_import.py`, `test_cart_order_integration.py`, `test_marketing_section.py:80`, `tests/unit/test_marketing_admin_site.py:69`;
  - frontend: `ProductCard.test.tsx`, `ProductInfo.test.tsx`.

**Acceptance Criteria:**
- Given активная акция, when клиенты ролей guest, retail, opt3, trainer и federation_rep оформляют заказ, then `OrderItem.unit_price` и `ЦенаЗаЕдиницу` равны `promo_price`.
- Given активная акция, when гость открывает каталог, then у акционного товара во всех раскладках акционная цена и бейдж «Акция», а розница зачёркнута рядом, если она выше акционной.
- Given менеджер снял «Активный» у текущего акционного типа или удалил его, when сохранение прошло, then акционных цен и флагов `is_promo` нет.
- Given в 1С поставлена пометка удаления на текущий вид цен «АКЦИЯ …», when пришёл `priceLists.xml`, then акции на сайте нет.

## Implementation Notes

- `promo.activate`: сначала выключить прежний текущий тип, потом включить новый. В обратном порядке частичный `UniqueConstraint` даст `IntegrityError`, а его молча проглотит `except Exception` в `process_price_types`.
- `frontend` тесты: зачёркнутая цена есть при `regular_price > promo_price` и отсутствует при равенстве и при акции выше цены.

## Spec Change Log

## Review Triage Log

## Design Notes

Почему пропавшая у предложения цена означает снятие с акции, а пропавший тип — нет: дельта выбирает, какие предложения выгрузить, но цены у каждого выгруженного предложения идут полным списком из белого списка (см. правило «Снятие товара с акции»). На уровне вида цен такого полного списка нет — отсюда следующий абзац.

Почему явный сигнал конца акции: при выгрузке «только изменения» БУС шлёт `priceLists.xml`, только если менялся сам вид цен (`БУС_ОбменССайтомВызовСервера`, стр. 304). Цены приходят дельтой, отсутствующие поля не обнуляются. Поэтому акция живёт до явного сигнала, а при смене акции цены сбрасываются массово.

Почему «новее по GUID»: полная выгрузка присылает все типы из белого списка, в том числе старую акцию без пометки. По одному порядку прихода текущую акцию не определить.

Снимки цен в корзине (решение владельца 2026-10-21 — не пересчитывать). `CartItem.price_snapshot` ставится только при создании строки, слияние (`cart/views.py:142`) меняет одно количество, заказ берёт снимок (`order_create.py:138`). Отсюда два известных и принятых следствия: товар, положенный в корзину до старта акции, оформится по прежней цене; положенный во время акции — по акционной и после её конца, пока строка лежит в корзине.

Повторное включение акционного типа. Включение типа в админке (в том числе после снятой в 1С пометки удаления — импорт известный тип сам не активирует) — это смена текущей акции, и `promo_price` обнуляется. В дельте цены не придут, потому что в 1С они не менялись. Акция вернётся только с полной выгрузкой, поэтому админка об этом предупреждает.

Раскатка на прод.
- Снимок прода 2026-10-21: акционного `PriceType` нет (на проде 7 типов, все сопоставлены). `is_promo=True` вручную у 6 товаров, `is_sale` у 6, `discount_percent` у 0.
- Data-шаг миграции нужен на случай, если белый список сохранят и выгрузят до деплоя: тогда тип ляжет с `product_field=""`.
- После деплоя — сразу полная выгрузка из 1С.
- 6 ручных отметок «Акция» снимет первый же импорт цен.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` -- expected: зелёный
- `cd frontend && npm run format:check && npm run lint && npx tsc --noEmit && npx vitest run` -- expected: без ошибок

**Manual checks:**
- Копия пакета `data/import_1c` с добавленным акционным типом: в админке «Типы цен» есть «АКЦИЯ …» → «Акционная цена», у товаров флаг «Акция», в карточке две цены.
