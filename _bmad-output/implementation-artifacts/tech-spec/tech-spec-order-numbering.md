---
title: "Новая схема нумерации заказов FREESPORT"
type: "feature"
created: "2026-05-02"
status: "draft"
context:
  - "_bmad-output/planning-artifacts/order-numbering-spec-agent-task.md"
  - "backend/apps/orders/models.py"
  - "backend/apps/orders/services/order_create.py"
  - "backend/apps/orders/admin.py"
  - "backend/apps/orders/services/order_export.py"
  - "backend/apps/orders/services/order_status_import.py"
  - "backend/apps/users/models.py"
---

# Техническая спецификация: новая схема нумерации заказов FREESPORT

## Intent

**Problem:** Сейчас `Order.generate_order_number()` создаёт UUID, а единый бизнес-формат заказа отсутствует. Это ломает читаемость для менеджеров, усложняет поиск, документы, email и обмен с `1С`, особенно после появления мастер-заказов и субзаказов.

**Approach:** Ввести каноническое хранение `order_number` по утверждённым правилам: мастер `CCCCCYYNNN`, субзаказ `CCCCCYYNNNS`, UI-форматирование только на границе отображения, атомарную генерацию через отдельный сервис/счётчик и нормализацию поиска в Django Admin.

## Boundaries & Constraints

**Always:**

- Канонический номер мастер-заказа хранится только как `CCCCCYYNNN`, например `0462026007`.
- UI master: `CCCC-YYNNN`, где `CCCC` — последние 4 цифры `CCCCC`, например `4620-26007`.
- Канонический номер субзаказа: `CCCCCYYNNNS`, например `04620260071`.
- UI suborder: `CCCCC-YYNNN-S`, например `04620-26007-1`.
- `customer_code` — отдельное неизменяемое поле пользователя, длина 5, только цифры.
- `NNN` — порядковый номер заказа клиента в календарном году, диапазон `001..999`.
- Генерация номера выполняется атомарно внутри `transaction.atomic()`.
- После создания `order_number` не меняется.
- Клиентские endpoint должны создавать только заказы авторизованных пользователей с заполненным `customer_code`.

**Ask First:**

- Как назначать `customer_code` существующим пользователям без кода клиента из 1С.
- Нужно ли брать `customer_code` из `User.onec_id`/`onec_guid`/отдельного импорта или генерировать локально.
- Нужно ли показывать в API отдельные поля `order_number_display` и `order_number_canonical`, либо оставить API только с каноническим `order_number`.
- Нужно ли мигрировать старые UUID-like `order_number` или оставить их неизменными как legacy.

**Never:**

- Не менять утверждённые форматы номеров.
- Не разрешать гостевые заказы в новом checkout flow.
- Не заменять `customer_code` на `user.id` без отдельного решения владельца продукта.
- Не использовать `count() + 1` без row lock/unique constraint/retry.
- Не форматировать UI-номер перед сохранением в БД.

## Терминология и формат

| Термин | Формат | Пример | Где используется |
| --- | --- | --- | --- |
| `customer_code` | `CCCCC` | `04620` | `User.customer_code`, snapshot в заказе |
| Master canonical | `CCCCCYYNNN` | `0462026007` | `Order.order_number` для `is_master=True` |
| Master UI | `CCCC-YYNNN` | `4620-26007` | frontend/admin/email/PDF display |
| Suborder canonical | `CCCCCYYNNNS` | `04620260071` | `Order.order_number` для `is_master=False` |
| Suborder UI | `CCCCC-YYNNN-S` | `04620-26007-1` | admin/1С/внутренние документы |

`YY` берётся от календарного года создания заказа в timezone проекта. `NNN` начинается с `001` для каждой пары `customer_code + YY`. `S` начинается с `1` и назначается последовательно внутри одного мастер-заказа.

## Current Code Findings

