---
title: 'Собственные title, description и canonical у страниц брендов каталога'
type: 'feature'
created: '2026-10-01'
status: 'done'
baseline_commit: 'b102b0611ff26cfe0be364285608f26fe91fa380'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/tasks/intent-catalog-brand-seo-metadata.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Шесть ссылок блока брендов (`/catalog?brand=<slug>`, бренды с `is_featured`) отдают базовые title, description и canonical `/catalog`: `generateMetadata` каталога параметр `brand` не знает. Сканер аудита найдёт дубли title и description и «canonical на другой URL».

**Approach:** Ветка страницы бренда в `generateMetadata`: адрес с единственным параметром `brand`, чей slug есть в списке избранных брендов (`/brands/featured/`), получает свои title, description и self-canonical. Остальные адреса не меняются.

## Boundaries & Constraints

**Always:** Страница бренда — `/catalog` с единственным query-параметром `brand` (ключи `undefined` не считаются); значение — строка, непустая после `trim`, без запятой. Запрос к API — только для такой страницы и только один: `GET ${getApiUrl()}/brands/featured/`, slug в адрес запроса не подставляется. Бренд найден, если его slug (без приведения регистра) есть в ответе. Любой сбой → существующий `catch` → базовые metadata. Тексты (`<Название>` — `name` записи из ответа после `trim`):
- title: `Спортивные товары <Название> оптом | OPTISPORT`
- description: `Товары бренда <Название> в каталоге OPTISPORT: цены и условия заказа для оптовых покупателей, доставка по России.`
- `keywords: null`, картинка по умолчанию; canonical и `og:url` — `/catalog?brand=<slug>` через `URLSearchParams`.

**Ask First:** изменение текстов; бренды вне списка `/brands/featured/`.

**Never:** менять сигнатуру `buildMetadata` (HIGH, 41.13); трогать `CatalogPageClient.tsx`, `BrandsBlock.tsx`, `sitemap.ts`, `robots.ts`, `middleware.ts`, бэкенд; H1 бренда, серверную выдачу, sitemap, мультибренд, `Brand.description`; в текстах — розницу, «B2B», превосходные степени.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Бренд в списке | `?brand=boybo` или `?brand=%20boybo%20`; ответ `/brands/featured/`: `[{id, name:'BoyBo', slug:'boybo', image, website}, …]` (поля `is_featured` в ответе нет) | тексты выше; canonical и `og:url` `/catalog?brand=boybo`; один запрос к `/brands/featured/` | N/A |
| Нет в списке | slug отсутствует в ответе: неизвестный, не избранный, `BoyBo` в другом регистре | базовые metadata | N/A |
| Сбой API | таймаут, сеть, не-2xx (в т.ч. 404 сборки бэкенда без `/featured/`); тело — не массив (`null`, объект); у записи `name` пустой, `'   '`, нестроковый или отсутствует | базовые metadata | без исключения |
| Не страница бренда | `brand=a,b`; `brand=`; массив `brand`; `brand` + `page`/`ordering`/`is_new` | базовые metadata | запроса к `/brands/` нет |
| Бренд + категория | `?brand=boybo&category=<валидный slug>` | metadata категории, как до правки | запроса к `/brands/` нет |
| Спецсимволы | `brand=a/b`, `brand=a?b`, `brand=..`, `brand=.`, `brand=boybo%00` | базовые metadata | запрос тот же `/brands/featured/`, slug в нём нет |

</frozen-after-approval>

## Code Map

