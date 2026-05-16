# Story 35.4: Cookie-баннер (уведомление об использовании cookie)

**Epic:** 35 — Соответствие 152-ФЗ о персональных данных
**Story ID:** 35.4
**Status:** done
**Priority:** Medium (завершает compliance-пакет 152-ФЗ; не блокирует другие истории)

---

## Story

Как посетитель сайта FREESPORT,
я хочу при первом визите видеть уведомление об использовании сайтом cookie со ссылкой на Политику обработки персональных данных,
чтобы быть информированным об обработке моих данных и подтвердить ознакомление одним кликом (требование 152-ФЗ).

Как владелец сайта,
я хочу, чтобы факт показа уведомления о cookie фиксировался на стороне браузера пользователя,
чтобы баннер не возникал при каждом переходе по страницам и не мешал UX после принятия.

---

## Контекст и решения

### Решения по scope (зафиксированы 2026-05-15)

1. **Тип баннера — информационный**, а не интерактивный (Accept/Reject). Текст в духе «Продолжая использовать сайт, вы соглашаетесь с использованием cookie», одна кнопка «Принять». Это стандартная практика реализации 152-ФЗ в РФ: cookie-уведомление носит **информационный** характер, не GDPR-style гранулярное согласие.
2. **Story — чисто frontend.** Backend **не затрагивается**: модель `UserConsent` (`backend/apps/common/models.py`) имеет только `CONSENT_TYPE_CHOICES = ["pdp_contract", "marketing_email"]` и расширять её под cookie **не нужно**. Факт принятия хранится в `localStorage` браузера. Никаких миграций, serializer'ов, API-endpoint'ов, view.
3. **Отличие от историй 35.2/35.3.** Те фиксировали согласия в `UserConsent` с IP/User-Agent (юридически значимые согласия в формах). Cookie-уведомление — информационное, аудиторский след в БД не требуется.

### Текущее состояние кодовой базы (проверено)

- **Cookie-баннера в проекте нет.** Поиск `Cookie` по `frontend/src` находит только auth-cookie (JWT) — `api-client.ts`, `middleware.ts`, `authStore.ts`. Готовых UI-компонентов баннера нет — реализуется с нуля.
- **Страница `/privacy-policy` существует** (`frontend/src/app/(blue)/privacy-policy/page.tsx`, Story 35.1, `done`). Ссылка из баннера ведёт на неё.
- **Root layout** `frontend/src/app/layout.tsx` — Server Component, рендерит `<html><body>{children}</body></html>`. Это единственный layout, оборачивающий ВСЕ route-группы (`(blue)`, `(electric)`, `(coming-soon)`). Cookie-баннер монтируется здесь, чтобы показываться на всём сайте.
- **`(blue)/layout.tsx`** оборачивает контент в `<Providers>` (Zustand/React Query). Cookie-баннеру провайдеры **не нужны** — монтируем в root layout, а не в `(blue)`.
- **Паттерн `localStorage` + SSR-safety** уже отработан в `frontend/src/hooks/useSearchHistory.ts`: состояние читается из `localStorage` в `useEffect` после монтирования, флаг `isLoaded` предотвращает запись до первой загрузки. Этот же паттерн используем здесь — он решает hydration mismatch.

---

## Acceptance Criteria

### AC-1: Hook `useCookieConsent` — управление состоянием в localStorage

**Given** новый hook `frontend/src/hooks/useCookieConsent.ts`,
**When** он вызывается из клиентского компонента,
**Then** он возвращает объект `{ isAccepted: boolean; isLoaded: boolean; accept: () => void }`:

- При монтировании в `useEffect` читает `localStorage.getItem("cookie_consent_accepted")`.
- `isLoaded` — `false` до завершения чтения из `localStorage`, затем `true`. Нужен, чтобы баннер **не рендерился во время SSR и до гидрации** (иначе hydration mismatch + мелькание).
- `isAccepted` — `true`, если в `localStorage` лежит значение `"1"`; иначе `false`.
- `accept()` — записывает `localStorage.setItem("cookie_consent_accepted", "1")` и выставляет `isAccepted = true`.
- Все обращения к `localStorage` обёрнуты в проверку `typeof window !== "undefined"` и `try/catch` (Safari private mode / отключённый storage бросает исключение — баннер не должен ронять страницу).

