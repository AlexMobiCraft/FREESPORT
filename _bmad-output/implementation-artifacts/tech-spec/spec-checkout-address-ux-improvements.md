---
title: "Улучшение блока адреса доставки в форме чекаута"
type: "feature"
created: "2026-04-29"
status: "done"
baseline_commit: "96de87521c423f4b27e141e8ace363c75dfc23f6"
context:
  - "{project-root}/_bmad-output/planning-artifacts/checkout-address-ux.md"
  - "{project-root}/CLAUDE.md"
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В блоке адреса доставки чекаута авторизованным пользователям не подставляется их сохранённый адрес. Текущий код читает `user.addresses[0]`, но `/api/v1/users/me/` не возвращает массив адресов — автозаполнение фактически мёртвое. Нет выбора между сохранёнными адресами и нет способа сохранить новый адрес из чекаута в профиль.

**Approach:** При монтировании `CheckoutForm` авторизованного пользователя загружать его адреса типа `shipping` через `addressService.getAddresses()`. Подставлять адрес с `is_default=true`; если адресов больше одного — показать селектор (карточки) над полями; после ручного редактирования предлагать чекбокс «Запомнить этот адрес в профиле» — при согласии после успешного создания заказа делать `POST /api/v1/users/addresses/` (с `is_default=true`, если у юзера ещё нет адресов).

## Boundaries & Constraints

**Always:**
- Использовать существующие `addressService` (`frontend/src/services/addressService.ts`) и тип `Address` (`frontend/src/types/address.ts`). Не дублировать сервис, не менять контракты API.
- Поля API (`building`, `building_section`, `postal_code`, `full_name`) маппить на поля формы (`house`, `buildingSection`, `postalCode`, `firstName`+`lastName`) через единый helper. Никаких ad-hoc маппингов в компонентах.
- Фильтрация `address_type === "shipping"` — на фронте (API не поддерживает query-фильтр).
- Сохранение адреса в профиль не должно блокировать UX заказа: заказ уже создан — ошибка POST `/users/addresses/` показывается тостом, не откатывает заказ.
- Tailwind CSS, react-hook-form через существующий `form` instance, валидация без изменений `checkoutSchema`.

**Ask First:**
- Если потребуется менять тип `User` или `checkoutSchema` (поле, валидация). По умолчанию — не менять.
- Если рендер UI селектора потребует нового UI-примитива вне существующих (по умолчанию — кастомные карточки на Tailwind, как в `AddressList`).

