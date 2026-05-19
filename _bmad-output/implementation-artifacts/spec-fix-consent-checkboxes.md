---
title: 'Исправление чекбоксов и текстов согласия в формах'
type: 'bugfix'
created: '2026-05-19'
status: 'done'
context: []
baseline_commit: '4ff9e6c0ec7bd444c37b337b85f89a4c9430c073'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В форме регистрации (`/register`) кастомный чекбокс при выборе закрашивается, но галочка внутри не появляется (баг проявляется в uncontrolled-режиме `react-hook-form`). Тексты двух чекбоксов согласия неполные/некорректные, а ссылка на политику ведёт только с фрагмента «обработку моих персональных данных». Тот же неполный текст и ссылка — в форме подписки на главной странице.

**Approach:** Починить компонент `Checkbox` так, чтобы иконка-галочка управлялась CSS-состоянием `peer-checked` (работает и в controlled, и в uncontrolled режимах). Обновить тексты чекбоксов согласия и сделать кликабельной всю фразу-название документа в форме регистрации и в форме подписки.

## Boundaries & Constraints

**Always:**
- Галочка отображается при любом способе использования `Checkbox` — и через `checked`-проп, и через `{...register()}`.
- Эталон визуала чекбокса — фильтр брендов в `SidebarFilters` (controlled-режим, галочка уже работает).
- Ссылка на политику ведёт на `/privacy-policy`, открывается в новой вкладке (`target="_blank" rel="noopener noreferrer"`).
- Точные тексты — см. Design Notes. Кликабельна вся фраза «Политикой обработки персональных данных ООО „Фриспорт"».
- Сохранить accessibility: `aria-labelledby` чекбокса должен покрывать весь видимый текст.

**Ask First:**
- Если потребуется изменить публичный API компонента `Checkbox` (пропсы) — согласовать.

**Never:**
- Не менять чекбоксы согласия в `B2BRegisterForm` (вне scope; они автоматически выиграют от фикса компонента).
- Не переводить чекбоксы форм согласия в controlled-режим ради обхода бага — баг чинится в самом компоненте.
- Не менять backend, схемы валидации, поля `pdp_consent` / `marketing_consent`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Чекбокс выбран (uncontrolled, register) | Клик по чекбоксу в `RegisterForm` | Квадрат закрашен primary + видна белая галочка | N/A |
| Чекбокс выбран (controlled) | `checked={true}` в `SidebarFilters` | Квадрат закрашен + видна галочка (без регрессии) | N/A |
| Indeterminate | `indeterminate={true}` | Виден minus-значок, галочка скрыта | N/A |
| Чекбокс не выбран | Начальное состояние | Пустой квадрат, галочка скрыта | N/A |
| Клик по тексту-ссылке политики | Клик по «Политикой обработки…» | Открывается `/privacy-policy` в новой вкладке, чекбокс НЕ переключается | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/components/ui/Checkbox/Checkbox.tsx` -- кастомный чекбокс; иконка `Check` рендерится по React-пропу `checked`, ломается в uncontrolled-режиме
- `frontend/src/components/auth/RegisterForm.tsx` -- форма `/register`; чекбоксы `pdp_consent` (стр. ~284-336) и `marketing_consent` (стр. ~338-351)
- `frontend/src/components/home/SubscribeForm.tsx` -- форма подписки на главной; чекбокс `pdp_consent` (стр. ~149-195)
- `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` -- тест проверяет accessible name marketing-чекбокса (`/получать рекламные… от freesport/i`, стр. ~45)
- `frontend/src/components/home/__tests__/SubscribeForm.test.tsx` -- тесты подписки (accessible name по фрагменту «обработку моих персональных данных» сохраняется)

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/components/ui/Checkbox/Checkbox.tsx` -- вынести `<Check>`/`<Minus>` из `<label>` в позицию sibling `peer`-инпута, абсолютное позиционирование поверх квадрата; видимость `<Check>` через `opacity-0 peer-checked:opacity-100` -- чинит галочку в uncontrolled-режиме (см. Design Notes)
- [x] `frontend/src/components/auth/RegisterForm.tsx` -- обновить текст `pdp_consent`-чекбокса и сделать ссылкой всю фразу-название политики; обновить текст `marketing_consent`-чекбокса; синхронизировать `aria-labelledby` (убран неиспользуемый suffix-id)
- [x] `frontend/src/components/home/SubscribeForm.tsx` -- обновить текст `pdp_consent`-чекбокса и ссылку аналогично `RegisterForm`; синхронизировать `aria-labelledby`
- [x] `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` -- обновить accessible name marketing-чекбокса и regex `link`-роли под новые тексты
- [x] `frontend/src/components/home/__tests__/SubscribeForm.test.tsx` -- обновить regex `link`-роли под новый текст ссылки (accessible name чекбокса сохранился)