**Константы модуля:** `STORAGE_KEY = "cookie_consent_accepted"`, `STORAGE_VALUE = "1"`.

---

### AC-2: Компонент `CookieConsentBanner` — рендер и поведение

**Given** новый клиентский компонент `frontend/src/components/layout/CookieConsentBanner.tsx` (директива `'use client'` обязательна — использует hook с `useState`/`useEffect`),
**When** компонент монтируется,
**Then**:

- Пока `isLoaded === false` — рендерит `null` (ничего не показывает до чтения `localStorage`).
- Если `isLoaded === true && isAccepted === true` — рендерит `null` (пользователь уже принял).
- Если `isLoaded === true && isAccepted === false` — рендерит баннер.

**Given** баннер отрендерен,
**When** пользователь нажимает кнопку «Принять»,
**Then** вызывается `accept()` → `localStorage` обновляется → баннер исчезает (`isAccepted` стало `true`).

**Given** пользователь принял cookie и перезагрузил/сменил страницу,
**When** любая страница рендерится,
**Then** баннер больше не появляется (значение читается из `localStorage`).

---

### AC-3: Содержимое и вёрстка баннера

**Given** баннер отрендерен,
**Then** он содержит:

- **Текст:** «Мы используем файлы cookie, чтобы сайт работал корректно. Продолжая пользоваться сайтом, вы соглашаетесь с обработкой файлов cookie и пользовательских данных.»
- **Ссылку** на `/privacy-policy` с текстом «Политика обработки персональных данных», открывается в новой вкладке (`target="_blank" rel="noopener noreferrer"`). Использовать `<Link>` из `next/link`.
- **Кнопку «Принять»** — компонент `Button` (`@/components/ui`, `variant="primary"`, `size="small"` или `"medium"`).

**Вёрстка:**
- Баннер — `position: fixed`, прижат к низу окна (`bottom-0 left-0 right-0`).
- `z-index` — `z-40` (ниже модальных окон/Drawer, которые используют более высокий слой; выше обычного контента).
- Фон — `bg-white` с верхней границей `border-t border-neutral-200` и тенью (`shadow-lg` или существующий токен тени).
- Контейнер контента — `container mx-auto px-4 py-3 sm:py-4`.
- Layout: текст + кнопка. Mobile-first — на мобильных вертикальный стек (`flex-col`), на `sm:` и выше — горизонтально (`sm:flex-row sm:items-center sm:justify-between`), кнопка не сжимается (`shrink-0`).
- Цвета текста — токены проекта: `text-text-primary` / `text-text-secondary` (как на странице `/privacy-policy`). Размер текста — `text-sm`.

---

### AC-4: Монтирование баннера глобально

**Given** root layout `frontend/src/app/layout.tsx`,
**When** в него добавляется `<CookieConsentBanner />`,
**Then**:

- Компонент рендерится **после** `{children}` внутри `<body>`.
- Баннер появляется на всех страницах всех route-групп (`(blue)`, `(electric)`, `(coming-soon)`).
- Root layout остаётся Server Component — он лишь рендерит клиентский компонент как потомка (директива `'use client'` живёт в `CookieConsentBanner.tsx`, не в layout). **Не** добавлять `'use client'` в `layout.tsx`.

---

### AC-5: Доступность (a11y)

**Given** баннер отрендерен,
**Then**:

- Контейнер баннера имеет `role="region"` и `aria-label="Уведомление об использовании cookie"`.
- Кнопка «Принять» — нативный `<button>` (через компонент `Button`), доступна с клавиатуры (Tab → Enter/Space), имеет видимый focus-ring (уже встроен в `Button`).
- Ссылка на политику — фокусируемая, с понятным текстом (не «здесь»/«подробнее» без контекста — текст ссылки = «Политика обработки персональных данных»).
- Контраст текста и фона соответствует WCAG AA (токены `text-text-primary` на `bg-white` — уже соответствуют).
- Баннер **не является** модальным окном и **не блокирует** взаимодействие со страницей и не перехватывает фокус — пользователь может пользоваться сайтом, не нажимая «Принять».

---

## Технические требования и ограничения

### Frontend (Next.js 15 / React 19)

**Создать:**
- `frontend/src/hooks/useCookieConsent.ts` — hook (паттерн из `useSearchHistory.ts`).
- `frontend/src/components/layout/CookieConsentBanner.tsx` — клиентский компонент.
- Тесты (см. раздел «Тесты»).

