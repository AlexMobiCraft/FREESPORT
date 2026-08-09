---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
currentRun:
  feature: role-from-1c-agreement
  epics: [39, 40]
  inputDocuments:
    - _bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md
    - _bmad-output/implementation-artifacts/spec-1c-unregistered-role.md
    - _bmad-output/implementation-artifacts/spec-1c-manager-link-counterparty.md
  stepsCompleted:
    - step-01-validate-prerequisites
    - step-02-design-epics
    - step-03-create-stories
    - step-04-final-validation
  status: complete
---

# FREESPORT - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for FREESPORT (Brands Block Feature), decomposing the requirements from the PRD and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-01: Admin can upload an image (logo) for a `Brand` entity.
FR-02: Admin can toggle a `Show on Homepage` (`is_featured`) flag for a `Brand`.
FR-03: System must prevent enabling `Show on Homepage` if no image is uploaded for the brand.
FR-04: Admin can remove a brand from the homepage by disabling the flag.
FR-05: User can view a "Brands" section on the homepage (Blue Theme).
FR-06: User can view a carousel/list of brands marked as `is_featured`.
FR-07: User sees a visual hover effect (animation) when interacting with a brand logo.
FR-08: User can click on a brand logo.
FR-09: Clicking a logo navigates the user to the catalog page with the brand filter active (`/catalog?brand={slug}`).
FR-10: System provides a public API endpoint to retrieve only `is_featured` brands.

### NonFunctional Requirements

NFR-01: **Image Optimization**: All brand logos must be served in next-gen formats (WebP/AVIF) via Next.js Image component and should not exceed 50KB.
NFR-02: **CLS (Cumulative Layout Shift)**: The brands block container must define explicit dimensions to prevent layout shift during loading.
NFR-03: **SSR**: The list of featured brands must be rendered on the server (SSR) to ensure immediate visibility and SEO indexability.
NFR-04: **Keyboard Navigation**: The carousel component must be navigable using keyboard controls (Tab to focus, Arrows to scroll).
NFR-05: **Touch Support**: The carousel must support swipe gestures on mobile devices.
NFR-06: **Contrast**: Background and logo colors must meet WCAG AA contrast standards.
NFR-07: **Code Standards**: Code must adhere to project TypeScript, ESLint, and Prettier configurations.
NFR-08: **Isolation**: The `BrandsBlock` must be a self-contained component with minimal external dependencies.

### Additional Requirements

- **Backend**: Update `Brand` model in `apps/products` (Brownfield context).
- **Backend**: API payloads must use `snake_case`.
- **Frontend**: Component architecture: `BrandsBlock` (Client) receiving data from Page (Server).
- **Frontend**: Use `next/image` with `object-contain`.
- **Architecture**: Follow "Service Layer" pattern if complex validation logic is needed (though validation here is simple).
- **Integration**: Use `GET /api/v1/products/brands/?is_featured=true` with caching strategy (1h TTL).

### FR Coverage Map

FR-01: Epic 1 - Admin can manage brand images
FR-02: Epic 1 - Admin can toggle featured status
FR-03: Epic 1 - System validates image presence
FR-04: Epic 1 - Admin can remove featured status
FR-05: Epic 1 - User sees brands section
FR-06: Epic 1 - User sees featured brands
FR-07: Epic 1 - User sees hover effects
FR-08: Epic 1 - User can click brand logo
FR-09: Epic 1 - User navigates to catalog
FR-10: Epic 1 - API provides featured brands

## Epic List

### Epic 33: Brands Block Implementation

Enable users to quickly navigate to popular brand catalogs from the homepage and allow admins to manage this content.
**FRs covered:** FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, FR-09, FR-10.
**NFRs covered:** NFR-1 to NFR-8.

### Epic 36: Critical Security & Export Fixes (Week 1)