**Acceptance Criteria:**
- Given пользователь на `/register`, when кликает по любому чекбоксу согласия, then квадрат закрашивается и внутри появляется белая галочка.
- Given фильтр брендов в каталоге, when бренд выбран, then галочка отображается как прежде (нет регрессии).
- Given пользователь читает чекбокс согласия в `/register` и в форме подписки, then текст соответствует Design Notes, а клик по фразе «Политикой обработки персональных данных ООО „Фриспорт“» открывает `/privacy-policy` в новой вкладке.
- Given чекбокс marketing-согласия в `/register`, then текст: «Я согласен (на) получать рекламные и информационные рассылки от ООО „Фриспорт“».

## Spec Change Log

### Итерация 2 — bad_spec (CRITICAL)

**Триггер:** ревьюеры (Blind Hunter + Acceptance Auditor) установили, что прежний план Design Notes нерабочий: CSS `peer-checked:opacity-100` на иконке `<Check>`, вложенной в `<label>`, не срабатывает. Tailwind `peer-checked:` генерирует селектор `.peer:checked ~ .target` (combinator `~` = general sibling). `<Check>` внутри `<label>` — потомок sibling-элемента, а не сам sibling, поэтому селектор его не выбирает.

**Исправлено:** Design Notes переписан — иконки `<Check>` и `<Minus>` выносятся ИЗ `<label>` и становятся прямыми siblings `peer`-инпута, позиционируются абсолютно поверх квадрата-`<label>`.

**Известное плохое состояние, которого избегаем:** иконка-галочка не отображается ни в одном режиме (CSS-селектор не матчит вложенный элемент).

**KEEP:** тексты чекбоксов и ссылок (`RegisterForm.tsx`, `SubscribeForm.tsx`) выверены аудитором символ-в-символ — сохранить. `aria-labelledby` (префикс + ссылка) — корректны, сохранить. Обновления тестов под новые тексты — корректны, сохранить.

### Итерация 3 — review closure (2026-05-19)

**Исправлено:** вернули scale-анимацию `peer-checked:scale-100` на `Checkbox` и заменили хрупкий substring-regex на полный accessible name PDP-чекбокса в тестах `RegisterForm` и `SubscribeForm`.

**Результат:** ревью-замечания по UX и matcher'у закрыты, поведение и тексты согласия остались в рамках Design Notes.

## Design Notes

**Корень бага:** иконка `<Check>` рендерится по React-пропу `checked` (`{checked && !indeterminate && <Check/>}`). В `RegisterForm` чекбоксы подключены через `{...register()}` — uncontrolled, проп `checked` всегда `undefined`. Квадрат закрашивается, т.к. это CSS `peer-checked:bg-primary` на `<label>` (label — прямой sibling `peer`-инпута, селектор `.peer:checked ~ label` матчит). Иконку нужно перевести на тот же CSS-механизм.

**Решение:** иконки `<Check>` и `<Minus>` выносятся из `<label>` и размещаются как прямые siblings `peer`-инпута (после `<input>` и `<label>` в DOM), позиционируются `absolute` поверх квадрата-`<label>`. Тогда `peer-checked:` на `<Check>` сработает (`.peer:checked ~ .Check` — sibling-отношение выполнено).

- `<Check>` рендерится всегда (когда `!indeterminate`), видимость через `opacity-0 peer-checked:opacity-100`.
- `<Minus>` рендерится по React-пропу `indeterminate` (всегда controlled — корректно).
- Иконки: `absolute inset-0 m-auto` для центровки в контейнере, `pointer-events-none` чтобы клик проходил на `<label>`, `aria-hidden="true"`.
- DOM-порядок в контейнере: `<input class="peer">`, затем `<label>`, затем иконки. `checkbox.nextElementSibling` остаётся `<label>` (тесты не ломаются).

**Точные тексты (кириллица «Фриспорт», вложенные кавычки — русские лапки „“, U+201E / U+201C — ASCII `"` запрещён ESLint-правилом react/no-unescaped-entities):**

