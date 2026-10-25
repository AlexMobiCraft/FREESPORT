---
title: 'D14-2: JSON-LD называет ролевую цену, а не розницу, до выбора варианта'
type: 'bugfix'
created: '2026-10-25'
status: 'done'
baseline_commit: 'cca91588'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Пока вариант не выбран (товар с опциями до автовыбора: SSR и первый рендер; товар без вариантов, `variants: []`), `offers.price` в JSON-LD без акции берёт `product.price.retail`, а `ProductInfo` показывает `getPriceForRole`. Оптовику разметка называет розницу (1200), хотя на экране 700. Ветка есть с baseline `78c7dde` (D11-1, D12-2, D13-2, D14-2).

**Approach:** Один источник суммы для экрана и разметки: чистая функция в `utils/pricing.ts` с логикой текущего `displayedPrice` из `ProductInfo`. `ProductInfo` и `ProductPageClient` вызывают её: первый — со своим `selectedVariant`, второй — с `offerVariant`.

## Boundaries & Constraints

**Always:** экранная цена не меняется ни в одном сценарии; акция действует для всех ролей, как сейчас; без варианта и без акции — `getPriceForRole(product.price ?? {retail: 0, currency: 'RUB'}, userRole)`; выбор варианта для разметки по-прежнему `selectedVariant ?? findDefaultVariant(...)`; комментарии на русском.

**Ask First:** любое изменение того, что видит покупатель; правки backend, сериализаторов цен или `getPriceForRole`.

**Never:** не трогать `availability` в JSON-LD и автовыбор варианта в `ProductSummary`; не дублировать формулу в двух компонентах; не править OpenAPI и типы API.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Без вариантов, оптовик | `variants: []`, `promo_price: null`, `price {retail 1200, wholesale.level1 700}`, роль `wholesale_level1` | экран и `offers.price` = 700 (SSR и после монтирования) | N/A |
| С опциями до автовыбора, оптовик | варианты с `size_value`, без акции, та же цена, SSR | в HTML 700 и `offers.price` = 700 | N/A |
| Гость / краулер | роль `guest`, без акции | розница 1200, как раньше | N/A |
| Акция без варианта | `promo_price 800`, `current_price 800` | 800 для любой роли, как раньше | `current_price` пуст → `promo_price` |
| Выбран вариант | `variant.current_price = '700.00'` | 700 | пустой `current_price` варианта → ветки акции/роли (как в `ProductInfo`), а не `NaN` |
| Нет `price` у товара | `price` отсутствует, без акции и варианта | 0 | дефолт `{retail: 0}` |

</frozen-after-approval>

## Code Map

- `frontend/src/utils/pricing.ts` -- `getPriceForRole`; сюда новая функция видимой цены товара.
- `frontend/src/components/product/ProductInfo.tsx:27-44` -- `displayedPrice`: эталонная логика, переносится в функцию.
- `frontend/src/components/product/ProductPageClient.tsx:56-65` -- `offerPrice` с веткой `product.price?.retail`.
- `frontend/src/components/product/ProductSummary.tsx` -- `findDefaultVariant`, автовыбор; не меняется.
- `frontend/src/utils/__tests__/pricing.test.ts` -- юнит-тесты цен.
- `frontend/src/components/product/__tests__/ProductPageClient.jsonld.test.tsx` -- JSON-LD, блок «цена в offers при акции».
- `frontend/src/components/product/__tests__/ProductOptions.integration.test.tsx:503-635` -- R72/R73 на настоящих компонентах.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/utils/pricing.ts` -- добавить `getProductDisplayPrice(product, userRole, variant)`: источник акции `variant ?? product`; вариант с непустым `current_price` → его цена; иначе акция → `product.current_price || promo`; иначе `getPriceForRole` с дефолтом цены -- единый источник для экрана и разметки.
- [x] `frontend/src/components/product/ProductInfo.tsx` -- `displayedPrice` через новую функцию, остальное без изменений -- экран остаётся как был.
- [x] `frontend/src/components/product/ProductPageClient.tsx` -- `offerPrice = getProductDisplayPrice(product, userRole, offerVariant)`, обновить комментарий -- закрывает оба пути D14-2.
- [x] `frontend/src/utils/__tests__/pricing.test.ts` -- юнит-тесты строк матрицы.
- [x] `frontend/src/components/product/__tests__/ProductPageClient.jsonld.test.tsx` -- оптовик, `variants: []`, без акции: `offers.price` 700 в SSR и после `render`.
- [x] `frontend/src/components/product/__tests__/ProductOptions.integration.test.tsx` -- оптовик, товар с размерами без акции: SSR-HTML показывает 700 и `offers.price` 700.
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- пометить D14-2 (и повторы D13-2, D12-2, D11-1) закрытыми со ссылкой на спеку.

**Acceptance Criteria:**
- Given новые регрессии, when их прогоняют на коде до правки, then хотя бы одна падает с `offers.price` = 1200.
- Given существующие тесты `ProductInfo`, `ProductPageClient.jsonld` и `ProductOptions.integration`, when прогон после правки, then все зелёные без изменения ожиданий.

## Design Notes

Функция принимает `Pick<ProductDetail, 'price' | 'current_price' | 'promo_price'>` и `Pick<ProductVariant, 'current_price' | 'promo_price'> | null`, чтобы не тянуть лишнее. Поведение при выбранном варианте с пустым `current_price` берётся из `ProductInfo` (эталон экрана). В `ProductPageClient` раньше получался `NaN` → `null` в JSON, теперь будет та же сумма, что на экране.

## Verification

**Commands:**
- `cd frontend; npx vitest run src/utils/__tests__/pricing.test.ts src/components/product` -- expected: все зелёные.
- `cd frontend; npm run format:check; npm run lint; npx tsc --noEmit` -- expected: без ошибок.

## Suggested Review Order

**Единый источник видимой цены**

- Вход: функция с логикой бывшего `displayedPrice`, ветка без варианта и акции — по роли.
  [`pricing.ts:78`](../../frontend/src/utils/pricing.ts#L78)

- Та самая ветка, где раньше разметка брала `retail`.
  [`pricing.ts:90`](../../frontend/src/utils/pricing.ts#L90)

- Разметка зовёт ту же функцию с вариантом по умолчанию.
  [`ProductPageClient.tsx:61`](../../frontend/src/components/product/ProductPageClient.tsx#L61)

- Экран переведён на функцию без изменения поведения.
  [`ProductInfo.tsx:43`](../../frontend/src/components/product/ProductInfo.tsx#L43)

**Тесты**

- Юнит-тесты строк матрицы.
  [`pricing.test.ts:134`](../../frontend/src/utils/__tests__/pricing.test.ts#L134)

- Товар без вариантов, оптовик: SSR и после монтирования.
  [`ProductPageClient.jsonld.test.tsx:158`](../../frontend/src/components/product/__tests__/ProductPageClient.jsonld.test.tsx#L158)

- Товар с опциями до автовыбора, SSR на настоящих компонентах.
  [`ProductOptions.integration.test.tsx:609`](../../frontend/src/components/product/__tests__/ProductOptions.integration.test.tsx#L609)