**Изменять:**
- `frontend/src/app/layout.tsx` — добавить импорт и `<CookieConsentBanner />` после `{children}`.
- `frontend/src/hooks/index.ts` — экспортировать `useCookieConsent` (если файл реэкспортирует hooks — проверить и добавить по аналогии).

**НЕ изменять:**
- `frontend/src/app/(blue)/layout.tsx` и другие layout'ы route-групп — баннер монтируется только в root layout.
- Backend — **никаких** изменений (см. «Контекст и решения», п. 2).

### Обязательные правила проекта (project-context.md §7)

- **`'use client'` обязателен** в `CookieConsentBanner.tsx` — компонент использует `useState`/`useEffect` (через hook). Без директивы — runtime-ошибка гидрации.
- **`next/image` не требуется** — баннер без изображений.
- **HTTP-клиент не нужен** — Story не делает запросов к API.
- **Zustand не использовать** — состояние локальное, `localStorage` достаточно; добавление store избыточно.
- **React 19:** `ref` не нужен; `forwardRef` не нужен. Hook и компонент — простые функции.

### SSR / гидрация — критично

`localStorage` недоступен на сервере. Если рендерить баннер на сервере по «угаданному» состоянию — будет hydration mismatch (server HTML ≠ client). Решение (паттерн `useSearchHistory`):

1. Начальное состояние `isLoaded = false`, `isAccepted = false`.
2. На сервере и при первом client-render `isLoaded === false` → компонент возвращает `null`. Server HTML и первый client HTML совпадают (оба пустые) — mismatch отсутствует.
3. `useEffect` (только клиент) читает `localStorage`, выставляет `isLoaded = true` и реальное `isAccepted`.
4. После этого баннер появляется (если не принят).

Лёгкое «появление баннера после гидрации» — допустимо и ожидаемо для этого паттерна.

---

## Структура файлов (изменения)

```
frontend/
  src/
    hooks/
      useCookieConsent.ts                          [CREATE]
      index.ts                                     [MODIFY] — реэкспорт (если применимо)
      __tests__/
        useCookieConsent.test.ts                   [CREATE]
    components/
      layout/
        CookieConsentBanner.tsx                    [CREATE]
        __tests__/
          CookieConsentBanner.test.tsx             [CREATE]
    app/
      layout.tsx                                   [MODIFY] — смонтировать <CookieConsentBanner />
```

---

## Реализация — `useCookieConsent` hook

`frontend/src/hooks/useCookieConsent.ts`:

```typescript
/**
 * useCookieConsent Hook
 * Управляет фактом принятия cookie-уведомления (152-ФЗ) в localStorage.
 */
import { useEffect, useState } from 'react';

const STORAGE_KEY = 'cookie_consent_accepted';
const STORAGE_VALUE = '1';

export interface UseCookieConsentReturn {
  /** Пользователь принял cookie-уведомление */
  isAccepted: boolean;
  /** Чтение из localStorage завершено (защита от SSR hydration mismatch) */
  isLoaded: boolean;
  /** Зафиксировать принятие */
  accept: () => void;
}

export function useCookieConsent(): UseCookieConsentReturn {
  const [isAccepted, setIsAccepted] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      setIsAccepted(localStorage.getItem(STORAGE_KEY) === STORAGE_VALUE);
    } catch (e) {
      // localStorage недоступен (Safari private mode и т.п.) — баннер просто покажется
      console.error('useCookieConsent: чтение localStorage не удалось', e);
    }
    setIsLoaded(true);
  }, []);

  const accept = () => {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(STORAGE_KEY, STORAGE_VALUE);
      } catch (e) {
        console.error('useCookieConsent: запись localStorage не удалась', e);
      }
    }
    setIsAccepted(true);
  };

  return { isAccepted, isLoaded, accept };
}
```

**Примечание:** даже если `localStorage` недоступен, `accept()` всё равно скрывает баннер на текущей сессии (через React-state) — UX не ломается.

---

## Реализация — `CookieConsentBanner` компонент

`frontend/src/components/layout/CookieConsentBanner.tsx`:

