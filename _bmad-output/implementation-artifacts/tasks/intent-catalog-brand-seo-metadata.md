# Intent: собственные title, description и canonical у страниц брендов каталога

**Источник:** полный обход сайта 01.10.2026 — `tmp/audit-2026-09-28-full-site-check-2026-10-01.md`, находка Б2.
**Проверено:** по коду `develop` = `ebed0202` и серверному HTML прода 01.10.2026 (`User-Agent: AuditikBot/1.0`, без cookie), API `/api/v1/brands/`.
**Исполнитель:** `bmad-quick-dev`. Тип — SEO-доработка, фронтенд, размер S. Решения, принятые в задании, перечислены в разделе «Решения»; владелец может их поменять до старта.
**Вне задачи:** H1 страницы бренда (сейчас «Каталог»); серверная первая страница выдачи по бренду; страницы брендов в `sitemap.xml`; мультибренд `?brand=a,b`; описание бренда из админки. Всё это — в разделе «Следующие шаги».
**Редакция 02.10.2026:** источник бренда — список `/brands/featured/`, а не `/brands/<slug>/` (см. «Решения» 1–3 и «Правки»). Обоснование — в «Design Notes» спеки `spec-catalog-brand-seo-metadata.md`; при расхождении действует спека.

## Проблема

Блок брендов на главной (`components/business/home/BrandsBlock/BrandsBlock.tsx:69`) ссылается на `/catalog?brand=<slug>` — по ссылке на каждый бренд с `is_featured=true`. Сейчас их шесть: `boybo`, `cosmoride`, `eclectica`, `elous`, `espado`, `ingame`.

`generateMetadata` каталога (`app/(blue)/catalog/page.tsx:135-170`) параметр `brand` не знает и отдаёт таким адресам базовые метаданные `/catalog`. Прод 01.10.2026:

| Адрес | title | canonical |
|---|---|---|
| `/catalog` | Каталог спортивных товаров \| OPTISPORT | `/catalog` |
| `/catalog?brand=boybo` (и ещё пять) | Каталог спортивных товаров \| OPTISPORT | `/catalog` |

Description у всех семи тоже одинаковый.

Сканер аудита начинает обход с `/home` и не учитывает canonical у дублей (память «Audit scanner behavior»). Шесть ссылок дадут в следующем прогоне три замечания разом: «Дубли title», «Дубли description» и «Canonical на другой URL». Это тот же механизм, что у категорий `basseyny-plyazh-aksessuary` и `suvenirnaya-produktsiya` в отчёте 28.09.

Страница бренда — отдельная посадочная страница со своим составом товаров, а не технический дубль каталога. Поэтому ей нужны свои метаданные, как подборкам (41.17, 41.22) и категориям (41.13).

## Решения

1. **Страница бренда** — адрес `/catalog`, у которого единственный query-параметр `brand`. Его значение после `trim` непустое, без запятой и совпадает со slug бренда из списка `/brands/featured/`. Распознавание строится по образцу `findCatalogCollection` (`page.tsx:95-102`): ключи со значением `undefined` не считаются, повторяющийся параметр (массив) — не страница бренда.
2. **Только избранные бренды.** На эти бренды есть ссылки (`BrandsBlock`), и набор управляется флагом `is_featured` в админке. Критерий — наличие slug в списке `/brands/featured/`: его же берёт блок на главной (активные бренды с `is_featured` и картинкой, до 50), поля `is_featured` в ответе нет. Остальные бренды (`intex`, `ruscosport`, `wips`, `titan`, …) попадают в адрес только через фильтр в сайдбаре — это `router` без ссылок, сканер и поисковик их не найдут. Так же отсекаются заглушки `bez-tm` («Без ТМ»), `bez-brenda`, `no-brand`, и в коде не появляется ещё один список технических значений (см. `deferred-work.md` про дублирование таких списков).
3. **Тексты** — только для оптовых покупателей, без розницы, превосходных степеней и «B2B» (D2, D7):
   - title: `Спортивные товары <Название> оптом | OPTISPORT` — для BoyBo 41 символ;
   - description: `Товары бренда <Название> в каталоге OPTISPORT: цены и условия заказа для оптовых покупателей, доставка по России.` — для BoyBo 109 символов;
   - `<Название>` — поле `name` записи списка `/brands/featured/`, после `trim`, как есть;
   - `keywords: null`, картинка — по умолчанию (`DEFAULT_OG_IMAGE_META`), как у подборок.