Закрыть критические дефекты: публичная утечка файлов импорта 1С, некорректная стоимость доставки в XML-экспорте заказов, захардкоженный `SITE_URL`.
**Приоритет:** 🔴 CRITICAL. **Источник:** security audit (#15, #16, #7).

### Epic 37: Auth Hardening — JWT & Sessions (Week 2-3)

Усилить безопасность аутентификации: добавить endpoint logout-all, устранить race condition при ротации токенов.
**Приоритет:** 🟠 HIGH. **Источник:** tech-debt.md (#5, #4).

### Epic 38: Session & Resource Cleanup (Week 4+)

Централизовать очистку сессий, обеспечить безопасное переключение аккаунтов, добавить GC временных файлов импорта 1С.
**Приоритет:** 🟡 MEDIUM. **Источник:** security audit (#6, #9, #13).

## Epic 33: Brands Block Implementation

**Goal:** Enable users to quickly navigate to popular brand catalogs from the homepage and allow admins to manage this content.

### Story 33.1: Brand Model & Admin Updates

As an Admin,
I want to upload brand logos and mark brands as featured on the homepage,
So that I can highlight key partners and improve navigation.

**Acceptance Criteria:**

**Given** the existing `Brand` model in `apps/products/models.py`,
**When** the model is updated,
**Then** it includes an `image` field (ImageField) and `is_featured` field (BooleanField, default=False).

**Given** the Django Admin interface for Brands,
**When** creating or editing a brand,
**Then** I can upload a logo image and check "Show on Homepage".

**Given** I check "Show on Homepage" but do not upload an image,
**When** I try to save,
**Then** the system prevents saving and shows a validation error: "Image is required for featured brands" (FR-03).

**Given** the Brand list in Admin,
**When** viewed,
**Then** I can see which brands are featured.

### Story 33.2: API Featured Brands Endpoint

As a Frontend Developer,
I want to fetch a list of featured brands via API,
So that I can display them on the homepage.

**Acceptance Criteria:**

**Given** unauthenticated users,
**When** they request `GET /api/v1/products/brands/?is_featured=true`,
**Then** the API returns a JSON list of brands where `is_featured=True`.
**And** the response includes fields: `id`, `name`, `slug`, `image` (URL).

**Given** the API response,
**When** serialized,
**Then** field names are in `snake_case` (e.g. `is_featured`, `company_name` if applicable).

**Given** the endpoint configuration,
**Then** responses are cached for 1 hour to reduce DB load (NFR-Integration).

### Story 33.3: BrandsBlock Component Logic & UI

As a User,
I want to see a carousel of brand logos on the homepage,
So that I can quickly access my favorite brands.

**Acceptance Criteria:**

**Given** the `BrandsBlock` component in `frontend/src/components/business/home/`,
**When** it receives a list of brands as props from the Server Component (SSR),
**Then** it renders a horizontal list/carousel of logos.

**Given** the component is rendered,
**When** viewed on different screen sizes,
**Then** it adapts responsively (e.g., swiper/scrollable on mobile).

**Given** brand logos,
**When** rendered,
**Then** they use `next/image` with `object-contain` style to handle varying aspect ratios (NFR-01).

**Given** a user hovers over a logo,
**When** using a mouse,
**Then** a subtle scale/opacity animation occurs (FR-07).

**Given** a user clicks a logo,
**When** clicked,
**Then** they are navigated to `/catalog?brand={slug}` (FR-09).

### Story 33.4: Integration into Homepage

As a User,
I want to see the brands block in the correct location on the homepage,
So that I can easily find it.

**Acceptance Criteria:**

**Given** the Blue Theme homepage (`src/app/(blue)/page.tsx`),
**When** the page renders,
**Then** it fetches the featured brands on the server side (SSR).

**Given** the fetched data,
**When** passed to `BrandsBlock`,
**Then** the block appears immediately below the main marketing banner section.

**Given** the page load process,
**Then** the brands block has explicit dimensions to prevent Layout Shift (CLS) during hydration (NFR-02).

---

# Security & Bugfix Sprint (2026-Q2)

> Эпики 36-38 не относятся к Brands Block — это отдельный security/bugfix спринт, запланированный 2026-05-18.
> Источник задач — `_bmad-output/planning-artifacts/tech-debt.md` (от 2026-01-18), пункты #3-#16. Трекинг — `_bmad-output/implementation-artifacts/sprint-status.yaml`.

## Epic 36: Critical Security & Export Fixes (Week 1)

**Goal:** Закрыть критические дефекты безопасности и экспорта до начала остальных работ спринта.

**Приоритет:** 🔴 CRITICAL

### Story 36.1: Move 1C import files from public MEDIA_ROOT

As a Security Engineer,
I want файлы импорта 1С не размещались в публично доступном `MEDIA_ROOT`,
So that XML-данные контрагентов, цен и остатков не утекают по прямой ссылке.

**Контекст (tech-debt #15):** `ImportOrchestratorService.import_dir = settings.MEDIA_ROOT / "1c_import"` (`import_orchestrator.py`). `MEDIA_ROOT` раздаётся nginx как статика — файлы импорта (цены, остатки, клиенты) можно скачать, подобрав URL. Рекомендация аудита: перенести хранение в приватную директорию (`var/` или иную) за пределами web-root.

**Acceptance Criteria:**

**Given** входящие файлы обмена с 1С (контрагенты, товары, цены, остатки),
**When** они принимаются и распаковываются,
**Then** они сохраняются в приватную директорию вне `MEDIA_ROOT` (не раздаётся nginx).

**Given** приватную директорию импорта,
**When** анонимный пользователь запрашивает файл по предполагаемому media-URL,
**Then** сервер возвращает 403/404, файл недоступен.

**Given** существующий пайплайн импорта (`VariantImportProcessor`, Celery-задачи),
**When** путь хранения изменён,
**Then** импорт товаров и контрагентов отрабатывает без регрессий.

### Story 36.2: Fix delivery cost in Order XML export

As a 1С Manager,
I want сумма документа в XML-экспорте заказа совпадала с суммой строк `<Товары>`,
So that интеграция с 1С не падает на валидации, когда у заказа есть стоимость доставки.

**Контекст (tech-debt #16):** `OrderExportService` задаёт сумму документа равной `order.total_amount` (включает доставку), но список `<Товары>` содержит только физические товары. При `delivery_cost > 0` сумма строк не сходится с суммой документа — интеграция с 1С падает на валидации. Рекомендация аудита: добавлять виртуальную позицию «Доставка» в список товаров при `delivery_cost > 0`.

**Acceptance Criteria:**

**Given** заказ с `delivery_cost > 0`,
**When** `OrderExportService` формирует XML,
**Then** в список `<Товары>` добавляется виртуальная позиция «Доставка» со стоимостью, равной `delivery_cost`.

**Given** экспортированный XML заказа с доставкой,
**When** проверяется сумма документа,
**Then** она равна сумме всех строк `<Товары>`, включая позицию «Доставка» (валидация 1С проходит).

**Given** заказ с `delivery_cost = 0`,
**When** формируется XML,
**Then** виртуальная позиция «Доставка» не добавляется.

**Given** интеграционный тест полного цикла экспорта,
**When** он выполняется,
**Then** покрывает оба случая — заказ с доставкой и без.

### Story 36.3: Fix hardcoded SITE_URL

As a Developer,
I want в письме сброса пароля адрес сайта брался из `settings.SITE_URL`, а не был захардкожен,
So that ссылка восстановления пароля корректна в production, а не указывает на `localhost:3000`.

**Контекст (tech-debt #7):** в `apps/users/views/authentication.py` (Password Reset) используется захардкоженный `localhost:3000` вместо `settings.SITE_URL`.

**Acceptance Criteria:**

**Given** код Password Reset в `apps/users/views/authentication.py`,
**When** формируется ссылка восстановления пароля,
**Then** базовый адрес берётся из `settings.SITE_URL`, захардкоженный `localhost:3000` удалён.

**Given** окружение production,
**When** пользователь запрашивает сброс пароля,
**Then** письмо содержит ссылку на production-домен.

**Given** прочие места backend, где может встречаться захардкоженный адрес сайта,
**When** выполняется проверка,
**Then** они также переведены на `settings.SITE_URL` либо подтверждено их отсутствие.

## Epic 37: Auth Hardening — JWT & Sessions (Week 2-3)

**Goal:** Усилить контроль над жизненным циклом токенов и сессий аутентификации.

**Приоритет:** 🟠 HIGH

> Примечание: пункт #3 tech-debt (JWT access token invalidation) исключён из спринта 2026-05-18 — уже реализован (`tech-spec/tech-spec-jwt-access-token-blacklist.md`, status: done). Эпик содержит 2 стори.

### Story 37.1: Logout-all endpoint

As a User,
I want иметь возможность выйти со всех устройств одним действием,
So that при подозрении на компрометацию я могу мгновенно отозвать все свои сессии.

**Контекст (tech-debt #5):** в backend нет endpoint'а для массовой инвалидации всех сессий пользователя. Рекомендация аудита: реализовать `/auth/logout-all/` через очистку `OutstandingToken`.

**Acceptance Criteria:**

**Given** аутентифицированный пользователь с несколькими активными сессиями,
**When** он вызывает `POST /api/v1/auth/logout-all/`,
**Then** все его refresh-токены попадают в blacklist, все access-токены инвалидируются.

**Given** выполнен logout-all,
**When** запрос приходит с любым ранее выданным токеном пользователя,
**Then** возвращается 401 Unauthorized.

**Given** endpoint logout-all,
**When** его вызывает неаутентифицированный пользователь,
**Then** возвращается 401, никакие сессии не затрагиваются.

### Story 37.2: Token rotation race condition

As a User,
I want одновременный refresh токена с разных устройств не приводил к неожиданному разлогину,
So that активная сессия не теряется из-за гонки при ротации refresh-токенов.

**Контекст (tech-debt #4):** в `frontend/src/services/api-client.ts` одновременный refresh с разных устройств может привести к разлогину из-за `ROTATE_REFRESH_TOKENS=True`. Рекомендация аудита: задокументировать поведение либо рассмотреть sliding sessions.

**Acceptance Criteria:**

**Given** конкурентные запросы refresh с разных устройств/вкладок,
**When** срабатывает ротация refresh-токена,
**Then** поведение детерминировано: гонка либо устранена, либо явно задокументирована как принятый риск с описанием UX-последствий.

**Given** варианты решения,
**When** принимается решение,
**Then** зафиксирован выбор между (а) дедупликацией одновременных refresh на клиенте, (б) sliding sessions, (в) документированием поведения.

**Given** выбранный вариант,
**When** он реализован или задокументирован,
**Then** изменения отражены в `api-client.ts` и/или в документации auth-флоу.

## Epic 38: Session & Resource Cleanup (Week 4+)

**Goal:** Навести порядок в очистке сессий и временных ресурсов, снизить технический долг.

**Приоритет:** 🟡 MEDIUM

### Story 38.1: Session cleanup centralization

As a Frontend Developer,
I want логика удаления токенов и очистки состояния сессии была в одном месте,
So that устраняется дублирование между `authStore.ts`, `api-client.ts` и `AuthProvider.tsx`.

**Контекст (tech-debt #6):** логика очистки сессии дублируется в трёх frontend-файлах: `authStore.ts`, `api-client.ts`, `AuthProvider.tsx`. Рекомендация аудита: централизовать в общую функцию `clearAuthState()`.

**Acceptance Criteria:**

**Given** продублированную логику очистки в трёх frontend-файлах,
**When** проводится рефакторинг,
**Then** создаётся единая функция `clearAuthState()`, вызываемая из всех трёх мест.

**Given** функцию `clearAuthState()`,
**When** выполняется logout, ошибка refresh или истечение сессии,
**Then** очистка токенов и состояния идентична и согласована для всех сценариев.

**Given** существующие тесты auth (Vitest),
**When** рефакторинг завершён,
**Then** регрессий нет.

### Story 38.2: Account switching safety

As a User,
I want переключаться между аккаунтами надёжно, без риска оставить старые токены валидными,
So that сессия предыдущего аккаунта полностью завершается перед входом в новый.

**Контекст (tech-debt #9):** в `frontend/src/stores/authStore.ts` нет метода надёжного переключения между аккаунтами. Рекомендация аудита: реализовать метод `switchAccount()`, обеспечивающий полную очистку старой сессии перед входом в новую.

**Acceptance Criteria:**

**Given** `authStore.ts`,
**When** добавляется метод `switchAccount()`,
**Then** он полностью очищает старую сессию (через `clearAuthState()` из story 38.1) до установки новой.

**Given** переключение через `switchAccount()`,
**When** новая сессия установлена,
**Then** старые токены недействительны, клиентское состояние не содержит данных прежнего пользователя.

**Given** метод `switchAccount()`,
**When** он покрыт тестом,
**Then** проверяется отсутствие утечки сессии между аккаунтами.

### Story 38.3: Temp file cleanup (GC)

As a System Operator,
I want временные файлы импорта 1С автоматически удалялись по TTL,
So that `MEDIA_ROOT/1c_temp/` не переполняет хранилище «осиротевшими» файлами.

**Контекст (tech-debt #13):** временные файлы в `MEDIA_ROOT/1c_temp/` остаются на диске после завершения импорта или при ошибке — риск переполнения хранилища. Рекомендация аудита: management command `cleanup_1c_temp` (создать), удаляющий файлы старше 24 часов, запускаемый через Celery Beat.

**Acceptance Criteria:**

**Given** временные файлы в `MEDIA_ROOT/1c_temp/` старше 24 часов,
**When** выполняется management command `cleanup_1c_temp`,
**Then** устаревшие файлы удаляются.

**Given** команду `cleanup_1c_temp`,
**When** настраивается расписание,
**Then** она зарегистрирована в Celery Beat для периодического запуска.

**Given** активную сессию импорта (`ImportSession` в статусе `IN_PROGRESS`),
**When** запускается `cleanup_1c_temp`,
**Then** её файлы не удаляются — согласованность с guard'ом из `tech-spec-fix-1c-import-cleanup-race.md` (AC сверх tech-debt #13).

**Given** запуск команды,
**When** удаление выполнено,
**Then** действие логируется (количество удалённых файлов) для диагностики.

---

# Роль клиента из 1С + четвёртый оптовый уровень (2026-Q3)

> Эпики 39-40 не относятся к Brands Block и к security-спринту. Источник — задание
> `_bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md` (2026-08-01).
> Предшественники: `spec-1c-unregistered-role`, `spec-1c-manager-link-counterparty` (обе выкачены).
>
> **Часть A (правка тиражного расширения `ОбменСБитриксУправлениеСайтомУТ` в УТ 11) вынесена за
> пределы эпиков** — это задача администратора 1С. Выполнена на тесте 2026-08-01, на прод не
> перенесена. Патч и формула отбора соглашений — `docs/integrations/1c/bus-extension-patch/`.
> Для эпика 40 это **внешняя блокирующая зависимость**: пока патч не на проде, выгрузка не
> содержит `<ЗначенияРеквизитов>` и импорт видит только `no_data`.

## Requirements Inventory (эпики 39-40)

### Functional Requirements

**Часть B — четвёртый оптовый уровень «Опт 4» (эпик 39):**

FR-39-01: Модель `ProductVariant` хранит цену `opt4_price` для роли `wholesale_level4` (по образцу `opt3_price`).
FR-39-02: Роль `wholesale_level4` присутствует в `User.ROLE_CHOICES` и входит в `User.B2B_ROLES` (проходит `is_b2b_user`).
FR-39-03: `ProductVariant.get_price_for_user` для роли `wholesale_level4` возвращает `opt4_price`, а при незаполненном `opt4_price` — `retail_price`.
FR-39-04: Справочник `PriceType` содержит запись «Опт 4 (до 50 тыс.руб в квартал)» с `onec_id = 4c1962d2-f8ed-11eb-81f3-00155d3cae02`, `product_field = "opt4_price"`, `user_role = "wholesale_level4"`.
FR-39-05: Импорт цен из 1С раскладывает вид цен «Опт 4» в поле `opt4_price` (`parser._map_price_type_to_field`, сбросы цен в `variant_import`).
FR-39-06: Фильтрация каталога по минимальной/максимальной цене работает для роли `wholesale_level4`.
FR-39-07: Товар с заполненным только `opt4_price` считается имеющим B2B-цену в сериализаторах и вью каталога.
FR-39-08: Админка отображает `opt4_price` в fieldset цен варианта и цветной бейдж роли `wholesale_level4`.
FR-39-09: Сериализаторы пользователей принимают `wholesale_level4` как допустимую роль.
FR-39-10: Сервис баннеров относит `wholesale_level4` к оптовым ролям.
FR-39-11: Фронтенд знает роль `wholesale_level4` и поле `opt4_price`: тип роли, признак B2B, выбор цены, каскад `opt4 → opt3 → opt2 → opt1 → retail` в `ProductCard`, списки оптовых ролей на главной и в каталоге.
FR-39-12: Экспорт заказа подставляет вид цен «Опт 4 (до 50 тыс.руб в квартал)» для роли `wholesale_level4` через `ONEC_EXCHANGE.PRICE_TYPE_BY_ROLE` и `PRICE_TYPE_ID_BY_NAME`.
FR-39-13: `docs/api/openapi.yaml` и `frontend/src/types/api.generated.ts` синхронизированы с новым полем и ролью.

**Часть C — маппинг роли из 1С (эпик 40):**

FR-40-01: Парсер контрагентов читает блок `<ЗначенияРеквизитов>` в `customer_data["price_type_ids"]` (GUID, нижний регистр, без пробелов, **дедуплицированные**), `customer_data["price_type_meta"]` (наименование вида цен, наименование соглашения, признак `СоглашениеТиповое`) и `customer_data["agreement_status"]` (реквизит `СоглашениеСтатус` со значением `НетСоглашения`, когда действующего соглашения у контрагента нет). Отсутствие блока целиком → пустые значения. После правки части A блок приходит у **каждого** контрагента, поэтому его отсутствие означает поломку выгрузки, а не бизнес-ситуацию. Обработка `<Роль>` не меняется.
FR-40-02: Сервис `resolve_role_from_price_types(price_type_ids, agreement_status)` возвращает `RoleResolution(role, reason, matched)` с `reason ∈ {resolved, no_data, no_agreement, unknown_price_type, ambiguous}` по правилам: статус `НетСоглашения` → `no_agreement`; блока не было и статуса нет → `no_data`; ни один GUID не найден в `PriceType` (или найденные несут пустой `user_role`) → `unknown_price_type`; больше одного GUID с непустой ролью → `ambiguous`; ровно один → `resolved`.
FR-40-03: Источником маппинга «вид цен → роль» служит `PriceType.user_role`, заполняемое миграцией данных из `ONEC_EXCHANGE.PRICE_TYPE_BY_ROLE`; у «РРЦ» и «МРЦ» поле остаётся пустым.
FR-40-04: `PriceType.user_role` выведено в админку — в `list_display` и доступно для редактирования.
FR-40-05: Поле `User.onec_price_type_id` хранит GUID вида цен из 1С и заполняется импортом **всегда**, независимо от того, применена ли роль. При `no_agreement` поле гасится — соглашение в 1С снято, и хранить прежний вид цен нельзя: по нему привязка (FR-40-11) выдала бы роль по несуществующему соглашению. При `no_data` поле **не изменяется**: отсутствие блока означает поломку выгрузки, а не отсутствие соглашения.
FR-40-06: Карточка пользователя в админке показывает `onec_price_type_id` и человекочитаемое наименование вида цен в блоке «Интеграция с 1С» (readonly).
FR-40-07: Импорт применяет роль только к записям, **не** проходящим `UserManager.unlinked_1c_record_q()`; непривязанная запись 1С сохраняет роль `unregistered` независимо от вида цен.
FR-40-08: Смена роли импортом фиксируется в `AuditLog` (`action="role_from_1c"`): прежнее и новое значение роли, GUID и наименование вида цен, наименование соглашения.
FR-40-09: Сессия импорта ведёт счётчики `roles_updated` (с разбивкой: прежняя роль `unregistered` / прежняя роль осмысленная), `roles_skipped_no_data`, `roles_skipped_no_agreement`, `roles_skipped_unknown_price_type`, `roles_skipped_ambiguous` и показывает их в отчёте. Разбивка `roles_updated` нужна менеджеру: смена роли с `unregistered` — норма первого дня, а перетирание роли, выданной вручную, он обязан увидеть.
FR-40-10: Отчёт сессии помечает прогон как аномалию, если блок `<ЗначенияРеквизитов>` не встретился **ни разу** (детектор регресса выгрузки при обновлении расширения БУС). После правки части A ожидаемая доля контрагентов с блоком — все контрагенты пакета, поэтому сигнал однозначен: блока нет → патч в расширении затёрт.
FR-40-11: Привязка заявки к контрагенту (`link_1c_customer`) переносит `onec_price_type_id` источника и в той же транзакции применяет роль через `resolve_role_from_price_types`; `role` включена в перечень перенесённых полей в `AuditLog` привязки.
FR-40-12: 1С является источником истины по уровню цен: роль, выставленная менеджером вручную, перетирается импортом (для привязанных аккаунтов).
FR-40-13: Существует тест-сторож согласованности прямого и обратного маппинга. Проверяются **только роли, чей вид цен несёт непустой `PriceType.user_role`** — `wholesale_level1…4` и `trainer`: для каждой из них `PRICE_TYPE_BY_ROLE → PRICE_TYPE_ID_BY_NAME → PriceType.user_role` возвращает исходную роль. Роли `retail`, `admin` и `federation_rep` исключаются **явным списком с комментарием**: у РРЦ `user_role` намеренно пуст (иначе пять контрагентов-маркетплейсов на виде цен РРЦ уедут в `retail` вопреки решению 1), а вид цен «Партнер» на портал не выгружается и записи `PriceType` не имеет. Сам экспорт заказа не меняется.

### NonFunctional Requirements

NFR-3940-01: **Реальные данные в тестах.** Тесты импорта строятся только на реальных XML из `data/import_1c/` (`contragents/` + контрольная выгрузка `contragents_pricetype/`, `priceLists/`, `prices/`). Синтетические XML запрещены (`CLAUDE.md`, `project-context.md` §4).
NFR-3940-02: **Маркировка тестов.** Каждый backend-тест помечен `@pytest.mark.unit` или `@pytest.mark.integration` — иначе выпадает из CI-фильтров.
NFR-3940-03: **Покрытие.** Затронутые модули относятся к критическим (`products`, `users`, интеграции) — покрытие ≥ 90 %, общее ≥ 70 %.
NFR-3940-04: **Атомарность.** Применение роли при привязке и перенос `onec_price_type_id` выполняются в одной `transaction.atomic()` с уже существующим `select_for_update()` на обеих записях.
NFR-3940-05: **Обратная совместимость критических путей.** После импорта записи 1С по-прежнему проходят `unlinked_1c_records()`; регистрация по ИНН, известному 1С, создаёт заявку (баг, чинившийся миграцией `0018`, не возвращается); колонка и фильтр «Кандидат 1С» в админке не пустеют; `find_link_candidates` продолжает возвращать кандидатов.
NFR-3940-06: **Миграции.** Проверяются на PostgreSQL в Docker, не на SQLite. Data-миграции обратимы (`reverse`) и идемпотентны.
NFR-3940-07: **API-контракт.** После правки сериализаторов и вью — обновление `docs/api/openapi.yaml` и регенерация `npm run generate:types`. **С 2026-08-04 рассинхрон виден автоматически:** workflow `.github/workflows/api-contract.yml` сверяет `openapi.yaml` со схемой, построенной из кода (сравниваются разобранные структуры, не текст), и краснеет, если регенерация `api.generated.ts` даёт непустой `git diff`. ⚠️ **Красный чек пока не блокирует мерж:** защита веток в репозитории не настроена вовсе (проверено `gh api` 2026-08-04 — `main` и `develop` отдают «Branch not protected»), поэтому гейт работает как сигнал, а не как замок. Контекст `Контракт синхронен с кодом` добавлен в `setup-branch-protection.sh`; блокирующим он станет после того, как защиту применят — см. предупреждение в шапке скрипта и `deferred-work.md`. ⚠️ Чего гейт **не** проверяет: `api.generated.ts` по-прежнему не импортируется модулями фронта, поэтому рассинхрон **рукописных** типов (`types/api.ts`, `services/productsService.ts`) с контрактом не ломает `tsc`. Их полнота проверяется ревью и тестами Vitest; типизация DTO-слоя от генерации отложена (`deferred-work.md`, `tech-debt.md` п. 20, цель 2).
NFR-3940-08: **Идемпотентность импорта.** Повторный прогон той же выгрузки не порождает лишних записей `AuditLog` и не «дёргает» роль туда-обратно.
NFR-3940-09: **Производительность импорта.** Маппинг `PriceType → user_role` разрешается не запросом на каждого контрагента: в пакете тысячи контрагентов, справочник читается один раз на сессию импорта. Кэш при этом не живёт дольше сессии — модульный `lru_cache` запрещён, иначе правка `user_role` в админке не подхватится долгоживущим Celery-воркером.
NFR-3940-10: **Язык кода.** Комментарии и docstrings нового кода — на русском, в стиле существующего кода.

### Additional Requirements

- **Внешняя зависимость эпика 40:** патч расширения `ОбменСБитриксУправлениеСайтомУТ` (XSD-макет `БУС_НастройкиОбмена.СхемаXSDОбмена` + `БУС_ВыгрузкаСервер.СформироватьДанныеПоКонтрагентам`) должен быть перенесён на прод администратором 1С. Передаётся патчем, не `.cfe` (тест — УТ 11.5.22.134 + БУС 8.1.0.40, прод — УТ 11.5.27.49 + БУС 8.1.0.45). Пункт о повторном наложении патча вносится в процедуру обновления модуля БУС.
- **Данные для тестов эпика 39:** снимок `data/import_1c/priceLists/` содержит шесть видов цен (сделан до добавления «Опт 4») — обновить до начала тестов импорта цен «Опт 4».
- **Внешняя зависимость эпика 40, вторая итерация (решение Alex, 2026-08-02):** патч части A дополняется реквизитом `СоглашениеСтатус` со значением `НетСоглашения`, который выгружается, когда действующего соглашения у контрагента нет. Блок `<ЗначенияРеквизитов>` начинает приходить у **каждого** контрагента, а не только у 433 партнёров. Смысл: «нет соглашения» и «выгрузка сломалась» перестают выглядеть одинаково — портал различает их по данным, а не по косвенному сессионному признаку. GUID при этом не «отравляется» словом: `ТипЦенId` остаётся пустым, статус приходит отдельным реквизитом. Правка возможна потому, что патч на прод ещё не переносился. Тянет за собой: обновление `docs/integrations/1c/bus-extension-patch/` (README, `patch_xsd_contragent.py`, `patch_bus_module.py`, `fragments/`) и переснятие контрольной выгрузки.
- **Данные для тестов эпика 40:** контрольная выгрузка `data/import_1c/contragents_pricetype/` (`test_base`; каталог `data/import_1c` в git игнорируется) переснимается после второй итерации части A. Абсолютные числа контрагентов в критерии приёмки не зашиваются — снимок обновляемый, и зашитые константы правились бы не глядя. Проверяются инварианты: ни у одного контрагента нет более одного различного `ТипЦенId`; каждый контрагент несёт либо GUID, либо статус `НетСоглашения`.
- **Ограничение миграции модели:** новое поле `ProductVariant.opt4_price` сопровождается `CheckConstraint products_opt4_price_positive` по образцу `products/migrations/0003_add_constraints.py`.
- **Изменение ранее зафиксированных решений:** правило `spec-1c-unregistered-role` «импорт никогда не меняет роль существующего пользователя» и пункт `spec-1c-manager-link-counterparty` «`role` не переносится при привязке» отменяются для привязанных аккаунтов — обе отмены фиксируются в Spec Change Log соответствующих спек.
- **`federation_rep` остаётся ручной ролью:** вид цен «Партнер» (`200a24fe-f07d-11eb-81f3-00155d3cae02`) на портал не выгружается, записи `PriceType` нет.
- **Вне объёма:** расхождение fallback между бэком (сразу `retail_price`) и фронтом (каскад по уровням) существует для уровней 1-3 и в этих эпиках не чинится. Экспорт заказа (`order_export`) не меняется, кроме добавления «Опт 4» в настройки.
- **Охват фичи:** роль из 1С получат 433 из 3168 клиентов (≈14 %), остальные остаются на ручном назначении — согласовано с заказчиком до выката.
- **Риск «массовая смена ролей на первом импорте» снят (решение Alex, 2026-08-01):** на проде нет живых портальных аккаунтов клиентов — только импортированные записи 1С, которые по FR-40-07 остаются `unregistered`. Management-команда dry-run из раздела «Риски» задания в объём не входит.

### UX Design Requirements

UX-документа (`bmad-ux` DESIGN/EXPERIENCE) для этой фичи нет — изменения затрагивают Django-админку и отображение цен на витрине. Требования к интерфейсу выражены в FR-39-08, FR-39-11, FR-40-04, FR-40-06.

## Epic List (эпики 39-40)

### Epic 39: Четвёртый оптовый уровень «Опт 4»

Клиент с квартальным оборотом до 50 тыс. руб. получает роль `wholesale_level4` и видит цену `opt4_price` в каталоге, карточке товара и на главной; цена приезжает из 1С обычным импортом цен; менеджер назначает уровень в админке, заказ уезжает в 1С с видом цен «Опт 4».
**FRs covered:** FR-39-01 … FR-39-13.
**NFRs covered:** NFR-3940-01, -02, -03, -06, -07, -10.
**Standalone:** да — работает без эпика 40, роль назначается вручную, как сейчас уровни 1-3.
**Зависимости:** нет. Требуется обновлённый снимок `data/import_1c/priceLists/` (7 видов цен) до начала тестов импорта цен.
**Релиз (решение Alex, 2026-08-01):** эпик выкатывается **отдельным релизом**, не дожидаясь эпика 40. До выката эпика 40 роль `wholesale_level4` назначается менеджером вручную.
**Атомарность выката (решение Alex, 2026-08-02):** стори эпика на прод **по одной не уезжают** — релиз собирается только после реализации всех четырёх. Это снимает два промежуточных дефекта: (1) до 39.2 `PriceType.product_field` для «Опт 4» перетирается импортом на `retail_price`, и цены вида «Опт 4» пишутся в розничную цену; (2) до 39.3 роль уже видна в публичном списке `user_roles_view`, но `SELF_SERVICE_ROLES` её не принимает — самостоятельная регистрация с ней даёт 400. Оба состояния существуют только внутри релизной ветки.
**Разбиение стори (решение Alex, 2026-08-01):** бэкенд и фронтенд — **разные стори**. Фронтовая стори идёт после бэкенда: ей нужны регенерированные типы из `openapi.yaml`.
**Сознательно принятый долг (решение Alex, 2026-08-01):** список оптовых ролей размножен по восьми фронтовым компонентам — роль дописывается во все точки как есть, рефакторинг к единому предикату в объём эпика **не входит**. Зафиксировано в `tech-debt.md` п. 17.
**Приёмка на проде (решение Alex, 2026-08-03):** эпик **нельзя объявить закрытым по зелёным тестам**. По замеру прода на 2026-08-03 `opt4_price` пуст у **100% вариантов (16 309 из 16 309)** — поле в 1С не заполнено ни у одной номенклатуры. Значит после выката всех четырёх стори клиент с ролью `wholesale_level4` увидит **розничную** цену: `get_price_for_user` вернёт `self.opt4_price or self.retail_price`. Код при этом полностью корректен, тесты зелёные, контракт синхронен — пользовательской ценности ноль. Критерий закрытия эпика — **непустой `opt4_price` в проде**, то есть в план выката закладываются два внешних шага: (1) заполнить вид цен «Опт 4» для номенклатуры в 1С, (2) прогнать выгрузку цен и убедиться, что `opt4_price` заполнился. Тот же класс отложенного эффекта, что `roles_updated = 0` в эпике 40.
**Предшествующая работа (решение Alex, 2026-08-03):** до реализации стори 39.3 отдельной стори закрывается `tech-debt.md` п. 18 — публичный каталог отдаёт `opt1/2/3_price` анонимным запросам вопреки инварианту `project-context.md` §3. Порядок именно такой, чтобы `opt4_price` попал в `openapi.yaml` уже с гейтом: одна регенерация контракта и типов фронта вместо двух, без ломающего изменения `required`. Форма исправления — вариант B (роль без права получает `0.0`). Побочный эффект: сдвиг номеров строк в Dev Notes стори 39.3 — освежить их последним таском той стори. Стори оформлена как внеэпиковая: `_bmad-output/implementation-artifacts/Story/security-wholesale-price-visibility.md` (закрывает обе половины инварианта `project-context.md` §3, включая проверку `is_verified` в `get_price_for_user`).

### Epic 40: Уровень цен клиента приходит из 1С

Менеджер перестаёт назначать уровень цен руками — соглашение об условиях продаж в 1С становится источником истины. Перевод клиента с «Опт 3» на «Опт 2» доезжает до портала ближайшим обменом и виден в `AuditLog`; отчёт сессии импорта показывает, кому роль обновили и по какой причине пропустили; исходный вид цен из 1С виден в карточке пользователя.
**FRs covered:** FR-40-01 … FR-40-13.
**NFRs covered:** NFR-3940-01 … -06, -08, -09. **Не применим:** NFR-3940-07 (API-контракт) — `onec_price_type_id` живёт только в админке, публичные сериализаторы и `openapi.yaml` эпик не трогает; этот NFR закрывается эпиком 39. **Сквозной:** NFR-3940-10 (русские комментарии и docstrings) — общий стандарт проекта, в AC отдельных стори не дублируется.
**Standalone:** да, при выполненной внешней зависимости. Строится на эпике 39: без записи `PriceType` для «Опт 4» 120 партнёров дадут `unknown_price_type` и критерий приёмки #2 задания не пройдёт.
**Зависимости:** эпик 39 (выкачен отдельным релизом ранее); **внешняя блокирующая** — патч расширения БУС на проде (часть A, задача администратора 1С, вне эпиков).
**Отложенный эффект (важно для формулировки цели):** на момент выката на проде нет живых клиентских портальных аккаунтов — все 4606 записей 1С непривязаны и по FR-40-07 остаются `unregistered`. Первый прогон импорта штатно даёт `roles_updated = 0`: заполняется только `onec_price_type_id` у ≈433 партнёров. Роли начинают меняться по мере регистрации клиентов и их привязки менеджером. Из этого следует, что **FR-40-10 (детектор регресса) — единственный наблюдаемый сигнал работоспособности в день выката**, поэтому он реализуется в первой стори эпика, а не в последней (решение Alex, 2026-08-01).
**Приёмка на проде (решение Alex, 2026-08-01):** в план выката закладывается **ручная привязка тестового аккаунта** к контрагенту с известным видом цен. Без неё критерии приёмки #1-#3 задания непроверяемы — применять роль не к чему.
**Pre-flight (решение Alex, 2026-08-01):** первая стори эпика несёт явный AC-предохранитель — контрольная выгрузка контрагентов **с прода** содержит блок `<ЗначенияРеквизитов>`. Часть A трекается вне BMAD, и без этого AC у эпика нет артефакта, подтверждающего закрытие внешней зависимости; отказ выгрузки после обновления модуля БУС тихий.

### FR Coverage Map

FR-39-01: Epic 39 — поле `ProductVariant.opt4_price` + constraint
FR-39-02: Epic 39 — роль `wholesale_level4` в `ROLE_CHOICES` и `B2B_ROLES`
FR-39-03: Epic 39 — `get_price_for_user` с fallback на `retail_price`
FR-39-04: Epic 39 — запись `PriceType` для «Опт 4» (data-миграция)
FR-39-05: Epic 39 — импорт цен «Опт 4» в `opt4_price`
FR-39-06: Epic 39 — фильтры каталога по min/max цене
FR-39-07: Epic 39 — признак «есть B2B-цена» в сериализаторах и вью
FR-39-08: Epic 39 — админка: fieldset цен и бейдж роли
FR-39-09: Epic 39 — сериализаторы пользователей принимают роль
FR-39-10: Epic 39 — баннеры относят роль к оптовым
FR-39-11: Epic 39 — фронтенд: тип роли, поле, каскад цен, списки B2B-ролей
FR-39-12: Epic 39 — экспорт заказа: `PRICE_TYPE_BY_ROLE` и `PRICE_TYPE_ID_BY_NAME`
FR-39-13: Epic 39 — синхронизация `openapi.yaml` и типов фронта
FR-40-01: Epic 40 — парсер читает `<ЗначенияРеквизитов>` с дедупликацией GUID
FR-40-02: Epic 40 — `resolve_role_from_price_types` и `RoleResolution`
FR-40-03: Epic 40 — `PriceType.user_role` как источник маппинга (data-миграция)
FR-40-04: Epic 40 — `PriceType.user_role` в админке
FR-40-05: Epic 40 — поле `User.onec_price_type_id`
FR-40-06: Epic 40 — вид цен в карточке пользователя (readonly)
FR-40-07: Epic 40 — роль применяется только к привязанным аккаунтам
FR-40-08: Epic 40 — `AuditLog` смены роли (`action="role_from_1c"`)
FR-40-09: Epic 40 — счётчики ролей в сессии импорта
FR-40-10: Epic 40 — детектор регресса выгрузки в отчёте сессии
FR-40-11: Epic 40 — перенос вида цен и применение роли при привязке
FR-40-12: Epic 40 — 1С перетирает роль, выставленную вручную
FR-40-13: Epic 40 — сторож согласованности `PRICE_TYPE_BY_ROLE` ↔ `PriceType.user_role`

## Epic 39: Четвёртый оптовый уровень «Опт 4»

**Goal:** Клиент с квартальным оборотом до 50 тыс. руб. получает роль `wholesale_level4` и видит цену `opt4_price` в каталоге, карточке товара и на главной; цена приезжает из 1С обычным импортом цен; менеджер назначает уровень в админке, заказ уезжает в 1С с видом цен «Опт 4».

**Приоритет:** 🟠 HIGH. **Источник:** `tasks/dev-task-role-from-1c-agreement.md`, часть B.
**Порядок стори:** 39.1 → {39.2, 39.3} → 39.4. Ни одна стори не зависит от последующих.

### Story 39.1: Роль wholesale_level4 и цена opt4_price в модели

As a Менеджер,
I want чтобы на портале существовал четвёртый оптовый уровень с собственной ценой,
So that я мог назначить его клиенту с оборотом до 50 тыс. руб. в квартал, а заказ такого клиента уехал в 1С по правильному виду цен.

**Контекст:** делается по образцу `wholesale_level3` / `opt3_price`. Цены живут на `ProductVariant` (`products/models.py:875,899`), не на `Product` — они переехали туда миграцией `0024_add_productvariant_colormapping.py`, а ценовые `CheckConstraint` модели `Product` тогда же сняты миграцией `0004_remove_brand_brands_unique_active_name_and_more.py`. Вид цен «Опт 4» в 1С действует, `ИспользоватьПриПродаже = Истина`, GUID `4c1962d2-f8ed-11eb-81f3-00155d3cae02`.

**Acceptance Criteria:**

**Given** модель `ProductVariant` (`backend/apps/products/models.py`),
**When** в неё добавлено поле `opt4_price`,
**Then** оно объявлено по образцу `opt3_price` с `help_text="Цена для роли wholesale_level4"` (FR-39-01).

**Given** миграцию схемы приложения `products`,
**When** она применена на PostgreSQL в Docker,
**Then** поле создано, а `CheckConstraint products_opt4_price_positive` на модели **`ProductVariant`** отклоняет отрицательное значение (FR-39-01, NFR-3940-06).
**And** constraint объявлен в `ProductVariant.Meta.constraints` — этого атрибута у модели сегодня нет, он заводится с нуля; образец формы выражения — `ImportSession.Meta.constraints` (`products/models.py:665`), где используется `models.Q(...)` и аргумент `condition=` (Django 5.2).

**Given** поле `PriceType.product_field` (`products/models.py:715`),
**When** список `choices` обновлён,
**Then** он содержит `("opt4_price", "Оптовая цена уровень 4")` (FR-39-04).

**Given** data-миграцию приложения `products`,
**When** она применена,
**Then** в справочнике есть запись `PriceType` с `onec_id="4c1962d2-f8ed-11eb-81f3-00155d3cae02"`, `onec_name="Опт 4 (до 50 тыс.руб в квартал)"`, `product_field="opt4_price"`, `user_role="wholesale_level4"`.
**And** повторное применение не создаёт дубля, а `reverse` удаляет только эту запись, не трогая остальные шесть (FR-39-04, NFR-3940-06).

**Given** `User.ROLE_CHOICES` и `User.B2B_ROLES` (`backend/apps/users/models.py:144,157`),
**When** добавлена роль `wholesale_level4`,
**Then** она присутствует в обоих, `is_b2b_user` для неё возвращает `True`, а `role_map` в блоке `TYPE_CHECKING` (`models.py:179`) её учитывает (FR-39-02).

**Given** миграцию приложения `users`,
**When** она применена,
**Then** `AlterField` для поля `role` синхронизирует `choices` со схемой по образцу `users/migrations/0017_add_unregistered_role.py` (FR-39-02).

**Given** вариант товара с заполненным `opt4_price` и пользователя с ролью `wholesale_level4`,
**When** вызывается `ProductVariant.get_price_for_user` (`products/models.py:1177`),
**Then** возвращается `opt4_price` (FR-39-03).

**Given** вариант товара с пустым `opt4_price` и того же пользователя,
**When** вызывается `get_price_for_user`,
**Then** возвращается `retail_price` — fallback как у уровней 1-3 (FR-39-03, решение 7 задания).

**Given** настройки `ONEC_EXCHANGE` (`backend/freesport/settings/base.py:348-366`),
**When** они дополнены,
**Then** `PRICE_TYPE_BY_ROLE["wholesale_level4"] == "Опт 4 (до 50 тыс.руб в квартал)"`, а `PRICE_TYPE_ID_BY_NAME` содержит это наименование с GUID `4c1962d2-f8ed-11eb-81f3-00155d3cae02` (FR-39-12).

**Given** заказ пользователя с ролью `wholesale_level4`,
**When** `OrderExportService` формирует XML,
**Then** в документ попадает вид цен «Опт 4 (до 50 тыс.руб в квартал)» с его GUID.
**And** код `order_export._get_price_type` (`orders/services/order_export.py:550`) при этом не изменяется — работает только за счёт настроек (FR-39-12).

**Given** все новые тесты этой стори,
**When** запускается `make test-unit`,
**Then** они помечены `@pytest.mark.unit` либо `@pytest.mark.integration` и проходят (NFR-3940-02).

**Given** применённые миграции,
**When** выполняется `python manage.py makemigrations --check --dry-run`,
**Then** незакоммиченных миграций нет (NFR-3940-06).

### Story 39.2: Импорт цен «Опт 4» из 1С

As a Контент-менеджер,
I want чтобы цена вида «Опт 4» из выгрузки 1С попадала в поле `opt4_price`,
So that портал перестал выбрасывать эти цены и четвёртый уровень наполнялся данными автоматически.

**Контекст:** сегодня `_map_price_type_to_field` (`products/services/parser.py:546`) не знает «Опт 4», и значение теряется при каждом обмене. Снимок `backend/data/import_1c/priceLists/` содержит шесть видов цен — сделан до добавления «Опт 4» в выгрузку.

**Acceptance Criteria:**

**Given** снимок реальных выгрузок `data/import_1c/priceLists/` и `data/import_1c/prices/`,
**When** он обновлён с базы, где «Опт 4» уже выгружается,
**Then** `priceLists` содержит семь видов цен, включая `4c1962d2-f8ed-11eb-81f3-00155d3cae02`, а `prices` содержит хотя бы одну цену этого вида — это предусловие остальных AC стори (NFR-3940-01).

**Given** функцию `_map_price_type_to_field` (`products/services/parser.py:546`),
**When** приходит вид цен с наименованием, содержащим «опт 4» или «опт4» в любом регистре,
**Then** возвращается `"opt4_price"`.
**And** эта ветка расположена **до** общих веток, распознающих «опт», иначе они перехватят значение первыми (FR-39-05).

**Given** реальный XML цен из `data/import_1c/prices/`, содержащий вид цен «Опт 4»,
**When** выполняется импорт цен,
**Then** у соответствующих вариантов заполнено поле `opt4_price` значением из выгрузки (FR-39-05).

**Given** сбросы цен в `products/services/variant_import.py:843,1001`,
**When** цены варианта сбрасываются перед обновлением,
**Then** `opt4_price` сбрасывается в `None` наравне с прочими ценовыми полями — иначе снятая в 1С цена останется на портале навсегда (FR-39-05).

**Given** тот же файл выгрузки,
**When** импорт выполняется повторно,
**Then** значения `opt4_price` не меняются и дублирующих записей не появляется (NFR-3940-08).

**Given** тесты этой стори,
**When** они написаны,
**Then** они используют **только** реальные XML из `data/import_1c/` — синтетические XML запрещены — и помечены `@pytest.mark.unit` либо `@pytest.mark.integration` (NFR-3940-01, -02).

### Story 39.3: Каталог, админка и API отдают цену уровня 4

As a Оптовый клиент четвёртого уровня,
I want видеть свою цену в каталоге, фильтровать по ней товары и получать её через API,
So that я мог работать с порталом так же, как клиенты уровней 1-3.

**Контекст:** прикладной слой бэкенда. Правки однотипные — «добавить `opt4_price` рядом с `opt3_price`» по списку из §B2 задания.

**Acceptance Criteria:**

**Given** фильтры каталога (`products/filters.py:275,310`),
**When** пользователь с ролью `wholesale_level4` фильтрует товары по минимальной и максимальной цене,
**Then** фильтрация выполняется по полю `opt4_price` (FR-39-06).

**Given** сериализаторы товаров (`products/serializers.py:109,478,514,549,590,628`),
**When** запрос делает пользователь с ролью `wholesale_level4`,
**Then** ответ содержит поле `opt4_price`, а метод `get_opt4_price` отдаёт цену по роли (FR-39-07).

**Given** товар, у которого из B2B-цен заполнена только `opt4_price`,
**When** вычисляется признак наличия B2B-цены в сериализаторах и в `products/views.py:87`,
**Then** товар считается имеющим B2B-цену — условие включает `Q(opt4_price__gt=0)` (FR-39-07).

**Given** карточку варианта товара в админке (`products/admin.py:641`),
**When** менеджер её открывает,
**Then** поле `opt4_price` отображается в fieldset цен рядом с `opt3_price` (FR-39-08).

**Given** список пользователей в админке (`users/admin.py:417`),
**When** отображается пользователь с ролью `wholesale_level4`,
**Then** бейдж роли имеет собственный цвет и читается наравне с прочими оптовыми уровнями (FR-39-08).

**Given** сериализатор пользователей (`users/serializers.py:90`),
**When** роль `wholesale_level4` приходит в запросе или назначается менеджером,
**Then** она принимается как допустимая B2B-роль (FR-39-09).

**Given** сервис баннеров (`banners/services.py:138`),
**When** страницу открывает пользователь с ролью `wholesale_level4`,
**Then** он получает баннеры, предназначенные оптовым ролям (FR-39-10).

**Given** фабрики тестовых данных (`products/factories.py:95,146`),
**When** создаётся вариант товара,
**Then** `opt4_price` заполняется наравне с прочими ценовыми полями (FR-39-07).

**Given** изменённые сериализаторы и вью,
**When** правки завершены,
**Then** `docs/api/openapi.yaml` обновлён: поле `opt4_price` и роль `wholesale_level4` присутствуют в схемах (FR-39-13, NFR-3940-07).

**Given** тесты этой стори,
**When** запускается `make test-unit`,
**Then** покрыты: фильтр по цене для роли, признак B2B-цены у товара только с `opt4_price`, вхождение роли в `B2B_ROLES`; все помечены маркерами (NFR-3940-02, -03).

### Story 39.4: Фронтенд показывает цену уровня 4

As a Оптовый клиент четвёртого уровня,
I want видеть свою цену на витрине — в каталоге, карточке товара и блоках главной страницы,
So that я видел актуальные для меня условия, а не розничную цену.

**Контекст:** стартует после 39.3 — нужен обновлённый `openapi.yaml` для регенерации типов. Правки точечные, по списку §B3 задания. Рефакторинг списков B2B-ролей в объём **не входит** (`tech-debt.md` п. 17).

**Acceptance Criteria:**

**Given** обновлённый `docs/api/openapi.yaml` из стори 39.3,
**When** выполняется `npm run generate:types`,
**Then** `frontend/src/types/api.generated.ts` содержит поле `opt4_price` и роль `wholesale_level4`, а сборка TypeScript проходит (FR-39-13, NFR-3940-07).

**Given** рукописные типы (`types/index.ts:25`, `types/api.ts:18,47`),
**When** они обновлены,
**Then** union ролей содержит `wholesale_level4`, а DTO товара — `opt4_price?: number` (FR-39-11).

**Given** утилиту `utils/pricing.ts:11,29,49`,
**When** цену выбирает пользователь с ролью `wholesale_level4`,
**Then** роль распознаётся как B2B и возвращается `opt4_price` (FR-39-11).

**Given** списки B2B-ролей (`utils/server-auth.ts:45`, `stores/authStore.ts:137`, `schemas/authSchemas.ts:167`),
**When** они обновлены,
**Then** `wholesale_level4` присутствует во всех трёх — пропуск любого даёт молчаливый дефект без ошибки сборки (FR-39-11).

**Given** сервис товаров (`services/productsService.ts:43,125`),
**When** приходит ответ API,
**Then** поле `opt4_price` присутствует в DTO и маппится в `level4` (FR-39-11).

**Given** компонент `ProductCard` (`components/business/ProductCard/ProductCard.tsx:119`),
**When** цена выбирается для пользователя четвёртого уровня,
**Then** работает каскад `opt4 → opt3 → opt2 → opt1 → retail`.
**And** расхождение этого каскада с бэкендовым fallback (сразу `retail_price`) существует для уровней 1-3 и в этой стори **не чинится** (FR-39-11).

**Given** списки оптовых ролей в `components/product/ProductInfo.tsx:61`, `app/(blue)/catalog/page.tsx:381` и шести компонентах `components/home/`,
**When** страницу открывает пользователь с ролью `wholesale_level4`,
**Then** он видит оптовое отображение цен во всех восьми местах (FR-39-11).

**Given** тесты Vitest,
**When** они написаны,
**Then** покрыты выбор цены в `pricing.ts` и каскад в `ProductCard` для роли `wholesale_level4` (NFR-3940-03).

## Epic 40: Уровень цен клиента приходит из 1С

**Goal:** Менеджер перестаёт назначать уровень цен руками — соглашение об условиях продаж в 1С становится источником истины. Перевод клиента с «Опт 3» на «Опт 2» доезжает до портала ближайшим обменом и виден в `AuditLog`; отчёт сессии импорта показывает, кому роль обновили и по какой причине пропустили; исходный вид цен из 1С виден в карточке пользователя.

**Приоритет:** 🟠 HIGH. **Источник:** `tasks/dev-task-role-from-1c-agreement.md`, часть C.
**Внешняя блокирующая зависимость:** патч расширения `ОбменСБитриксУправлениеСайтомУТ` на проде (часть A, задача администратора 1С, вне эпиков) — **во второй редакции, с реквизитом `СоглашениеСтатус`** (решение Alex, 2026-08-02). До его переноса выгрузка не содержит `<ЗначенияРеквизитов>`, и весь эпик наблюдаемо работает в режиме `no_data`. Артефакт закрытия зависимости — AC-предохранитель в стори 40.1.
**Порядок стори:** {40.1, 40.2} → 40.3 → 40.4 → 40.5. Стори 40.1 и 40.2 независимы друг от друга и могут идти параллельно. Ни одна стори не зависит от последующих.
**Точки промежуточного выката:** 40.3 выкатывается сама по себе — импорт пишет вид цен, роли не трогая. Автоприменение включается только с 40.4, и откат 40.4 не тянет за собой миграцию поля.

**Заметки реализации (из закрытых стори эпика).** Записаны здесь, а не только в Completion Notes: `create-story` подтягивает лишь одну непосредственно предыдущую стори, поэтому находки 40.3 до 40.5 иначе не доедут.

- **Справочник `PriceType` в тестовой БД засеян ровно одним GUID** — «Опт 4» (`4c1962d2-…`, миграция `products/0053`), а тестовая БД строится **С** миграциями (в `backend/pytest.ini` нет `--nomigrations`, вопреки `backend/CLAUDE.md`). Создание `PriceType` с этим же `onec_id` в тесте даёт `duplicate key`. Использовать другой GUID снимка (например «РРЦ» `3d1482c4-…`) либо `get_or_create` (стори 40.2, 40.3).
- **Контрагентов с двумя различными `ТипЦенId` в снимке ноль** — ветка `ambiguous` тестируется вариацией входа сервиса (подмена `price_type_ids` на два GUID из того же снимка), а не выгрузкой; синтетический XML по-прежнему запрещён (NFR-3940-01, стори 40.1, 40.3).
- **`User.onec_price_type_id` однозначен по построению** — гасится в `""` при `НетСоглашения`, не пишется при двух и более различных GUID, не затирается при отсутствии блока реквизитов. На этом инварианте стоит AC 40.5 `resolve_role_from_price_types([onec_price_type_id источника])`: без него привязка выдала бы роль там, где резолвер обязан ответить `ambiguous` (стори 40.3).

### Story 40.1: Парсер читает вид цен из выгрузки и ловит регресс выгрузки

As a Администратор интеграции с 1С,
I want чтобы портал читал вид цен контрагента из выгрузки и громко сообщал, если блок перестал приходить,
So that молчаливая поломка выгрузки после обновления модуля БУС была видна в тот же день, а не через месяцы неизменившихся ролей.

**Контекст:** данные приезжают в новом блоке `<ЗначенияРеквизитов>` (`ТипЦенId`, `ТипЦенНаименование`, `СоглашениеНаименование`, `СоглашениеТиповое`, `СоглашениеСтатус`), который формирует патч части A во второй редакции. Ключевое свойство второй редакции: блок приходит у **каждого** контрагента — при отсутствии соглашения GUID пуст, а `СоглашениеСтатус` равен `НетСоглашения`. Благодаря этому «нет соглашения» и «патч затёрт обновлением расширения» перестают выглядеть одинаково. Правки при обновлении тиражного расширения теряются, отказ тихий: файлы продолжат приходить, но без блока. Поэтому детектор регресса — первая стори эпика, а не последняя: в день выката это единственный наблюдаемый сигнал работоспособности (`roles_updated` штатно равен нулю, живых привязанных аккаунтов на проде нет).

**Acceptance Criteria:**

**Given** контрольную выгрузку контрагентов, снятую **с продуктивной базы** после переноса патча БУС второй редакции,
**When** она получена,
**Then** хотя бы один узел `<Контрагент>` содержит блок `<ЗначенияРеквизитов>` с непустым `ТипЦенId`,
**And** хотя бы один — блок со статусом `НетСоглашения`: обе ветки патча проверяются, иначе половина правки может быть накачена вхолостую.
**And** без выполнения этого AC стори не закрывается — это единственный артефакт, подтверждающий закрытие внешней зависимости части A.

**Given** `_parse_customer_node` (`backend/apps/users/services/parser.py:79`),
**When** узел контрагента содержит блок `<ЗначенияРеквизитов>`,
**Then** `customer_data["price_type_ids"]` — список GUID в нижнем регистре без пробелов,
**And** `customer_data["price_type_meta"]` — список словарей с наименованием вида цен, наименованием соглашения и признаком `СоглашениеТиповое` (FR-40-01).

**Given** узел контрагента, у которого действующего соглашения нет,
**When** он разобран,
**Then** `customer_data["agreement_status"] == "НетСоглашения"`, а `price_type_ids` пуст,
**And** слово-маркер не попадает в `price_type_ids`: `ТипЦенId` остаётся полем под GUID, статус живёт отдельным реквизитом (FR-40-01).

**Given** контрагента-маркетплейс, у которого один и тот же `ТипЦенId` приходит дважды (соглашения «Выкуп …» и «Комиссионное …» на виде цен РРЦ),
**When** узел разобран,
**Then** `price_type_ids` содержит **один** элемент — дедупликация выполняется в парсере, до разрешения роли, иначе 42 контрагента получат ложный `ambiguous` (FR-40-01).

**Given** узел контрагента без блока `<ЗначенияРеквизитов>` (старая выгрузка либо затёртый патч),
**When** он разобран,
**Then** `price_type_ids == []`, `price_type_meta == []`, `agreement_status` пуст, исключения не возникает (FR-40-01).

**Given** разбор элементов `<Роль>` (`parser.py:100`),
**When** стори завершена,
**Then** этот код не изменён — отбор по значению «Покупатель» работает как прежде (FR-40-01).

**Given** контрольную выгрузку `data/import_1c/contragents_pricetype/`, переснятую после второй редакции патча,
**When** она разобрана целиком,
**Then** ни у одного контрагента нет более одного различного `ТипЦенId`,
**And** каждый контрагент несёт либо непустой `price_type_ids`, либо статус `НетСоглашения` — контрагентов без блока в выгрузке нет,
**And** проверяются именно эти инварианты, а не абсолютное число контрагентов: снимок обновляемый, и зашитая константа правилась бы не глядя при каждом переснятии (NFR-3940-01).

**Given** сессию импорта контрагентов,
**When** за весь прогон блок `<ЗначенияРеквизитов>` не встретился **ни разу**,
**Then** `report_details` сессии несёт признак аномалии и счётчик контрагентов с блоком,
**And** итоговый вывод команды `import_customers_from_1c` печатает предупреждение о вероятной поломке выгрузки (FR-40-10).

**Given** сессию, где блок встретился хотя бы у одного контрагента,
**When** прогон завершён,
**Then** признак аномалии не выставляется, а счётчик показывает фактическое число контрагентов с блоком (FR-40-10).

**Given** вторую редакцию патча, при которой блок приходит у каждого контрагента,
**When** в прогоне оказались контрагенты **без** блока,
**Then** их число попадает в отчёт отдельным счётчиком — это признак частичного регресса или устаревшего снимка, даже когда общая аномалия не выставлена (FR-40-10).

**Given** тесты этой стори,
**When** они написаны,
**Then** они построены **только** на реальных XML из `data/import_1c/` (`contragents/` и `contragents_pricetype/`) и помечены `@pytest.mark.unit` либо `@pytest.mark.integration` (NFR-3940-01, -02).

### Story 40.2: Справочник видов цен несёт роль портала и разрешает её

As a Менеджер,
I want чтобы соответствие «вид цен 1С → роль портала» хранилось в справочнике и правилось из админки,
So that появление нового вида цен в 1С не требовало релиза, а решение о роли принималось по явным и проверяемым правилам.

**Контекст:** поле `PriceType.user_role` (`backend/apps/products/models.py:739`) объявлено, пусто у всех записей и нигде не читается. Обратное направление (роль → вид цен при экспорте заказа) уже живёт в `ONEC_EXCHANGE.PRICE_TYPE_BY_ROLE`. Модель `PriceType` в админке **не зарегистрирована вовсе** — регистрация входит в объём стори. Стори не зависит от 40.1 и может выполняться параллельно с ней.

**Acceptance Criteria:**

**Given** data-миграцию приложения `products`,
**When** она применена,
**Then** `PriceType.user_role` заполнено из `ONEC_EXCHANGE.PRICE_TYPE_BY_ROLE` сопоставлением по `onec_name`: «Опт 1…4» → `wholesale_level1…4`, «Тренер» → `trainer`,
**And** у «РРЦ» и «МРЦ» поле остаётся пустым — иначе пять контрагентов-маркетплейсов на виде цен РРЦ уедут в `retail` вопреки решению 1 задания (FR-40-03).

**Given** ту же миграцию,
**When** она применена повторно,
**Then** значения не дублируются и не перезаписываются вслепую, а `reverse` очищает `user_role` только у записей, которые миграция заполняла (FR-40-03, NFR-3940-06).

**Given** админку приложения `products`,
**When** менеджер открывает справочник типов цен,
**Then** модель `PriceType` зарегистрирована, `list_display` содержит `onec_name`, `product_field`, `user_role` и `is_active`,
**And** `user_role` доступно для редактирования (FR-40-04).

**Given** новый модуль `backend/apps/users/services/price_type_role.py`,
**When** он создан,
**Then** в нём объявлены `RoleResolution(role: str | None, reason: str, matched: list[str])` и функция `resolve_role_from_price_types(price_type_ids: list[str], agreement_status: str = "") -> RoleResolution` (FR-40-02).

**Given** контрагента со статусом `НетСоглашения`,
**When** вызывается `resolve_role_from_price_types`,
**Then** возвращается `role=None`, `reason="no_agreement"`, `matched=[]`,
**And** эта причина отличается от `no_data` по смыслу и по последствиям: `no_agreement` — подтверждённое 1С отсутствие соглашения, `no_data` — отсутствие данных как таковых (FR-40-02).

**Given** пустой список GUID **без** статуса `НетСоглашения` (блока в выгрузке не было),
**When** вызывается `resolve_role_from_price_types`,
**Then** возвращается `role=None`, `reason="no_data"`, `matched=[]` (FR-40-02, решение 4).

**Given** список, ни один GUID которого не найден в `PriceType`,
**When** вызывается разрешение,
**Then** возвращается `role=None`, `reason="unknown_price_type"` (FR-40-02, решение 1).

**Given** GUID, который **найден** в `PriceType`, но у записи пустой `user_role` (РРЦ, МРЦ),
**When** вызывается разрешение,
**Then** возвращается `role=None`, `reason="unknown_price_type"` — «известен как вид цен, но роли не несёт» трактуется наравне с неизвестным, иначе маркетплейсы поедут в `retail` (FR-40-02, решение 1).

**Given** список с двумя и более GUID, каждый из которых несёт непустой `user_role`,
**When** вызывается разрешение,
**Then** возвращается `role=None`, `reason="ambiguous"`, а `matched` содержит все конфликтующие GUID (FR-40-02, решение 5).

**Given** список, в котором ровно один GUID несёт непустой `user_role` (остальные — с пустым или неизвестные),
**When** вызывается разрешение,
**Then** возвращается эта роль, `reason="resolved"`, `matched` содержит сработавший GUID (FR-40-02).

**Given** пакет из тысяч контрагентов,
**When** выполняется разрешение роли для каждого,
**Then** справочник `PriceType` читается один раз на сессию импорта, а не запросом на контрагента,
**And** кэш маппинга **живёт не дольше сессии импорта**: модульный или процессный кэш (`lru_cache` на функции) запрещён явно — маппинг редактируется из админки (FR-40-04), а долгоживущий Celery-воркер продолжил бы отдавать значение, отменённое менеджером час назад (NFR-3940-09).

**Given** тест-сторож согласованности прямого и обратного маппинга,
**When** он выполняется,
**Then** для каждой из ролей `wholesale_level1`, `wholesale_level2`, `wholesale_level3`, `wholesale_level4`, `trainer` цепочка `PRICE_TYPE_BY_ROLE → PRICE_TYPE_ID_BY_NAME → PriceType.user_role` возвращает исходную роль,
**And** роли `retail`, `admin` и `federation_rep` исключены **явным списком с комментарием**: у РРЦ `user_role` намеренно пуст, а вид цен «Партнер» на портал не выгружается и записи `PriceType` не имеет (FR-40-13).

**Given** экспорт заказа (`orders/services/order_export.py:550`),
**When** стори завершена,
**Then** его код не изменён — сторож проверяет согласованность, но не переводит экспорт на новый источник (FR-40-13).

**Given** тесты этой стори,
**When** запускается `make test-unit`,
**Then** покрыты все четыре значения `reason`, случай «GUID известен, роль пуста» и сторож; все помечены маркерами (NFR-3940-02, -03).

### Story 40.3: Портал хранит вид цен из 1С, роли не трогая

As a Ответственный за выкат эпика,
I want чтобы портал начал накапливать вид цен из 1С отдельным выкатом, до включения автоприменения роли,
So that к моменту выката 40.4 данные уже были накоплены и проверены глазами, а откат автоприменения не тянул за собой откат миграции поля.

**Контекст:** промежуточная точка выката, ценность операционная, а не пользовательская — так и записано намеренно. Импорт начинает сохранять `ТипЦенId`, но **роли не трогает**: поведение портала для пользователей не меняется, риск нулевой. Побочно менеджер получает вид цен из 1С прямо в карточке — в том числе на странице привязки, где иначе пришлось бы переключаться в 1С. Поле нужно и импорту (40.4), и привязке (40.5). Стори опирается на 40.1 (парсер отдаёт `price_type_ids` и `agreement_status`) и 40.2 (наименование вида цен по GUID для отображения).

**Acceptance Criteria:**

**Given** модель `User` (`backend/apps/users/models.py`),
**When** в неё добавлено поле `onec_price_type_id` (`CharField`, `blank=True`, длина по образцу `PriceType.onec_id`),
**Then** миграция применена на PostgreSQL в Docker, поле создано (FR-40-05, NFR-3940-06).

**Given** `_create_customer` (`backend/apps/users/services/processor.py`),
**When** импортируется новый контрагент с непустым `price_type_ids`,
**Then** `onec_price_type_id` записан,
**And** роль нового контрагента остаётся `IMPORTED_CUSTOMER_ROLE` (`unregistered`) независимо от вида цен (FR-40-05, §5 задания).

**Given** `_update_customer`,
**When** обновляется существующая запись с непустым `price_type_ids`,
**Then** `onec_price_type_id` записан **всегда** — и для привязанных, и для непривязанных записей, независимо от того, применяется ли роль (FR-40-05).

**Given** контрагента со статусом `НетСоглашения` (`reason="no_agreement"`), у которого ранее был сохранён вид цен,
**When** выполняется импорт,
**Then** `onec_price_type_id` **гасится** — 1С подтвердила, что соглашения больше нет,
**And** без этого привязка (40.5) выдала бы роль по соглашению, снятому в 1С месяцы назад, без единой ошибки в логах (FR-40-05).

**Given** контрагента, у которого блок `<ЗначенияРеквизитов>` отсутствует целиком (`reason="no_data"`),
**When** выполняется импорт,
**Then** ранее сохранённое значение `onec_price_type_id` **не затирается** — после второй редакции патча блок обязан приходить у каждого контрагента, поэтому его отсутствие означает поломку выгрузки, а не снятое соглашение; обнуление уничтожило бы данные у всех разом (FR-40-05, FR-40-10).

**Given** карточку пользователя в админке (`backend/apps/users/admin.py:196,258`),
**When** менеджер её открывает,
**Then** в блоке «Интеграция с 1С» показаны `onec_price_type_id` и человекочитаемое наименование вида цен, оба readonly,
**And** если GUID порталу неизвестен или пуст, наименование отображается как «—», а страница не падает (FR-40-06).

**Given** ту же выгрузку,
**When** импорт выполняется повторно,
**Then** значение `onec_price_type_id` не меняется и лишних записей логов не появляется (NFR-3940-08).

**Given** прогон импорта контрольной выгрузки после этой стори,
**When** он завершён,
**Then** роли всех записей не изменились по сравнению с состоянием до прогона — стори выкатывается самостоятельно и не меняет поведение портала (FR-40-05).

**Given** тесты этой стори,
**When** они написаны,
**Then** они используют реальные XML из `data/import_1c/contragents_pricetype/`, покрывают запись поля при создании и обновлении, отсутствие затирания при `no_data` и отображение наименования в админке; все помечены маркерами (NFR-3940-01, -02).

### Story 40.4: Импорт применяет роль привязанным аккаунтам

As a Менеджер,
I want чтобы уровень цен клиента приезжал из 1С сам и отчёт импорта объяснял каждое решение,
So that я перестал вести уровни вручную, а расхождение портала с 1С было видно в отчёте и в `AuditLog`, а не всплывало на заказе.

**Контекст:** ключевая стори эпика. `unlinked_1c_record_q()` (`users/models.py:75-94`) включает условие `role='unregistered'` — если импорт поставит роль импортированным записям, вернётся баг, чинившийся миграцией `0018`: регистрация с известным ИНН откажет, колонка и фильтр «Кандидат 1С» опустеют, `find_link_candidates` вернёт пустой список. Отсюда правило: роль применяется только к записям, **не** проходящим `unlinked_1c_record_q()`. Регрессионные проверки критических путей входят в эту стори как AC (решение Alex, 2026-08-01).

**Acceptance Criteria:**

**Given** `_update_customer` (`backend/apps/users/services/processor.py`),
**When** обновляемая запись **проходит** `User.objects.unlinked_1c_record_q()` (непривязанная запись 1С),
**Then** роль не изменяется ни при каком виде цен, а `onec_price_type_id` записывается (FR-40-07).

**Given** ту же функцию,
**When** обновляемая запись **не проходит** `unlinked_1c_record_q()` (живой привязанный аккаунт) и разрешение вернуло `reason="resolved"`,
**Then** роль аккаунта заменяется разрешённой,
**And** флаг `role_preserved=True` (`processor.py:141-142`) для таких записей больше не выставляется (FR-40-07, FR-40-12).

**Given** привязанный аккаунт с ролью, выставленной менеджером вручную, и вид цен из 1С, дающий другую роль,
**When** выполняется импорт,
**Then** роль перетирается значением из 1С (FR-40-12, решение 3).

**Given** контрагента на соглашении «Опт 2» и на соглашении «Опт 4»,
**When** соответствующие привязанные аккаунты обновляются импортом,
**Then** они получают роли `wholesale_level2` и `wholesale_level4` соответственно (FR-40-07, критерии приёмки #1, #2).

**Given** смену роли импортом,
**When** она выполнена,
**Then** создаётся запись `AuditLog` с `action="role_from_1c"`, `resource_type="User"`, `resource_id` аккаунта,
**And** в деталях зафиксированы прежняя и новая роль, GUID и наименование вида цен, наименование соглашения (FR-40-08, критерий приёмки #3).

**Given** привязанный аккаунт, чья роль уже совпадает с разрешённой,
**When** выполняется импорт,
**Then** роль не переписывается, запись `AuditLog` не создаётся и счётчик `roles_updated` не растёт (NFR-3940-08).

**Given** `process_customers` и команду `import_customers_from_1c` (`management/commands/import_customers_from_1c.py:173`),
**When** прогон завершён,
**Then** `stats` и `report_details` сессии содержат `roles_updated`, `roles_skipped_no_data`, `roles_skipped_no_agreement`, `roles_skipped_unknown_price_type`, `roles_skipped_ambiguous`,
**And** итоговый вывод команды печатает все пять счётчиков (FR-40-09, критерий приёмки #6).

**Given** счётчик `roles_updated`,
**When** формируется отчёт,
**Then** он разбит на две величины: смены, где прежняя роль была `unregistered`, и смены, где прежняя роль была осмысленной,
**And** вторая величина выводится в отчёте отдельной строкой — первая это норма первого дня, а вот перетирание роли, выданной менеджером вручную (FR-40-12), он обязан увидеть, не открывая `AuditLog` (FR-40-09).

**Given** привязанный аккаунт с видом цен, неизвестным порталу или не несущим роли (акции, `МКС`, `Закупочные`, РРЦ),
**When** выполняется импорт,
**Then** роль не изменяется, а счётчик `roles_skipped_unknown_price_type` увеличивается (решение 1, критерий приёмки #7).

**Given** привязанный аккаунт с двумя разными видами цен, каждый из которых несёт роль,
**When** выполняется импорт,
**Then** роль не изменяется, а счётчик `roles_skipped_ambiguous` увеличивается (решение 5).

**Given** привязанный аккаунт без блока `<ЗначенияРеквизитов>` в выгрузке,
**When** выполняется импорт,
**Then** роль не изменяется, а счётчик `roles_skipped_no_data` увеличивается (решение 4).

**Given** привязанный аккаунт со статусом `НетСоглашения`,
**When** выполняется импорт,
**Then** роль не изменяется — снятие соглашения не означает «клиент больше не оптовик», это решение менеджера,
**And** счётчик `roles_skipped_no_agreement` увеличивается, а `onec_price_type_id` гасится по FR-40-05 (FR-40-09).

**Given** прогон импорта контрольной выгрузки,
**When** он завершён,
**Then** `SELECT role, COUNT(*) FROM users WHERE created_in_1c AND onec_id IS NOT NULL AND password = '' GROUP BY role` возвращает только `unregistered` (критерий приёмки #4, NFR-3940-05).

**Given** те же данные после импорта,
**When** проверяются критические пути привязки,
**Then** записи 1С по-прежнему попадают в `User.objects.unlinked_1c_records()`,
**And** регистрация по ИНН, известному 1С, создаёт заявку, а не отказ,
**And** аннотация-индикатор и фильтр «Кандидат 1С» в админке не пустеют, а `find_link_candidates` возвращает кандидатов (NFR-3940-05, критерий приёмки #5).

**Given** пакет из тысяч контрагентов,
**When** выполняется импорт,
**Then** маппинг видов цен читается один раз на сессию импорта — дополнительного запроса на каждого контрагента не появляется,
**And** кэш не переживает сессию: модульный `lru_cache` запрещён, иначе правка `user_role` в админке не подхватится долгоживущим Celery-воркером (NFR-3940-09).

**Given** спеку `spec-1c-unregistered-role`,
**When** стори завершена,
**Then** в её Spec Change Log зафиксирована отмена правила «импорт никогда не меняет роль существующего пользователя» — для привязанных аккаунтов оно больше не действует,
**And** сам текст отменённого правила в теле спеки **вычеркнут** со ссылкой на запись в Change Log, а не оставлен как есть: тело документа читают, а changelog — нет.

**Given** тесты этой стори,
**When** запускается `make test`,
**Then** покрыты все сценарии таблицы «Часть C» раздела 9 задания на реальных XML из `data/import_1c/`, покрытие затронутых модулей ≥ 90 %, все тесты помечены маркерами (NFR-3940-01, -02, -03).

### Story 40.5: Привязка заявки переносит вид цен и сразу выдаёт роль

As a Менеджер,
I want чтобы при связывании заявки с контрагентом 1С аккаунт сразу получал уровень цен из соглашения,
So that клиент видел свои цены с первого входа, а не ждал следующего обмена или моего ручного назначения роли.

**Контекст:** `link_1c_customer` (`backend/apps/users/services/link_1c_customer.py`) уже работает под `transaction.atomic()` с `select_for_update()` на обеих записях — новая логика встраивается в существующую транзакцию, отдельной не заводится. Комментарий у `TRANSFERRED_USER_FIELDS` (`link_1c_customer.py:27`) объявляет `role` намеренно непереносимой — он подлежит обновлению вместе с кодом.

**Acceptance Criteria:**

**Given** `link_1c_customer`,
**When** привязка выполняется успешно,
**Then** `onec_price_type_id` источника перенесён на аккаунт заявителя внутри уже существующей `transaction.atomic()` с `select_for_update()` — отдельная транзакция и отдельный `save()` вне блока не появляются (FR-40-11, NFR-3940-04).

**Given** ту же транзакцию,
**When** `resolve_role_from_price_types([onec_price_type_id источника])` вернул `reason="resolved"`,
**Then** роль цели заменяется разрешённой в той же транзакции (FR-40-11).

**Given** разрешение с `reason` ∈ {`no_data`, `no_agreement`, `unknown_price_type`, `ambiguous`},
**When** выполняется привязка,
**Then** роль цели не изменяется, а сама привязка выполняется штатно — отсутствие вида цен не является отказом привязки (FR-40-11).

**Given** разрешённую роль, не входящую в `User.B2B_ROLES`,
**When** выполняется привязка,
**Then** роль не применяется — цель обязана оставаться B2B-аккаунтом, иначе она выпадет из `link_target_q()` и последующих B2B-сценариев (FR-40-11).

**Given** запись `AuditLog` с `action="link_1c_customer"`,
**When** роль при привязке фактически изменилась,
**Then** `role` присутствует в `changes.transferred_fields`,
**And** `changes.previous_values` содержит прежнюю роль цели (FR-40-11).

**Given** привязку, при которой роль не менялась,
**When** создаётся `AuditLog`,
**Then** `role` в `transferred_fields` отсутствует — список отражает только фактически изменённые поля, как и для остальных полей (FR-40-11).

**Given** комментарий к `TRANSFERRED_USER_FIELDS` (`link_1c_customer.py:27`), объявляющий `role` непереносимой,
**When** стори завершена,
**Then** он приведён в соответствие с новым поведением (FR-40-11).

**Given** спеку `spec-1c-manager-link-counterparty`,
**When** стори завершена,
**Then** в её Spec Change Log зафиксирована отмена правила «`role` не переносится при привязке»,
**And** сам текст отменённого правила в теле спеки **вычеркнут** со ссылкой на запись в Change Log — иначе следующий разработчик прочитает тело, а не changelog.

**Given** ошибку на любом шаге привязки после переноса вида цен,
**When** транзакция откатывается,
**Then** ни `onec_price_type_id`, ни роль цели не остаются изменёнными — частичного состояния не возникает (NFR-3940-04).

**Given** план выката эпика на прод,
**When** он готовится,
**Then** в него включён шаг ручной привязки тестового аккаунта к контрагенту с известным видом цен — без него критерии приёмки #1-#3 задания непроверяемы, поскольку живых привязанных клиентских аккаунтов на проде нет.

**Given** тесты этой стори,
**When** запускается `make test`,
**Then** покрыты перенос вида цен, применение роли в одной транзакции, три причины отказа в применении, состав `AuditLog` и откат при ошибке; все помечены маркерами (NFR-3940-02, -03).