- `backend/apps/orders/models.py` хранит `order_number` как `CharField(max_length=50, unique=True)` и генерирует UUID в `Order.generate_order_number()`.
- `backend/apps/orders/services/order_create.py` уже создаёт мастер-заказ и N субзаказов внутри `@transaction.atomic`; это правильная точка входа для новой генерации.
- `backend/apps/users/models.py` не содержит `customer_code`; есть `onec_id`, `onec_guid`, B2B-поля и роли.
- `backend/apps/orders/admin.py` ищет по raw `order_number`; нормализация UI-формата пока отсутствует.
- `backend/apps/orders/services/order_export.py` экспортирует в `1С` субзаказы, кладёт `order.order_number` в `<Номер>`, а `<Ид>` оставляет `order-{id}`.
- `backend/apps/orders/services/order_status_import.py` импортирует статусы по `<Номер>` с fallback по `<Ид>`, значит новый номер должен быть обратно совместимым в XML flow.
- `frontend/src/types/order.ts`, `OrderCard`, `OrderDetail`, `OrderSuccessView`, `orderPdfExport.ts` отображают raw `order_number` напрямую.

## Data Model

**User model:**

- Добавить `customer_code = CharField(max_length=5, unique=True, null=True/blank=True на время миграции)`.
- Валидатор: `RegexValidator(r"^\d{5}$")`.
- После rollout поле должно быть обязательным для пользователей, которым разрешён checkout.
- Изменение `customer_code` после первого заказа запрещено на уровне admin/form/service validation.

**Order model:**

- Сохранить `order_number` как канонический immutable identifier.
- Добавить snapshot-поля для аудита и индексов:
  - `customer_code_snapshot = CharField(max_length=5, db_index=True, blank=True)`;
  - `order_year = PositiveSmallIntegerField(null=True, db_index=True)` — полный год или `YY` нужно выбрать при реализации; рекомендуется полный год `2026` для читаемости запросов;
  - `customer_year_sequence = PositiveSmallIntegerField(null=True)`;
  - `suborder_sequence = PositiveSmallIntegerField(null=True, blank=True)`.
- Ограничения:
  - `UniqueConstraint(fields=["customer_code_snapshot", "order_year", "customer_year_sequence"], condition=Q(is_master=True))`;
  - `UniqueConstraint(fields=["parent_order", "suborder_sequence"], condition=Q(is_master=False))`;
  - `CheckConstraint(customer_year_sequence__gte=1, customer_year_sequence__lte=999)` для новых заказов;
  - `CheckConstraint(suborder_sequence__gte=1)` для субзаказов.

**Counter model:**

Рекомендуется отдельная модель `CustomerOrderSequence`:

- `customer_code`;
- `year`;
- `last_sequence`;
- unique по `customer_code + year`.

Она нужна, чтобы не считать заказы через `count()` и безопасно блокировать ровно одну строку счётчика.

## Генерация номеров

Реализовать отдельный domain service, например `backend/apps/orders/services/order_numbering.py`.

**Master algorithm:**

1. Внутри `transaction.atomic()` получить пользователя через `select_for_update()` или убедиться, что строка пользователя уже стабильна.
2. Проверить `user.is_authenticated` и `user.customer_code`.
3. Вычислить `year = timezone.localdate().year`, `yy = str(year)[-2:]`.
4. Получить или создать `CustomerOrderSequence(customer_code, year)`.
5. Заблокировать строку счётчика через `select_for_update()`.
6. Увеличить `last_sequence` на 1.
7. Если значение стало `> 999`, выбросить доменную ошибку `OrderNumberSequenceExhausted` и откатить транзакцию.
8. Сформировать `order_number = f"{customer_code}{yy}{sequence:03d}"`.
9. Записать snapshot-поля в мастер-заказ.
10. При `IntegrityError` по unique constraint выполнить ограниченный retry или вернуть 409/400 с логированием.

**Suborder algorithm:**

1. Субзаказы создаются только после сохранения мастера в той же транзакции.
2. Для каждой группы в `OrderCreateService` назначить `suborder_sequence` начиная с `1` в стабильном порядке групп.
3. `sub.order_number = f"{master.order_number}{suborder_sequence}"`.
4. Скопировать `customer_code_snapshot`, `order_year`, `customer_year_sequence` с мастера.
5. Сохранить `parent_order=master`, `is_master=False`.

**Ordering note:** группы субзаказов сейчас создаются из `groups.items()`. Для стабильного `S` нужно сортировать ключи групп, например по `(vat_key is None, vat_key, warehouse_key or "")`.

## Backend/API changes

