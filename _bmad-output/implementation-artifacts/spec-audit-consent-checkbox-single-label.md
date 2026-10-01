---
title: 'Одна подпись у чекбокса — декоративный квадрат перестаёт быть <label>'
type: 'bugfix'
created: '2026-10-01'
status: 'done'
baseline_commit: '4615b8ce'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/tasks/intent-audit-2026-09-28-consent-checkbox-label.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** У каждого `input` в `Checkbox` и `ElectricConsentCheckbox` два `<label for>`: первый — пустой декоративный квадрат (в electric после отметки там «✓»), второй — текст согласия. Простой анализатор HTML (`input.labels[0]`) видит пустую подпись, поэтому сканер аудита 28.09.2026 не находит отдельного согласия на рассылку на `/home` и `/register`. Это гипотеза, но пустой `<label>` и две подписи у одного поля — дефект разметки в любом случае.

**Approach:** Квадрат становится `<span aria-hidden="true">`, а нативный `input` — прозрачный слой 20×20 поверх квадрата (`opacity-0`, `absolute`, `z-10`) вместо `sr-only`. Клик, клавиатура и `react-hook-form` работают без JS-обработчиков, внешний вид не меняется.

## Boundaries & Constraints

**Always:** `input` остаётся первым в контейнере, чтобы работали `peer-*`. Набор классов квадрата сохраняется, кроме `cursor-pointer`: курсор задаёт `input`. Стили, которые отвечают за состояния (hover, focus-ring, checked, indeterminate, disabled, error, motion-reduce), визуально не меняются. `aria-labelledby` у потребителей остаются. Комментарии на русском.

**Ask First:** правка потребителей `Checkbox`, кроме комментария в `SubscribeForm`; изменение доступных имён чекбоксов.