```tsx
'use client';

import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui';
import { useCookieConsent } from '@/hooks/useCookieConsent';

export default function CookieConsentBanner() {
  const { isAccepted, isLoaded, accept } = useCookieConsent();

  // До чтения localStorage и после принятия — не рендерим (защита от hydration mismatch)
  if (!isLoaded || isAccepted) return null;

  return (
    <div
      role="region"
      aria-label="Уведомление об использовании cookie"
      className="fixed bottom-0 left-0 right-0 z-40 border-t border-neutral-200 bg-white shadow-lg"
    >
      <div className="container mx-auto flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:py-4">
        <p className="text-sm text-text-secondary">
          Мы используем файлы cookie, чтобы сайт работал корректно. Продолжая
          пользоваться сайтом, вы соглашаетесь с обработкой файлов cookie и
          пользовательских данных согласно{' '}
          <Link
            href="/privacy-policy"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary underline hover:no-underline"
          >
            Политике обработки персональных данных
          </Link>
          .
        </p>
        <Button variant="primary" size="medium" onClick={accept} className="shrink-0">
          Принять
        </Button>
      </div>
    </div>
  );
}
```

**Проверить перед использованием:**
- Токены `text-text-secondary`, `text-primary`, `border-neutral-200` — используются в проекте (`/privacy-policy` page использует `text-text-primary`, Button — `bg-primary`). Если конкретного токена нет в `tailwind.config` / `globals.css` — взять ближайший существующий аналог, не вводить новый.
- `Button` экспортируется из `@/components/ui` (barrel `frontend/src/components/ui/index.ts`); дефолтный/именованный экспорт — `Button` (`variant`, `size`, `children` — см. `ButtonProps`).

---

## Реализация — монтирование в root layout

`frontend/src/app/layout.tsx` — добавить импорт и компонент. **Не** добавлять `'use client'`:

```tsx
import CookieConsentBanner from '@/components/layout/CookieConsentBanner';

// ...внутри RootLayout, в <body>:
      <body className={`${inter.variable} ${robotoCondensed.variable} font-sans antialiased`}>
        {children}
        <CookieConsentBanner />
      </body>
```

---

## Тесты

### `frontend/src/hooks/__tests__/useCookieConsent.test.ts`

Vitest + `@testing-library/react` (`renderHook`, `act`). Покрыть:

1. Начальное состояние: `isLoaded` становится `true` после эффекта, `isAccepted === false` при пустом `localStorage`.
2. `isAccepted === true`, если в `localStorage` заранее лежит `cookie_consent_accepted = "1"`.
3. `accept()` записывает `"1"` в `localStorage` и переводит `isAccepted` в `true`.
4. Битое/чужое значение в `localStorage` (например `"abc"`) → `isAccepted === false`.
5. (Опционально) `localStorage.getItem` бросает исключение → hook не падает, `isLoaded === true`, `isAccepted === false`.

`beforeEach`: `localStorage.clear()`.

### `frontend/src/components/layout/__tests__/CookieConsentBanner.test.tsx`

Vitest + RTL. Покрыть:

1. При пустом `localStorage` баннер рендерится: видны текст, ссылка на `/privacy-policy`, кнопка «Принять».
2. Если `localStorage` уже содержит `cookie_consent_accepted = "1"` — баннер не рендерится (`queryBy... === null`).
3. Клик по «Принять» → баннер исчезает из DOM **и** `localStorage` содержит `"1"`.
4. Ссылка на политику имеет `href="/privacy-policy"`, `target="_blank"`, `rel` с `noopener`.
5. a11y: контейнер имеет `role="region"` и `aria-label`; кнопка доступна (`getByRole('button', { name: /принять/i })`).

`beforeEach`: `localStorage.clear()`.

**Покрытие:** hook `useCookieConsent` ≥ 90%, компонент `CookieConsentBanner` ≥ 90%.

### Проверки сборки

- `npm run test -- src/hooks/__tests__/useCookieConsent.test.ts src/components/layout/__tests__/CookieConsentBanner.test.tsx` — зелёные.
- `npm run build` — без ошибок TypeScript.
- Targeted `npx eslint` по созданным/изменённым файлам — без новых ошибок (общий `npm run lint` в проекте падает на pre-existing файлах вне scope — это known issue, см. историю 35.1).

---

## Связанные истории

- **Завершает** Epic 35 (152-ФЗ): после 35.4 эпик можно переводить в `done`, запускать ретроспективу.
- **Использует:** страницу `/privacy-policy` (Story 35.1, `done`) — ссылка из баннера.
- **Независима** от 35.2 / 35.3 — не трогает `UserConsent`, формы регистрации и подписки, backend.