**Never:**
- Не реализовывать редактирование/удаление адресов из чекаута (это раздел `/profile/addresses`).
- Не интегрировать DaData/внешний автокомплит.
- Не вызывать `getAddresses()` для гостей (неавторизованных).
- Не вызывать `getAddresses()` повторно после успешного `POST` на финальном шаге — заказ уже создан, обновление списка избыточно.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Гость | `isAuthenticated=false` | Селектор не рендерится; чекбокс «запомнить» скрыт; форма пустая | N/A |
| Авторизован, адресов нет | `getAddresses()` → `[]` | Селектор скрыт; после ввода адреса показывается чекбокс «Запомнить». Если выбран — POST с `is_default=true` | API упал — тост «не удалось загрузить адреса», форма остаётся пустой |
| Авторизован, 1 shipping-адрес | `[a1]` | Поля автозаполнены из `a1`; селектор скрыт; после редактирования чекбокс «Запомнить» (POST `is_default=false`) | Маппинг ошибся — fallback на пустые поля |
| Авторизован, 2+ shipping, есть `is_default` | `[a1{default}, a2, a3]` | Поля автозаполнены `is_default`-адресом; селектор показывает все 3 карточки, дефолт выделен | — |
| Авторизован, 2+ shipping, нет `is_default` | `[a1, a2]` | Поля автозаполнены первым из массива (бэк сортирует `-created_at`); селектор показан | — |
| Выбор другого адреса в селекторе | Клик по `a2` | Все поля формы перезаписываются данными `a2`; чекбокс «Запомнить» сбрасывается | — |
| Ручное редактирование после автозаполнения | Юзер меняет любое поле | Показывается чекбокс «Запомнить этот адрес в профиле»; в селекторе снимается выделение | — |
| Submit + чекбокс активен | Заказ создан, `saveAddress=true` | После `router.push(/checkout/success/...)` фоном `POST /users/addresses/` с маппингом полей | POST упал — тост-ошибка, заказ не откатывается |
| Submit + чекбокс активен, но адрес идентичен выбранному из селектора | Юзер выбрал из селектора, ничего не менял | Чекбокс не показывается — нечего сохранять | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/components/checkout/CheckoutForm.tsx` — оркестрирует загрузку адресов, маппит выбранный/дефолтный адрес в `defaultValues`, прокидывает selector-state в `AddressSection`, после `createOrder` запускает фоновое сохранение адреса.
- `frontend/src/components/checkout/AddressSection.tsx` — рендерит UI селектора (карточки) над существующими полями, чекбокс «Запомнить» под полями. Получает props: `addresses`, `selectedAddressId`, `onSelectAddress`, `showSaveCheckbox`, `saveAddress`, `onToggleSaveAddress`.
- `frontend/src/components/checkout/AddressCardOption.tsx` — **новый**, маленький presentational компонент карточки адреса для селектора (имя получателя, `full_address`, бейдж «по умолчанию», radio-state). Не переиспользуем `business/AddressCard` — там есть кнопки edit/delete.
- `frontend/src/utils/checkout/addressMapping.ts` — **новый** helper. Экспортирует `addressToFormValues(address: Address): Partial<CheckoutFormData>` и `formValuesToAddressPayload(data: CheckoutFormData): AddressFormData`. Содержит склейку `firstName + lastName ↔ full_name`.
- `frontend/src/services/addressService.ts` — **используем как есть** (getAddresses, createAddress).
- `frontend/src/types/address.ts` — **используем как есть** (тип `Address`, `AddressFormData`).
- `frontend/src/stores/authStore.ts` — источник `user`, `isAuthenticated` через `authSelectors`.
- `frontend/src/components/checkout/__tests__/AddressSection.test.tsx` — расширить: рендер селектора, переключение, чекбокс.
- `frontend/src/components/checkout/__tests__/CheckoutForm.test.tsx` — расширить: моки `addressService.getAddresses`/`createAddress`, ветки edge-cases из матрицы.

## Tasks & Acceptance

**Execution:**

- [x] `frontend/src/utils/checkout/addressMapping.ts` -- создать helper с двумя функциями (`addressToFormValues`, `formValuesToAddressPayload`) -- единая точка маппинга снимает риск рассинхронизации полей API ↔ формы.
- [x] `frontend/src/components/checkout/AddressCardOption.tsx` -- создать карточку выбора (radio-style, отображает `full_name`, `full_address`, бейдж `is_default`) -- переиспользуемая presentational единица для селектора.
- [x] `frontend/src/components/checkout/AddressSection.tsx` -- добавить рендер селектора (видим, если `addresses.length > 1`) и чекбокса «Запомнить» (видим по флагу из CheckoutForm); сохранить существующую разметку и тесты полей -- расширение без переломки.
- [x] `frontend/src/components/checkout/CheckoutForm.tsx` -- (1) убрать использование `userWithAddresses.addresses[0]`; (2) добавить `useEffect` загрузки адресов через `addressService.getAddresses()` для авторизованного юзера, фильтр по `address_type==="shipping"`; (3) state: `addresses`, `selectedAddressId`, `saveAddress`; (4) подписка `form.watch` для определения «изменено ли после автозаполнения»; (5) после `await createOrder(data)` — если `saveAddress && currentOrder?.id` — fire-and-forget `addressService.createAddress(...)` с `is_default = addresses.length===0`; (6) тосты на ошибки сохранения адреса (использовать `sonner`, как в `AddressList`).
- [x] `frontend/src/components/checkout/__tests__/AddressSection.test.tsx` -- добавить тесты: рендер селектора при `addresses.length>1`, скрытие при `<2`, переключение через клик, рендер чекбокса по флагу.
- [x] `frontend/src/components/checkout/__tests__/CheckoutForm.test.tsx` -- добавить тесты для всех строк I/O Matrix: моки `getAddresses` (пустой/один/несколько), ошибка API, submit с/без чекбокса, проверка вызова `createAddress` с правильным payload и `is_default`.

**Acceptance Criteria:**

- Given авторизованный юзер с одним shipping-адресом и `is_default=true`, when открывает `/checkout`, then поля адреса заполнены данными этого адреса, селектор адресов не виден.
- Given авторизованный юзер с тремя shipping-адресами (один `is_default`), when открывает `/checkout`, then над полями отображается селектор с тремя карточками, дефолтная выделена, поля автозаполнены из дефолтной.
- Given юзер выбрал в селекторе другой адрес, when селектор перерисовался, then все поля формы перезаписались данными выбранного адреса и чекбокс «Запомнить» скрыт.
- Given юзер вручную изменил `city` после автозаполнения, when поле потеряло фокус, then под полями появился чекбокс «Запомнить этот адрес в профиле» (по умолчанию выключен).
- Given чекбокс «Запомнить» включён, у юзера 0 сохранённых адресов, when форма успешно отправлена и `currentOrder.id` доступен, then выполнен `POST /api/v1/users/addresses/` с `is_default=true` и корректным маппингом всех полей; ошибка вызова не блокирует переход на success-страницу.
- Given гость на чекауте, when форма отрисована, then `addressService.getAddresses` не вызывается, селектор не рендерится, чекбокса «Запомнить» нет.
- Given API адресов вернул 500, when CheckoutForm смонтировался, then показан тост-ошибка, форма пустая, юзер может заполнить вручную и оформить заказ.
- Все существующие тесты `AddressSection.test.tsx` и `CheckoutForm.test.tsx` проходят без изменений ожидаемого поведения полей.

## Spec Change Log

### Loop 1 (2026-04-29) — adversarial + edge-case + acceptance review

**Finding:** `splitFullName` падал на `null/undefined` в `full_name`; race: поздний resolve `getAddresses` перезаписывал введённые пользователем данные; при logout адреса «протекали» в следующую сессию; `shouldValidate:false` оставлял фантом-ошибки; `is_default` race при медленной загрузке; stale `showSaveCheckbox` в `onSubmit`; тест POST createAddress молча пропускал проверку.

**Amended:**
- `addressMapping.ts`: `splitFullName` — null-guard (`string | null | undefined`).
- `CheckoutForm.tsx`:
  - `addressesLoaded` state — защищает `is_default` от ложного `true` до резолва API.
  - Race-guard в `getAddresses` useEffect — не перезаписывает поля, если юзер уже что-то ввёл.
  - Reset addresses при logout (`if (!isAuthenticated) { setAddresses([]); ... }`).
  - `form.clearErrors([...ADDRESS_FIELDS])` после `applyAddressToForm` — убирает фантомы.
  - `onSubmit` пересчитывает dirty-vs-address по валидированному `data`, а не по stale `showSaveCheckbox`.
  - Toast при ошибке `createAddress` убран (пользователь уже на success-странице — console.error достаточно).
- `AddressCardOption.tsx`: `break-words` на `full_address`.
- Тесты: добавлен mock `deliveryService`, rewrite POST test с полной формой + 3 новых edge-case теста.

**KEEP (positive preservation):**
- Единый `addressMapping.ts` как источник истины маппинга — не менять.
- Fire-and-forget паттерн для `createAddress` (без await перед router.push) — сохранить.
- `showSaveCheckbox` через `useMemo` + `form.watch` — архитектура верная, изменили только consumers.
- `AddressCardOption` — presentational без edit/delete — не перегружать.

## Design Notes

**Маппинг полей** (источник истины — `addressMapping.ts`):

```ts
// Address (API) → CheckoutFormData
{
  city, street, postal_code → postalCode,
  building → house,
  building_section → buildingSection,
  apartment,
  full_name → firstName + lastName (split на первый пробел: "Иван Иванов" → ["Иван", "Иванов"])
  phone
}
// CheckoutFormData → AddressFormData (POST payload)
{
  address_type: "shipping",
  full_name: `${firstName} ${lastName}`.trim(),
  phone, city, street,
  building: house, building_section: buildingSection ?? "",
  apartment: apartment ?? "",
  postal_code: postalCode,
  is_default: addresses.length === 0,
}
```

**Детект «изменено вручную»:** хранить в state `lastAppliedAddressId` (id адреса, чьи данные сейчас в полях, или `null` если не из адреса). Подписаться на `form.watch` для адресных полей; если значение поля отличается от соответствующего в `addresses.find(a=>a.id===lastAppliedAddressId)` — выставить флаг `isManuallyEdited=true`. Чекбокс «Запомнить» рендерится только при `isAuthenticated && isManuallyEdited`.

**UI селектора:** горизонтальный grid карточек (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3`), каждая — clickable card с border, выбранная — `border-blue-500 bg-blue-50`. Бейдж «По умолчанию» — `text-xs bg-blue-100 text-blue-700 rounded px-2 py-0.5`. Стилистика консистентна с `AddressCard` из профиля, но без кнопок edit/delete.

