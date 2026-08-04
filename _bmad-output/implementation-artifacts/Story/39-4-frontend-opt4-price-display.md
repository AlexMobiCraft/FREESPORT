---
baseline_commit: 0e005137f0fae00a93cfcc3535a6cef3a3adb0ba
---

# Story 39.4: Фронтенд показывает цену уровня 4

Status: done

> 🚧 **БЛОКИРУЮЩЕЕ ПРЕДУСЛОВИЕ — стори 39.3 должна быть реализована и влита.**
> Проверено на `0e005137`: `docs/api/openapi.yaml` содержит **0** вхождений `opt4_price` и **0** вхождений `wholesale_level4`. Пока 39.3 не сдана, AC1 физически невыполним — `npm run generate:types` перегенерирует `api.generated.ts` без нового поля и роли, и Task 1 «пройдёт» вхолостую.
> **Первое действие дева:** выполнить проверку из Task 0. Если она даёт 0 — остановиться и сообщить Alex, а не «обойти» регенерацию ручной правкой файла.

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Оптовый клиент четвёртого уровня**,
I want **видеть свою цену на витрине — в каталоге, карточке товара и блоках главной страницы**,
so that **я видел актуальные для меня условия, а не розничную цену**.

## Acceptance Criteria

1. **AC1 (FR-39-13, NFR-3940-07). Регенерация типов из контракта.** После `npm run generate:types` файл `frontend/src/types/api.generated.ts` содержит `readonly opt4_price: number;` в схемах `ProductList` и `ProductDetail` и `'wholesale_level4'` в `RoleEnum`. Команда запускается **с хоста** из каталога `frontend/` — контейнер frontend монтирует только `../frontend:/app`, каталога `docs/` внутри нет. Файл правится **только генератором**.
2. **AC2 (FR-39-11). Рукописные типы.** Четыре правки, все обязательны:
   (а) `frontend/src/types/index.ts:25` — `wholesale_level4` в union `UserRole`;
   (б) `frontend/src/types/api.ts:18` — `wholesale_level4` в union `User['role']`;
   (в) `frontend/src/types/api.ts:47` — `opt4_price?: number;` в интерфейсе `Product`;
   (г) `frontend/src/types/api.ts:299` — `level4?: number;` в `ProductPrice.wholesale`.
   Пункт (г) в задании `§B3` **не перечислен**, но без него `pricing.ts` не скомпилируется (AC3 читает `price.wholesale?.level4`), а `productsService` не сможет положить туда значение (AC5).
3. **AC3 (FR-39-11). Утилита ценообразования.** В `frontend/src/utils/pricing.ts`: `wholesale_level4` добавлен в union `UserRole` (`:11`), в предикат `isB2BRole` (`:29`) и в `switch` функции `getPriceForRole` (`:49`) веткой `return price.wholesale?.level4 || price.retail`. Каскада `level4 → level3 → …` здесь **нет** — форма ветки совпадает с уровнями 1-3 (каскад живёт только в `ProductCard`, см. AC6). Через `isB2BRole` роль автоматически получает право видеть РРЦ в `ProductCard` (`:438`, `:562`) — это соответствует правке `INFO_PRICE_ROLES` на бэкенде в стори 39.3.
4. **AC4 (FR-39-11). Списки B2B-ролей.** `wholesale_level4` присутствует во всех трёх: `frontend/src/utils/server-auth.ts:45` (массив `validRoles` — без него SSR-профиль оптовика уровня 4 схлопнется в `retail`), `frontend/src/stores/authStore.ts:137` (`B2B_ROLES` — питает селектор `useIsB2BUser`), `frontend/src/schemas/authSchemas.ts:167` (`role`-enum схемы `b2bRegisterSchema`). Пропуск любого даёт молчаливый дефект без ошибки сборки.
5. **AC5 (FR-39-11). Сервис товаров.** В `frontend/src/services/productsService.ts`: `opt4_price?: number;` в DTO `ApiProductDetailResponse` (`:43`) и `level4: apiProduct.opt4_price,` в маппинге `price.wholesale` внутри `adaptProductToDetail` (`:125`). Без второй правки карточка товара получит `wholesale.level4 === undefined`, и `getPriceForRole` тихо вернёт розницу.
6. **AC6 (FR-39-11). Каскад в `ProductCard`.** В `getProductPrice` (`frontend/src/components/business/ProductCard/ProductCard.tsx:111-135`) появляется ветка `case 'wholesale_level4'` **после** `wholesale_level3`, реализующая каскад `opt4 → opt3 → opt2 → opt1 → retail`. Расхождение этого каскада с бэкендовым fallback (сразу `retail_price`) существует для уровней 1-3 и в этой стори **не чинится** — не «выравнивать» ни ту, ни другую сторону.
7. **AC7 (FR-39-11). Восемь точек списков оптовых ролей.** Пользователь с ролью `wholesale_level4` получает оптовое отображение во всех восьми: `components/product/ProductInfo.tsx:58-64` (`canSeeRrp`), `app/(blue)/catalog/page.tsx:378-385` (`isB2B`), `components/home/HitsSection.tsx:104-111`, `NewArrivalsSection.tsx:42-49`, `PromoSection.tsx:41-48`, `SaleSection.tsx:41-48` (`isB2B`), `components/home/HeroSection.tsx:97-101` и `ElectricHeroSection.tsx:134-138` (цепочка `user?.role === …`). Два последних — **другой формы** (не массив), править их копипастой массива нельзя.
8. **AC8 (NFR-3940-03). Тесты Vitest.** Покрыты: `getPriceForRole` для роли уровня 4 (значение из `wholesale.level4` и fallback на `retail` при его отсутствии); `isB2BRole('wholesale_level4') === true`; каскад в `ProductCard` — отдаётся `opt4_price`, а при его отсутствии `opt3_price`. Тесты добавляются в существующие файлы `src/utils/__tests__/pricing.test.ts` и `src/components/business/ProductCard/__tests__/ProductCard.test.tsx`, новых файлов не заводить.
9. **AC9. Зелёная сборка и стиль.** `npx tsc --noEmit`, `npm run lint`, `npm run format:check` и `npm run test` проходят; регрессии относительно базовой линии из Dev Notes нет. `api.generated.ts` после генерации приведён к prettier-стилю проекта (генератор выдаёт двойные кавычки, в репозитории — одинарные).

