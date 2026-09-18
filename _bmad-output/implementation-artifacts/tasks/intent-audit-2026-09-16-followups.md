# Intent: хвосты третьего аудита optisport.ru — контент для исправлений

**Источник:** проверка закрытия отчёта 16.09.2026, выполнена 18.09.2026 — `tmp/audit-2026-09-16-verification-2026-09-18.md`.
**Эпик:** `_bmad-output/planning-artifacts/epic-41-site-audit.md`. Решения D1–D8 — `sprint-change-proposal-2026-09-16.md`.
**Проверено:** по коду `develop` = `372b3efb` и HTTP-запросами к проду 18.09.2026.
**Назначение:** готовые тексты, координаты и план правок для `bmad-create-story` / `bmad-quick-dev`. Код этим документом не меняется. Перед правкой любого символа — `npx gitnexus impact <symbol> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` (CLAUDE.md).

| # | Что | Где исполнять | Нужны решения владельца |
|---|---|---|---|
| A | `example` в production bundle (zustand `devtools`) | Открытый `[Review][Patch]` стори 41.20 | Нет, решение 18.09 уже есть |
| B | Приёмка 41.18 в браузере | Task 8.7 стори 41.18 | Тестовый аккаунт |
| C | Розница и превосходные степени в метаданных `/home`, `/coming-soon`, `/electric` | Новая стори эпика 41 (S) | Да — R1, R2 |
| D | Двойной тег robots на 404 | Та же стори, что C, или quick-dev (XS) | Нет |
| E | Трекер: влить переоткрытие 41.20 в `develop` | Git | Нет |

---

## A. `example` в production bundle — стори 41.20

**Факт (прод 18.09).** В общем чанке `3688-912aa751a9ddbcb4.js` есть строка `…and value of this only key should be a state object. Example: { "type": "__setState", "state": { "abc123Store": …`. Это текст ошибки middleware `devtools` из `zustand` 4.5.7 (`node_modules/zustand/esm/middleware.mjs`).

**Причина.** `devtools` из `zustand/middleware` безусловно оборачивает четыре стора, поэтому попадает в production-сборку:

| Стор | Строка | Имя |
|---|---|---|
| `src/stores/authStore.ts` | 11, 43 | `AuthStore` |
| `src/stores/cartStore.ts` | 12, 55 (снаружи `persist`) | `CartStore` |
| `src/stores/favoritesStore.ts` | 2, 22 | `FavoritesStore` |
| `src/stores/orderStore.ts` | 12, 34 | `OrderStore` |

Помимо строки `Example`, в production `devtools` отдаёт состояние `AuthStore` (включая `accessToken` и `user`) расширению Redux DevTools в браузере пользователя. Токен при этом свой, а не чужой, но это ещё один довод убрать `devtools` из production.

**Правка.** Одна обёртка, которая в production превращается в тождественную функцию. Webpack вычисляет условие с `process.env.NODE_ENV` на этапе сборки и отбрасывает мёртвую ветку, экспорт `devtools` становится неиспользуемым, а `zustand` объявляет `"sideEffects": false`. Поэтому код middleware должен выпасть из чанка, а `persist` в `cartStore` останется.

```ts
// src/stores/devtoolsInDev.ts
import { devtools } from 'zustand/middleware';

/**
 * `devtools` только вне production. В production-сборке ветка вырезается вместе
 * с кодом middleware zustand: в bundle не попадает подсказка `Example: {…}`
 * (срабатывание 168-ФЗ, стори 41.20), а состояние сторов не уходит в Redux DevTools.
 */
export const devtoolsInDev: typeof devtools =
  process.env.NODE_ENV === 'production'
    ? ((initializer => initializer) as typeof devtools)
    : devtools;
```

В четырёх сторах `import { devtools } from 'zustand/middleware'` заменить на `import { devtoolsInDev } from './devtoolsInDev'`, а вызов `devtools(` — на `devtoolsInDev(`. В `cartStore` импорт `persist` из `zustand/middleware` остаётся. Сигнатуры сторов не меняются: тип `typeof devtools` сохраняет мутатор `['zustand/devtools', never]`.

**Проверки.**
1. `impact` по `useAuthStore`, `useCartStore`, `useFavoritesStore`, `useOrderStore` до правки.
2. Поиск обращений к API devtools у сторов: `grep -rn "\.devtools\b" frontend/src`. Ожидается пусто. Если найдётся, в production оно получит `undefined`.
3. `npm run build`, затем `grep -rli example .next/static/chunks` — должно быть пусто, без учёта регистра и по всем чанкам, а не только по пяти страницам. **Если строка осталась** (tree-shaking не сработал), запасной вариант — `next.config.ts` → `webpack: (config, { dev }) => { if (!dev) config.resolve.alias['zustand/middleware$'] = <локальный модуль, реэкспортирующий только persist>; }`. Решать это только после неудачного п. 3, не заранее.
4. `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run format:check`.
5. Прод после выката: повторить fail-closed проверку шага 8.10 стори 41.20 без учёта регистра на `/home`, `/register`, `/b2b-register`, `/password-reset`, `/electric`.

