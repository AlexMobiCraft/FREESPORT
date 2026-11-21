---
title: 'РРЦ на сайте = розничная цена из 1С; удаление поля ProductVariant.rrp'
type: 'bugfix'
created: '2026-11-20'
status: 'done'
route: 'dispatch'
baseline_commit: 'd28db408'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Под ценой роли строка «РРЦ» выводит `ProductVariant.rrp`, а его импорт не пишет с ~августа 2026. Вид цен 1С «РРЦ» уходит в `retail_price` (`parser.py:623-626`), в `rrp` лежат старые числа, близкие к МРЦ: BGS322 — розница 2530, `rrp` 2105, МРЦ 2150. Гость строку не видит: на скриншоте владельца браузер нёс `sessionid` от входа в админку.

**Approach:** Строка «РРЦ» показывает `retail_price` — API отдаёт в поле `rrp` розницу варианта. Колонка `ProductVariant.rrp` удаляется со всех вариантов, вид цен с маппингом `rrp` пропадает. Администраторы и менеджеры строку не видят.

## Boundaries & Constraints

**Always:**
- Имя поля API `rrp` и правило видимости (`can_see_info_prices`, гость и розница поля не получают) сохраняются. Значение — `retail_price` того же варианта; в списке — первого варианта, как сейчас.
- Строку «РРЦ» на фронте показывает только `isB2BRole(userRole)` (`utils/pricing.ts`): `admin`, `retail`, `unregistered`, `guest` её не видят. Менеджеры на проде — `role=retail`, `is_staff`.
- B2B-роль видит строку «РРЦ» всегда, даже если цена роли равна РРЦ (решение владельца 20.11.2026). Скрыта только при пустой или нулевой рознице.
- Вид цен 1С с «ррц» в названии всегда идёт в `retail_price`, с «рекоменд» или без.
- Миграция переводит `PriceType` с `product_field='rrp'` в `''`, затем удаляет поле. На проде таких видов 0. Следующая загрузка `priceLists` перемаппит такой вид новым парсером в `retail_price` — риск двух видов на рознице есть только в dev/test.

**Never:**
- Не трогать `msrp` (МРЦ): поле, импорт, API остаются.
- Не менять серверное определение роли по `sessionid`.
- Не переименовывать `retail_price` и не менять расчёт цены роли.
- Не менять `INFO_PRICE_ROLES` (`pricing_policy.py:79-92`): API по-прежнему отдаёт `rrp`/`msrp` админу, строку скрывает фронт.

## I/O & Edge-Case Matrix

| Роль | Цена карточки | Строка «РРЦ» |
|---|---|---|
| guest, retail, unregistered | розница | нет (API не отдаёт `rrp`) |
| admin, менеджер (`retail` + staff) | розница | нет |
| federation_rep | цена федерации | нет (API не отдаёт `rrp`) |
| wholesale_level1 | Опт 1 = 1800, розница 2530 | «РРЦ: 2 530 ₽» |
| vip, цена роли = рознице 2530 | 2530 | «РРЦ: 2 530 ₽» |
| B2B, вариант с розницей 0 | Опт 1 | нет |

</frozen-after-approval>

## Code Map