## Tasks / Subtasks

- [x] **Task 0: Проверка блокирующего предусловия** (AC: 1)
  - [x] 0.1: Из корня репозитория выполнить `grep -c "opt4_price" docs/api/openapi.yaml` и `grep -c "wholesale_level4" docs/api/openapi.yaml`
  - [x] 0.2: Если хотя бы один результат `0` — **остановиться**, сообщить Alex «стори 39.3 не влита, 39.4 стартовать нельзя». Не править `openapi.yaml` и не дописывать `api.generated.ts` руками
  - [x] 0.3: Если оба > 0 — зафиксировать в Completion Notes фактический коммит 39.3, поверх которого работаешь

- [x] **Task 1: Регенерация типов** (AC: 1, 9)
  - [x] 1.1: С хоста, из каталога `frontend/`: `npm run generate:types`
  - [x] 1.2: Проверить diff: `opt4_price` в `ProductList` и `ProductDetail`, `wholesale_level4` в `RoleEnum`
  - [x] 1.3: Привести файл к стилю проекта: `npx prettier --write src/types/api.generated.ts` (иначе `format:check` упадёт на кавычках)
  - [x] 1.4: Файл руками **не** править — он помечен `Do not make direct changes to the file`

- [x] **Task 2: Рукописные типы** (AC: 2)
  - [x] 2.1: `src/types/index.ts:25` — `| 'wholesale_level4'` после `'wholesale_level3'`
  - [x] 2.2: `src/types/api.ts:18` — то же в union `User['role']`
  - [x] 2.3: `src/types/api.ts:47` — `opt4_price?: number;` после `opt3_price?: number;`
  - [x] 2.4: `src/types/api.ts:299` — `level4?: number;` в `ProductPrice.wholesale` после `level3?: number;`
  - [x] 2.5: Делать **до** остальных задач: `authStore.B2B_ROLES` типизирован как `Array<User['role']>`, и без 2.2 правка AC4 не скомпилируется

- [x] **Task 3: Утилита `pricing.ts`** (AC: 3)
  - [x] 3.1: `:11` — `| 'wholesale_level4'` в union `UserRole` после `'wholesale_level3'`
  - [x] 3.2: `:29` — `role === 'wholesale_level4' ||` в `isB2BRole` после ветки level3
  - [x] 3.3: `:49` — `case 'wholesale_level4': return price.wholesale?.level4 || price.retail;` после кейса level3
  - [x] 3.4: Комментарий над `isB2BRole` про `unregistered`/`guest` **не трогать** — он объясняет исключения, а не состав

- [x] **Task 4: Списки B2B-ролей** (AC: 4)
  - [x] 4.1: `src/utils/server-auth.ts:45` — `'wholesale_level4',` в `validRoles` после `'wholesale_level3',`
  - [x] 4.2: `src/stores/authStore.ts:137` — то же в `B2B_ROLES`
  - [x] 4.3: `src/schemas/authSchemas.ts:167` — `'wholesale_level4',` в `z.enum` поля `role` схемы `b2bRegisterSchema`
  - [x] 4.4: `registerSchema` (`authSchemas.ts:54`) и `ROLE_OPTIONS` (`components/auth/RegisterForm.tsx:52-57`) **не трогать** — там нет ни уровня 2, ни уровня 3 (см. Dev Notes → «Мина: две схемы регистрации»)

- [x] **Task 5: Сервис товаров** (AC: 5)
  - [x] 5.1: `src/services/productsService.ts:43` — `opt4_price?: number;` после `opt3_price?: number;` в `ApiProductDetailResponse`
  - [x] 5.2: `src/services/productsService.ts:125` — `level4: apiProduct.opt4_price,` после строки `level3: …`

- [x] **Task 6: Каскад в `ProductCard`** (AC: 6)
  - [x] 6.1: `ProductCard.tsx` — ветка `case 'wholesale_level4'` после level3 (точный код — в Dev Notes; однострочником не влезает в `printWidth: 100`)
  - [x] 6.2: Ветки `trainer` / `federation_rep` / `default` **не трогать**
  - [x] 6.3: `isB2BRole` в `ProductCard:438,562` правок не требует — подхватится из `pricing.ts` (Task 3.2)

- [x] **Task 7: Восемь точек списков оптовых ролей** (AC: 7)
  - [x] 7.1: `src/components/product/ProductInfo.tsx:61` — `'wholesale_level4',` после `'wholesale_level3',`; обновить комментарий на `:57` («оптовики (1-4)»)
  - [x] 7.2: `src/app/(blue)/catalog/page.tsx:381` — то же в `isB2B`
  - [x] 7.3: `src/components/home/HitsSection.tsx:107` — то же
  - [x] 7.4: `src/components/home/NewArrivalsSection.tsx:45` — то же
  - [x] 7.5: `src/components/home/PromoSection.tsx:44` — то же
  - [x] 7.6: `src/components/home/SaleSection.tsx:44` — то же
  - [x] 7.7: `src/components/home/HeroSection.tsx:100` — `|| user?.role === 'wholesale_level4'` в цепочку `if`
  - [x] 7.8: `src/components/home/ElectricHeroSection.tsx:137` — то же
  - [x] 7.9: Контроль полноты: `grep -rn "wholesale_level3" frontend/src --include=*.ts --include=*.tsx` — рядом с каждым вхождением в **исходниках** должен появиться уровень 4 (тестовые файлы и `api.generated.ts` — исключения, см. Dev Notes)