**Приёмка.** Закрывает `[Review][Patch]` «Третье ревью 18.09.2026» стори 41.20. После этого стори возвращается в `done`, а в запись E21 реестра 41.16 дописывается строка о прод-приёмке.

---

## B. Приёмка 41.18 в браузере — Task 8.7

Часть через `curl` выполнена проверкой 18.09: 307, `Set-Cookie`, отсутствие `noindex` и `/login?next=`. Результаты перенести в стори. Осталось выполнить в браузере без cookie с тестовым аккаунтом владельца:

| # | Сценарий | Ожидание |
|---|---|---|
| 1 | Шапка → «Избранное» → вход | После входа `/profile/favorites`, cookie `loginReturnTo` удалена |
| 2 | Подвал → «Личный кабинет» → вход | После входа `/profile` |
| 3 | Корзина с товаром → `/checkout` → «Войти» → вход | После входа `/checkout` |
| 4 | Старая ссылка `/login?next=%2Fprofile%2Forders` → вход | После входа `/profile/orders` (приоритет URL над cookie) |
| 5 | `/login?next=https://evil.example` → вход | После входа `/` (open-redirect 41.12) |
| 6 | Сценарий 1, но вход позже чем через 10 минут | После входа `/` (cookie истекла) |

После прохождения — статус `done` в стори и `sprint-status.yaml`.

---

## C. Розница и превосходные степени в метаданных — новая стори

**Проблема.** Тексты расходятся с решениями D2 и D7: розничная регистрация отключена, гость заказ не оформляет, обещать розничные условия нельзя. «Крупнейший», «ведущих», «Ведущая» — превосходная степень без подтверждения (38-ФЗ ст. 5 ч. 3 п. 1). «Платформа» и «B2B» — формулировки, которые D7 уже убрал из корня.

**Решения владельца, нужны до create-story:**

- **R1.** Розничная регистрация отключена временно, розничный сайт впереди (флаг `REGISTRATION_ALLOW_RETAIL`). Убирать розницу из метаданных сейчас, по аналогии с D2 и D7? Рекомендация: **да**. Метаданные описывают текущее предложение сайта. При включении розницы тексты вернутся вместе с флагом.
- **R2.** Тема `/electric` закрыта `Disallow`, из синей темы на неё ссылок нет, но она открыта публично. Что с ней делать: (а) исправить только метаданные — рекомендация, минимальная правка; (б) отдавать 404 на проде, как демо-маршруты D6. Вариант (б) шире: `/electric/*` — отдельная тема с каталогом, решать её судьбу стоит отдельно.

**Тексты (при R1 = да).** Длины посчитаны.

| Адрес / файл | Поле | Было | Стало |
|---|---|---|---|
| `/home` — `app/(blue)/home/page.tsx:8` | title | Спортивные товары оптом и в розницу | **Спортивные товары оптом — каталог и условия \| OPTISPORT** (55) |
| `/home` — `:10` | description | Платформа для оптовых и розничных продаж спортивных товаров. Широкий ассортимент, выгодные условия для бизнеса. | **Оптовые поставки спортивных товаров для магазинов, спортивных клубов и федераций: каталог, цены для оптовых покупателей, доставка по России.** (140) |
| `/home` — `:11` | keywords | спортивные товары оптом, спортивные товары в розницу, спортивная экипировка | **удалить поле** (как D7: поисковики meta keywords не используют) |
| `/coming-soon` — `app/(coming-soon)/coming-soon/page.tsx:13` | description | OPTISPORT — оптовые и розничные продажи спортивных товаров. Сайт скоро откроется, … | **OPTISPORT — оптовые продажи спортивных товаров. Сайт скоро откроется, по вопросам сотрудничества пишите на info@optisport.ru.** (125) |
| `/coming-soon` — `app/ComingSoonClient.tsx:55-57` | текст карточки | Платформа для оптовых и розничных `<br />` продаж спортивных товаров | **Оптовые продажи `<br />` спортивных товаров** |
| `/electric` — `app/(electric)/electric/page.tsx:43-67` | вся `metadata` | title «OPTISPORT - Спортивные товары оптом и в розницу»; description «Крупнейший интернет-магазин… Более 10 000 товаров от ведущих брендов. Выгодные цены для B2B клиентов.»; keywords с «B2B спорттовары»; `openGraph.url` = корень; twitter «Более 10 000 товаров от ведущих брендов» | Заменить на `buildMetadata({ title: 'OPTISPORT — спортивные товары оптом', description: 'Оптовые продажи спортивных товаров: каталог, условия для оптовых покупателей, доставка по России.', path: '/electric' })` — тексты корневого умолчания D7 (35 / 97). Keywords нет, canonical и `og:url` — `/electric`, превосходных степеней и «B2B» нет |

