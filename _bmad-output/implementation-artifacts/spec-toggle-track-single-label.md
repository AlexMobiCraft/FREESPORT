---
title: 'Одна подпись у Toggle — трек перестаёт быть <label>'
type: 'bugfix'
created: '2026-10-01'
status: 'done'
baseline_commit: 'b102b061'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/spec-audit-consent-checkbox-single-label.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** У `input` в `Toggle` две подписи `<label for>`: первая — пустой трек с бегунком, вторая — текст. Поэтому `input.labels[0]` пустой — тот же дефект разметки, который у `Checkbox` исправили в `spec-audit-consent-checkbox-single-label`.

**Approach:** Тот же приём: трек становится `<span aria-hidden="true">`, а нативный `input` — прозрачный слой поверх трека (`opacity-0`, `absolute inset-0`, `z-10`) вместо `sr-only`. Клик по треку попадает прямо в `input`, JS-обработчики не нужны, внешний вид не меняется.

## Boundaries & Constraints

**Always:** `input` остаётся первым в контейнере, на нём держатся `peer-*`. Набор классов трека сохраняется, кроме `cursor-pointer`: курсор задаёт `input`. `role="switch"`, `aria-checked`, `aria-label`, генерация `id`, guard `disabled` в `handleChange` и `className` на треке остаются как есть. Комментарии на русском.

**Ask First:** правка `SidebarFilters` и других потребителей; изменение доступного имени переключателя.

**Never:** перевод бегунка с JS-класса `checked && 'translate-x-5'` на CSS; `Checkbox`, `ElectricConsentCheckbox` и прочие компоненты; JS-обработчики клика по треку.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Подпись пропсом | `<Toggle label="Test" />` | `input.labels.length === 1`, текст «Test» | N/A |
| Без подписи | `<Toggle />` | `input.labels.length === 0` | N/A |
| Клик по треку или тексту | пользователь кликает | `onChange` вызывается один раз | N/A |
| Disabled | `disabled` | клик не переключает, курсор `not-allowed` | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/components/ui/Toggle/Toggle.tsx` -- компонент, трек — `<label htmlFor>` на стр. 45-91
- `frontend/src/components/ui/Toggle/__tests__/Toggle.test.tsx` -- ищет трек через `label[for]`, бегунок через первый `span`
- `frontend/src/components/business/SidebarFilters/SidebarFilters.tsx:241` -- единственный потребитель; сам `SidebarFilters` ни одна страница не импортирует, только его тест (`getByLabelText('Только в наличии')`)
- `frontend/src/components/ui/Checkbox/Checkbox.tsx:33-80` -- образец: прозрачный input, `isolate` на обёртке, квадрат — `aria-hidden` span

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/components/ui/Toggle/Toggle.tsx` -- обёртка `relative` → `relative isolate`; у `input` `sr-only peer` → `peer absolute inset-0 z-10 m-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-not-allowed`; трек `<label htmlFor>` → `<span aria-hidden="true">` без `cursor-pointer`; комментарий у `input` по образцу `Checkbox` -- первая подпись больше не пустая
- [x] `frontend/src/components/ui/Toggle/__tests__/Toggle.test.tsx` -- в существующих тестах поменять только селекторы: трек — `screen.getByRole('switch').nextElementSibling`, бегунок — `track.firstElementChild`; утверждения не трогать. Новые тесты: `labels.length` 1 с подписью и 0 без; трек — `SPAN` с `aria-hidden="true"`; у `input` нет `sr-only`, есть `opacity-0`, `absolute`, `inset-0`; клик по тексту подписи вызывает `onChange` -- после правки `label[for]` и первый `span` указывают на другие элементы

**Acceptance Criteria:**
- Given отрендеренный `Toggle`, when проверяем DOM, then пустых `<label for>` нет и у `input` не больше одной подписи
- Given тест `SidebarFilters` с `getByLabelText('Только в наличии')`, when прогоняем Vitest, then он зелёный без правок
- Given изменённое дерево, when выполняем `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"`, then затронуты только `Toggle` и его тест

## Design Notes

Обёртка трека — flex-элемент без собственного размера, поэтому `inset-0 h-full w-full` даёт `input` ровно 44×24, как у трека. `z-10` нужен, потому что трек (`relative`) в DOM идёт после `input` и иначе перекрыл бы его; `isolate` держит `z-10` внутри обёртки. У трека нет `hover:`-стилей, переводить на `peer-hover:` нечего. Фокусный outline браузера скрыт `opacity-0`, кольцо по-прежнему рисует `peer-focus:ring-*` на треке.

## Verification

**Commands:**
- `npm run format:check` (в `frontend/`) -- expected: без расхождений
- `npm run lint` -- expected: 0 warnings
- `npx tsc --noEmit` -- expected: без ошибок
- `npx vitest run src/components/ui/Toggle src/components/business/SidebarFilters` -- expected: все зелёные; затем полный `npm test`

## Suggested Review Order

**Одна подпись: трек перестаёт быть `<label>`**

- Точка входа: прозрачный нативный input поверх трека вместо `sr-only`; `appearance-none` — чтобы растягивался во всех движках.
  [`Toggle.tsx:42`](../../frontend/src/components/ui/Toggle/Toggle.tsx#L42)

- Трек — `aria-hidden` span; классы прежние, без `cursor-pointer`.
  [`Toggle.tsx:48`](../../frontend/src/components/ui/Toggle/Toggle.tsx#L48)

- `isolate` удерживает `z-10` input внутри обёртки.
  [`Toggle.tsx:28`](../../frontend/src/components/ui/Toggle/Toggle.tsx#L28)

**Тесты**

- Селекторы трека и бегунка — от input, а не через `label[for]` и первый `span`.
  [`Toggle.test.tsx:13`](../../frontend/src/components/ui/Toggle/__tests__/Toggle.test.tsx#L13)

- `input.labels`: 1 с подписью, 0 без; трек — span; слой с `z-10` и `isolate`; клик по тексту.
  [`Toggle.test.tsx:223`](../../frontend/src/components/ui/Toggle/__tests__/Toggle.test.tsx#L223)
