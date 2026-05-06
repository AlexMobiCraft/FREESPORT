# Задача разработчику: улучшение блока адреса доставки в форме заказа

**Дата:** 2026-04-29  
**Приоритет:** средний  
**Статус:** открыта

---

## Контекст

В текущей реализации (`CheckoutForm` / `AddressSection`) адрес доставки заполняется вручную. При наличии авторизованного пользователя поля автозаполняются из `user.addresses[0]` — первого адреса в массиве, без учёта флага `is_default` и без возможности выбрать другой адрес. Нужно доработать этот блок в трёх направлениях.

---

## Требования

### 1. Автозаполнение из адреса по умолчанию

Если пользователь авторизован и у него есть сохранённые адреса — подставлять в поля формы адрес с флагом `is_default = true` и `address_type = "shipping"` (а не просто первый в массиве).

Текущее поведение (исправить):
```typescript
city: user?.addresses?.[0]?.city || ""
```
Ожидаемое поведение:
```typescript
const defaultAddress = user?.addresses?.find(a => a.is_default && a.address_type === "shipping")
city: defaultAddress?.city || ""
```

---

### 2. Выбор адреса из сохранённых (если адресов больше одного)

Если у авторизованного пользователя `addresses.length > 1` — показывать над полями формы UI для выбора адреса (выпадающий список или группу карточек). При выборе адреса — заполнять поля формы данными выбранного адреса.

Если адрес только один или пользователь не авторизован — блок выбора не показывать, только поля ввода.

Адреса получать через уже реализованный API:
```
GET /api/v1/users/addresses/
```
Фильтровать по `address_type = "shipping"`.

---

### 3. Предложение сохранить новый/изменённый адрес в профиль

Если авторизованный пользователь вручную изменил поля адреса (или ввёл адрес впервые), — перед отправкой заказа показывать чекбокс или небольшой prompt:

> «Запомнить этот адрес в профиле?»

При согласии — после успешного создания заказа выполнять:
```
POST /api/v1/users/addresses/
{ address_type: "shipping", city, street, house, apartment, postal_code, is_default: false }
```

Если у пользователя нет ни одного адреса — предлагать сохранить с `is_default: true`.

---

## Документы для реализации

| Документ | Что нужно |
|---|---|
| `raw/docs/archive/v4/stories/epic-15/15.1.checkout-page-form.md` | Текущая реализация `AddressSection.tsx`, схема Zod, автозаполнение `defaultValues`, структура тестов |
| `raw/docs/archive/v4/stories/epic-15/15.2.orders-api-integration.md` | Тип `CreateOrderPayload` — поле `delivery_address`, как адрес идёт в заказ |
| `raw/docs/archive/v4/epics/epic-15/epic-15-checkout.md` | Общая архитектура checkout, упоминание `/profile/addresses` как опциональной интеграции |
| `raw/docs/archive/releases/personal_cabinet_api_v1.0.md` | API адресов: `GET/POST /api/v1/users/addresses/`, структура ответа, флаг `is_default` |
| `raw/docs/archive/v4/epics/epic-2/story-2.3-personal-cabinet-api-decisions.md` | Модель `Address`: поля `address_type`, `is_default`, логика автосброса флага default при сохранении нового |

---

## Затрагиваемые файлы

- `frontend/src/components/checkout/AddressSection.tsx` — основные изменения UI
- `frontend/src/components/checkout/CheckoutForm.tsx` — логика выбора/сохранения адреса
- `frontend/src/schemas/checkoutSchema.ts` — схема без изменений, но учесть совместимость
- `frontend/src/services/` — добавить или расширить сервис для `GET/POST /api/v1/users/addresses/`
- `frontend/src/types/` — добавить тип `Address` с полями `id`, `address_type`, `is_default`, `city`, `street`, `house`, `apartment`, `postal_code`

---

## Не входит в задачу

- Управление адресами в личном кабинете (редактирование/удаление) — это отдельный раздел профиля, уже реализован
- Интеграция с внешними сервисами автокомплита адресов (DaData и пр.) — отдельная задача