- `Order.save()` не должен генерировать UUID через `generate_order_number()` для новых checkout-заказов. Номер должен приходить из сервиса создания, иначе модель не знает пользователя и master/suborder context.
- `OrderCreateSerializer.validate()` должен отклонять неавторизованного пользователя и пользователя без `customer_code` до чтения гостевой корзины.
- `_get_user_cart()` должен перестать поддерживать guest cart для order create path или оставить только legacy read-only сценарий вне checkout.
- `OrderCreateService.create()` должен вызывать `OrderNumberingService.next_master_number(user)` перед `master.save()` и назначать номера субзаказам явно.
- `OrderDetailSerializer`/`OrderListSerializer` могут оставить `order_number` каноническим. Если нужен display на backend, добавить read-only `order_number_display`.
- OpenAPI `docs/api/openapi.yaml` и generated frontend types нужно обновить после изменения контрактов.

## Admin search and normalization

Добавить helper, например `normalize_order_number_query(raw: str) -> list[str]`, и использовать его в `OrderAdmin.get_search_results()`.

Поддерживаемые входы:

| Input | Output candidate |
| --- | --- |
| `0462026007` | `0462026007` |
| `4620-26007` | `0462026007` |
| `04620-26007-1` | `04620260071` |
| `04620260071` | `04620260071` |

Для master UI `4620-26007` первая цифра `customer_code` отсутствует. Утверждённый пример требует нормализации в `0462026007`, поэтому helper должен искать кандидата по suffix: `order_number__endswith="462026007"` или дополнять ведущим `0` только если это явно утверждённое правило. Рекомендуется suffix-поиск для корректности при будущих `customer_code`, не начинающихся с `0`.

Невалидные формы: пустой ввод, буквы, неверная длина, несколько дефисов вне шаблона, `NNN=000`, `NNN>999`, `S<1`. Для них admin должен fallback на стандартный поиск по email/tracking, но не возвращать неожиданные заказы.

## Frontend formatting

Создать единый formatter, например `frontend/src/utils/orderNumberFormat.ts`:

- `formatOrderNumber(canonical: string, options?: { kind?: "auto" | "master" | "suborder" })`;
- `isCanonicalMasterOrderNumber(value)`;
- `isCanonicalSubOrderNumber(value)`;
- `normalizeOrderNumberInput(value)` только для admin-like сценариев, если они появятся на frontend.

Использовать formatter в:

- `frontend/src/components/checkout/OrderSuccessView.tsx`;
- `frontend/src/components/business/OrderCard/OrderCard.tsx`;
- `frontend/src/components/business/OrderDetail/OrderDetail.tsx`;
- `frontend/src/utils/orderPdfExport.ts`;
- email/PDF paths, если форматирование остаётся на backend, применить аналогичный Python helper.

Frontend не должен отправлять UI-номер в order create/update API. Для ссылок `/profile/orders/[id]` сохраняется `id`, не `order_number`.

## Интеграции

**1С export:**

- `<Номер>` для субзаказа станет `CCCCCYYNNNS`.
- `<Ид>` рекомендуется оставить `order-{id}` как immutable technical id, чтобы снизить риск конфликтов.
- Проверить, ожидает ли 1С номер документа именно субзаказа или мастер-заказа. Текущий экспорт работает по субзаказам.

**1С status import:**

- Импорт уже ищет по `<Номер>` и fallback по `<Ид>`.
- После rollout 1С должна возвращать `<Номер>` субзаказа, если статус относится к субзаказу.
- XML с номером мастера при наличии sub_orders должен по-прежнему отклоняться текущим master-guard, если не будет отдельного бизнес-решения.

**Email/PDF/logs/admin actions:**

- В пользовательских каналах показывать UI master для мастер-заказа.
- Во внутренних логах сохранять канонический номер; можно добавлять display рядом только как дополнительное поле.
- CSV export из admin должен явно выбрать canonical или display. Рекомендация: две колонки `Order Number` и `Display Number`.

## Migration & backward compatibility

