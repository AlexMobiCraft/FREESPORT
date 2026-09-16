---
title: 'Оформление страницы /unsubscribe в дизайн-системе сайта'
type: 'feature'
created: '2026-09-16'
baseline_commit: 'e4c54c91'
status: 'done'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Страница `/unsubscribe` лежит в `frontend/src/app/unsubscribe/` — вне route-группы `(blue)`, поэтому рендерится без шапки и подвала сайта и использует чужую палитру (slate/orange-классы вместо дизайн-токенов). Сообщение «Ссылка недействительна» оформлено голым текстом, не в стиле сайта.

**Approach:** Перенести маршрут в `frontend/src/app/(blue)/unsubscribe/` (route-группа не входит в URL — адрес `/unsubscribe` не изменится), чтобы страница получила `Header`/`Footer` через `(blue)/layout.tsx` → `LayoutWrapper`. Переоформить контент по образцу `/cart` (контейнер, Breadcrumb, заголовок, карточка) и состояние «Ссылка недействительна» — по образцу `EmptyCart` (иконка lucide + заголовок + пояснение + CTA «На главную»).

## Boundaries & Constraints

**Always:**
- URL `/unsubscribe` не меняется; middleware-обработчик (`pathname === '/unsubscribe'`, заголовки `Cache-Control: no-store`, `Referrer-Policy: no-referrer`) и проверка в `YandexMetrika` продолжают работать без правок.
- В `page.tsx` сохранить `export const dynamic = 'force-dynamic'`, `metadata` (title, description, robots noindex, referrer no-referrer).
- Страница НЕ рендерит собственный `<main>` — единственный landmark `<main>` выдаёт `LayoutWrapper` (см. spec-blue-nested-main-landmark).
- Стили — только дизайн-токены проекта: `max-w-[1280px] mx-auto px-4 lg:px-6 py-6`, `text-display-m`, `text-title-l`, `text-body-m`, `text-text-primary/secondary/inverse`, `bg-primary`, `hover:bg-primary-hover`, `bg-white rounded-[var(--radius-md)] shadow-[var(--shadow-default)]`, `rounded-[var(--radius-sm)]`. Никаких slate-*/orange-*-утилит.
- Сохранить a11y-поведение `UnsubscribeClient`: `role="status"`, `aria-live` (polite/assertive), `tabIndex={-1}` + перенос фокуса на результат, чтение токена из `location.hash` с немедленной очисткой fragment.
- Сохранить контракт состояний: checking → confirm → submitting → success/error; retryable для всех ошибок, кроме `invalid_token`.
- Кнопки — компонент `@/components/ui/Button` (primary для «Отписаться от рассылки», secondary для «Повторить»); CTA-ссылка «На главную» — `next/link` со стилями как у кнопки «В каталог» в `EmptyCart`.
- Комментарии и тексты UI — на русском.

**Ask First:**
- Любое изменение текстов сообщений (`ERROR_MESSAGES`, пояснений) или контракта токена.
- Изменение URL маршрута или middleware.

**Never:**
- Не трогать backend (`unsubscribeService`, API `/newsletter/unsubscribe/`), логику токена, middleware, `YandexMetrika`.
- Не дублировать `Header`/`Footer` локальным layout'ом в `unsubscribe/` — только перенос в `(blue)`.
- Не вводить собственный `<main>`, `<html>`, `<body>`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Валидный токен | `/unsubscribe#<43-символьный токен>` | Шапка+подвал, breadcrumb, карточка с подтверждением; fragment очищен | N/A |
| Подтверждение | Клик «Отписаться от рассылки» | Запрос отправлен → «Запрос на отписку обработан», фокус на результат | N/A |
| Невалидный/отсутствующий токен | `/unsubscribe` без hash или hash не по паттерну | Карточка в стиле EmptyCart: иконка, «Ссылка недействительна», пояснение, CTA «На главную»; API не вызывается | Кнопки «Повторить» нет |
| Retryable-ошибка API | throttled/network_error/server_error | Заголовок ошибки + пояснение + «Повторить» | Повторный submit |

</frozen-after-approval>

## Code Map

