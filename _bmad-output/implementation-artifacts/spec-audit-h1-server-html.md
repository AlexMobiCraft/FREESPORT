---
title: 'H1 в серверном HTML для /home, /cart и каталога'
type: 'bugfix'
created: '2026-09-29'
status: 'done'
baseline_commit: 'da84b18869ab78d684634394184cbbad80140bd4'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/tasks/intent-audit-2026-09-28-h1.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Сканер аудита (28.09.2026) читает серверный HTML, а в нём у `/home`, `/cart` и 15 адресов каталога H1 нет или он пуст: `HeroSection` и `CartSkeleton` рендерят заглушки без заголовка, в H1 каталога стоит `Skeleton`, пока клиент грузит дерево категорий.

**Approach:** Внешний вид не меняется. Главная получает визуально скрытый H1 в `HomePage` (заголовки баннеров становятся H2); заглушка корзины рендерит настоящий H1; каталог получает начальный текст H1 с сервера через пропс `initialHeading`. Построчные ссылки и точные строки — в файле интента из `context`.

## Boundaries & Constraints

**Always:**
- На каждой странице ровно один H1 — и в серверном HTML, и после гидратации.
- H1 главной: «OPTISPORT — спортивные товары оптом» (как корневой title, `app/layout.tsx:22`). H1 корзины: «Ваша корзина», те же классы, что в `CartPage.tsx:67`.
- Заголовок каталога не показывает промежуточный текст между серверным и итоговым (ни скелетон, ни «Каталог», ни пустую строку): серверный текст держится до синхронизации подписи категории с адресом, затем сбрасывается навсегда. После сброса использовать его нельзя — при выборе категории в сайдбаре мелькнёт старая.
- Slug сверять без `trim`; при повторяющемся `category` брать первое значение, пустой `category` — как его отсутствие.
- Заголовок вычисляется и там, где `fetchInitialProducts` выдачу пропускает (клиентская навигация, `refreshToken`).
- Дерево категорий грузится один раз за рендер и делится между выдачей и заголовком; загрузки идут параллельно. Существующие тесты `page.test.tsx` считают вызовы `fetch` и проходят без правки.
- Перед правкой символа — `npx gitnexus impact <символ> --direction upstream -r "C:\Users\1\DEV\FREESPORT"`; собранный blast radius — LOW везде.

**Ask First:** `impact` вернул HIGH/CRITICAL; для цели нужно менять видимый текст, класс или вёрстку сверх описанного.

**Never:** менять дизайн главной и корзины, `ElectricHeroSection` и `/electric`, `generateMetadata`, метаданные и canonical, остальные 13 адресов отчёта; коммитить `.env*`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Без категории | `/catalog`, `?is_new=true`, `?category=` | `initialHeading` = «Каталог», дерево не запрашивается | N/A |
| Категория найдена | `?category=<slug>`, slug есть в дереве | `name` категории из дерева | N/A |
| Slug не найден | `?category=no-such-slug` | «Каталог» (как у клиента после загрузки дерева) | N/A |
| Дерево недоступно | не 2xx, таймаут, битый JSON | `null`: H1 показывает `Skeleton`, как раньше | Исключение не выходит из страницы |
| Повторяющийся параметр | `?category=a&category=b` | по первому значению | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/app/(blue)/catalog/page.tsx` -- `fetchCategories`, `fetchInitialProducts`, страница: сюда заголовок и пропс
- `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx` -- H1 (:1546), эффекты синхронизации категории (:687, :748), `urlActiveCategoryId` (:554), обёртка `CatalogPage` (:1839) → `CatalogContent` (:371)
- `frontend/src/components/home/HomePage.tsx`, `HeroSection.tsx` -- `<h1>` баннеров в ветках :158 и :205
- `frontend/src/components/cart/CartSkeleton.tsx` -- «Title skeleton» (:82); рендерится из `CartPage.tsx:44,49`

## Tasks & Acceptance

**Execution:**
- [x] `components/home/HomePage.tsx` -- первым в контейнере `<h1 className="sr-only">` с текстом главной -- H1 есть, пока герой показывает заглушку
- [x] `components/home/HeroSection.tsx` -- `<h1>` → `<h2>` в двух ветках, классы прежние -- иначе после баннеров два H1
- [x] `components/cart/CartSkeleton.tsx` -- скелетон заголовка заменить на `<h1>` -- H1 во всех состояниях корзины, вёрстка не прыгает
- [x] `app/(blue)/catalog/CatalogPageClient.tsx` -- `initialHeading?: string | null` через `CatalogPage` в `CatalogContent`; H1 по правилам «Always» -- без мерцания
- [x] `app/(blue)/catalog/page.tsx` -- вычисление заголовка по матрице, общая загрузка дерева, пропс `initialHeading` -- H1 с текстом в серверном HTML
- [x] Тесты рядом с кодом (`__tests__`): `HomePage` (один H1 при заглушке), `HeroSection` (H2 в fallback и API, H1 нет), `CartSkeleton` (H1), `CatalogPage` (`initialHeading` «Туризм»/«Каталог» без скелетона; последовательность текстов H1 по коммитам через `Profiler` при загрузке дерева без «Каталог» и пустой строки; сохранённый тест со скелетоном :420), `page.test.tsx` (строки матрицы, заголовок при пропущенной выдаче, одна загрузка дерева)

**Acceptance Criteria:**
- Given серверный HTML `/home`, `/cart`, `/catalog`, `?category=<slug>`, `?is_new=true`, `?category=no-such-slug`, when считать `<h1`, then он один и с непустым текстом.
- Given страница после гидратации и загрузки данных, when считать H1, then он один, вёрстка главной и корзины не изменилась, H1 каталога — как раньше.
- Given `/catalog?category=<slug>` с серверным текстом, when клиент загружает дерево, then H1 остаётся названием категории, в консоли нет предупреждений гидратации.

## Design Notes

Каскад на клиенте: дерево и `isCategoriesLoading=false` приходят одним коммитом, `activeCategoryId` ставит эффект :687, подпись — эффект :748. Между ними H1 сейчас равен «Каталог», затем пустой строке; скелетон это прикрывал. Схема:

```
serverHeading     = useState(initialHeading ?? null)
serverHeadingSlug = useState(categorySlugParam)   // адрес при монтировании
held = categorySlugParam === serverHeadingSlug ? serverHeading : null   // смена адреса — текст чужой
// сброс, когда адрес сменился ИЛИ (!isCategoriesLoading && activeCategoryId === urlActiveCategoryId
//        && (activeCategoryId === null || activeCategoryLabel))
H1 = held ?? (isCategoriesLoading ? <Skeleton/> : activeCategoryId !== null ? label : 'Каталог')
```

Пропс `initialHeading` после монтирования не читается, поэтому чужой текст отсекает сравнение slug: и в рендере (без этого на один коммит мелькнула бы чужая категория), и в эффекте (сброс).

## Verification

**Commands** (из `frontend/`):
- `npm run format:check; npm run lint; npx tsc --noEmit; npm test` -- expected: все четыре гейта проходят
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` -- expected: только `HomePage`, `HeroSection`, `CartSkeleton`, `CatalogContent`, `CatalogPage`, `page.tsx` и тесты

