---
title: 'РРЦ на сайте = розничная цена из 1С; удаление поля ProductVariant.rrp'
type: 'bugfix'
created: '2026-11-20'
status: 'ready-for-dev'
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
- Не менять серверное определение роли по `sessionid` — это задача спеки `spec-product-page-ssr-jwt-auth.md`.
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
- `backend/apps/products/migrations/0061_remove_productvariant_rrp.py` — новая: RunPython `PriceType(product_field='rrp') → ''` (reverse — noop), `RemoveField`, `AlterField` выборов.
- `backend/apps/products/serializers.py:80-98` — `ProductVariantSerializer`: `rrp` в `Meta.fields` больше не из чего строить (иначе `ImproperlyConfigured`) — объявить `SerializerMethodField` с `@extend_schema_field` (строка Decimal, nullable): `f"{retail_price:.2f}"`, `None` при ≤ 0. Контракт `string | null` (`openapi.yaml:4924-4929`) сохраняется. `:530,667` — список: `get_rrp` → `float(variant.retail_price)`, `None` при ≤ 0. `to_representation` `:101-108`, `:645` не трогать.
- `backend/apps/products/services/parser.py:623-626` — «ррц» → `retail_price` без ветки «рекоменд».
- `backend/apps/products/services/variant_import.py:1992-1995` — удалить автозаполнение розницы из `rrp`.
- `backend/apps/products/admin.py:68,685,744` — убрать `rrp` из полей; `:602-606` `rrp_display` — как сейчас (выбор варианта и сортировка по обратной FK), но по `retail_price`: `ordering="variants__retail_price"`, подпись «РРЦ».
- `frontend/src/components/product/ProductInfo.tsx:73-83,186-197` — `canSeeRrp` → `isB2BRole(userRole)`.
- `frontend/src/components/business/ProductCard/ProductCard.tsx:531,665` — условие `isB2BRole(userRole)` без `mode === 'b2b'` (mode у админа `b2b`).
- `frontend/src/components/home/HitsSection.tsx:104-115,330` — `isB2B` для `rrp` → `isB2BRole(userRole)` (сейчас список включает `admin`); список `isB2B` для `mode` не трогать.
- `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` — описание `rrp`: «РРЦ = розничная цена варианта»; синхронизировать по рецепту `check_openapi_sync` (память `reference_backend_checks_in_container`).
- Тесты на удалённую логику — переписать или удалить: `apps/products/tests/unit/test_price_logic.py:52-97` (автозаполнение), `apps/products/tests/unit/test_parser_helpers.py:150`, `tests/unit/test_services/test_xml_parser.py:244` («рекоменд» → `rrp`). Остальные упоминания `rrp` (`git grep -wn rrp backend frontend/src`) — фикстуры, поправить.
- Документация: `docs/architecture/09-database-schema.md:161`, `docs/architecture/request-to-1c-developer.md:284`, `docs/architecture/10-testing-strategy.md` — убрать колонку `rrp`, РРЦ = `retail_price`.

## Tasks & Acceptance

**Execution:**
- [ ] `models.py`, `migrations/0061_*` — удалить поле и выбор, миграция данных PriceType — колонки нет, путаницы нет.
- [ ] `parser.py`, `variant_import.py` — «ррц» → `retail_price`, без автокопии — импорт не ссылается на удалённое поле.
- [ ] `serializers.py` — `rrp` из `retail_price` — фронт получает настоящую РРЦ без смены контракта.
- [ ] `admin.py` — колонка «РРЦ» из розницы, без поля `rrp`.
- [ ] `ProductInfo.tsx`, `ProductCard.tsx`, `HitsSection.tsx` — видимость по `isB2BRole`.
- [ ] `openapi.yaml`, `api.generated.ts` — синхронизировать.
- [ ] Тесты: строки матрицы в `ProductInfo.test.tsx`, `ProductCard.test.tsx`; сериализатор деталки и списка — `rrp == retail_price` для B2B, `None` при рознице 0, нет поля для гостя и federation_rep; парсер — «РРЦ» и «Рекомендованная розничная цена» → `retail_price`; миграция — вид `rrp` получает `''`. Поправить фикстуры остальных тестов.

**Acceptance Criteria:**
- Given оптовик 1 и BGS322 (Опт 1 < 2530), when он открывает карточку, then под ценой «РРЦ: 2 530 ₽».
- Given администратор или менеджер, when он открывает карточку или каталог, then строки «РРЦ» нет.
- Given миграции применены, when `\d product_variants`, then колонки `rrp` нет; полный импорт 1С проходит без ошибок.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar apps/products tests/integration tests/unit` — зелёное.
- `cd frontend && npx vitest run src/components/product src/components/business/ProductCard src/components/home && npm run format:check && npm run lint && npx tsc --noEmit` — без ошибок.
- `backend-lint`, `makemigrations --check` — чисто.

**Manual checks:**
- Локально `migrate`, затем `\d product_variants` — колонки `rrp` нет; импорт по навыку `import-1c` (полный, с `priceLists` и `prices`) — без ошибок, у вариантов `retail_price` = РРЦ из 1С.

## Implementation Notes

## Spec Change Log

## Review Triage Log