- `frontend/src/app/(blue)/catalog/page.tsx` -- `generateMetadata` (135-167); образцы: `findCatalogCollection` (95-102), `collectCategories` (104-124), `fetchCategories` (126-133: `revalidate: 3600`, таймаут 3000)
- `frontend/src/app/(blue)/catalog/__tests__/metadata.test.ts` -- тесты подборок и категорий; помощники `response()`, `metadataFor()`, `expectBaseMetadata()`
- `backend/apps/products/views.py:456` -- `BrandViewSet.featured`: плоский список (`pagination_class=None`), активные бренды с `is_featured` и картинкой, до 50 штук, кэш Django 1 ч; тот же список строит `BrandsBlock` на главной
- `backend/apps/products/serializers.py:357` -- `BrandFeaturedSerializer`: поля `id, name, slug, image, website`, **без `is_featured`**

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/app/(blue)/catalog/page.tsx` -- `findCatalogBrandSlug(params): string | null`; `fetchFeaturedBrands(): Promise<Map<string, string> | null>` (slug → name): `GET ${getApiUrl()}/brands/featured/`, `next: { revalidate: 3600 }`, таймаут 3000 мс; `null` при не-2xx и при теле, которое не массив; записи с нестроковым или пустым `slug`/`name` пропускаются, `slug` берётся как есть, `name` — после `trim`; ветка бренда после подборки и до категории -- бренд найден в `Map` → metadata бренда, иначе выполнение идёт дальше и даёт базовые metadata; сбои уходят в существующий `catch`; образцы -- `findCatalogCollection`, `collectCategories`, `fetchCategories`
- [x] `frontend/src/app/(blue)/catalog/__tests__/metadata.test.ts` -- сценарии матрицы; мок ответа `/brands/featured/` повторяет реальную форму (`id, name, slug, image, website`, без `is_featured`); проверить URL запроса (`http://backend:8000/api/v1/brands/featured/`) и `next: { revalidate: 3600 }`; на `/catalog`, подборках и категориях запросов к `/brands/featured/` нет; `brand=..`, `brand=.`, `brand=boybo\u0000`, `brand=a/b` -- запрос ровно к `/brands/featured/`, базовые metadata; тело `null`, объект и массив с мусорными записями -- базовые без исключения; тексты без `/рознич|розниц|B2B|Ведущ|Крупнейш/i`; description ≤ 160 при `name` до 40 символов -- закрепить поведение и отсутствие лишних запросов

**Acceptance Criteria:**
- Given `/catalog`, `?is_new=true`, `?category=turizm`, `?brand=intex`, `?brand=boybo&page=2`, when рендерится страница, then metadata как до правки.
- Given шесть адресов `?brand=<slug>` из `BrandsBlock`, when их запрашивает бот без cookie, then у каждого уникальные title и description и self-canonical.

## Design Notes

Description для BoyBo — 108 символов (в intent указано 109; на текст не влияет). В 160 символов он укладывается при `name` до 57: `Brand.name` допускает 100, но у featured-брендов имена короткие, усечение не вводим.

**Источник бренда — `/brands/featured/`, а не `/brands/<slug>/`.** Intent-файл описывает вариант с `retrieve` по slug; действует эта спека. Причины:
- Next кэширует только ответы 200 (`next/dist/server/lib/patch-fetch.js:611`). При запросе по slug ключ кэша зависел бы от адреса, а 404 не кэшировались бы: каждый случайный `?brand=…` доходил бы до бэкенда. Список — один ключ на все адреса, как дерево категорий.
- Slug не попадает в путь запроса. `encodeURIComponent` точки не экранирует, и `fetch` свёл бы `/brands/../` к корню API.
- Список содержит ровно бренды, на которые ведут ссылки `BrandsBlock`: он строится по `is_featured` и картинке. Поля `is_featured` в ответе нет, поэтому критерий — наличие slug в списке.

**Расхождение с клиентом у бренда без остатков.** Клиент канонизирует `brand` по другому списку — `/brands/?has_stock=true` (`CatalogPageClient.tsx:719`, `1075-1081`). У избранного бренда без остатков сервер отдаст metadata бренда и self-canonical, а клиент после гидрации уберёт `brand` из адреса, и title вернётся к базовому. Кодом это не закрываем: такой бренд администратор вручную снимает с главной (`is_featured`), ссылка из `BrandsBlock` пропадает вместе с ним. На 02.10.2026 все шесть избранных брендов есть в `/brands/?has_stock=true`. Меньше всего товаров у `eclectica`: 7 из 8 активных в наличии.

**Свежесть.** Кэш бэкенда (1 ч) и кэш Next (1 ч) складываются: новый избранный бренд получает свои metadata, а снятие флага возвращает базовые не позже чем через ~2 ч. Canonical у такого адреса при этом меняется.

