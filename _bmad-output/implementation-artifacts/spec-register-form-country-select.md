---
title: 'Селектор «Страна» в основной форме регистрации (RegisterForm) для B2B-ролей'
type: 'bugfix'
created: '2026-07-24'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'b2a97cc9'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/spec-manager-region-routing.md'
  - '{project-root}/frontend/src/components/auth/B2BRegisterForm.tsx'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Фича маршрутизации B2B-заявок на регионального менеджера ([[spec-manager-region-routing]]) добавила селектор «Страна» только в `B2BRegisterForm.tsx` (маршрут `/b2b-register`). Но пользователи регистрируются через основную форму `RegisterForm.tsx` (маршрут `/register`) с селектором «Тип аккаунта», где поля «Страна» нет — `country` не попадает в payload, и для B2B-заявок из Беларуси/Казахстана маршрутизация всегда идёт по дефолту «Россия».

**Approach:** Добавить в `RegisterForm.tsx` селектор «Страна» (Россия/Беларусь/Казахстан, default «Россия»), показываемый только для B2B-ролей (как уже сделано для «Название компании»), с пробросом `country` в payload. Расширить `registerSchema` полем `country`. Поведение и вёрстку повторить по образцу `B2BRegisterForm.tsx`.

## Boundaries & Constraints

**Always:**
- Селектор «Страна» показывается только для B2B-ролей (`role !== 'retail'`, условие `isB2BRole`), рядом с полем «Название компании».
- `country` всегда присутствует в payload с default «Россия» (backend принимает `country` с дефолтом, строгой валидации нет — см. Spec Change Log в [[spec-manager-region-routing]]).
- Значения строго: `Россия`, `Беларусь`, `Казахстан` — совпадают с backend `User.country` choices и правилами `ManagerRoutingRule`.
- Паттерны из `B2BRegisterForm.tsx` (разметка `<select>`, aria-атрибуты, обработка `errors.country`) переиспользовать, не изобретать новый UI.

**Never:**
- Не трогать `B2BRegisterForm.tsx` (там уже реализовано корректно).
- Не расширять список стран сверх России/Беларуси/Казахстана.
- Не менять backend (`serializers.py`, модели, миграции) — серверная часть фичи уже готова и принимает `country`.
- Не делать «Страна» видимой/обязательной для `retail`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Выбрана B2B-роль | role=wholesale_level1 | Селектор «Страна» отрендерен, default «Россия» | N/A |
| B2B, выбрана Беларусь | role=wholesale_level1, country=Беларусь | В payload `country: 'Беларусь'` | N/A |
| Роль retail | role=retail | Селектор «Страна» скрыт | N/A |
| B2B без явного выбора | role=trainer, country не менялся | В payload `country: 'Россия'` (default) | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/schemas/authSchemas.ts` — `registerSchema`: добавить `country: z.enum(['Россия','Беларусь','Казахстан']).default('Россия')` (образец — `b2bRegisterSchema:144`).
- `frontend/src/components/auth/RegisterForm.tsx` — селектор «Страна» внутри блока `isB2BRole` (рядом с company_name, `RegisterForm.tsx:236`); `country` в payload `registerData` (`RegisterForm.tsx:107`); `country: 'country'` в `REGISTER_FIELD_ERROR_MAP`.
- `frontend/src/components/auth/B2BRegisterForm.tsx` — **образец** разметки `<select>` (строки 408-436), не менять.
- `frontend/src/types/api.ts` — `RegisterRequest.country?: string` уже есть (строка 151), менять не нужно.
- `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` — тест рендера/submit со «Страна» для B2B.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/schemas/authSchemas.ts` -- добавить в `registerSchema` поле `country: z.enum(['Россия','Беларусь','Казахстан']).default('Россия')` -- чтобы форма знала о поле и подставляла дефолт.
- [x] `frontend/src/components/auth/RegisterForm.tsx` -- (1) в блоке `{isB2BRole && (...)}` добавить `<select>` «Страна» по образцу `B2BRegisterForm.tsx:408-436` (id `register-country`, `{...register('country')}`, опции Россия/Беларусь/Казахстан, вывод `errors.country`); (2) добавить `country: data.country` в `registerData`; (3) добавить `country: 'country'` в `REGISTER_FIELD_ERROR_MAP`; (4) задать `country: 'Россия'` в `defaultValues` -- проброс страны в API для B2B-маршрутизации.
- [x] `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` -- тест: для B2B-роли селектор «Страна» рендерится и submit отправляет выбранную страну; для retail — селектор отсутствует. (Также обновлён существующий retail-submit тест: payload теперь содержит `country: 'Россия'`.)

**Acceptance Criteria:**
- Given пользователь выбрал B2B-роль (например «Оптовик»), when форма отрендерена, then виден селектор «Страна» с опциями Россия/Беларусь/Казахстан и выбранной по умолчанию «Россия».
- Given B2B-пользователь выбрал «Беларусь» и отправил форму, when вызывается `authService.register`, then в payload `country === 'Беларусь'`.
- Given пользователь оставил роль «Розничный покупатель» (retail), when форма отрендерена, then селектор «Страна» отсутствует и поведение регистрации не меняется.
- Given B2B-роль без ручного изменения страны, when форма отправлена, then `country === 'Россия'` (default) — жёсткой ошибки нет.

## Design Notes

`RegisterForm` — унифицированная форма (retail + B2B через `Тип аккаунта`), в отличие от отдельного `B2BRegisterForm`. Поэтому «Страна», в отличие от `B2BRegisterForm` (где поле всегда видимо), показывается условно — по `isB2BRole`, симметрично полю «Название компании». Разметку `<select>` копировать из `B2BRegisterForm.tsx` (строки 408-436), меняя только `id`/`aria-describedby` префикс на `register-country`.

## Verification

**Commands:**
- `cd frontend && npm run test -- src/components/auth/__tests__/RegisterForm.test.tsx` -- expected: тесты формы (включая новый на «Страна») зелёные.
- `cd frontend && npx tsc --noEmit` -- expected: нет ошибок типов (`country` согласован в схеме, payload и `RegisterRequest`).

**Manual checks:**
- На `/register` выбрать «Оптовик» → появляется «Страна»; выбрать «Беларусь», отправить → в сетевом запросе `country: 'Беларусь'`. Выбрать «Розничный покупатель» → «Страна» исчезает.

## Suggested Review Order

**Схема (источник поля country)**

- Поле `country` с enum и дефолтом «Россия» — точка правды для формы
  [`authSchemas.ts:60`](../../frontend/src/schemas/authSchemas.ts#L60)

**UI-биндинг в основной форме**

- Условный `<select>` «Страна» для B2B-ролей (скрыт для retail)
  [`RegisterForm.tsx:266`](../../frontend/src/components/auth/RegisterForm.tsx#L266)

- Проброс `country` в payload `authService.register`
  [`RegisterForm.tsx:120`](../../frontend/src/components/auth/RegisterForm.tsx#L120)

- Дефолт «Россия» в `defaultValues` и маппинг backend-ошибок
  [`RegisterForm.tsx:93`](../../frontend/src/components/auth/RegisterForm.tsx#L93)

**Тесты**

- Рендер/скрытие селектора и submit с выбранной страной
  [`RegisterForm.test.tsx:864`](../../frontend/src/components/auth/__tests__/RegisterForm.test.tsx#L864)
</content>
</invoke>