- [x] **Task 8: Тесты** (AC: 8)
  - [x] 8.1: `src/utils/__tests__/pricing.test.ts` — `level4: 10490` в `mockPrice.wholesale`; кейс «возвращает wholesale level4 для роли wholesale_level4»
  - [x] 8.2: Там же — кейс fallback: `priceWithoutWholesale` и `partialWholesale` уже существуют (`:55-61`, `:80-91`), добавить в них проверку роли уровня 4
  - [x] 8.3: Там же — новый `describe('isB2BRole')` либо кейс внутри существующего: `isB2BRole('wholesale_level4') === true`, `isB2BRole('unregistered') === false` (сторож обратной стороны)
  - [x] 8.4: `ProductCard.test.tsx` — `opt4_price: 700` в `mockProduct` (`:74-82`); кейс `displays wholesale level 4 pricing` → `700 ₽`
  - [x] 8.5: Там же — кейс каскада: `{ ...mockProduct, opt4_price: undefined }` с `userRole="wholesale_level4"` → `800 ₽` (падение на `opt3_price`)
  - [x] 8.6: Проверить, что существующие кейсы уровней 1-3 (`:225-243`) не сломались от нового поля в `mockProduct`

- [x] **Task 9: Прогон, стиль, сборка** (AC: 9)
  - [x] 9.1: `npx tsc --noEmit` из `frontend/`
  - [x] 9.2: `npm run test` — сверить с базовой линией из Dev Notes
  - [x] 9.3: `npm run lint` и `npm run format:check`
  - [x] 9.4: `docker compose --env-file .env -f docker/docker-compose.yml restart frontend` — правки `frontend/src/` требуют рестарта контейнера (`project-context.md` §1)
  - [x] 9.5: `npx gitnexus detect-changes --scope all` перед коммитом

## Dev Notes

### Что уже сделано в 39.1-39.3 — переделывать НЕ нужно

| Слой | Состояние |
|---|---|
| `ProductVariant.opt4_price`, `get_price_for_user`, `PriceType`, `ROLE_CHOICES`, `B2B_ROLES`, `ONEC_EXCHANGE` | ✅ 39.1 |
| Маппинг «Опт 4» в парсере 1С, сбросы цен в `variant_import` | ✅ 39.2 |
| Фильтры каталога, `opt4_price` в сериализаторах, `Prefetch`, админка, `SELF_SERVICE_ROLES`, баннеры, фабрики, `openapi.yaml` | ✅ 39.3 (**предусловие этой стори**) |
| Гейт видимости оптовых цен `apps/products/pricing_policy.py` (`WHOLESALE_PRICE_FIELDS`, `INFO_PRICE_ROLES`) | ✅ `security-wholesale-price-visibility` |

Эта стори — **только `frontend/`**. Ни одного файла в `backend/` и `docs/` не трогает.

### ⚠️ Мина №1: `api.generated.ts` никем не импортируется

`grep -rn "api\.generated" frontend/src` даёт **ноль** импортов: файл генерируется и коммитится, но приложение его не использует. Все потребители — рукописные: `types/api.ts`, `types/index.ts`, `services/productsService.ts`, `utils/pricing.ts`.

**Следствие, критичное для планирования:** формулировка AC1 из epics.md «…а сборка TypeScript проходит» выполняется **тривиально** — регенерация ничего не ломает и ничего не чинит. Реальная работа стори — Tasks 2-7 по рукописным типам и компонентам. Не считать Task 1 доказательством того, что фронт «увидел» роль: он не увидит её ни на йоту, пока не сделаны Tasks 2-3.

Долг зафиксирован (`tech-debt.md` п. 20, 2026-08-03), формулировка NFR-3940-07 в `epics.md` в том же заходе исправлена — прежнее «рассинхрон ломает сборку фронта» было неверно. Устранение долга (CI-гейт на регенерацию либо типизация DTO-слоя от `components['schemas']`) в объём этой стори **не входит**.

### ⚠️ Мина №2: `ProductPrice.wholesale.level4` в задании не перечислен

Задание (`dev-task-role-from-1c-agreement.md` §B3) называет `types/api.ts:18,47` — union роли и `Product.opt4_price`. Но `getPriceForRole` (AC3) читает `price.wholesale?.level4`, а `adaptProductToDetail` (AC5) туда пишет — оба обращаются к типу `ProductPrice` (`types/api.ts:294-304`), где перечислены только `level1..level3`. Без правки (г) из AC2 `tsc` упадёт с `Property 'level4' does not exist`. Правка обязательна, хотя в списке задания её нет.

### ⚠️ Мина №3: две схемы регистрации, править нужно ровно одну

| Схема | Роли | Правим? |
|---|---|---|
| `registerSchema` (`authSchemas.ts:54`) — форма `RegisterForm.tsx` | `retail`, `trainer`, `wholesale_level1`, `federation_rep` | **НЕТ** — там нет ни level2, ни level3 |
| `b2bRegisterSchema` (`authSchemas.ts:164-170`) — форма `B2BRegisterForm.tsx` | `wholesale_level1..3`, `trainer`, `federation_rep` | **ДА** (AC4) |

`ROLE_OPTIONS` в `RegisterForm.tsx:52-57` показывает единственный оптовый пункт с ярлыком «Оптовик» (`wholesale_level1`) — уровни в этой форме не выбираются вовсе. Добавление туда четвёртого уровня — расширение UX за пределы стори. `isB2BRole` в `RegisterForm.tsx:176` — это **локальная константа** `selectedRole !== 'retail'`, одноимённая с функцией из `pricing.ts`, но не она; правок не требует.

### ⚠️ Мина №4: prettier поверх генератора

`api.generated.ts` не входит в `.prettierignore`, а в репозитории лежит в prettier-стиле (одинарные кавычки, `printWidth: 100`). `openapi-typescript@7` выдаёт двойные кавычки. Если не прогнать `prettier --write` после генерации, `npm run format:check` упадёт. При коммите то же сделает `lint-staged` (`prettier --write` на `*.ts`), но проверять AC9 нужно до коммита.

