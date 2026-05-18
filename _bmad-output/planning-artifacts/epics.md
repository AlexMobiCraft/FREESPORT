---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
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