- Старые `order_number` не менять без отдельной миграционной стратегии.
- Legacy UUID-like номера должны продолжать открываться, экспортироваться и импортироваться через `order-{id}` fallback.
- Новые поля `customer_code_snapshot/order_year/customer_year_sequence/suborder_sequence` сначала добавлять nullable, затем заполнить только для новых заказов.
- Feature flag рекомендуется для order create path: `ORDER_NUMBERING_V2_ENABLED`.
- Rollout:
  1. добавить поля и helpers;
  2. заполнить/проверить `customer_code` у пользователей;
  3. включить генерацию для staging;
  4. проверить checkout, admin search, 1С export/import;
  5. включить на production;
  6. после стабилизации запретить checkout без `customer_code` окончательно.

## Impact analysis

| Component | Что меняется | Критичность | Тип изменения |
| --- | --- | --- | --- |
| `User model` | Новое поле `customer_code`, уникальность, immutable validation | High | DB/API/admin |
| `Order model` | Snapshot-поля, constraints, отказ от UUID generator в create flow | High | DB/domain |
| `OrderCreateService` | Атомарная генерация master/suborder numbers | High | Backend service |
| `OrderCreateSerializer` | Запрет guest checkout, проверка `customer_code` | High | API validation |
| Sub-order flow | `suborder_sequence`, stable ordering groups, номер `master+S` | High | Backend service |
| Django Admin | Нормализация поиска UI/canonical, display helpers | Medium | Admin UX |
| Serializers/API | Возможное поле `order_number_display`, OpenAPI update | Medium | API contract |
| Frontend UI | Единый formatter вместо raw display | Medium | UI |
| PDF/email | Display format для пользовательских документов | Medium | Communications |
| 1С export/import | Новый `<Номер>` субзаказа, fallback по `<Ид>` сохранить | High | Integration |
| Tests | Unit/integration/regression coverage на генерацию и форматирование | High | QA |

## Tasks & Acceptance

**Execution:**

- [ ] `backend/apps/users/models.py` -- добавить `customer_code` с regex/unique и admin/read-only правилами -- нужен стабильный `CCCCC`.
- [ ] `backend/apps/orders/models.py` -- добавить snapshot-поля, constraints и модель `CustomerOrderSequence` -- нужна атомарная последовательность по клиенту и году.
- [ ] `backend/apps/orders/services/order_numbering.py` -- реализовать генератор, formatter и normalizer -- изолировать доменную логику от модели.
- [ ] `backend/apps/orders/services/order_create.py` -- назначать master/suborder номера внутри текущей транзакции -- убрать UUID из нового checkout flow.
- [ ] `backend/apps/orders/serializers.py` -- запретить guest order create и валидировать `customer_code` -- выполнить утверждённое бизнес-правило.
- [ ] `backend/apps/orders/admin.py` -- переопределить `get_search_results()` и добавить display canonical/UI -- поддержать менеджерский поиск.
- [ ] `backend/apps/orders/services/order_export.py` и `order_status_import.py` -- проверить/обновить тесты XML `<Номер>` для субзаказов -- не сломать 1С.
- [ ] `frontend/src/utils/orderNumberFormat.ts` -- добавить formatter и тесты -- убрать raw display из UI.
- [ ] `frontend/src/components/**` и `frontend/src/utils/orderPdfExport.ts` -- использовать formatter в списке, деталях, success, PDF -- единый UX.
- [ ] `docs/api/openapi.yaml` и generated types -- обновить контракт после backend changes -- синхронизировать API/frontend.

**Acceptance Criteria:**

- Given authenticated user with `customer_code=04620` and first order in 2026, when checkout succeeds, then master `order_number` is `0462026001` and UI display is `4620-26001`.
- Given same user has sequence `006` in 2026, when next checkout succeeds, then master `order_number` is `0462026007`.
- Given order split into two suborders, when service creates suborders, then their canonical numbers are `04620260071` and `04620260072` and UI values are `04620-26007-1`, `04620-26007-2`.
- Given two concurrent checkout requests for the same user/year, when both pass validation, then generated `NNN` values are unique and no duplicate `order_number` is stored.
- Given sequence for user/year is `999`, when next checkout is attempted, then transaction rolls back with controlled validation error and no order/items/stock changes persist.
- Given unauthenticated request or authenticated user without `customer_code`, when order create endpoint is called, then API returns validation/permission error and no guest order is created.
- Given admin search input `0462026007`, `4620-26007`, `04620-26007-1`, or `04620260071`, when search runs, then the expected master/suborder is found.
- Given legacy UUID-like order exists, when viewed/exported/searched by existing raw number or `order-{id}` in 1С import fallback, then legacy behavior remains supported.
- Given frontend receives canonical `order_number`, when rendering order list/detail/success/PDF, then it displays the approved UI format and does not mutate API payloads.