**Never:** тексты согласий, их порядок и валидация; `ElectricCheckbox`, `Toggle`, `AddressModal`, `ElectricSidebar`; JS-обработчики клика по квадрату.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Подпись пропсом | `<Checkbox label="Test" />` | `input.labels.length === 1`, текст «Test» | N/A |
| Без подписи | `<Checkbox />` без внешнего `<label for>` | `input.labels.length === 0` | N/A |
| Внешняя подпись | формы согласий: `/home`, `/register`, `/b2b-register`, `/electric` | у ПДн и рассылки по одной подписи с текстом согласия | N/A |
| Клик по квадрату | пользователь кликает по квадрату | галочка ставится и снимается | N/A |
| Disabled | `disabled` | клик не переключает, курсор `not-allowed` | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/components/ui/Checkbox/Checkbox.tsx` -- общий чекбокс темы blue, шесть потребителей (SubscribeForm, RegisterForm, B2BRegisterForm, CatalogPageClient, SidebarFilters, AddressSection)
- `frontend/src/components/home/ElectricSubscribeForm.tsx` -- локальный `ElectricConsentCheckbox` (стр. 109-180), используется только здесь
- `frontend/src/components/home/SubscribeForm.tsx:283-285` -- устаревший комментарий про «пустой квадрат»
- `frontend/src/components/ui/Checkbox/__tests__/Checkbox.test.tsx` -- проверки классов квадрата через `nextElementSibling`
- `frontend/src/components/{home,auth}/__tests__/*` -- тесты четырёх форм согласий

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/components/ui/Checkbox/Checkbox.tsx` -- `input`: `sr-only peer` → `peer absolute inset-0 z-10 m-0 h-5 w-5 cursor-pointer opacity-0 disabled:cursor-not-allowed`; квадрат `<label htmlFor>` → `<span aria-hidden="true">` без `cursor-pointer`; переписать комментарии у input и иконок (клик попадает в прозрачный `input`) -- первая подпись больше не пустая
- [x] `frontend/src/components/home/ElectricSubscribeForm.tsx` -- та же правка в `ElectricConsentCheckbox`; `hover:bg-[var(--color-primary)]/15` → `peer-hover:bg-[var(--color-primary)]/15`, потому что `input` перекрывает квадрат и тот перестаёт получать `:hover`; в JSDoc указать, что `aria-labelledby` нужен из-за ссылки, вынесенной из `<label>` -- одна подпись, hover сохраняется
- [x] `frontend/src/components/home/SubscribeForm.tsx` -- переписать комментарий на стр. 283-285: `aria-labelledby` нужен, чтобы в имя вошла ссылка на документ, вынесенная из `<label>` -- комментарий перестаёт противоречить коду
- [x] `frontend/src/components/ui/Checkbox/__tests__/Checkbox.test.tsx` -- новые тесты: `labels.length` 1 и 0; квадрат — `SPAN` с `aria-hidden="true"`; у `input` нет `sr-only`, есть `opacity-0`, `absolute`, `inset-0`; клик по тексту подписи переключает чекбокс. Существующие проверки не трогать
- [x] `frontend/src/components/home/__tests__/{SubscribeForm,ElectricSubscribeForm}.test.tsx`, `frontend/src/components/auth/__tests__/{RegisterForm,B2BRegisterForm}.test.tsx` -- в каждом новый тест: у чекбоксов ПДн и рассылки `labels.length === 1`, подпись ПДн содержит «персональных данных», подпись рассылки — «рассылок». В Electric обновить комментарий в тесте про «✓» (стр. 119) -- прямая проверка того, что видит анализатор

**Acceptance Criteria:**
- Given отрендеренные `Checkbox` или `ElectricConsentCheckbox`, when проверяем DOM, then пустых `<label for>` нет и у каждого `input` не больше одной связанной подписи
- Given существующие тесты на `getByRole('checkbox', { name: … })` и клик по `label[for="…-pdp-consent"]`, when прогоняем Vitest, then они зелёные без правок
- Given изменённое дерево, when выполняем `npx gitnexus detect-changes --scope all`, then затронуты только `Checkbox`, `ElectricConsentCheckbox`/`ElectricSubscribeForm`, `SubscribeForm` (комментарий) и тесты

## Design Notes

Если просто заменить квадрат на `<span>` и оставить `input` с `sr-only`, клик по квадрату перестанет ставить галочку. Прозрачный нативный `input` поверх кастомного квадрата — стандартный приём. `z-10` нужен потому, что квадрат (`relative`) идёт в DOM после `input` и иначе перекрыл бы его. Фокусный outline браузера невидим из-за `opacity-0`; кольцо фокуса по-прежнему рисует `peer-focus:ring-*`. В electric квадрат смещён на `pt-0.5` и скошен (`-skew-x-12` выносит углы примерно на 2 px с каждой стороны), поэтому `input` там `-left-0.5 top-0.5 h-5 w-6` — точно по охватывающему прямоугольнику. В `Checkbox` у `input` `h-full w-full`, размер повторяет квадрат. `isolate` на обёртке не выпускает `z-10` в общий порядок наложения страницы.

## Verification

**Commands:**
- `npm run format:check` (в `frontend/`) -- expected: без расхождений
- `npm run lint` -- expected: 0 warnings
- `npx tsc --noEmit` -- expected: без ошибок
- `npx vitest run src/components/ui/Checkbox src/components/home src/components/auth` -- expected: все зелёные; затем полный `npm test`

**Manual checks (if no CLI):**
- `curl -s http://localhost:3000/home | grep -o '<label[^>]*for="[^"]*consent[^"]*"[^>]*>[^<]*'` -- две строки с текстом согласия, пустых нет
- Chrome на `/home`, `/register`, `/b2b-register`, `/electric`, `/catalog`, `/checkout`: клик по квадрату и по тексту переключает, клик по ссылке не переключает, Tab показывает только кольцо квадрата

## Suggested Review Order

**Одна подпись: квадрат перестаёт быть `<label>`**

- Точка входа: прозрачный нативный input поверх квадрата вместо `sr-only`.
  [`Checkbox.tsx:44`](../../frontend/src/components/ui/Checkbox/Checkbox.tsx#L44)

- Квадрат — `aria-hidden` span; классы состояний прежние, без `cursor-pointer`.
  [`Checkbox.tsx:50`](../../frontend/src/components/ui/Checkbox/Checkbox.tsx#L50)

- `isolate` удерживает `z-10` input внутри обёртки.
  [`Checkbox.tsx:33`](../../frontend/src/components/ui/Checkbox/Checkbox.tsx#L33)

**Electric: та же правка с поправкой на скос**

- Input точно по охватывающему прямоугольнику скошенного квадрата и `pt-0.5`.
  [`ElectricSubscribeForm.tsx:140`](../../frontend/src/components/home/ElectricSubscribeForm.tsx#L140)

- `hover:` → `peer-hover:`: квадрат перекрыт input и сам hover не получает.
  [`ElectricSubscribeForm.tsx:161`](../../frontend/src/components/home/ElectricSubscribeForm.tsx#L161)

- JSDoc: `aria-labelledby` нужен ради ссылки вне `<label>`, а не из-за «✓».
  [`ElectricSubscribeForm.tsx:115`](../../frontend/src/components/home/ElectricSubscribeForm.tsx#L115)

- Комментарий у потребителя больше не ссылается на пустой квадрат.
  [`SubscribeForm.tsx:283`](../../frontend/src/components/home/SubscribeForm.tsx#L283)

**Тесты**

- `input.labels`: 1 с подписью, 0 без; квадрат — span; клик по тексту.
  [`Checkbox.test.tsx:81`](../../frontend/src/components/ui/Checkbox/__tests__/Checkbox.test.tsx#L81)

- По одной подписи у ПДн и рассылки в каждой форме согласий.
  [`SubscribeForm.test.tsx:125`](../../frontend/src/components/home/__tests__/SubscribeForm.test.tsx#L125)

- Electric: одна подпись и разметка квадрата.
  [`ElectricSubscribeForm.test.tsx:115`](../../frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx#L115)

- Регистрация розницы и B2B — та же проверка подписей.
  [`RegisterForm.test.tsx:130`](../../frontend/src/components/auth/__tests__/RegisterForm.test.tsx#L130)
  [`B2BRegisterForm.test.tsx:111`](../../frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx#L111)