Чекбокс 1 (`pdp_consent`, обе формы) — статичный префикс + ссылка:
```
Я даю согласие на обработку моих персональных данных в соответствии с [ссылка→/privacy-policy: Политикой обработки персональных данных ООО „Фриспорт“]
```
Кликабельна целиком фраза `«Политикой обработки персональных данных ООО „Фриспорт“»` (с обрамляющими ёлочками). `aria-labelledby` = id префикса + id ссылки.

Чекбокс 2 (`marketing_consent`, только `RegisterForm`):
```
Я согласен (на) получать рекламные и информационные рассылки от ООО „Фриспорт“
```

## Verification

**Commands:**
- `cd frontend && npm run test -- src/components/ui/Checkbox src/components/auth/__tests__/RegisterForm.test.tsx src/components/home/__tests__/SubscribeForm.test.tsx` -- expected: все тесты зелёные (Checkbox-тесты — проверка на регрессию)
- `cd frontend && npx tsc --noEmit` -- expected: без ошибок типов
- `cd frontend && npm run lint` -- expected: без новых ошибок

**Manual checks:**
- `/register`: клик по обоим чекбоксам — закрашивание + галочка; клик по ссылке политики открывает `/privacy-policy` в новой вкладке, не переключая чекбокс.
- Главная страница, блок подписки: текст и ссылка чекбокса совпадают с `RegisterForm`.
- Каталог, фильтр брендов: галочки отображаются без регрессии.

## Suggested Review Order

**Корень бага — рендер галочки**

- Точка входа: иконки `<Check>`/`<Minus>` вынесены в siblings `peer`-инпута — теперь CSS `peer-checked` их выбирает
  [`Checkbox.tsx:87`](../../frontend/src/components/ui/Checkbox/Checkbox.tsx#L87)

**Тексты согласия и ссылка на политику**

- Полный текст PDP-чекбокса + вся фраза-название политики стала ссылкой
  [`RegisterForm.tsx:304`](../../frontend/src/components/auth/RegisterForm.tsx#L304)

- `aria-labelledby` сокращён до префикс+ссылка после удаления suffix-label
  [`RegisterForm.tsx:288`](../../frontend/src/components/auth/RegisterForm.tsx#L288)

- Новый текст marketing-чекбокса
  [`RegisterForm.tsx:339`](../../frontend/src/components/auth/RegisterForm.tsx#L339)

- Те же правки текста и ссылки в форме подписки на главной
  [`SubscribeForm.tsx:166`](../../frontend/src/components/home/SubscribeForm.tsx#L166)

**Тесты**

- Полный accessible name PDP-чекбокса и `link`-роли обновлены под новые тексты
  [`RegisterForm.test.tsx:43`](../../frontend/src/components/auth/__tests__/RegisterForm.test.tsx#L43)

- `link`-роль подписки обновлена под новый текст ссылки
  [`SubscribeForm.test.tsx:67`](../../frontend/src/components/home/__tests__/SubscribeForm.test.tsx#L67)

## Review Findings (2026-05-19)

### Patch

- [x] [Review][Patch] Удалена анимация `peer-checked:scale-100` из `<label>` — регрессия UX [`frontend/src/components/ui/Checkbox/Checkbox.tsx:62`]
  - Комментарий компонента (строка 3) всё ещё упоминает «анимацию масштаба», что теперь не соответствует коду. При checked-переходе квадрат меняет цвет/границу, но масштабирование пропало.
- [x] [Review][Patch] Хрупкий substring-regex в тесте PDP-чекбокса [`frontend/src/components/auth/__tests__/RegisterForm.test.tsx:43,69`]
  - Accessible name чекбокса теперь содержит полный текст (prefix + link). Regex `/обработку моих персональных данных/i` матчит подстроку и может сломаться при будущем изменении prefix. Рекомендуется использовать более специфичный matcher.

### Defer

- [x] [Review][Defer] `Minus` при `indeterminate` не имеет анимации исчезновения [`frontend/src/components/ui/Checkbox/Checkbox.tsx:96-101`] — deferred, pre-existing
  - `<Check>` получил `transition-opacity`, а `<Minus>` — нет. При смене `indeterminate → checked` `Minus` исчезает мгновенно, `Check` появляется с fade. Pre-existing inconsistency, minor cosmetic.
