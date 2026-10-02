---
title: 'Карточка товара: бренд-заглушка в title/JSON-LD и HTML-теги в описании'
type: 'bugfix'
created: '2026-10-02'
status: 'done'
baseline_commit: '6a146a471ccb6b2f72e8341fa5753db9ea779ece'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/tasks/intent-audit-2026-10-02-product-cards-and-minor.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** На карточке товара бренд-заглушка импорта попадает в title («Мяч футбольный гибридный №4 - Без ТМ | OPTISPORT», 97 товаров) и в JSON-LD `brand`. Описание из 1С с `<br>` (21 товар) и `\n` выводится как сырой текст: покупатель видит буквальный «<br>», переводы строк схлопываются, теги уходят в `meta`/`og:description` и JSON-LD.

**Approach:** Фронтенд-only. Общий хелпер распознаёт бренд-заглушку по slug/имени: для неё title без « - бренд», а в JSON-LD нет `brand`. Описание переводится в простой текст одной функцией: видимый блок сохраняет переводы строк, а meta, og и JSON-LD получают текст со схлопнутыми пробелами. Meta и og обрезаются до 160 символов по границе слова. Пункт А1 интента (служебная пометка BB300) — правка данных в 1С/админке, кода не требует.

## Boundaries & Constraints

**Always:** список slug-заглушек `bez-tm`, `bez-brenda`, `no-brand` — в одном месте. Заглушкой считаются и имя, пустое после `trim`, и имя `-`. Для настоящего бренда title не меняется: `«<название> - <бренд> | OPTISPORT»`. Описание рендерится только как текст.

**Ask First:** если для простого текста понадобится менять бэкенд, импорт или сериализатор.

**Never:** `dangerouslySetInnerHTML` для описания (из 1С оно приходит без санитайзера). Не трогать видимую подпись бренда (`ProductInfo.tsx`), бэкенд, импорт 1С и данные в БД. Не добавлять многоточие при обрезке и не вводить запасной meta description для товаров без описания (это вне задачи).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Бренд-заглушка | brand `Без ТМ`/slug `bez-tm` (также `no-brand`, `bez-brenda`) | title `Мяч №4 \| OPTISPORT`; в JSON-LD нет ключа `brand` | N/A |
| Пустой бренд | `brand: null` → `''`; имя `'  '` или `-` | как у заглушки | N/A |
| Настоящий бренд | `BoyBo`/`boybo` | title `<название> - BoyBo \| OPTISPORT`, `brand` в JSON-LD есть | N/A |
| `<br>` в описании | `А<br>Б<br/>В<br />Г</p>Д` | видимо: строки А…Д; meta: `А Б В Г Д` | N/A |
| Теги и сущности | `<b>x</b> &amp; &lt;y&gt; &quot;z&quot; &#39;q&#39;&nbsp;w` | `x & <y> "z" 'q' w` — теги удалены, сущности декодированы | N/A |
| Знак «меньше» в тексте | `размер < 5 и > 3` | текст не теряется (тегом считается только `<` + буква, `/` или `!`) | N/A |
| Длинное описание | > 160 символов | meta/og ≤ 160, обрезаны на пробеле, слово не разорвано; JSON-LD — полный текст | одно слово > 160 символов → жёсткая обрезка |
| Пустой результат | `''` или `<br><br>` | видимый блок «Описание» не выводится; JSON-LD без `description`; meta — `''`, как сейчас | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/app/(blue)/product/[slug]/page.tsx` -- `generateMetadata`: шаблон title (стр. 37), description/ogDescription (стр. 38–39)
- `frontend/src/components/product/ProductPageClient.tsx` -- JSON-LD `Product` (стр. 83–123), `.replaceAll('<', '\\u003c')` сохранить
- `frontend/src/components/product/ProductSummary.tsx` -- видимый блок «Описание» (стр. 472–476)
- `frontend/src/services/productsService.ts` -- `ApiProductDetailResponse.brand` уже содержит `slug`; `adaptProductToDetail` (стр. 122) его отбрасывает
- `frontend/src/types/api.ts` -- `ProductDetail` (стр. 361)
- `frontend/src/utils/htmlContent.ts` -- рядом с `extractBodyContent`; тесты в `utils/__tests__/htmlContent.test.ts`
- `frontend/src/components/product/__tests__/ProductPageClient.jsonld.test.tsx` -- ожидает `parsed.description === product.description` с `</script>`-нагрузкой

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/types/api.ts` -- `brand_slug?: string` в `ProductDetail` -- slug нужен для распознавания заглушки
- [x] `frontend/src/services/productsService.ts` -- `brand_slug: apiProduct.brand?.slug || ''` в `adaptProductToDetail` -- адаптер пересобирает объект вручную
- [x] `frontend/src/utils/brand.ts` (новый) + `utils/__tests__/brand.test.ts` -- `PLACEHOLDER_BRAND_SLUGS`, `isPlaceholderBrand(name, slug?)` -- единый список
- [x] `frontend/src/utils/htmlContent.ts` + тесты -- `htmlToPlainText(html)` (переводы строк сохранены, лишние пустые строки и пробелы по краям строк убраны), `toMetaDescription(text, max = 160)` (пробелы схлопнуты, обрезка по слову) -- одна точка преобразования
- [x] `frontend/src/app/(blue)/product/[slug]/page.tsx` + `__tests__/page.test.tsx` -- title через `isPlaceholderBrand`; description и ogDescription через `toMetaDescription(htmlToPlainText(...))`; тесты `generateMetadata` по матрице
- [x] `frontend/src/components/product/ProductPageClient.tsx` + jsonld-тест -- `description` = схлопнутый простой текст или ключ отсутствует; `brand` только для настоящего бренда; в тесте поправить ожидание `description`, добавить кейсы заглушки и `<br>`
- [x] `frontend/src/components/product/ProductSummary.tsx` + новый тест -- выводить `htmlToPlainText(description)` в элементе с `whitespace-pre-line`; блок только при непустом результате