### Blast radius (GitNexus pre-flight выполнен)

| Символ | Risk | Прямых вызывающих |
|---|---|---|
| `getPriceForRole` (`utils/pricing.ts`) | **LOW** | 1 — `ProductInfo` |
| `adaptProductToDetail` (`services/productsService.ts`) | **LOW** | 1 — `ProductsService.getProductBySlug` |
| `isB2BRole` (`utils/pricing.ts`) | **LOW** | 2 вызова в `ProductCard` (`:438`, `:562`) — отображение РРЦ |
| `getProductPrice` (`ProductCard.tsx`) | 🔴 **CRITICAL** | 1 прямой (`ProductCard`), **8 процессов**, 4 модуля |

🔴 **CRITICAL у `getProductPrice`.** GitNexus насчитал 12 затронутых узлов и 8 процессов: `SearchPage`, `SearchPageClient`, `CatalogContent`, `BlueHomePage`, `ElectricHomePage`, `PromoSection`, `NewArrivalsSection`, `SaleSection` — то есть **все страницы, где рендерится карточка товара**. Это следствие центральности `ProductCard`, а не опасности самой правки: изменение **строго аддитивное** — новый `case` в `switch`, который сегодня не достижим ни для одной существующей роли (`wholesale_level4` во фронтовом union'е пока отсутствует). Сигнатура, тип возврата и все существующие ветки не меняются, поэтому ни один из восьми процессов поведения не меняет. Риск реализуется **только** если дев тронет соседние ветки или `default` — этого делать нельзя.

⚠️ Индекс GitNexus на момент подготовки стори был `stale` относительно `0e005137`, но расхождение — два markdown-файла (`Story/security-wholesale-price-visibility.md`, `tech-debt.md`); `frontend/` не менялся, координаты и радиус актуальны. Незакоммиченный `backend/conftest.py` в индекс не попал — на эту стори не влияет (backend не трогаем).

### Точный код: типы

`frontend/src/types/index.ts` (после `| 'wholesale_level3'`, `:25`):

```ts
  | 'wholesale_level4'
```

`frontend/src/types/api.ts`, union `User['role']` (после `| 'wholesale_level3'`, `:18`):

```ts
    | 'wholesale_level4'
```

`frontend/src/types/api.ts`, интерфейс `Product` (после `opt3_price?: number;`, `:47`):

```ts
  opt4_price?: number;
```

`frontend/src/types/api.ts`, `ProductPrice.wholesale` (после `level3?: number;`, `:299`):

```ts
    level4?: number;
```

### Точный код: `utils/pricing.ts`

Union `UserRole` (после `:11`):

```ts
  | 'wholesale_level4'
```

`isB2BRole` (после строки `role === 'wholesale_level3' ||`, `:29`):

```ts
    role === 'wholesale_level4' ||
```

`getPriceForRole` (после кейса `wholesale_level3`, `:49-50`):

```ts
    case 'wholesale_level4':
      return price.wholesale?.level4 || price.retail;
```

**Почему без каскада.** Форма один в один с уровнями 1-3: пустая цена уровня → сразу `price.retail`. Каскад по уровням живёт только в `ProductCard.getProductPrice` — это предсуществующее расхождение двух реализаций на фронте, зафиксированное в epics.md как «вне объёма». Не сводить их здесь: `getPriceForRole` питает карточку товара (`ProductInfo`), и введение каскада изменило бы цену для уровней 1-3.

### Точный код: списки B2B-ролей

`frontend/src/utils/server-auth.ts` (после `'wholesale_level3',`, `:45`):

```ts
      'wholesale_level4',
```

`frontend/src/stores/authStore.ts` (после `'wholesale_level3',`, `:137`):

```ts
  'wholesale_level4',
```

`frontend/src/schemas/authSchemas.ts` (после `'wholesale_level3',`, `:167`):

```ts
      'wholesale_level4',
```

Порядок правок важен: `B2B_ROLES` объявлен как `Array<User['role']>`, поэтому `types/api.ts` (Task 2.2) должен быть поправлен раньше, иначе `tsc` отвергнет литерал.

### Точный код: `services/productsService.ts`

DTO `ApiProductDetailResponse` (после `opt3_price?: number;`, `:43`):

```ts
  opt4_price?: number;
```

Маппинг в `adaptProductToDetail` (после `level3: apiProduct.opt3_price,`, `:125`):

```ts
        level4: apiProduct.opt4_price,
```

DTO списочного эндпоинта отдельного интерфейса не имеет — списки типизированы `Product` из `types/api.ts`, поэтому Task 2.3 закрывает и их.

### Точный код: каскад в `ProductCard`

`frontend/src/components/business/ProductCard/ProductCard.tsx`, `getProductPrice` — **после** ветки `wholesale_level3` (`:119-120`) и **до** `trainer`:

```ts
    case 'wholesale_level4':
      return (
        product.opt4_price ||
        product.opt3_price ||
        product.opt2_price ||
        product.opt1_price ||
        product.retail_price
      );
```

Однострочная форма (как у level3) даёт ~120 символов при `printWidth: 100` в `.prettierrc` — prettier всё равно развернёт её в скобки. Писать сразу в развёрнутом виде, чтобы `format:check` не расходился с коммитом.

### Точный код: восемь точек списков оптовых ролей

**Форма A — массив ролей (6 файлов).** Вставить `'wholesale_level4',` после `'wholesale_level3',`:

| Файл | Строка | Переменная |
|---|---|---|
| `src/components/product/ProductInfo.tsx` | `:61` | `canSeeRrp` |
| `src/app/(blue)/catalog/page.tsx` | `:381` | `isB2B` |
| `src/components/home/HitsSection.tsx` | `:107` | `isB2B` |
| `src/components/home/NewArrivalsSection.tsx` | `:45` | `isB2B` |
| `src/components/home/PromoSection.tsx` | `:44` | `isB2B` |
| `src/components/home/SaleSection.tsx` | `:44` | `isB2B` |

В `ProductInfo.tsx` заодно поправить комментарий `:57` — сейчас там `// RRP видят только оптовики (1-3), тренеры и админы`, станет `(1-4)`. Комментарий — часть контракта чтения, оставлять расходящимся нельзя.

**Форма B — цепочка сравнений (2 файла).** `src/components/home/HeroSection.tsx:97-101` и `src/components/home/ElectricHeroSection.tsx:134-138` устроены иначе:

```ts
    if (
      user?.role === 'wholesale_level1' ||
      user?.role === 'wholesale_level2' ||
      user?.role === 'wholesale_level3' ||
      user?.role === 'wholesale_level4'
    ) {
      return STATIC_BANNERS[0];
    }
```

Это fallback-баннер главной, когда API баннеров ничего не вернул. Обе цепочки перечисляют **только оптовые уровни** (без `trainer`/`federation_rep`/`admin`) — не «дополнять до полного списка B2B», состав здесь другой намеренно.

**Почему рефакторинг запрещён.** Списки — сознательно принятый долг эпика (`tech-debt.md` п. 17, решение Alex 2026-08-01): роль дописывается во все точки как есть, сведение к единому предикату `isWholesaleRole()` в объём **не входит**.

### Контроль полноты правок

```bash
cd /c/Users/1/DEV/FREESPORT
grep -rn "wholesale_level3" frontend/src --include=*.ts --include=*.tsx
```

Ожидаемые вхождения **без** соседнего `wholesale_level4` после правок — только эти:

| Файл | Почему остаётся один |
|---|---|
| `src/types/api.generated.ts` | генерируется; уровень 4 там появляется из `RoleEnum` отдельной строкой |
| `src/components/business/ProfileForm/ProfileForm.test.tsx:112` | тест перебирает роли для проверки B2B-полей формы; расширение — вне AC |
| `src/utils/__tests__/pricing.test.ts` | существующие кейсы уровня 3 остаются, рядом добавляются кейсы уровня 4 |
| `src/components/business/ProductCard/__tests__/ProductCard.test.tsx:239` | то же |

Всё остальное обязано иметь пару.

### Тесты: что и куда

**`src/utils/__tests__/pricing.test.ts`** — файл уже покрывает `getPriceForRole` по всем ролям и `formatPrice`. Правки:

1. `mockPrice.wholesale` (`:12-16`) — добавить `level4: 10490,` (ниже level3 `10790`, порядок значений в моке убывающий);
2. новый кейс рядом с `:34`:

```ts
  it('возвращает wholesale level4 для роли wholesale_level4', () => {
    expect(getPriceForRole(mockPrice, 'wholesale_level4')).toBe(10490);
  });
```

3. в существующих сценариях fallback (`:55-61` — `priceWithoutWholesale`, `:80-91` — `partialWholesale`) добавить проверку роли уровня 4 → `12990` (retail);
4. сторож предиката:

```ts
describe('isB2BRole', () => {
  it('относит wholesale_level4 к B2B', () => {
    expect(isB2BRole('wholesale_level4')).toBe(true);
  });

  it('не относит unregistered к B2B', () => {
    expect(isB2BRole('unregistered')).toBe(false);
  });
});
```

Импорт в шапке файла (`:6`) дополнить: `import { getPriceForRole, formatPrice, isB2BRole } from '../pricing';`.

**`src/components/business/ProductCard/__tests__/ProductCard.test.tsx`** — `mockProduct` (`:74-82`) имеет `retail_price: 1200, opt1_price: 1000, opt2_price: 900, opt3_price: 800`. Добавить `opt4_price: 700,` после `opt3_price`. Кейсы — в блок с ролевым ценообразованием (рядом с `:237-243`):

```ts
    it('displays wholesale level 4 pricing', () => {
      render(
        <ProductCard product={mockProduct} userRole="wholesale_level4" mode="b2b" layout="grid" />
      );

      expect(screen.getByText('700 ₽')).toBeInTheDocument();
    });

    it('falls back to level 3 price when opt4 is missing', () => {
      const productWithoutOpt4 = { ...mockProduct, opt4_price: undefined };
      render(
        <ProductCard product={productWithoutOpt4} userRole="wholesale_level4" mode="b2b" layout="grid" />
      );

      expect(screen.getByText('800 ₽')).toBeInTheDocument();
    });
```

Второй кейс — единственная проверка того, что каскад действительно каскад, а не копия ветки level3. `formatPrice` рендерит через `Intl.NumberFormat('ru-RU')` с неразрывным пробелом-разделителем — для четырёхзначных сумм (`700`, `800`) разделителя нет, поэтому строки простые; при выборе других значений сверяться с существующими кейсами (`'1 000 ₽'`).

Добавление `opt4_price` в `mockProduct` существующие кейсы уровней 1-3 не задевает: их ветки `switch` до `opt4_price` не доходят.

**Моки `src/__mocks__/products.ts` и `src/__mocks__/productDetail.ts`** (демо-данные и MSW) уровень 4 не получают — это вне AC. Если решишь дополнить, делай во **всех** записях сразу и вынеси отдельным пунктом в Completion Notes.

### Каскад фронта против fallback бэка

| Слой | Поведение при пустой `opt4_price` |
|---|---|
| Бэкенд `get_price_for_user`, фильтры каталога | сразу `retail_price` |
| Фронт `getPriceForRole` (`ProductInfo`) | сразу `price.retail` |
| Фронт `getProductPrice` (`ProductCard`) | каскад `opt4 → opt3 → opt2 → opt1 → retail` |

Расхождение существует для уровней 1-3, зафиксировано в epics.md («Вне объёма») и в этой стори **не чинится**. Уровень 4 воспроизводит ту же асимметрию намеренно.

### Приёмка эпика — почему зелёные тесты ≠ готово

По замеру прода на 2026-08-03 `opt4_price` пуст у **100 % вариантов (16 309 из 16 309)** — вид цен «Опт 4» в 1С не заполнен ни у одной номенклатуры. После выката всех четырёх стори клиент с ролью `wholesale_level4` увидит **розничную** цену, и это корректная работа кода. Критерий закрытия эпика 39 — непустой `opt4_price` в проде: (1) заполнить вид цен «Опт 4» в 1С, (2) прогнать выгрузку цен. Оба шага — вне этой стори; в Completion Notes их не «закрывать».

Релизное правило: стори эпика 39 **на прод по одной не выкатываются** (решение Alex, 2026-08-02) — релиз собирается после 39.1 → 39.2 → 39.3 → 39.4 целиком. Эта стори снимает последнее расхождение релизной ветки: `openapi.yaml` уже содержит `opt4_price`, а типы фронта — ещё нет.

### Антипаттерны (НЕ ДЕЛАТЬ)

- **НЕ** трогать `backend/` и `docs/api/openapi.yaml` — всё сделано в 39.1-39.3.
- **НЕ** править `src/types/api.generated.ts` руками и **не** «дописывать» в него роль, если Task 0 показал, что 39.3 не влита.
- **НЕ** рефакторить списки оптовых ролей к единому предикату — сознательно принятый долг (`tech-debt.md` п. 17).
- **НЕ** добавлять `wholesale_level4` в `registerSchema` и `ROLE_OPTIONS` (`RegisterForm.tsx`) — там нет и уровней 2-3.
- **НЕ** вводить каскад в `getPriceForRole` и **не** убирать каскад из `ProductCard` — расхождение зафиксировано как вне объёма.
- **НЕ** трогать ветки `trainer` / `federation_rep` / `default` в `getProductPrice` — именно они делают радиус правки CRITICAL безопасным.
- **НЕ** «дополнять до полного B2B-списка» цепочки в `HeroSection`/`ElectricHeroSection` — там намеренно только оптовые уровни.
- **НЕ** заводить новые тестовые файлы — кейсы идут в существующие `pricing.test.ts` и `ProductCard.test.tsx`.
- **НЕ** запускать `npm run generate:types` внутри контейнера frontend — `docs/` туда не примонтирован.
- **НЕ** править `frontend_tests.log` / `test_results.txt` — мусорные артефакты прошлых прогонов, в `.gitignore`.

### Команды

```bash
# Всё выполняется с хоста, из каталога frontend/
cd /c/Users/1/DEV/FREESPORT/frontend

# 1. Регенерация типов (читает ../docs/api/openapi.yaml)
npm run generate:types
npx prettier --write src/types/api.generated.ts

# 2. Проверки
npx tsc --noEmit
npm run test
npm run lint
npm run format:check

# 3. Точечный прогон изменённых тестов
npx vitest run src/utils/__tests__/pricing.test.ts
npx vitest run src/components/business/ProductCard/__tests__/ProductCard.test.tsx

# 4. Применение правок в работающем окружении (из корня репозитория)
cd /c/Users/1/DEV/FREESPORT
docker compose --env-file .env -f docker/docker-compose.yml restart frontend

# 5. Перед коммитом
npx gitnexus detect-changes --scope all
```

**Базовые линии замерены на `0e005137` перед началом стори — все четыре проверки зелёные:**

```
npm run test        →  Test Files 144 passed (144)
                       Tests 2421 passed | 16 skipped (2437)   (~137 с)
npx tsc --noEmit    →  чисто, exit 0
npm run lint        →  чисто (eslint --max-warnings=0)
npm run format:check → All matched files use Prettier code style!
```

Предсуществующих падений и предупреждений **нет ни одного** — любой красный результат после правок принадлежит этой стори, списывать на «фоновый долг» нечего. Ожидаемый прирост: `pricing.test.ts` с 17 до 20 кейсов (+1 на `getPriceForRole`, +2 на `isB2BRole`; проверки fallback добавляются внутрь существующих `it`, счётчик не меняя), `ProductCard.test.tsx` +2 кейса. Число **файлов** остаётся 144 — новых тестовых файлов стори не заводит.

E2E (Playwright) стори не затрагивает — ролевых сценариев уровня 4 в `frontend/tests/e2e/` нет, `npm run test:e2e` в объём не входит.

### Project Structure Notes

- Next.js 15 App Router + React 19. Все затрагиваемые компоненты (`ProductCard`, `ProductInfo`, `home/*`, `catalog/page.tsx`) уже клиентские — директиву `'use client'` добавлять не нужно и не нужно снимать.
- `server-auth.ts` — серверный модуль (`next/headers`), в клиентские компоненты не импортируется. Правка `validRoles` влияет на SSR-путь карточки товара (`app/(blue)/product/[slug]/page.tsx:64-75`).
- Комментарии на русском (NFR-3940-10, `project-context.md` §6).
- Стиль: prettier `singleQuote`, `printWidth: 100`, `trailingComma: es5`, `arrowParens: avoid`; eslint `--max-warnings=0`.
- `tsconfig.json` — `strict: true`; необъявленное поле в типе даёт ошибку компиляции, а не warning.
- Новых зависимостей стори не вводит.
- HTTP — только через `services/api-client.ts` (`project-context.md` §7); эта стори новых запросов не добавляет.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 39.4: Фронтенд показывает цену уровня 4 — AC в BDD-формате]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 39 — порядок стори, атомарность выката, приёмка на проде, сознательно принятый долг]
- [Source: _bmad-output/planning-artifacts/epics.md#Requirements Inventory — FR-39-11, FR-39-13, NFR-3940-03, -07, -10]
- [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements — «Вне объёма»: расхождение fallback бэка и каскада фронта]
- [Source: _bmad-output/planning-artifacts/tech-debt.md#17 — список оптовых ролей размножен по восьми файлам, рефакторинг вне объёма]
- [Source: _bmad-output/planning-artifacts/tech-debt.md#20 — api.generated.ts не импортируется и не проверяется в CI; устранение вне объёма стори]
- [Source: _bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md#B3 Frontend — список файлов и строк]
- [Source: _bmad-output/implementation-artifacts/Story/39-3-catalog-admin-api-opt4-price.md#Дрейф openapi.yaml и команда регенерации — состояние контракта, от которого стартует эта стори]
- [Source: frontend/src/types/index.ts:21-30 — union UserRole]
- [Source: frontend/src/types/api.ts:14-25, :37-49, :294-304 — User.role, Product, ProductPrice]
- [Source: frontend/src/utils/pricing.ts:7-61 — UserRole, isB2BRole, getPriceForRole]
- [Source: frontend/src/utils/server-auth.ts:38-53 — validRoles и fallback на retail]
- [Source: frontend/src/stores/authStore.ts:134-141 — B2B_ROLES и селектор useIsB2BUser]
- [Source: frontend/src/schemas/authSchemas.ts:40-56, :118-177 — registerSchema против b2bRegisterSchema]
- [Source: frontend/src/components/auth/RegisterForm.tsx:52-57, :175-181 — ROLE_OPTIONS и локальная константа isB2BRole]
- [Source: frontend/src/services/productsService.ts:19-73, :112-131 — ApiProductDetailResponse и adaptProductToDetail]
- [Source: frontend/src/components/business/ProductCard/ProductCard.tsx:108-135, :438, :562 — getProductPrice и показ РРЦ через isB2BRole]
- [Source: frontend/src/components/product/ProductInfo.tsx:11-14, :57-64 — UserRole prop и canSeeRrp]
- [Source: frontend/src/app/(blue)/catalog/page.tsx:376-385 — userRole и isB2B]
- [Source: frontend/src/components/home/HeroSection.tsx:94-111, ElectricHeroSection.tsx:132-145 — форма B, цепочка сравнений]
- [Source: frontend/src/components/home/{HitsSection,NewArrivalsSection,PromoSection,SaleSection}.tsx — форма A, массив isB2B]
- [Source: frontend/src/utils/__tests__/pricing.test.ts:9-91 — mockPrice и существующие кейсы fallback]
- [Source: frontend/src/components/business/ProductCard/__tests__/ProductCard.test.tsx:73-100, :225-250 — mockProduct и кейсы ролевого ценообразования]
- [Source: frontend/package.json:5-23 — scripts, включая generate:types]
- [Source: frontend/.prettierrc, frontend/eslint.config.mjs, frontend/tsconfig.json — стиль и strict-режим]
- [Source: docker/docker-compose.yml — frontend монтирует только ../frontend, docs/ вне контейнера]
- [Source: project-context.md §1, §6, §7 — рестарт контейнера frontend, язык кода, Next 15 / React 19]

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code, workflow `bmad-dev-story`)

### Debug Log References

| Проверка | Команда | Результат |
|---|---|---|
| Предусловие 39.3 (Task 0) | `grep -c "opt4_price\|wholesale_level4" docs/api/openapi.yaml` | 5 и 2 вхождения → 39.3 влита (HEAD `16ea6d2d`) |
| GitNexus pre-flight | `npx gitnexus status`, `impact` по 4 символам | индекс up-to-date на `16ea6d2`; `getProductPrice` — **CRITICAL** (1 прямой, 8 процессов, 4 модуля), `getPriceForRole` / `adaptProductToDetail` — LOW, `isB2BRole` — UNKNOWN (омоним локальной константы в `RegisterForm`) |
| Регенерация типов (Task 1) | `npm run generate:types` | 13 вставок / 2 удаления в `api.generated.ts` |
| RED-прогон новых тестов | `npx vitest run pricing.test.ts ProductCard.test.tsx` | **4 failed, 56 passed** — падения ровно в новых кейсах (AC3, AC6, AC8) |
| GREEN-прогон тех же файлов | та же команда после Tasks 3-7 | **60 passed** (pricing 20, ProductCard 40) |
| Контроль полноты (Task 7.9) | `grep -rn "wholesale_level3" frontend/src` | 24 вхождения; без пары остались только 4 ожидаемых (`api.generated.ts`, `ProfileForm.test.tsx`, `pricing.test.ts`, `ProductCard.test.tsx`) |
| Типы (Task 9.1) | `npx tsc --noEmit` | exit 0, чисто |
| Полный Vitest (Task 9.2) | `npm run test` | **144 files passed, 2426 passed \| 16 skipped** (99 с) — базовая линия 2421 + 5 новых кейсов |
| Линт и стиль (Task 9.3) | `npm run lint`, `npm run format:check` | eslint чисто (`--max-warnings=0`); «All matched files use Prettier code style!» |
| Рестарт окружения (Task 9.4) | `docker compose … restart frontend` | `Container freesport-frontend Started` |
| GitNexus (Task 9.5) | `npx gitnexus detect-changes --scope all` | 24 файла, 40 символов, 25 процессов, risk critical — ожидаемо для `getProductPrice`; посторонних символов нет |

`prettier --write` по `api.generated.ts` (Task 1.3) отдельной командой не потребовался — он уже входит в npm-скрипт `generate:types` (`openapi-typescript … && prettier --write ./src/types/api.generated.ts`). `format:check` это подтвердил.

### Completion Notes List

**Реализовано по ACs**

- **AC1** — типы перегенерированы поверх коммита 39.3 `16ea6d2d` (Task 0.3). `readonly opt4_price: number;` появился в схемах `ProductList` и `ProductDetail`; `'wholesale_level4'` в `RoleEnum` **уже присутствовал** до правки (см. расхождение 1). Файл правился только генератором.
- **AC2** — все четыре правки внесены: `wholesale_level4` в union `UserRole` (`types/index.ts`) и в `User['role']` (`types/api.ts`), `opt4_price?: number;` в `Product`, `level4?: number;` в `ProductPrice.wholesale`. Последняя — та, которой нет в задании §B3; без неё `tsc` падает на `pricing.ts` и `productsService.ts`.
- **AC3** — `pricing.ts`: роль в union, в предикате `isB2BRole` и ветка `case 'wholesale_level4': return price.wholesale?.level4 || price.retail;`. Каскад намеренно не вводился — форма один в один с уровнями 1-3.
- **AC4** — роль добавлена во все три списка: `server-auth.validRoles`, `authStore.B2B_ROLES`, `authSchemas.b2bRegisterSchema`. `registerSchema` и `ROLE_OPTIONS` не тронуты (там нет и уровней 2-3).
- **AC5** — `opt4_price?: number;` в DTO `ApiProductDetailResponse` и `level4: apiProduct.opt4_price,` в маппинге `adaptProductToDetail`.
- **AC6** — ветка `case 'wholesale_level4'` в `getProductPrice` с каскадом `opt4 → opt3 → opt2 → opt1 → retail`, записана сразу в развёрнутом виде под `printWidth: 100`. Ветки `trainer` / `federation_rep` / `default` и соседние уровни не тронуты — именно это делает CRITICAL-радиус безопасным.
- **AC7** — все восемь точек закрыты: шесть массивов (`ProductInfo.canSeeRrp`, `catalog/page.tsx`, `HitsSection`, `NewArrivalsSection`, `PromoSection`, `SaleSection`) и две цепочки сравнений (`HeroSection`, `ElectricHeroSection`) — вторые правились по своей форме, не копипастой массива. Комментарий в `ProductInfo.tsx` обновлён на «оптовики (1-4)».
- **AC8** — `pricing.test.ts`: кейс значения `level4`, проверки fallback в обоих существующих сценариях, новый `describe('isB2BRole')` со сторожем `unregistered → false`. `ProductCard.test.tsx`: `opt4_price: 700` в `mockProduct`, кейс отображения `700 ₽` и кейс каскада (`opt4_price: undefined` → `800 ₽`). Новых файлов не заведено.
- **AC9** — `tsc --noEmit`, `npm run lint`, `npm run format:check`, `npm run test` зелёные; регрессий относительно базовой линии нет (144 файла как было, +5 кейсов).

**Расхождения со спекой стори (обнаружены по факту, не дефекты реализации)**

1. **`wholesale_level4` уже был в `api.generated.ts`.** Спека ожидала его появления в diff регенерации. Фактически роль попала в закоммиченный файл раньше — вместе с регенерацией по тех.долгу п. 20 (`4708dd8a`), после того как 39.1 добавила её в `ROLE_CHOICES`. AC1 в части `RoleEnum` выполнен состоянием файла, в части `opt4_price` — этой стори.
2. **В diff `api.generated.ts` попал один посторонний ханк** — у операции получения категории `id: string` заменился на `id: number` с описанием. Это накопленный дрейф закоммиченного файла относительно контракта (типы не регенерировались после правок категорий), а не следствие правок стори. Файл правится только генератором, поэтому ханк оставлен как есть; на компиляцию и тесты не влияет (`api.generated.ts` в приложении не импортируется — мина №1 Dev Notes).
3. **Базовая линия тестов совпала точно** (2421 → 2426 при неизменных 144 файлах и 16 skipped), в отличие от 39.3, где линии в спеке устарели.

**Вне объёма — к сведению Alex**

- **Гейт `api-contract.yml` после этой стори должен позеленеть.** Он падал на шаге `npm run generate:types` + `git status --porcelain`: контракт содержал `opt4_price`, а типы фронта — нет. Теперь типы приведены в соответствие с контрактом; расхождение релизной ветки, о котором предупреждала 39.3, снято.
- **Приёмка эпика 39 не закрыта зелёными тестами.** По замеру прода `opt4_price` пуст у 100 % вариантов (16 309 из 16 309) — клиент с ролью уровня 4 увидит розничную цену, и это корректная работа кода. Для закрытия эпика нужны два шага в 1С: заполнить вид цен «Опт 4» и прогнать выгрузку цен.
- **Долг не трогался** (в соответствии с антипаттернами): списки оптовых ролей не сведены к единому предикату (`tech-debt.md` п. 17); `api.generated.ts` по-прежнему не импортируется приложением (п. 20); моки `src/__mocks__/products.ts` и `productDetail.ts` уровень 4 не получили.

### File List

**Изменённые — типы**

- `frontend/src/types/api.generated.ts` (перегенерирован)
- `frontend/src/types/api.ts`
- `frontend/src/types/index.ts`

**Изменённые — логика и компоненты**

- `frontend/src/utils/pricing.ts`
- `frontend/src/utils/server-auth.ts`
- `frontend/src/stores/authStore.ts`
- `frontend/src/schemas/authSchemas.ts`
- `frontend/src/services/productsService.ts`
- `frontend/src/components/business/ProductCard/ProductCard.tsx`
- `frontend/src/components/product/ProductInfo.tsx`
- `frontend/src/app/(blue)/catalog/page.tsx`
- `frontend/src/components/home/HitsSection.tsx`
- `frontend/src/components/home/NewArrivalsSection.tsx`
- `frontend/src/components/home/PromoSection.tsx`
- `frontend/src/components/home/SaleSection.tsx`
- `frontend/src/components/home/HeroSection.tsx`
- `frontend/src/components/home/ElectricHeroSection.tsx`

**Изменённые — тесты**

- `frontend/src/utils/__tests__/pricing.test.ts`
- `frontend/src/components/business/ProductCard/__tests__/ProductCard.test.tsx`

**Изменённые — артефакты процесса**

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/Story/39-4-frontend-opt4-price-display.md`

## Change Log

| Дата | Изменение |
|---|---|
| 2026-08-04 | Реализована стори 39.4: типы фронта перегенерированы из контракта с `opt4_price`; роль `wholesale_level4` добавлена в рукописные типы, `pricing.ts` (union, `isB2BRole`, `getPriceForRole`), три списка B2B-ролей, DTO и маппинг `productsService`, каскад `getProductPrice` в `ProductCard` и все восемь точек списков оптовых ролей. Добавлено 5 кейсов Vitest в два существующих файла. Статус → review. |