**Manual checks:**
- Серверный HTML: цикл `curl` из интента по шести адресам, ожидание — везде `1` и непустой текст. Docker Desktop не запущен (на 29.09.2026): поднять его либо использовать стенд `next start` с проксированием к API прода.
- В браузере на `/home`, `/cart`, `/catalog?category=…`: нет предупреждений гидратации, заголовок каталога не мигает.

## Suggested Review Order

**Серверный заголовок каталога** (точка входа)

- Страница грузит дерево один раз и делит между выдачей и заголовком, параллельно.
  [`page.tsx:259`](../../frontend/src/app/(blue)/catalog/page.tsx#L259)

- Выбор текста по матрице: без категории, найдена, не найдена, сбой дерева.
  [`page.tsx:242`](../../frontend/src/app/(blue)/catalog/page.tsx#L242)

- Единый способ читать параметр, как клиент: первое значение, без `trim`.
  [`page.tsx:69`](../../frontend/src/app/(blue)/catalog/page.tsx#L69)

**Клиент каталога: серверный текст без мерцания**

- Новый пропс: до загрузки дерева H1 показывает текст сервера, а не скелетон.
  [`CatalogPageClient.tsx:373`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L373)

- Состояние стартует с серверного текста; slug адреса при монтировании защищает от чужой категории.
  [`CatalogPageClient.tsx:406`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L406)

- Удержание и необратимый сброс: каскад эффектов не должен показать «Каталог» или пустоту.
  [`CatalogPageClient.tsx:778`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L778)

- H1 берёт удерживаемый текст первым, скелетон остаётся запасным.
  [`CatalogPageClient.tsx:1586`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L1586)

**Главная и корзина**

- Скрытый H1 страницы: заголовок баннера меняется и до загрузки его нет.
  [`HomePage.tsx:53`](../../frontend/src/components/home/HomePage.tsx#L53)

- Заголовки баннеров стали H2: иначе после загрузки на странице два H1.
  [`HeroSection.tsx:158`](../../frontend/src/components/home/HeroSection.tsx#L158)
  [`HeroSection.tsx:205`](../../frontend/src/components/home/HeroSection.tsx#L205)

- Заглушка корзины несёт настоящий H1: на сервере корзина всегда в ней.
  [`CartSkeleton.tsx:83`](../../frontend/src/components/cart/CartSkeleton.tsx#L83)

**Тесты**

- Текст H1 на каждом коммите React: ловит мерцание, проверено мутацией.
  [`CatalogPage.test.tsx:2351`](../../frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx#L2351)

- Смена адреса до загрузки дерева: чужая категория не мелькает даже на кадр.
  [`CatalogPage.test.tsx:2404`](../../frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx#L2404)

- Блок клиентских тестов заголовка: сброс, ошибка дерева, выбор в сайдбаре.
  [`CatalogPage.test.tsx:2281`](../../frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx#L2281)

- Матрица серверного заголовка и пропущенная выдача.
  [`page.test.tsx:183`](../../frontend/src/app/(blue)/catalog/__tests__/page.test.tsx#L183)

- Одна загрузка дерева на рендер: без общего загрузчика краснеют три теста.
  [`page.test.tsx:263`](../../frontend/src/app/(blue)/catalog/__tests__/page.test.tsx#L263)

- Главная, герой и корзина: один H1 и H1 в `renderToString`.
  [`HomePage.test.tsx:77`](../../frontend/src/components/home/__tests__/HomePage.test.tsx#L77)
  [`HeroSection.test.tsx:416`](../../frontend/src/components/home/__tests__/HeroSection.test.tsx#L416)
  [`CartSkeleton.test.tsx:84`](../../frontend/src/components/cart/__tests__/CartSkeleton.test.tsx#L84)