## Test strategy

**Backend unit:**

- `OrderNumberingService` master format, suborder format, display format, invalid inputs.
- `normalize_order_number_query()` for canonical/UI/invalid master and suborder inputs.
- Sequence overflow `999 -> error`.

**Backend integration:**

- Concurrent checkout with `transaction.atomic()` and `select_for_update()`.
- Full checkout creates master + suborders with expected numbers and snapshots.
- Guest checkout denied.
- Admin search returns expected queryset.
- 1С export uses suborder canonical `<Номер>` and keeps `<Ид>order-{id}</Ид>`.
- 1С status import finds suborder by new number and still supports fallback by `<Ид>`.

**Frontend unit:**

- Formatter master/suborder/legacy fallback.
- Components render display number in `OrderCard`, `OrderDetail`, `OrderSuccessView`.
- PDF file name policy: либо canonical для безопасного файла, либо sanitized display — выбрать и закрепить тестом.

**Markers:** backend tests должны использовать проектные pytest-маркеры `unit`, `integration`, при зависимости от внешних данных — `data_dependent`.

## Risks

- `customer_code` отсутствует в текущей модели, а источник значения не утверждён.
- UI master теряет первую цифру `CCCCC`; поиск `4620-26007` не всегда обратимо восстанавливает полный `customer_code` без suffix-search.
- Текущий код всё ещё поддерживает guest orders в serializer/export comments; новая логика должна явно закрыть create path.
- 1С может ожидать прежний UUID-like `<Номер>` или номер мастера вместо субзаказа.
- Stable ordering субзаказов важен: изменение порядка групп может менять `S` между похожими заказами.
- Legacy orders и новые numeric orders будут сосуществовать в одном `order_number` поле.

## Open questions

1. Какой авторитетный источник `customer_code`: 1С, ручное назначение менеджером, локальный генератор или отдельный импорт?
2. Нужно ли `customer_code` для всех ролей или только для B2B/верифицированных покупателей?
3. Должен ли API возвращать отдельный `order_number_display`, чтобы frontend не дублировал форматирование?
4. Что показывать менеджеру при неоднозначном suffix-search для `4620-26007`, если теоретически найдены несколько заказов?
5. Нужно ли мигрировать старые номера в новый формат или оставить legacy навсегда?
6. Какой формат номера должен видеть `1С` в `<Номер>`: субзаказ canonical `CCCCCYYNNNS` или мастер canonical `CCCCCYYNNN` плюс отдельный признак субзаказа?
7. Нужно ли резервировать диапазоны `customer_code` для клиентов из 1С и локально созданных клиентов?

## Verification

**Commands:**

- `docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest backend/apps/orders backend/apps/users -m "unit or integration"` -- expected: новые backend tests passed.
- `npm run test -- src/utils/orderNumberFormat.test.ts src/components/business/OrderCard/OrderCard.test.tsx src/components/business/OrderDetail/OrderDetail.test.tsx src/components/checkout/__tests__/OrderSuccessView.test.tsx src/utils/__tests__/orderPdfExport.test.ts` -- expected: frontend formatter/display tests passed.
- `make docs-sync-api` -- expected: API docs remain synchronized after serializer/OpenAPI changes.

**Manual checks:**

- Создать staging-пользователя с `customer_code=04620`, оформить заказ, проверить master/suborder в DB, admin, UI, email/PDF и XML export.
- Проверить admin search по `0462026007`, `4620-26007`, `04620-26007-1`, `04620260071`.

## Spec Change Log

Пока пусто. Изменения после ревью добавлять append-only.

## Готовность к реализации

Спецификация готова как `draft` для ревью владельцем продукта/техлидом. До реализации нужно закрыть open questions по источнику `customer_code`, API display field и контракту `1С` по `<Номер>`.