Title `/home` отличается от корневого «OPTISPORT — спортивные товары оптом», поэтому дубля с `/register` и другими страницами на корневом умолчании не будет.

**Не менять:** `components/home/AboutTeaser.tsx:20` («…для розничных магазинов, спортивных клубов и федераций»). Розничные магазины — оптовые клиенты, это корректно. Description `/catalog` «Оптовые и рекомендованные розничные цены» тоже не трогать: это решение D2.

**Тесты, которые изменятся:**
- `app/(blue)/home/__tests__/page.test.tsx:153-185` — title, description, `openGraph`, `twitter` под новые тексты. Добавить отрицательную проверку: в title, description и social-полях нет `/рознич|розниц|Платформа|B2B|Ведущ|Крупнейш/i`, `keywords` отсутствует.
- `app/(coming-soon)/coming-soon/__tests__/page.test.tsx` — description; та же отрицательная проверка.
- `app/__tests__/ComingSoonClient.test.tsx` — текст карточки, если он там проверяется.
- `/electric` — новый тест метаданных по образцу корневого (41.19).

**AC (черновик для create-story):**

**Given** страницы `/home`, `/coming-soon`, `/electric`
**When** строятся метаданные (title, description, Open Graph, Twitter)
**Then** тексты равны таблице выше, `keywords` нет
**And** ни в одном поле нет «рознич…», «розниц…», «Платформа», «B2B», «Ведущ…», «Крупнейш…», «10 000»

**Given** карточка `/coming-soon`
**When** она отображается
**Then** текст — «Оптовые продажи спортивных товаров»

**Given** выкат на прод (NFR-41-08)
**When** `curl -A "AuditikBot/1.0"` снимает `/home`, `/coming-soon`, `/electric`
**Then** метаданные совпадают с AC, снимок приложен к стори

---

## D. Двойной тег robots на 404

**Факт (прод 18.09).** `/nonexistent-xyz` и `/catalog/zzz` отвечают 404 и несут два тега:

```html
<meta name="robots" content="noindex"/>
<meta name="robots" content="noindex, nofollow"/>
```

**Причина.** Первый тег Next 15.5.18 добавляет сам к любому ответу со статусом 404 (`next/dist/server/app-render/app-render.js:160-164`, условие `is404Page || isInvalidStatusCode`). Второй идёт из `robots: { index: false, follow: false }` в `app/not-found.tsx:8`.

**Правка.** Удалить `robots` из `metadata` в `app/not-found.tsx`. Title «Страница не найдена | OPTISPORT» оставить.

**Условие безопасности.** `not-found.tsx` рендерится и там, где статус **не** 404: `notFound()` после начала стриминга отдаёт 200, это ограничение Next 15.5.18, см. комментарий в `app/(blue)/[slug]/page.tsx:61, 81`. Для таких адресов `[slug]`, `product/[slug]` и других `noindex` ставит их собственная `generateMetadata` (`[slug]/page.tsx:66`, прод `/product/zzz-none` → `noindex, follow`), а не `not-found.tsx`. До правки подтвердить это `grep` по всем вызовам `notFound()`: у каждой динамической страницы, которая может вызвать `notFound()` при статусе 200, должен быть свой условный `noindex`.

**Тест.** Интеграционный или e2e-снимок настоящего 404 (механизм 41.0): ровно один `<meta name="robots">` и он содержит `noindex`.

**Приоритет.** Низкий, косметика: оба тега запрещают индексацию. Можно исполнить вместе с C.

---

## E. Трекер

- Коммит `d64d4909` (стори 41.20 → `in-progress`, открытый `[Review][Patch]`) есть только в ветке `docs/story-41-20-reopen`. В `develop` стори 41.20 числится `done`. Влить его через PR до начала работы по A.
- После A и B: 41.18 и 41.20 → `done`. Стори для C и D добавить в `epic-41-site-audit.md` и `sprint-status.yaml` после решений R1/R2.
- Повторный прогон сканера — после выката A и C. На `/coming-soon` ведёт `/`, поэтому именно с неё сканер начинает обход, и C повлияет на отчёт.