---

## Примечания для разработчика

1. **Не записывать cookie-принятие в backend.** Это осознанное решение (см. «Контекст и решения»). Не добавлять `consent_type="cookie"` в `UserConsent`, не создавать API.
2. **Не использовать настоящий `document.cookie`** — хранение в `localStorage` (паттерн `useSearchHistory`). Несмотря на название «cookie-баннер», факт принятия логичнее держать в `localStorage`: не уходит на сервер, не раздувает заголовки запросов.
3. **SSR-safety обязательна** — ранний `return null` при `!isLoaded`. Иначе hydration mismatch (см. раздел «SSR / гидрация»).
4. **Баннер — не модалка.** Не блокировать скролл/фокус, не затемнять страницу. Пользователь может игнорировать баннер и пользоваться сайтом.
5. **`z-index`:** `z-40`. Проверить, что модальные окна (`Modal`, `Drawer`, `ConfirmDialog` в `components/ui`) используют более высокий слой — баннер не должен перекрывать их. Если конфликт — понизить слой баннера, не повышать у модалок.
6. **Электрик-тема:** баннер монтируется в root layout, поэтому появится и на `/electric` (comparison-demo). Это приемлемо — отдельная стилизация под Electric Orange **не требуется** (в отличие от Story 35.3, где были два отдельных компонента форм). Один универсальный баннер.
7. **Текст баннера** можно при необходимости согласовать с владельцем — но дефолт из AC-3 юридически корректен и достаточен.

---

## Definition of Done

- [x] Hook `useCookieConsent` создан, SSR-safe, обёрнут в `try/catch`
- [x] Компонент `CookieConsentBanner` создан с директивой `'use client'`
- [x] Баннер показывается при первом визите, скрывается после «Принять»
- [x] Состояние сохраняется между перезагрузками (localStorage)
- [x] Баннер смонтирован в root `layout.tsx`, появляется на всех route-группах
- [x] Ссылка ведёт на `/privacy-policy`, открывается в новой вкладке
- [x] a11y: `role="region"`, `aria-label`, доступность с клавиатуры
- [x] Нет hydration mismatch (проверить консоль браузера в dev)
- [x] Тесты hook и компонента проходят, покрытие ≥ 90%
- [x] `npm run build` без ошибок TypeScript
- [x] Backend не затронут (нет изменений в `backend/`)