- `frontend/src/app/unsubscribe/page.tsx` — перенести в `(blue)/unsubscribe/`, переоформить
- `frontend/src/app/unsubscribe/UnsubscribeClient.tsx` — перенести, перевести на дизайн-токены
- `frontend/src/app/(blue)/layout.tsx` — источник Header/Footer (не менять)
- `frontend/src/components/layout/LayoutWrapper.tsx` — рендерит единственный `<main>` (не менять)
- `frontend/src/components/cart/EmptyCart.tsx` — образец error/empty-стейта
- `frontend/src/components/cart/CartPage.tsx` — образец контейнера + Breadcrumb + h1
- `frontend/src/components/ui/Button/Button.tsx` — варианты кнопок
- `frontend/src/app/__tests__/UnsubscribeClient.test.tsx` — обновить импорт/перенести рядом со страницей
- `frontend/src/middleware.ts` — `/unsubscribe` в KNOWN_TOP_LEVEL_ROUTES + no-store заголовки (контроль, не менять)

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/app/(blue)/unsubscribe/page.tsx` — `git mv` из `app/unsubscribe/`; разметка: контейнер `max-w-[1280px] mx-auto px-4 lg:px-6 py-6`, `Breadcrumb` («Главная» → «Отписка от рассылки»), `h1 text-display-m font-bold text-text-primary`, карточка `bg-white rounded-[var(--radius-md)] shadow-[var(--shadow-default)]` с `UnsubscribeClient` внутри — без `<main>`, сохранить metadata и `force-dynamic`
- [x] `frontend/src/app/(blue)/unsubscribe/UnsubscribeClient.tsx` — `git mv`; перевести все состояния на дизайн-токены; кнопки → `Button`; `invalid_token` — центрированный блок по образцу EmptyCart: иконка lucide (напр. `MailX`/`Link2Off`, `w-16 h-16 text-neutral-500`), заголовок `text-title-l font-semibold text-text-primary`, пояснение `text-body-m text-text-secondary`, `Link href="/"` со стилями CTA — перенос «внешности» без изменения логики состояний
- [x] `frontend/src/app/__tests__/UnsubscribeClient.test.tsx` — перенести в `app/(blue)/unsubscribe/__tests__/` и исправить импорт на `../UnsubscribeClient` (тесты рядом с компонентом по конвенции проекта)
- [ ] Проверка: `git status` не содержит потерянных файлов; `app/unsubscribe/` удалена целиком

**Acceptance Criteria:**
- Given открыт `/unsubscribe#<валидный токен>`, when страница отрендерилась, then видны Header и Footer сайта, breadcrumb «Главная / Отписка от рассылки», заголовок и карточка в дизайн-токенах; в DOM ровно один `<main>`
- Given `/unsubscribe` без валидного токена, when отрендерилось состояние invalid_token, then блок в стиле EmptyCart: иконка, «Ссылка недействительна», пояснение, ссылка «На главную»; API не вызывался
- Given любое состояние страницы, when проверены классы, then в разметке нет `slate-*`/`orange-*` утилит — только дизайн-токены
- Given существующий набор тестов `UnsubscribeClient`, when `npm run test`, then все тесты зелёные без изменения их логики

## Spec Change Log

## Design Notes

Ключевая идея: `(blue)` — route-группа, `(blue)/unsubscribe` продолжает отвечать на `/unsubscribe`, при этом специфичный маршрут побеждает catch-all `(blue)/[slug]`. `LayoutWrapper` применяет blue-шапку/подвал ко всем путям, кроме `/`, `/electric*` и `/electric-orange-test` — `/unsubscribe` попадает в общую ветку. Палитра primary сайта — `#ff6600` (orange), т.е. кнопки автоматически станут «фирменными».

## Verification

**Commands:**
- `cd frontend && npx vitest run "src/app/(blue)/unsubscribe" src/app/__tests__` — expected: все тесты UnsubscribeClient проходят
- `cd frontend && npx tsc --noEmit` — expected: без ошибок
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — expected: затронуты только unsubscribe-маршрут и его тест

**Manual checks (if no CLI):**
- `docker compose --env-file .env -f docker/docker-compose.yml restart frontend`, открыть `http://localhost:3000/unsubscribe` — шапка, подвал, карточка «Ссылка недействительна» с иконкой и кнопкой «На главную»

## Suggested Review Order

**Каркас страницы (route-группа → шапка/подвал)**

- Перенос в `(blue)` даёт Header/Footer через layout; контейнер и breadcrumb как на /cart.
  [`page.tsx:19`](../../frontend/src/app/(blue)/unsubscribe/page.tsx#L19)
- Секция-карточка в дизайн-токенах; свой `<main>` убран — его рендерит LayoutWrapper.
  [`page.tsx:30`](../../frontend/src/app/(blue)/unsubscribe/page.tsx#L30)

**Состояния клиента**

- Тупиковое состояние invalid_token по образцу EmptyCart: иконка, пояснение, CTA «На главную».
  [`UnsubscribeClient.tsx:119`](../../frontend/src/app/(blue)/unsubscribe/UnsubscribeClient.tsx#L119)
- Кнопки переведены на компонент `Button` (primary/secondary), все состояния — на дизайн-токены.
  [`UnsubscribeClient.tsx:75`](../../frontend/src/app/(blue)/unsubscribe/UnsubscribeClient.tsx#L75)

**Периферия**

- Новый тест CTA-ветки invalid_token (testid, href, отсутствие «Повторить»).
  [`UnsubscribeClient.test.tsx:54`](../../frontend/src/app/(blue)/unsubscribe/__tests__/UnsubscribeClient.test.tsx#L54)
- Smoke-тест страницы: breadcrumb, aria-связка, отсутствие `<main>`, metadata.
  [`page.test.tsx:22`](../../frontend/src/app/(blue)/unsubscribe/__tests__/page.test.tsx#L22)