- `backend/apps/products/models.py:1228` — поле `rrp` удалить; `:947` — убрать выбор `rrp` из `PriceType.product_field`.
- `backend/apps/products/migrations/0061_remove_productvariant_rrp.py` — новая: RunPython `PriceType(product_field='rrp') → ''` (reverse — noop), `RemoveField`, `AlterField` выборов. `process_price_types` и так перезапишет `product_field` при первой загрузке `priceLists` (`variant_import.py:2744`, любой непустой маппинг); data-шаг нужен, чтобы до неё в админке не висел вид цен с недопустимым выбором.
- `backend/apps/products/serializers.py:80-98` — `ProductVariantSerializer`: `rrp` в `Meta.fields` больше не из чего строить (иначе `ImproperlyConfigured`) — объявить `SerializerMethodField` с `@extend_schema_field` (строка Decimal, nullable): `f"{retail_price:.2f}"`, `None` при ≤ 0. Контракт `string | null` (`openapi.yaml:4924-4929`) сохраняется. `:530,667` — список: `get_rrp` → `float(variant.retail_price)`, `None` при ≤ 0. `to_representation` `:101-108`, `:645` не трогать.
- `backend/apps/products/services/parser.py:623-626` — «ррц» → `retail_price` без ветки «рекоменд».
- `backend/apps/products/services/variant_import.py:1992-1995` — удалить автозаполнение розницы из `rrp`.
- `backend/apps/products/admin.py:68,685,744` — убрать `rrp` из полей; `:602-606` `rrp_display` — как сейчас (выбор варианта и сортировка по обратной FK), но по `retail_price`: `variants.filter(retail_price__gt=0)` (поле NOT NULL — `isnull=False` ничего не отсекает и покажет «0.00 ₽»), `ordering="variants__retail_price"`, подпись «РРЦ».
- `frontend/src/components/product/ProductInfo.tsx:73-83,186-197` — `canSeeRrp` → `isB2BRole(userRole)`.
- `frontend/src/components/business/ProductCard/ProductCard.tsx:531,665` — условие `isB2BRole(userRole)` без `mode === 'b2b'` (mode у админа `b2b`).
- `frontend/src/components/home/HitsSection.tsx:104-115,330` — `isB2B` для `rrp` → `isB2BRole(userRole)` (сейчас список включает `admin`); список `isB2B` для `mode` не трогать.
- `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` — `rrp` в трёх схемах: `:4509` и `:4785` (`number | null`, описание из docstring `get_rrp` — поменять docstring на «РРЦ = розничная цена первого варианта»), `:4924` (`ProductVariant`, `string | null`, описание из `@extend_schema_field`: «РРЦ = розничная цена варианта»). Синхронизировать командой `check_openapi_sync`.
- Тесты на удалённую логику — переписать или удалить: `apps/products/tests/unit/test_price_logic.py:52-97` (автозаполнение), `apps/products/tests/unit/test_parser_helpers.py:150`, `tests/unit/test_services/test_xml_parser.py:244` («рекоменд» → `rrp`). Остальные упоминания `rrp` (`git grep -wn rrp backend frontend/src`) — фикстуры, поправить.
- Документация: `docs/architecture/09-database-schema.md:161`, `docs/architecture/request-to-1c-developer.md:284`, `docs/architecture/10-testing-strategy.md` — убрать колонку `rrp`, РРЦ = `retail_price`.

## Tasks & Acceptance

**Execution:**
- [x] `models.py`, `migrations/0061_*` — удалить поле и выбор, миграция данных PriceType — колонки нет, путаницы нет.
- [x] `parser.py`, `variant_import.py` — «ррц» → `retail_price`, без автокопии — импорт не ссылается на удалённое поле.
- [x] `serializers.py` — `rrp` из `retail_price` — фронт получает настоящую РРЦ без смены контракта.
- [x] `admin.py` — колонка «РРЦ» из розницы, без поля `rrp`.
- [x] `ProductInfo.tsx`, `ProductCard.tsx`, `HitsSection.tsx` — видимость по `isB2BRole`.
- [x] `openapi.yaml`, `api.generated.ts` — синхронизировать.
- [x] Тесты: строки матрицы в `ProductInfo.test.tsx`, `ProductCard.test.tsx`; сериализатор деталки и списка — `rrp == retail_price` для B2B, `None` при рознице 0, нет поля для гостя и federation_rep; парсер — «РРЦ» и «Рекомендованная розничная цена» → `retail_price`; миграция — вид `rrp` получает `''`. Поправить фикстуры остальных тестов.