---

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-16: `npx gitnexus analyze ..`; индекс обновлён, затем `npx gitnexus impact RootLayout --direction upstream --repo FREESPORT --depth 3` → risk LOW, 0 direct callers, 0 affected processes.
- 2026-05-16: RED: `npm run test -- src/hooks/__tests__/useCookieConsent.test.ts src/components/layout/__tests__/CookieConsentBanner.test.tsx` → ожидаемо упал на отсутствующих `useCookieConsent` / `CookieConsentBanner`.
- 2026-05-16: GREEN: тот же targeted test command → 2 files passed, 11 tests passed.
- 2026-05-16: `npm run test:coverage -- src/hooks/__tests__/useCookieConsent.test.ts src/components/layout/__tests__/CookieConsentBanner.test.tsx --coverage.include=src/hooks/useCookieConsent.ts --coverage.include=src/components/layout/CookieConsentBanner.tsx` → hook 94.44%, banner 100%.
- 2026-05-16: `npx eslint src/hooks/useCookieConsent.ts src/hooks/__tests__/useCookieConsent.test.ts src/components/layout/CookieConsentBanner.tsx src/components/layout/__tests__/CookieConsentBanner.test.tsx src/hooks/index.ts src/app/layout.tsx --max-warnings=0` → passed.
- 2026-05-16: `npm run build` → passed; предупреждения Next.js только про несколько lockfile и ESLint plugin.
- 2026-05-16: `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml restart frontend` → `freesport-frontend` restarted.
- 2026-05-16: Browser check на `http://127.0.0.1:3000/coming-soon` → баннер виден, ссылка `/privacy-policy` с `_blank`/`noopener noreferrer`, после «Принять» исчезает, после reload не возвращается, hydration warnings = 0.
- 2026-05-16: `npm run test` → полный frontend regression passed.
- 2026-05-16: `git diff --check` по изменённым файлам → passed (только Windows LF→CRLF warnings для BMAD YAML/MD).
- 2026-05-16: `npx gitnexus detect-changes --scope all --repo FREESPORT` → risk low, affected processes 0.
- 2026-05-16: Review patch impact: `npx gitnexus impact CookieConsentBanner --direction upstream --repo FREESPORT --depth 3` → risk LOW, 0 direct callers, 0 affected processes.
- 2026-05-16: RED review patch: `npm run test -- src/components/layout/__tests__/CookieConsentBanner.test.tsx` → ожидаемо упал на проверке фразы `согласно Политике обработки персональных данных.`.
- 2026-05-16: GREEN review patch: `npm run test -- src/components/layout/__tests__/CookieConsentBanner.test.tsx` → 1 file passed, 5 tests passed.
- 2026-05-16: `npm run test -- src/hooks/__tests__/useCookieConsent.test.ts src/components/layout/__tests__/CookieConsentBanner.test.tsx` → 2 files passed, 11 tests passed.
- 2026-05-16: `npx eslint src/components/layout/CookieConsentBanner.tsx src/components/layout/__tests__/CookieConsentBanner.test.tsx --max-warnings=0` → passed.
- 2026-05-16: `npm run test:coverage -- src/hooks/__tests__/useCookieConsent.test.ts src/components/layout/__tests__/CookieConsentBanner.test.tsx --coverage.include=src/hooks/useCookieConsent.ts --coverage.include=src/components/layout/CookieConsentBanner.tsx` → hook 94.44%, banner 100%.
- 2026-05-16: `npm run build` → passed; предупреждения Next.js только про несколько lockfile и ESLint plugin.
- 2026-05-16: `npm run test` → полный frontend regression passed.
- 2026-05-16: `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml restart frontend` → `freesport-frontend` restarted.
- 2026-05-16: Browser check на `http://127.0.0.1:3000/coming-soon` → `согласно` и `Политике ... данных.` присутствуют, ссылка `/privacy-policy` с `_blank`/`noopener noreferrer`, после «Принять» `localStorage=1`, после reload баннер не возвращается, hydration warnings = 0.
- 2026-05-16: Final `npx gitnexus detect-changes --scope all --repo FREESPORT` → 4 files, 1 symbol (`CookieConsentBanner`), 1 affected flow, risk medium.

### Completion Notes List

- Реализован SSR-safe hook `useCookieConsent`: читает `cookie_consent_accepted` из `localStorage`, возвращает `isLoaded` для защиты от hydration mismatch, безопасно обрабатывает ошибки чтения/записи.
- Добавлен глобальный клиентский `CookieConsentBanner` с фиксированным нижним layout, ссылкой на `/privacy-policy`, доступным `role="region"` и кнопкой `Button`.
- Баннер смонтирован в root `frontend/src/app/layout.tsx` после `{children}`, без добавления `'use client'` в layout.
- Добавлены unit/component тесты для localStorage-состояния, исключений storage, поведения кнопки, ссылки и a11y-атрибутов.
- Review patch: текст баннера приведён к утверждённой формулировке со встроенной ссылкой в дательном падеже: `согласно Политике обработки персональных данных.`
- Review patch: File List и Change Log дополнены под фактический commit `f35b6edb`, включая принятые сопутствующие изменения зависимостей/линтинга.
- Backend не изменялся; модель `UserConsent`, API, serializers, migrations не затронуты.

### File List

- `frontend/src/hooks/useCookieConsent.ts` — создан SSR-safe hook cookie consent.
- `frontend/src/hooks/__tests__/useCookieConsent.test.ts` — добавлены тесты hook.
- `frontend/src/components/layout/CookieConsentBanner.tsx` — создан глобальный cookie-баннер.
- `frontend/src/components/layout/__tests__/CookieConsentBanner.test.tsx` — добавлены component tests баннера.
- `frontend/src/hooks/index.ts` — добавлен реэкспорт `useCookieConsent`.
- `frontend/src/app/layout.tsx` — баннер смонтирован глобально после `{children}`.
- `.gitignore` — приняты сопутствующие ignore-правила для `supabase-backup` artifacts из commit `f35b6edb`.
- `frontend/eslint.config.mjs` — принят ignore `next-env.d.ts` из commit `f35b6edb`.
- `frontend/package.json` — принят апгрейд Next.js / `eslint-config-next` 15.5.15 → 15.5.18 и пин `typescript` 5.8.2 из commit `f35b6edb`.
- `frontend/package-lock.json` — lockfile синхронизирован с принятыми dependency changes из commit `f35b6edb`.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — статус Story 35.4 синхронизирован.
- `_bmad-output/implementation-artifacts/Story/35-4-cookie-banner.md` — BMAD-статус, чеклист и Dev Agent Record обновлены.