**Трекинговые параметры.** Адрес `?brand=boybo&utm_source=…` (также `yclid`, `fbclid`) не считается страницей бренда: canonical у него `/catalog`, как у подборок с лишними параметрами.

**Self-canonical и серверный HTML.** В серверном HTML страницы бренда пока нет товаров (`fetchInitialProducts` пропускает `brand`). Поисковик может не принять self-canonical и выбрать `/catalog`. Тогда выигрыш получают сканер аудита и сниппет, а для поиска он появится после «Следующих шагов» №2 из intent-файла.

## Verification

**Commands:**
- `cd frontend; npx vitest run "src/app/(blue)/catalog"` -- expected: все тесты зелёные
- `cd frontend; npm run format:check; npm run lint; npx tsc --noEmit` -- expected: без ошибок
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` -- expected: затронуты только `generateMetadata` каталога и новые хелперы

**Manual checks (if no CLI):**
- После релиза: цикл `curl` из intent-файла по шести брендам, дважды (первый прогон идёт по холодному кэшу после деплоя) -- у каждого свой title, description и canonical.
- Уникальность на семи адресах (`/catalog` и шесть брендов) -- вывод пуст:

  ```bash
  for q in "" ?brand=boybo ?brand=cosmoride ?brand=eclectica ?brand=elous ?brand=espado ?brand=ingame; do
    curl -s -A "AuditikBot/1.0" "https://optisport.ru/catalog$q" \
      | grep -oE '<title>[^<]*</title>|<meta name="description"[^>]*>'
  done | sort | uniq -d
  ```

- В браузере: на `/catalog` отметить в сайдбаре один избранный бренд -- title вкладки меняется на брендовый; отметить второй бренд -- title возвращается к базовому. Это ожидаемое поведение, а не ошибка: при смене адреса Next заново вызывает `generateMetadata`, а `?brand=a,b` -- не страница бренда.

## Suggested Review Order

**Выбор метаданных: ветка бренда**

- Точка входа: ветка после подборки и до категории; нет в списке — идём дальше к базовым.
  [`page.tsx:195`](../../frontend/src/app/%28blue%29/catalog/page.tsx#L195)

- Страница бренда — единственный параметр `brand`: без запятой, не пустой после `trim`.
  [`page.tsx:113`](../../frontend/src/app/%28blue%29/catalog/page.tsx#L113)

**Источник бренда: список избранных**

- Один плоский запрос без slug в пути: общий ключ кэша, `..` не меняет адрес.
  [`page.tsx:174`](../../frontend/src/app/%28blue%29/catalog/page.tsx#L174)

- Разбор ответа: мусорные записи пропускаются, не массив — `null`, slug как есть.
  [`page.tsx:157`](../../frontend/src/app/%28blue%29/catalog/page.tsx#L157)

- Таймаут 3 с, как у дерева категорий и выдачи.
  [`page.tsx:13`](../../frontend/src/app/%28blue%29/catalog/page.tsx#L13)

**Тесты**

- Главный сценарий: тексты, self-canonical, ровно один запрос с `revalidate: 3600`.
  [`metadata.test.ts:285`](../../frontend/src/app/%28blue%29/catalog/__tests__/metadata.test.ts#L285)

- Шесть брендов дают уникальные title и description.
  [`metadata.test.ts:321`](../../frontend/src/app/%28blue%29/catalog/__tests__/metadata.test.ts#L321)

- Сбои API и невалидные тела — базовые metadata без исключения.
  [`metadata.test.ts:421`](../../frontend/src/app/%28blue%29/catalog/__tests__/metadata.test.ts#L421)

- Бренд вместе с категорией: metadata категории, запроса брендов нет.
  [`metadata.test.ts:491`](../../frontend/src/app/%28blue%29/catalog/__tests__/metadata.test.ts#L491)

- Спецсимволы в slug не попадают в адрес запроса.
  [`metadata.test.ts:530`](../../frontend/src/app/%28blue%29/catalog/__tests__/metadata.test.ts#L530)