**Fire-and-forget сохранение:** не `await` перед `router.push`. Вызвать `addressService.createAddress(payload).catch(err => toast.error(...))` параллельно с навигацией. Заказ уже создан — UX заказа не должен зависеть от сохранения адреса.

## Verification

**Commands:**

- `cd frontend && npm run test -- src/components/checkout/__tests__/AddressSection.test.tsx` — все тесты зелёные, новые покрывают селектор и чекбокс.
- `cd frontend && npm run test -- src/components/checkout/__tests__/CheckoutForm.test.tsx` — все тесты зелёные, покрыты строки I/O Matrix.
- `cd frontend && npx tsc --noEmit` — без ошибок типов.
- `cd frontend && npm run lint` — без новых предупреждений.

**Manual checks:**

- Залогиниться юзером с 0/1/3 shipping-адресами (создать через `/profile/addresses` если нужно), открыть `/checkout`, проверить визуально все ветки матрицы. Убедиться, что чекбокс появляется только после реального изменения поля. Submit-flow → проверить в DevTools Network, что `POST /users/addresses/` уходит после `POST /orders/` и не блокирует редирект.

## Suggested Review Order

**Entry point: orchestration and state management**

- Core checkout form — loads addresses, manages selection/dirty/save state, fire-and-forget save
  [`CheckoutForm.tsx:61`](../../../frontend/src/components/checkout/CheckoutForm.tsx#L61)

- Address loading useEffect — race guard, auth reset, addressesLoaded flag
  [`CheckoutForm.tsx:130`](../../../frontend/src/components/checkout/CheckoutForm.tsx#L130)

- Submit handler — dirty recalc from validated `data`, shouldSaveAddress guard
  [`CheckoutForm.tsx:224`](../../../frontend/src/components/checkout/CheckoutForm.tsx#L224)

**Mapping layer (API ↔ form)**

- Null-safe splitFullName, addressToFormValues, formValuesToAddressPayload, isFormDirtyVsAddress
  [`addressMapping.ts:35`](../../../frontend/src/utils/checkout/addressMapping.ts#L35)

**UI components**

- Address section — selector grid, save checkbox, existing fields preserved
  [`AddressSection.tsx:36`](../../../frontend/src/components/checkout/AddressSection.tsx#L36)

- Radio-style card with break-words, is_default badge, Check icon
  [`AddressCardOption.tsx:21`](../../../frontend/src/components/checkout/AddressCardOption.tsx#L21)

**Tests**

- 27 CheckoutForm tests — I/O Matrix, address loading, POST save, edge-cases
  [`CheckoutForm.test.tsx:1`](../../../frontend/src/components/checkout/__tests__/CheckoutForm.test.tsx#L1)

- 21 AddressSection tests — selector, checkbox, existing field tests preserved
  [`AddressSection.test.tsx:1`](../../../frontend/src/components/checkout/__tests__/AddressSection.test.tsx#L1)