**Acceptance Criteria:**
- Given оптовик 1 и BGS322 (Опт 1 < 2530), when он открывает карточку, then под ценой «РРЦ: 2 530 ₽».
- Given администратор или менеджер, when он открывает карточку или каталог, then строки «РРЦ» нет.
- Given миграции применены, when `\d product_variants`, then колонки `rrp` нет; полный импорт 1С проходит без ошибок.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar apps/products tests/integration tests/unit` — зелёное.
- `cd frontend && npx vitest run src/components/product src/components/business/ProductCard src/components/home && npm run format:check && npm run lint && npx tsc --noEmit` — без ошибок.
- `backend-lint`, `makemigrations --check` — чисто.

**Выкат и откат:**
- Один релиз. Колонку удаляет `migrate` при старте нового backend (`docker/entrypoint_backend.sh:9`); celery пересоздаётся позже (`deploy.yml:461`) — импорт, попавший в эти секунды, на старом коде упадёт один раз и пройдёт следующим запуском.
- Откат через `gh workflow run deploy.yml -f image_tag=<sha прошлого релиза>` без подготовки уронит каталог, корзину и импорт: старый образ выбирает `rrp`, а `0061` в нём нет и назад не откатить. Перед откатом выполнить на проде:
  ```sql
  ALTER TABLE product_variants ADD COLUMN rrp numeric(10,2) NULL;
  ```
  Колонка пустая и nullable — старому коду этого хватает. Запись `0061` в `django_migrations` после отката остаётся, поэтому повторный выкат миграцию не перезапустит: колонка останется лишней, но безвредной (новый код её не читает). Удалить её потом вручную: `ALTER TABLE product_variants DROP COLUMN rrp;`.

**Manual checks:**
- Локально `migrate`, затем `\d product_variants` — колонки `rrp` нет; импорт по навыку `import-1c` (полный, с `priceLists` и `prices`) — без ошибок, у вариантов `retail_price` = РРЦ из 1С.

## Implementation Notes

- `ProductCard`: проп `mode` больше ни на что не влияет — убран из деструктуризации (eslint `no-unused-vars`), в интерфейсе оставлен с пояснением: его передают семь вызывающих. Условие `product.rrp != null && product.rrp > 0` вместо `product.rrp && ...` — прежнее выражение при `rrp = 0` выводило в разметку «0» (ловит тест «розница 0»).
- `ProductVariantSerializer.rrp`: описание схемы — через `help_text` поля в `@extend_schema_field` (docstring метода drf-spectacular при явном поле не берёт). `openapi.yaml` правлен точечно: генератор переставляет методы путей, `check_openapi_sync` — «синхронен».
- Полный прогон `apps/products tests/integration tests/unit` с `-n 4`: 5235 passed, 81 skipped, 1 failed — тайминговый `test_retrieve_product_with_100_variants_under_500ms` под нагрузкой воркеров; отдельно — passed.
- Manual checks (`migrate` на dev-БД, `\d product_variants`, полный импорт по навыку `import-1c`) не выполнялись — за владельцем.
- Патчи повторного ревью (20.11.2026): в `_map_price_type_to_field` «ррц» проверяется сразу после акции и точных названий, раньше оптовых и тренерского маркеров. В реальных `priceLists` таких комбинаций нет, поэтому выгрузка ведёт себя как раньше. Добавлен `TestMigration0061AppliedToExistingCatalog`: схема откатывается к 0060, данные заводятся историческими моделями, затем миграция применяется исполнителем. Мутация (убрать `RunPython`) роняет тест. Интеграционные тесты дополнены двумя вариантами с разной розницей и `rrp: null` в списке. Полный прогон с `-n 4`: 5242 passed, 81 skipped, 1 failed — снова тайминговый `test_retrieve_product_with_100_variants_under_500ms`, отдельно passed. `makemigrations --check` — изменений нет.

- Патчи ревью по рабочему дереву (21.11.2026): E2E-импорт закоммиченного среза (`test_full_http_exchange_imports_catalog_from_private_dir`) проверяет, что вид «РРЦ» (`3d1482c4-…`) смаппен в `retail_price`, а у картриджа INTEX 29002 (`069efcc9-…`) розница 635, МРЦ 540, Опт 1 443 из `prices.xml`. Фронт: в `ProductOptions.integration.test.tsx` оптовик переключает вариант — «РРЦ» меняется 7 990 → 8 490; в `CatalogPage.test.tsx` — оптовик видит «РРЦ», админ нет, в плитке и списке (мутация `userRole="retail"` в ветке списка роняет тест); `rrp: null` — в `ProductCard` (обе раскладки) и `ProductInfo`. Для этого ручные типы `rrp` расширены до `number | null` / `string | null` (`types/api.ts`, `productsService.ts`), в `HitsSection` — `product.rrp ?? undefined` для `ElectricProductCard`. Фикстура `catalog_before_rrp_migration` откатывает схему внутри `try`. Прогон с `-n 4`: 5243 passed, 81 skipped, 0 failed; vitest (product, ProductCard, home, catalog, services): 1064 passed; `format:check`, `lint`, `tsc`, black/isort/flake8, `makemigrations --check` — чисто. Полный импорт на dev-БД (Manual checks) по-прежнему за владельцем.

## Spec Change Log

- 2026-11-20, party mode (сессия 21): из Never удалена ссылка на несуществующую спеку (решение владельца, правка frozen); `rrp_display` — `retail_price__gt=0`; в Code Map все три схемы OpenAPI и docstring `get_rrp`; пояснение data-шага миграции; раздел «Выкат и откат» — один релиз и SQL перед откатом (решение владельца, вариант двух релизов отклонён). Поиск с жёстким `userRole="retail"` вынесен в `deferred-work.md`.

## Review Triage Log

Итерация 1 (20.11.2026). Слой graph-impact не выполнен: индекс собран на HEAD `40ddc20`, незакоммиченный diff даёт `stale` — сбой слоя, перезапуск после `analyze --force`.

| # | Слой | Находка | Вердикт | Маршрут | Доказательство |
|---|---|---|---|---|---|
| 1 | verification-gap | `HitsSection`: нет теста, кому видна «РРЦ» в хитах | medium | patch | `HitsSection.test.tsx` не задаёт роль и не ищет «РРЦ»; возврат `isB2B` (с `admin`) не уронит ни один тест |
| 2 | verification-gap | `ProductCard`: нет отрицательного теста admin + `mode="b2b"` в `layout="list"` | medium | patch | Отрицательный `it.each` рендерит только `grid`; `CatalogPageClient` передаёт админу `list` + `b2b` |
| 3 | verification-gap | `rrp_display` без тестов | low | patch | `git grep rrp_display` — только `admin.py`; changelist-тест проверяет лишь 200 |
| 4 | blind | `test_rrp_price_type_writes_retail_price` создаёт вид уже с `retail_price` — имя «РРЦ» мимо маппера; нет теста перемаппинга `''` → `retail_price` в `process_price_types` | low | patch | Тест в diff: `product_field="retail_price"`, `hasattr` всегда False |
| 5 | blind | Комментарий `INFO_PRICE_FIELDS` в `pricing_policy.py` утверждает, что инфо-цены закрыты от розницы, хотя `rrp` = `retail_price` | low | patch | `retail_price` отдаётся всем ролям; гейт сохранён решением спеки (Never), комментарий вводит в заблуждение |
| 6 | blind | Проп `mode` в `ProductCard` мёртвый, не помечен `@deprecated` | low | patch | Деструктуризация удалена, вызывающие (7) передают проп |
| 7 | blind | Тест миграции проверяет `_meta`, а не колонку в БД | low | patch | `test_rrp_field_and_choice_removed` — только `get_fields()`; AC про `\d product_variants` |
| 8 | blind | vip-тест `ProductCard` не проверяет показанную цену 2530; проверка `/₽0/` хрупкая | low | patch | Равенство цены роли и РРЦ задано только фикстурой |
| 9 | blind | Окно деплоя: старые celery-воркеры между `migrate` (entrypoint backend) и пересозданием celery падают на любом запросе с `ProductVariant`, не только импорт | medium | defer | `deploy.yml`: backend → `sleep 15` + check → celery; `orders/tasks.py:35-36` `select_related("variant")`, `ProgrammingError` не в `autoretry_for` — письмо о заказе в окне теряется. Порядок деплоя — существующий, вскрыт удалением колонки |
| 10 | edge, blind | Два активных вида на `retail_price` («РРЦ» + «РРЦ рекомендованная») без защиты | low | reject | Спека (Always) принимает риск только для dev/test; на проде видов `rrp` 0, в реальной выгрузке только «РРЦ»; защита — новая ветка |
| 11 | edge | После отката и повторного выката вид `rrp` молча пропускается | low | reject | Требует вида «рекоменд…ррц» в 1С — в выгрузке его нет; защита — новая ветка |
| 12 | edge, blind | Колонка «РРЦ» в админке берёт вариант не так, как API | low | reject | Спека: выбор варианта «как сейчас»; N+1 был и до правки |
| 13 | edge | В списке первый вариант с розницей 0 даёт `null` при цене у других | false | reject | `first_variant_ordering` внутри группы ставит вперёд вариант с `retail_price > 0` |
| 14 | edge | Миграция обнуляет маппинг вида с нераспознаваемым именем | low | reject | На проде видов `rrp` 0 |
| 15 | edge | «РРЦ опт 1» уйдёт в `opt1_price`, вопреки «ррц всегда в retail» | low | reject | Таких имён в 1С нет (`data/import_1c/priceLists`) |
| 16 | edge | Утверждение спеки об откате неточно | — | reject | Исправление — правка спеки этой сборки |
| 17 | blind | «Максимальная рекомендованная розничная цена» уйдёт в `retail_price` | false | reject | В 1С вид называется «МРЦ» (`priceLists`); ветка «рознич» существовала до правки |
| 18 | blind | `ElectricProductCard`: `{rrp && …}` выведет «0» | false | reject | API при рознице ≤ 0 отдаёт `null` (`get_rrp`) |
| 19 | blind | Electric-хиты: B2B видит «2 530 ₽» и «РРЦ: 2 530 ₽» рядом | low | reject | Карточка electric показывает `retail_price` всем ролям и до правки; исправление — ролевые цены в electric-карточке |
| 20 | blind | Документы `er-diagram.md`, `role-based-pricing-pattern.md`, примеры, `PROJECT_INFO.md` описывают отдельное поле РРЦ | low | reject | Там вымышленные `recommended_retail_price`/`max_suggested_retail_price` — существовали до правки; `PROJECT_INFO` («инфо-цены РРЦ, МРЦ») остаётся верным |
| 21 | blind | Неверная ссылка `variant_import.py:2744` в спеке | — | reject | Исправление — правка спеки этой сборки |

Итерация 2 (21.11.2026, `/bmad-build`, diff `d28db408..` рабочее дерево без `_bmad-output`). Все четыре слоя завершились, индекс GitNexus свежий (`f2b8b0f`), новых циклов нет.

| # | Слой | Находка | Вердикт | Маршрут | Доказательство |
|---|---|---|---|---|---|
| 22 | verification-gap | Сортировка колонки «РРЦ» в админке (`ordering="variants__retail_price"`) не проверена: опечатка дала бы 500 без падения тестов | low | patch | `test_rrp_display_*` вызывают метод напрямую, `test_admin_onec_deleted.py:97` открывает changelist без `o=` |
| 23 | edge, blind | Миграция ставит `''`, а не `retail_price` — цены «РРЦ» пропускаются до следующей загрузки `priceLists` | low | reject | carried: «Отклонено» повторного ревью; Always спеки задаёт `''`, на проде видов `rrp` 0 |
| 24 | edge | Вид с маппингом `rrp` и нераспознаваемым именем навсегда остаётся без маппинга | low | reject | carried #14 |
| 25 | edge, blind | Откат через `image_tag` роняет старый образ на БД без колонки | — | reject | carried #16: раздел «Выкат и откат» с SQL, два релиза отклонены владельцем; исправление — правка спеки |
| 26 | edge | «МРЦ (от РРЦ)» уйдёт в `retail_price` | low | reject | До правки «ррц» тоже проверялся раньше «мрц» — поведение не изменилось; таких имён в `priceLists` нет |
| 27 | edge, blind | «Розничная» и «РРЦ» на одном поле — розница зависит от порядка в XML; заказ берёт вид по алфавиту (`order_create.py:261`) | low | reject | carried #10; graph-impact: на проде видов `rrp` 0, риск только dev/test |
| 28 | edge | Первый вариант с акцией и розницей 0 даёт `rrp: null` при цене у других | low | reject | `first_variant_ordering` ставит акционный активный вариант первым; розница 0 при акции из 1С не приходит; Always: «в списке — первого варианта, как сейчас» |
| 29 | edge, blind | `rrp_display` в админке выбирает вариант не так, как API; сортировка дублирует строки | low | reject | carried #12 и Review Findings [Defer] |
| 30 | blind | Приоритет «ррц» над «опт»/«тренер» опасен для имён вида «Опт 1 от РРЦ» | low | reject | Реализован по Always («всегда идёт в `retail_price`») и патчу повторного ревью; исправление — правка спеки |
| 31 | blind | `ElectricProductCard` выведет «0» при `rrp = 0` | false | reject | carried #18: `get_rrp` отдаёт `None` при рознице ≤ 0 |
| 32 | blind | Electric-хиты: оптовик видит розницу и как цену, и как РРЦ | low | reject | carried #19 |
| 33 | blind | Раскладка `compact` не выводит РРЦ | low | reject | carried: Review Findings [Defer], решение владельца — отдельная задача |
| 34 | blind | Вызывающие `ProductCard` держат свои списки `isB2B` и передают мёртвый `mode` | low | reject | Code Map: список `isB2B` для `mode` не трогать, `mode` оставлен в интерфейсе (`@deprecated`) |
| 35 | blind | Видимость РРЦ решают два списка (`INFO_PRICE_ROLES` и `isB2BRole`), admin получает поле, которое фронт прячет | low | reject | Never: не менять `INFO_PRICE_ROLES` |
| 36 | blind | Тест миграции откатывает схему к 0060 в каждом прогоне — необратимая будущая миграция его сломает | low | reject | Сейчас проходит; сценарий будущий, исправление — не прямая правка (политика удаления/маркер) |
| 37 | blind | Тест перемаппинга вызывает приватный маппер вместо разбора `priceLists`; E2E-проверка «РРЦ» ничего нового не ловит | low | reject | Разбор `priceLists` → маппер покрыт `test_parser_helpers`/`test_xml_parser`; E2E-проверка цен INTEX — патч повторного ревью |
| 38 | blind | Документы с `recommended_retail_price`; `import-process.md` не описывает правило «ррц» | low | reject | carried #20; в `import-process.md` нет ни «РРЦ», ни `rrp` — устаревшего текста нет |
| 39 | blind | `rrp` строкой в варианте и числом в списке; `parseFloat(rrp!)` прячет `null` | false | reject | Контракт сохранён по Always; `ProductInfo.tsx:178,180` гардят `rrp \|\| '0'` до `!`, тест `rrp = null` есть |
| 40 | graph-impact | `update_variant_prices` CRITICAL, `_map_price_type_to_field` HIGH, `ProductCard` HIGH | — | reject | Названы в спеке, несогласованных вызывающих нет, тесты есть |

### Review Findings

Повторное ревью `d28db408..f2b8b0f`, 20.11.2026. Все пять слоёв завершились; GitNexus не обнаружил новых циклов.

- [x] [Review][Patch] Исполнить правило приоритета РРЦ перед оптовыми и тренерским маркерами: «РРЦ Опт 1» сейчас маппится в `opt1_price`. Это подтверждённое отклонение от спецификации, но не подтверждённый случай в рабочей выгрузке. [backend/apps/products/services/parser.py:611]
- [x] [Review][Patch] Проверить переход `0060 → 0061` на исторической модели: удаление `RunPython` из последовательности не ломает нынешние тесты, поскольку те вызывают функцию напрямую и отдельно проверяют схему. [backend/apps/products/tests/unit/test_price_logic.py:305]
- [x] [Review][Patch] Проверить РРЦ двух вариантов с разной розницей: сейчас утверждение охватывает только `variants[0]`, поэтому подстановка цены первого варианта во все варианты останется незамеченной. [backend/tests/integration/test_catalog_price_visibility.py:416]
- [x] [Review][Patch] Проверить, что API списка при нулевой рознице возвращает `rrp: null`: нынешний тест обращается только к деталке. [backend/tests/integration/test_catalog_price_visibility.py:454]
- [x] [Review][Defer] При выкладке старый Celery может потерять письмо о заказе после удаления колонки до пересоздания воркеров. [.github/workflows/deploy.yml:450] — отложено ранее; порядок выкладки существовал до этой правки, риск подтверждён повторно.
- [x] [Review][Defer] Сортировка «РРЦ» в админке использует все цены вариантов, а ячейка показывает одну; проверка метода не ловит несовпадающий порядок. [backend/apps/products/admin.py:601] — прежняя сортировка по обратной связи сохранена по спецификации.
- [x] [Review][Defer] Положительная розница с копейками округляется до целых рублей в `ProductCard` и `ProductInfo`, вплоть до «0 ₽» при сумме меньше 50 копеек. [frontend/src/utils/pricing.ts:165] — форматирование существовало до изменения источника РРЦ.
- [x] [Review][Defer] В компактных карточках обычной главной (хиты, новинки, акции, распродажа) строка РРЦ не выводится. [frontend/src/components/business/ProductCard/ProductCard.tsx:352] — по решению владельца вынесено из текущего исправления в отдельную задачу.

Приёмка полного импорта 1С не подтверждена: ручной прогон с `priceLists` и `prices` не выполнялся. Приведённый полный прогон backend завершился с одной тайминговой ошибкой; отдельный повтор этого теста прошёл. В рамках повторного ревью тесты и импорт не запускались.

**Отклонено:**
- Пропуск цен до следующей загрузки `priceLists` — предусмотренный переход для старого маппинга; на проде таких маппингов не обнаружено, импорт пишет предупреждение.
- Два вида на `retail_price` — спецификация принимает риск для dev/test, при этом двойной маппинг в рабочей выгрузке не подтверждён.
- Отсутствие `currency` в тестовом словаре — ложное замечание: `VariantImportProcessor.process_price_types` принимает свой `PriceTypeData`, в котором нет `currency`.
- Формулировка «зелёное» для полного прогона — расходится с подробными результатами; предложенная правка касается только текста проверяемой спецификации.
- Отсутствие предупреждения о письмах в тексте выката — предложенная правка касается только текста проверяемой спецификации; сам риск уже подтверждён и отложен отдельно.
- Отсутствие РРЦ в каталоге и подборках Electric — по решению владельца не исправляется: Electric не работает, направление планируется полностью удалить из проекта.

### Review Findings — актуальное рабочее дерево

20.11.2026, база `d28db408`, рабочее дерево поверх `f2b8b0f`. Все пять слоёв завершились; новых циклов нет. Итог после решения владельца: 5 исправлений, 6 отложенных, 7 отклонённых.

- [x] [Review][Patch] В проверке полного импорта реальных `priceLists` и `prices` утверждать маппинг вида «РРЦ» и точную розничную цену конкретного SKU после импорта; статус успеха не ловит пропуск цены. [backend/tests/integration/test_onec_import.py:327–351]
- [x] [Review][Patch] Проверять обновление строки «РРЦ» при переключении варианта у оптовика; текущий интеграционный сценарий проверяет только основную цену под розничной ролью. [frontend/src/components/product/__tests__/ProductOptions.integration.test.tsx:410–422]
- [x] [Review][Patch] Проверять строку «РРЦ» для оптовика в обоих режимах каталога; тест отдельной карточки не ловит потерю `userRole` в вызывающем компоненте. [frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:1533–1556]
- [x] [Review][Patch] Покрыть `rrp: null` в карточке и деталке: тесты с `0` и `"0.00"` не ловят подстановку цены роли вместо отсутствующей РРЦ. [frontend/src/components/business/ProductCard/__tests__/ProductCard.test.tsx:394–399; frontend/src/components/product/__tests__/ProductInfo.test.tsx:495–504]
- [x] [Review][Patch] Начинать `try/finally` в фикстуре до отката схемы, чтобы восстановление запускалось и при сбое получения исторических моделей. [backend/apps/products/tests/unit/test_price_logic.py:338–357]
- [x] [Review][Defer] Не менять приоритет для «АКЦИЯ РРЦ»: парсер по-прежнему возвращает `promo_price`. [backend/apps/products/services/parser.py:599–616] — решение владельца: «В рабочей выгрузке такого названия нет и не будет».
- [x] [Review][Defer] Старый Celery может без повтора потерять письмо о заказе в окне между миграцией и заменой воркеров. [.github/workflows/deploy.yml:450–461] — отложено ранее; подтверждено повторно.
- [x] [Review][Defer] Сортировка в админке по всем вариантам не соответствует одной цене в ячейке и может дублировать товар. [backend/apps/products/admin.py:601–605] — прежняя сортировка сохранена намеренно.
- [x] [Review][Defer] Положительная цена меньше 50 копеек отображается как «0 ₽». [frontend/src/utils/pricing.ts:165–173] — прежнее форматирование.
- [x] [Review][Defer] Сгенерированные типы требуют ключ `rrp`, хотя API убирает его для ряда ролей. [frontend/src/types/api.generated.ts:2559,2721,2806] — та же рассинхронизация была в базовом коммите; совместимость контракта оставлена без изменений.
- [x] [Review][Defer] Пример теста МРЦ обращается к несуществующему `max_suggested_retail_price` вместо `msrp`. [docs/architecture/10-testing-strategy.md:290–292] — ошибка присутствовала до этой правки.

**Отклонено:**
- Откат восстанавливает схему, но не старые значения РРЦ — инструкция обещает совместимость старого образа, не восстановление удалённых данных; предложенное уточнение относится к тексту спецификации.
- Повторный `ADD COLUMN` неидемпотентен, если пропущена ручная очистка — уточнение относится к инструкции в этой спецификации, не к выполняемому коду.
- Миграция использует менеджер без `.using(...)` — в поддерживаемых настройках только база `default`; влияние на вторую базу не установлено.
- Два активных вида могут обновить одну цену в порядке XML — риск явно принят для dev/test и не подтверждён для рабочей выгрузки.
- Нераспознаваемое имя со старым ручным маппингом `rrp` останется без маппинга — на проде таких маппингов нет, а импорт ведёт журнал пропусков.
- Старый импорт после отката может вернуть маппинг `rrp`, а повторный выкат его не очистит — не подтверждён необходимый старый вид цен в рабочей выгрузке.
- Локальные XML для BGS322 содержат другие розничные суммы — это не дефект кода; пример с 2 530 ₽ не подтверждён на проде. Полный импорт и тесты в этом ревью не запускались.