### Change Log

- 2026-05-16: Реализован frontend-only cookie-баннер Story 35.4, добавлены hook/component tests, выполнены targeted/full frontend проверки и story переведена в `review`.
- 2026-05-16: Закрыты review patch-находки: ссылка встроена в предложение баннера, File List/Change Log дополнены под фактический diff commit `f35b6edb`, story возвращена в `review`.

### Review Findings

_Code review 2026-05-16 (BMad adversarial review: Blind Hunter + Edge Case Hunter + Acceptance Auditor)._

_Решения по decision-needed (2026-05-16): текст баннера — встроить ссылку в предложение (вариант эталонного кода спеки); внеплановые изменения коммита — принять, обновить документацию story. Обе находки переведены в `[Review][Patch]`._

- [x] [Review][Patch] Исправить текст баннера — встроить ссылку в предложение [frontend/src/components/layout/CookieConsentBanner.tsx:21-31] — Текущий текст: «…пользовательских данных.» + отдельный фрагмент-ссылка без точки. Заменить на вариант эталонного кода спеки: «…вы соглашаетесь с обработкой файлов cookie и пользовательских данных согласно <Link>Политике обработки персональных данных</Link>.» (дательный падеж, ссылка встроена в предложение, точка после).
- [x] [Review][Patch] Дополнить File List и Change Log story под фактический дифф коммита [_bmad-output/implementation-artifacts/Story/35-4-cookie-banner.md:408-421] — File List перечисляет 8 файлов, но коммит f35b6edb также изменил package.json, package-lock.json, .gitignore, frontend/eslint.config.mjs (апгрейд Next.js 15.5.15→15.5.18, пин typescript 5.8.2). Внеплановые изменения приняты как легитимные — задокументировать их в File List и Change Log.
- [x] [Review][Defer] fixed-баннер перекрывает нижний контент без компенсирующего отступа [frontend/src/components/layout/CookieConsentBanner.tsx:13] — deferred, минорный UX
- [x] [Review][Defer] Нет aria-live — скринридер не анонсирует появление баннера после гидрации [frontend/src/components/layout/CookieConsentBanner.tsx:12] — deferred, AC-5 a11y выполнен, это необязательное улучшение
- [x] [Review][Defer] Нет pb-[env(safe-area-inset-bottom)] — на iOS кнопка «Принять» заходит под home indicator [frontend/src/components/layout/CookieConsentBanner.tsx:13] — deferred, минорный mobile-polish
- [x] [Review][Defer] Кнопка баннера остаётся в tab-order под модальным оверлеем [frontend/src/components/layout/CookieConsentBanner.tsx:13] — deferred, зависит от pre-existing focus-trap модалок

_Code review run 2 — 2026-05-16 (BMad adversarial review: Blind Hunter + Edge Case Hunter + Acceptance Auditor). Триаж: 0 decision-needed, 0 patch, 3 defer; остальные находки отклонены как noise/false-positive — в т.ч. контраст `text-text-secondary` (#4b5c7a на белом ≈6.75:1) проходит WCAG AA; `z-40` корректно ниже модалок (z-50); scope-creep package.json/.gitignore/eslint уже принят в run 1; «фантомное» принятие на SSR невозможно — `accept` живёт в `'use client'`-компоненте._

- [x] [Review][Defer] Нет синхронизации согласия между вкладками [frontend/src/hooks/useCookieConsent.ts:14-24] — deferred, спека описывает информационный баннер, multi-tab sync не требуется
- [x] [Review][Defer] Ссылка target="_blank" без a11y-индикации «открывается в новой вкладке» [frontend/src/components/layout/CookieConsentBanner.tsx:21-29] — deferred, AC-5 выполнен, необязательное a11y-улучшение
- [x] [Review][Defer] Текст баннера `<p>` без max-w — неограниченный рост высоты на узких экранах [frontend/src/components/layout/CookieConsentBanner.tsx:20] — deferred, минорный UX-polish