4. **Canonical и `og:url` — собственный адрес** `/catalog?brand=<slug>`. Строится через `URLSearchParams`, как у категории (`page.tsx:155-156`). Так сделано у подборок в 41.22 и у категорий в 41.13.
5. **Все прочие комбинации — без изменений.** Базовые метаданные и canonical `/catalog`: `brand` + любой другой параметр (`page`, `ordering`, `is_new`, `in_stock`…), два бренда через запятую, пустой `brand`, бренд вне списка избранных, неизвестный slug, ошибка или таймаут API. Мультибренд и сочетания с фильтрами — технические варианты, их канон — `/catalog`. Исключение — `brand` + валидная `category`: как и сейчас, метаданные категории (ветка категории срабатывает при любых других параметрах, `page.tsx:147`).

## Правки

Перед правкой — `npx gitnexus impact generateMetadata --direction upstream -r "C:\Users\1\DEV\FREESPORT"` (AGENTS.md, раздел GitNexus) и сообщить blast radius. Имя `generateMetadata` неоднозначно: оно есть у многих страниц. Если impact вернёт `ambiguous`, взять узел из `app/(blue)/catalog/page.tsx` через `npx gitnexus context generateMetadata --file "frontend/src/app/(blue)/catalog/page.tsx" -r "C:\Users\1\DEV\FREESPORT"`. Сигнатуру `buildMetadata` не менять (HIGH, 41.13).

**`frontend/src/app/(blue)/catalog/page.tsx`:**

- `findCatalogBrandSlug(params): string | null` — распознавание по решению 1, рядом с `findCatalogCollection`.
- `fetchFeaturedBrands(): Promise<Map<string, string> | null>` (slug → name) — `GET ${getApiUrl()}/brands/featured/` с `next: { revalidate: 3600 }` и `AbortSignal.timeout(3000)`, как `fetchCategories`; результат собирается по образцу `collectCategories`. Эндпоинт отдаёт плоский список (на проде 02.10.2026 — шесть записей с полями `id, name, slug, image, website`, без `is_featured`). `null` — при не-2xx и при теле, которое не массив; записи с нестроковым или пустым `slug`/`name` пропускаются, `name` берётся после `trim`. Slug из адреса в путь запроса не попадает: ключ кэша один на все адреса брендов, а 404 на случайных slug до бэкенда не доходят (Next кэширует только ответы 200).
- В `generateMetadata` ветка бренда — после проверки подборки и до ветки категории. Бренд не найден в списке — выполнение идёт дальше и даёт базовые metadata. Любой сбой ведёт в существующий `catch` → `buildCatalogMetadata()`.
- Запрос к API только при распознанной странице бренда: на `/catalog`, подборках и категориях лишних запросов быть не должно.
- `CatalogPageClient.tsx`, `BrandsBlock.tsx`, `sitemap.ts`, `robots.ts`, `middleware.ts`, бэкенд не трогать.

**`frontend/src/app/(blue)/catalog/__tests__/metadata.test.ts`** — сценарии по образцу 41.17 и 41.22, `fetch` замокан:

| Вход | Ожидание |
|---|---|
| `?brand=boybo`, API `/brands/featured/`: `[{ id, name: 'BoyBo', slug: 'boybo', image, website }]` (без `is_featured`, как на проде) | title, description по решению 3; canonical и `openGraph.url` = `/catalog?brand=boybo`; `keywords: null`; один запрос на `http://backend:8000/api/v1/brands/featured/` с `next: { revalidate: 3600 }` |
| `?brand=%20boybo%20` | то же, slug после `trim` |
| `?brand=intex`, slug нет в списке | базовые метаданные, canonical `/catalog` |
| `?brand=BoyBo` (другой регистр) | базовые: slug сравнивается как есть |
| `/brands/featured/` отвечает 404 (сборка бэкенда без эндпоинта) или другим не-2xx | базовые |
| API — таймаут или сетевая ошибка | базовые, без исключения |
| у записи списка `name: '   '`, нестроковый или без `name` | базовые |
| тело ответа `null`, объект или массив с мусорными записями | базовые, без исключения |
| `?brand=boybo,espado` | базовые, запроса к API нет |
| `?brand=` | базовые, запроса нет |
| `?brand=boybo&page=2`, `&ordering=…`, `&is_new=true` | базовые, запроса к `/brands/` нет |
| `?brand=boybo&category=<валидный slug>` | метаданные категории, как до правки; запроса к `/brands/` нет |
| повторяющийся `brand` (массив) | базовые |
| slug со спецсимволами (`a/b`, `a?b`, `..`, `.`, `boybo\u0000`) | базовые; запрос ровно к `/brands/featured/`, slug в его адресе нет |
| `/catalog`, подборки, категории | ожидания существующих тестов не меняются, запросов к `/brands/featured/` нет |

Отрицательная проверка на тексты бренда: нет `/рознич|розниц|B2B|Ведущ|Крупнейш/i`. Description не длиннее 160 символов при `name` до 40 символов.

## Критерии приёмки

- Шесть адресов из `BrandsBlock` отдают в серверном HTML уникальный title, уникальный description и self-canonical. Проверка после релиза — дважды, первый прогон идёт по холодному кэшу после деплоя:

  ```bash
  for b in boybo cosmoride eclectica elous espado ingame; do
    curl -s -A "AuditikBot/1.0" "https://optisport.ru/catalog?brand=$b" \
      | grep -oE '<title>[^<]*</title>|<link rel="canonical"[^>]*>|<meta name="description"[^>]*>'
  done
  ```

  Уникальность на семи адресах (`/catalog` и шесть брендов) — вывод пуст:

  ```bash
  for q in "" ?brand=boybo ?brand=cosmoride ?brand=eclectica ?brand=elous ?brand=espado ?brand=ingame; do
    curl -s -A "AuditikBot/1.0" "https://optisport.ru/catalog$q" \
      | grep -oE '<title>[^<]*</title>|<meta name="description"[^>]*>'
  done | sort | uniq -d
  ```

- В браузере: на `/catalog` отметить в сайдбаре один избранный бренд — title вкладки меняется на брендовый; отметить второй — возвращается к базовому.

- `/catalog`, `/catalog?is_new=true`, `/catalog?category=turizm`, `/catalog?brand=intex`, `/catalog?brand=boybo&page=2` — метаданные как до правки.
- `npm run format:check`, `npm run lint`, `npx tsc --noEmit`, `npx vitest run "src/app/(blue)/catalog"` — зелёные.
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` перед коммитом: затронут только `generateMetadata` каталога и новые хелперы.

## Следующие шаги (не в этой задаче)

1. **H1 страницы бренда.** Сейчас на всех страницах брендов H1 «Каталог», и с title он не совпадает. Если менять, то вместе на сервере (`resolveInitialHeading`) и на клиенте (`CatalogPageClient`); при этом надо решить, что показывать при выборе бренда чекбоксом в сайдбаре.
2. **Серверная выдача по бренду.** `fetchInitialProducts` пропускает адреса с `brand` (`page.tsx:197`): в серверном HTML страницы бренда нет ни одного товара. Без этого добавлять бренды в `sitemap.xml` рано — поисковик получит пустую посадочную страницу. После этого — sitemap по образцу подборок 41.22 (только бренды с товарами в наличии).
3. **Описание бренда из админки** (`Brand.description`, сейчас пустое у всех 14) как источник description — после решения владельца о текстах.