**Acceptance Criteria:**
- Given товар с брендом `Без ТМ`, when страница отрендерена на сервере, then `<title>` = `<название> | OPTISPORT`, а в JSON-LD нет строки «Без ТМ».
- Given описание с `<br>`, when страница отрендерена, then в HTML нет `&lt;br&gt;`, а `meta description` не содержит `<`, не длиннее 160 символов и не обрывается посреди слова.
- Given существующий тест на `</script>` в названии, when тесты прогнаны, then JSON-LD по-прежнему не закрывает `<script>`.

## Design Notes

Удалять теги регэкспом `/<(?:\/?[a-zA-Z][^>]*|!--[\s\S]*?--)>/g` (по ТЗ это не санитайзер: результат выводится как текст, а React его экранирует). Порядок: `<br…>`, `</p>` и `</div>` → `\n`; удалить остальные теги; декодировать сущности, `&amp;` последним, чтобы `&amp;lt;` дал `&lt;`, а не `<`. Обрезка по слову: `text.slice(0, max)` → обрезать до последнего пробела, если он есть, затем `trimEnd`.

## Verification

**Commands:**
- `cd frontend; npx vitest run src/utils src/components/product "src/app/(blue)/product" src/services` -- expected: зелёные
- `cd frontend; npm run format:check; npm run lint; npx tsc --noEmit` -- expected: без ошибок и предупреждений

**Manual checks:**
- `curl -s http://localhost:3000/product/kovrik-dlja-jogi-espado-nbr-1836110-sm-zelenyj-es2123-110` (если локальная БД содержит товар) -- нет `&lt;br&gt;`, title/JSON-LD без «Без ТМ» у товаров с заглушкой.

## Suggested Review Order

**Бренд-заглушка**

- Единый список заглушек: slug и имя, «Без ТМ» узнаётся даже при другом slug.
  [`brand.ts:25`](../../frontend/src/utils/brand.ts#L25)

- Title без « - бренд» для заглушки; настоящий бренд — по-старому, с trim.
  [`page.tsx:40`](../../frontend/src/app/(blue)/product/[slug]/page.tsx#L40)

- JSON-LD: `brand: undefined` выбрасывается из JSON для заглушки.
  [`ProductPageClient.tsx:98`](../../frontend/src/components/product/ProductPageClient.tsx#L98)

- Адаптер протаскивает slug бренда, который раньше отбрасывал.
  [`productsService.ts:123`](../../frontend/src/services/productsService.ts#L123)

**Описание из 1С как простой текст**

- Точка преобразования: script/style с содержимым, блоки → строка, теги прочь, сущности.
  [`htmlContent.ts:77`](../../frontend/src/utils/htmlContent.ts#L77)

- Цепочка блочных тегов даёт один перевод строки, а не пустые строки.
  [`htmlContent.ts:20`](../../frontend/src/utils/htmlContent.ts#L20)

- Сущности в один проход: `&amp;lt;` не превращается в `<`.
  [`htmlContent.ts:57`](../../frontend/src/utils/htmlContent.ts#L57)

- Обрезка meta по границе слова, без висящих знаков и половин суррогатов.
  [`htmlContent.ts:116`](../../frontend/src/utils/htmlContent.ts#L116)

- meta/og: схлопнутый текст ≤ 160 символов.
  [`page.tsx:38`](../../frontend/src/app/(blue)/product/[slug]/page.tsx#L38)

- JSON-LD: полный текст; защита `<` → `<` осталась последним рубежом.
  [`ProductPageClient.tsx:95`](../../frontend/src/components/product/ProductPageClient.tsx#L95)

- Видимый блок: текст с `whitespace-pre-line`, без `dangerouslySetInnerHTML`.
  [`ProductSummary.tsx:145`](../../frontend/src/components/product/ProductSummary.tsx#L145)

**Тесты и типы**

- `generateMetadata`: заглушки, имя при чужом slug, точная обрезка, og/twitter.
  [`page.test.tsx:262`](../../frontend/src/app/(blue)/product/[slug]/__tests__/page.test.tsx#L262)

- Страховка: `</script>` из сущностей описания экранирован в JSON-LD.
  [`ProductPageClient.jsonld.test.tsx:100`](../../frontend/src/components/product/__tests__/ProductPageClient.jsonld.test.tsx#L100)

- Разметка из 1С: списки, `<br clear>`, таблицы, style, сущности.
  [`htmlContent.test.ts:67`](../../frontend/src/utils/__tests__/htmlContent.test.ts#L67)

- Адаптер: slug бренда и `brand: null`.
  [`productsService.test.ts:147`](../../frontend/src/services/__tests__/productsService.test.ts#L147)

- Поле `brand_slug` в типе и фикстуре MSW.
  [`api.ts:370`](../../frontend/src/types/api.ts#L370)
