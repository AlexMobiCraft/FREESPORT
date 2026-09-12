---
baseline_commit: 62319ddc
# Точка ветвления: ветка создана от локального develop на 62319ddc (reflog: «Created from
# HEAD»); это коммит create-story, только документы. Координаты кода проверены на 501535a7
# (2026-09-11), а frontend/ и backend/ в 501535a7..62319ddc не менялись. Первоначальный
# baseline 501535a7 захватывал в диапазон документы эпика (24 файла), поэтому по первому
# ревью он заменён на 62319ddc: `git diff --stat 62319ddc f47b5f83` = 18 файлов коммита
# реализации. Модель changeset — как в 41.9: review_head = HEAD, на котором выполнено
# последнее ревью; доработка по его замечаниям лежит поверх и в просмотренный diff
# `baseline_commit..review_head` не входит по построению.
review_head: f47b5f83
excluded_commits: []
---

# Story 41.10: Оформление заказа и корзина глазами анонима

Status: done

> 🔴 **Серверный HTML `/checkout` полей формы не содержит УЖЕ СЕЙЧАС — и это ничего не доказывает.** Замер 2026-09-11: `curl https://optisport.ru/checkout` отдаёт 29 КБ, в которых только `Загрузка...` и `<title>`, ни одного `<input>`. Причина — `AuthProvider` (`frontend/src/providers/AuthProvider.tsx:164-173`) обёрнут вокруг **всего** `(blue)/layout.tsx` (через `Providers.tsx`) и, пока `isLoading`, вместо детей отдаёт полноэкранный спиннер. На сервере `isLoading` всегда `true`, поэтому серверный HTML любой blue-страницы — один спиннер (та же причина, что у холодных якорей: `deferred-work.md`, раздел стори 41.4). Сканер при этом процитировал «Корзина пуста… Контактные данные…» — **он исполняет JS**. Отсюда: (а) приёмка — по отрендеренному в браузере DOM, а не только по `curl`; (б) гейт `/checkout` обязан быть самостоятельным: если `AuthProvider` когда-нибудь начнёт рендерить детей во время инициализации (так предлагает `deferred-work.md` для починки SSR), серверный рендер `CheckoutPageClient` всё равно должен дать индикатор загрузки, а не поля.
> 🔴 **`useAuth()` вне `AuthProvider` возвращает `isInitialized: false`** — дефолт контекста (`AuthProvider.tsx:38-41`), а проверка `if (!context)` в `useAuth` не срабатывает никогда. Любой тест, рендерящий `CheckoutPageClient` без провайдера и без мока `@/providers/AuthProvider`, навсегда застрянет в состоянии загрузки. Мок обязателен (Task 6).
> 🔴 **Нужен собственный `clearOrder()` при монтировании страницы.** `currentOrder` в `orderStore` переживает переход на success-страницу, а чистит его сейчас только `CheckoutForm` при своём монтировании (`CheckoutForm.tsx:113-117`). Новый гейт решает, монтировать ли форму, **до** неё. Без очистки на уровне страницы покупатель, вернувшийся на `/checkout` после прошлого заказа, навсегда увидит «Переходим к подтверждению заказа». Подробнее — в Dev Notes, «Состояние redirecting».
> 🟠 **У анонима серверная корзина бывает, но при входе не переносится.** `CartViewSet` — `AllowAny` с гостевой корзиной по `session_key` (`backend/apps/cart/views.py:28-54`), фронт кладёт в неё товары без проверки входа (`HitsSection.tsx:189`, `catalog/page.tsx:1436` и др.). А сигнал `merge_guest_cart_on_login` (`backend/apps/cart/signals.py:47-90`) не срабатывает никогда: он выходит при `created=False`, то есть при любом входе, и требует `instance._request`, который в `backend/apps/` не присваивается нигде. На выбор адреса ссылки на вход это влияет (Dev Notes, «Адрес ссылки на вход»), чинить в этой стори нельзя: это бэкенд. Находка уже записана в `deferred-work.md` (раздел create-story 41.10); решение Alex 2026-09-11 — оставить там, отдельной стори нет.
> 🟠 **E2E `tests/e2e/checkout.spec.ts` сломается почти целиком.** 15 из 17 тестов открывают `/checkout` анонимом и заполняют форму, то есть охраняют исправляемый дефект. Workflow `e2e-tests.yml` запускается на каждый PR с `frontend/**`. В обязательные контексты `develop` он не входит, но сейчас зелёный, и красным его оставлять нельзя (Task 7).
> 🟢 **Blast radius LOW по всему, что меняется.** `npx gitnexus impact --repo "C:\Users\1\DEV\FREESPORT"` (2026-09-11, индекс на a73c3bb; кода с тех пор не менялось): `CheckoutPageClient` — 1 прямой вызывающий (`CheckoutPage`), процесс `CheckoutPage`, LOW; `CheckoutForm` — LOW, не меняется. `EmptyCart`, `CartSkeleton`, `CartError` — единственный вызывающий `CartPage` → `CartPageRoute` (`cypher`: `impact` по ним возвращает `ambiguous` из-за дубля `Function`/`Const`). ⚠️ **`ReturnsAndSupportNotice` — HIGH** (6 узлов: `CartSummary`, `OrderSummary`, процессы `CheckoutPage` и `CartPageRoute`), поэтому **сам компонент не меняется**, добавляются только новые места вызова.

## Story

As a **посетитель, который не вошёл или у которого пуста корзина**,
I want **видеть на `/checkout` и `/cart` понятное состояние вместо формы, которую нельзя отправить, и при этом — условия возврата и контакт поддержки**,
so that **сайт не собирал мои данные впустую и сообщал обязательную торговую информацию в любом состоянии**.

**Закрывает:** FR-41-25; FR-41-15 и FR-41-20 в редакции 2026-09-10; отложенный пункт ревью 41.4 «checkout не отличает загрузку корзины от пустой» (`deferred-work.md:935`). **Соблюдает:** NFR-41-01, NFR-41-03, NFR-41-06, NFR-41-08.

**Порядок эпика:** `{41.10, 41.11} → 41.12`. С 41.11 общих файлов нет. 41.12 ждёт мёржа этой стори: редакция 3 обоснования опирается на FR-41-25 — гость не видит формы оформления.

## Acceptance Criteria

### AC1 (FR-41-25) — аноним видит приглашение войти, а не форму

**Given** сессия восстановлена (`useAuth().isInitialized === true`), пользователь не вошёл (`useAuthStore().isAuthenticated === false`)
**When** он открывает `/checkout`
**Then** под заголовком «Оформление заказа» показан блок `data-testid="checkout-login-required"`: заголовок h2 `Войдите, чтобы оформить заказ`, текст `Оформление заказа доступно после входа в личный кабинет.` и ссылка `Войти` с `href="/login?next=%2Fcheckout"`
**And** в DOM страницы нет элемента `<form>` и ни одного `input`, `textarea`, `select`: полей контактов, адреса, доставки и комментария нет
**And** то же поведение и при непустой гостевой корзине: форма зависит от входа, а не от корзины
**And** запрос корзины (`fetchCart`) для анонима **не** выполняется. `GET /cart/` для анонима создаёт сессию и строку `Cart` (`cart/views.py:44-54`), и каждый заход сканера плодил бы мусорные гостевые корзины

### AC2 (FR-41-25) — загрузка не выглядит как пустая корзина, серверный HTML без полей

**Given** сессия ещё восстанавливается (`isInitialized === false`) **или** авторизованный пользователь, чья корзина ещё не загружена
**When** отображается `/checkout`
**Then** показан индикатор `data-testid="checkout-loading"` (`Spinner`, `role="status"`) с видимым текстом `Загрузка…`
**And** текста `Корзина пуста` и полей формы нет
**And** первый рендер `CheckoutPageClient` — до эффектов, то есть то, что попадёт в серверный HTML, — это индикатор загрузки при **любом** состоянии сторов, включая «авторизован и в сторе уже есть товары». Проверяется `renderToString` (Task 6)
**And** `curl -s http://localhost/checkout` (и на проде после выката) не содержит `name="email"`, `name="phone"`, `name="city"`, `name="comment"`

### AC3 (FR-41-25) — авторизованный с пустой корзиной

**Given** авторизованный пользователь, загрузка корзины завершилась успешно, товаров нет
**When** он открывает `/checkout`
**Then** показан блок `data-testid="checkout-empty-cart"`: h2 `Корзина пуста`, текст `Добавьте товары из каталога, чтобы оформить заказ.`, ссылка `В каталог` → `/catalog`
**And** `<form>` и полей формы в DOM нет
**And** нулевого итога нет: `total-price` и `total-price-items` отсутствуют — AC6 стори 41.4 сохраняется

### AC4 (FR-41-25) — ошибка загрузки корзины с повтором

**Given** авторизованный пользователь, загрузка корзины завершилась ошибкой (`cartStore.error` не пуст после `fetchCart`)
**When** отображается `/checkout`
**Then** показан блок `data-testid="checkout-cart-error"` с `role="alert"`: h2 `Не удалось загрузить корзину`, текст `Проверьте подключение и попробуйте ещё раз.`, кнопка `Повторить`
**And** текста `Корзина пуста` и полей формы нет. Сырой текст ошибки (`Network Error`, `Request failed with status code 500`) пользователю не выводится
**And** «Повторить» переводит страницу в `checkout-loading` и заново вызывает `fetchCart`; при успехе показывается форма или пустое состояние по фактической корзине

### AC5 (FR-41-20, FR-41-16) — авторизованный с товарами: регрессии нет

**Given** авторизованный пользователь, корзина загружена, товары есть
**When** он открывает `/checkout`
**Then** форма, сводка `order-summary`, кнопка `checkout-submit-button`, строка со ссылкой на `/privacy-policy` и `returns-support-notice` внутри `order-summary` — ровно как после стори 41.4
**And** автозаполнение контактов из `user`, загрузка сохранённых адресов, черновик формы при переходе к условиям возврата (`CheckoutForm.draft.test.tsx`) работают без изменений
**And** инвариант FR-41-20 держится конструкцией: поля формы рендерятся только в этой ветке, а в ней всегда есть ссылка на политику

### AC6 (FR-41-25) — после успешного заказа не мигает пустое состояние

**Given** заказ создан: `createOrder` записал `currentOrder`, затем `clearCartLocal()` очистил корзину (`orderStore.ts:70-82`)
**When** страница перерисовывается до перехода на `/checkout/success/{id}`
**Then** показан индикатор `data-testid="checkout-redirecting"` с текстом `Заказ оформлен. Переходим к подтверждению…`, а не `checkout-empty-cart`
**And** переход на success-страницу выполняется, как раньше
**And** если `currentOrder` остался от прошлого заказа, он **не** блокирует форму: `CheckoutPageClient` вызывает `clearOrder()` при своём монтировании. Сценарий «оформил заказ → вернулся на `/checkout` с новыми товарами → видит форму» покрыт тестом

### AC7 (FR-41-15) — условия возврата и поддержка в любом состоянии

**Given** `/checkout` в любом состоянии из AC1–AC6
**When** страница отображается
**Then** на ней ровно **один** блок `data-testid="returns-support-notice"` (`getAllByTestId(...).length === 1`). В состояниях без формы он стоит в блоке состояния, в состоянии формы — внутри `order-summary`, как после 41.4
**Given** `/cart` с пустой корзиной (`EmptyCart`), во время загрузки (`CartSkeleton`) и при ошибке (`CartError`)
**When** страница отображается
**Then** на ней ровно один `returns-support-notice`. Требование владельца (Alex, 2026-09-11): в корзине блок виден **всегда**, в том числе когда она пуста
**And** `/cart` с товарами не меняется: блок, как и прежде, внутри `cart-summary` (`CartSummary.tsx:121`)
**And** компонент `ReturnsAndSupportNotice` не меняется (HIGH blast radius), только появляются новые места вызова
**And** ссылка на политику ПДн в состояниях без формы **не** выводится. Абзац «Нажимая кнопку, вы соглашаетесь…» без кнопки бессмыслен, а замечание сканера касается форм (`sprint-change-proposal-2026-09-10.md`, п. 4.2, «Отличие от входного документа»)

### AC8 (NFR-41-06) — доступность

**Given** каждый блок состояния (`checkout-loading`, `checkout-login-required`, `checkout-empty-cart`, `checkout-cart-error`, `checkout-redirecting`) и обновлённые `EmptyCart`, `CartSkeleton`, `CartError`
**When** проверяется доступность
**Then** `axe` не находит нарушений ни в одном из них
**And** иерархия заголовков не нарушена: h1 «Оформление заказа» → h2 блока состояния
**And** ссылки `Войти` и `В каталог` и кнопка `Повторить` достижимы с клавиатуры, их доступные имена совпадают с видимым текстом
**And** индикаторы озвучиваются через `role="status"`, ошибка — через `role="alert"`. Приглашение войти и пустое состояние — **не** `role="alert"`, поэтому `InfoPanel` (он всегда `role="alert"`, `InfoPanel.tsx:97`) для них не используется

### AC9 (NFR-41-01) — тесты и E2E

**Given** изменения стори
**When** прогоняются проверки
**Then** `npm run test`, `npm run lint`, `npm run format:check`, `npx tsc --noEmit` зелёные; число тестов до и после записано в Debug Log
**And** `frontend/src/app/(blue)/checkout/__tests__/page.test.tsx` переписан. Кейсы «Неавторизованный — должен отображать форму checkout» и «должен отображать пустую форму» охраняют дефект и заменяются кейсами AC1
**And** `tests/e2e/checkout.spec.ts`: тесты формы выполняются авторизованным пользователем (моки профиля и refresh), добавлен анонимный сценарий AC1. Прогон `npm run test:e2e` зелёный, либо в Debug Log записано, почему локально не прогнан, и CI-прогон PR зелёный

### AC10 (NFR-41-08) — приёмка глазами анонима

**Given** стори готова к приёмке
**When** она проверяется
**Then** проверка проведена в браузере без cookie и `localStorage` (приватное окно или чистый контекст Playwright) на локальном стенде **с настоящим бэкендом**, без моков: `/checkout` анонимом — AC1 и AC7; `/cart` анонимом с пустой корзиной — AC7; `/checkout` анонимом **после** добавления товара в гостевую корзину — всё равно AC1
**And** `curl` серверного HTML `/checkout` — AC2
**And** авторизованный сценарий (AC5) проверен тем же прогоном, но приёмкой сам по себе не считается
**And** результаты с командами записаны в Debug Log. Прод-проверка после выката — за владельцем (выкат ручной)

### AC11 — границы: что стори НЕ делает

**Then** **нет** редиректа `/checkout` → `/login` в `middleware.ts`: аноним не увидел бы условий возврата и поддержки (FR-41-15). `/checkout` в `protectedPaths` (`middleware.ts:376`) **не** добавляется
**And** **не** трогается бэкенд: гостевые корзины, `merge_guest_cart_on_login`, `openapi.yaml`, типы фронта. NFR-41-02 не задействован
**And** **не** меняются `ReturnsAndSupportNotice`, `OrderSummary`, `CheckoutForm`, `AuthProvider`, `authStore`, `cartStore`, `orderStore`, `LoginForm`, страница `/login`. Строка о политике на форме входа — стори 41.12
**And** **не** удаляются защитные ветки пустой корзины внутри `CheckoutForm` (`InfoPanel` «Корзина пуста», `CheckoutForm.tsx:328-335`) и `OrderSummary` (`empty-cart-message`, AC6 стори 41.4). На странице они становятся недостижимы, но охраняют компоненты при прямом использовании, и на них завязаны тесты `OrderSummary.test.tsx` и `CheckoutForm.test.tsx`
**And** **не** добавляется ссылка «Зарегистрироваться» в приглашение: она уже есть на `/login`, а розничная регистрация отключена (`REGISTRATION_ALLOW_RETAIL`)
**And** **не** правится пре-существующее: потеря гостевой корзины при входе остаётся в `deferred-work.md`, где уже записана (решение Alex 2026-09-11). Open redirect в `LoginForm` передан в стори 41.12 (решение Alex 2026-09-11): `LoginForm` правит она, в этой стори файл не трогается

## Tasks / Subtasks

- [x] **Task 1. Ветка и baseline**
  - [x] `git switch -c feature/story-41-10-checkout-for-anonymous` от `develop`: прямые коммиты в `develop` запрещены, ветка защищена
  - [x] `git rev-parse --short HEAD` сверить с `baseline_commit: 501535a7`. Если `frontend/` менялся (`git diff --stat 501535a7 HEAD -- frontend`), перечитать координаты в Dev Notes
  - [x] **До правок** прогнать затрагиваемое и записать число зелёных: `cd frontend; npm run test -- --run "src/app/(blue)/checkout" src/components/checkout src/components/cart src/utils/checkout`

- [x] **Task 2. Чистая функция выбора состояния** (AC1–AC6)
  - [x] Новый `frontend/src/utils/checkout/checkoutView.ts`:
        ```ts
        /** Состояние страницы оформления заказа (Story 41.10, FR-41-25). */
        export type CheckoutView =
          | 'loading' | 'anonymous' | 'error' | 'redirecting' | 'empty' | 'form';

        export type CartLoadStatus = 'pending' | 'ready' | 'error';

        export interface CheckoutViewInput {
          isAuthInitialized: boolean;
          isAuthenticated: boolean;
          cartLoad: CartLoadStatus;
          hasItems: boolean;
          isRedirecting: boolean;
        }

        export function resolveCheckoutView(input: CheckoutViewInput): CheckoutView {
          // Порядок проверок — часть требования, см. Dev Notes «Приоритет состояний».
          if (!input.isAuthInitialized) return 'loading';
          if (!input.isAuthenticated) return 'anonymous';
          if (input.cartLoad === 'pending') return 'loading';
          if (input.cartLoad === 'error') return 'error';
          if (input.isRedirecting) return 'redirecting';
          if (!input.hasItems) return 'empty';
          return 'form';
        }
        ```
  - [x] Комментарии на русском (NFR-41-03). Функция без побочных эффектов — её тестирует таблица (Task 6)

- [x] **Task 3. Компонент состояний `CheckoutStateView`** (AC1–AC4, AC6–AC8)
  - [x] Новый `frontend/src/components/checkout/CheckoutStateView.tsx`, директива `'use client'`: у кнопки «Повторить» обработчик (`project-context.md`, §7)
  - [x] Пропсы: `view: Exclude<CheckoutView, 'form'>` и `onRetry?: () => void`
  - [x] Разметка — белая карточка в стиле `OrderSummary` (`rounded-lg bg-white p-6 shadow-sm`), палитра Tailwind gray, как у всей страницы checkout: `text-gray-900` / `text-gray-600`. Тексты и `data-testid` — **дословно** из AC1–AC4 и AC6
  - [x] `loading` и `redirecting` — `Spinner` из `@/components/ui` (`size="large"`, осмысленный `label`, у него уже `role="status"`) и видимый текст. `error` — контейнер с `role="alert"`. `anonymous` и `empty` — без `role="alert"`
  - [x] Ссылки `Войти` и `В каталог` — `next/link`, оформлены как основная кнопка. Классы CTA взять из `EmptyCart.tsx:34`. `Button` из `@/components/ui` рендерит только `<button>` и ссылкой быть не может
  - [x] Адрес входа — одна константа модуля, собранная так же, как её собирает middleware (`url.searchParams.set('next', pathname)`, `middleware.ts:407`):
        ```ts
        // Тот же вид, что у middleware (`next=%2F...`): сканер считает разные написания
        // одного адреса разными страницами (повторный аудит 10.09.2026).
        const LOGIN_HREF = `/login?${new URLSearchParams({ next: '/checkout' })}`;
        ```
  - [x] В конце карточки — **один** `<ReturnsAndSupportNotice className="text-center text-xs text-gray-500" />` (типографика как в `OrderSummary.tsx:158`), во всех пяти состояниях
  - [x] Экспорт — именованный, по образцу соседних компонентов `components/checkout/`. Barrel-файла в `components/checkout/` нет, заводить не нужно

- [x] **Task 4. `CheckoutPageClient` — гейт** (AC1–AC7)
  - [x] `frontend/src/app/(blue)/checkout/CheckoutPageClient.tsx`. Источники:
    - `const { isInitialized } = useAuth()` из `@/providers/AuthProvider`
    - `const { user, isAuthenticated } = useAuthStore()` — деструктуризация, как сейчас, иначе сломаются моки `mockReturnValue` в тестах
    - `const { items, fetchCart } = useCartStore()` (`error` читается через `useCartStore.getState().error` после `await fetchCart()`, а не отдельной деструктуризацией — избегает неиспользуемой переменной)
    - `const { currentOrder, clearOrder } = useOrderStore()`
  - [x] Локальное `const [cartLoad, setCartLoad] = useState<CartLoadStatus>('pending')`. **Не** использовать `cartStore.isLoading`: до запуска эффекта он `false`, и первый кадр выглядел бы как пустая корзина — ровно дефект `deferred-work.md:935`
  - [x] Эффект монтирования: `clearOrder()` (AC6, обязательно — см. врезку 🔴 выше)
  - [x] Эффект загрузки корзины с зависимостями `[isInitialized, isAuthenticated, user?.id, fetchCart]` и счётчиком попыток для отбрасывания устаревших ответов:
        - `!isInitialized || !isAuthenticated` → ничего не запрашивать (AC1)
        - иначе `setCartLoad('pending')` → `await fetchCart()` → если попытка не устарела, `setCartLoad(useCartStore.getState().error ? 'error' : 'ready')`
        - `fetchCart` ошибок не бросает: пишет их в `cartStore.error` и сбрасывает его в `null` в начале (`cartStore.ts:110-121`)
  - [x] `onRetry` = та же загрузка (вынесена в `useCallback` как `loadCart`)
  - [x] `const view = resolveCheckoutView({ isAuthInitialized: isInitialized, isAuthenticated, cartLoad, hasItems: items.length > 0, isRedirecting: currentOrder?.id != null })`
  - [x] Разметка: контейнер и h1 «Оформление заказа» — без изменений, приветствие — по-прежнему только при `isAuthenticated && user`. Далее `view === 'form' ? <CheckoutForm user={user} /> : <CheckoutStateView view={view} onRetry={retry} />`
  - [x] Docstring: добавлены Story 41.10 и перечень состояний

- [x] **Task 5. Корзина: блок в пустом, загрузочном и ошибочном состоянии** (AC7)
  - [x] `EmptyCart.tsx`: `<ReturnsAndSupportNotice className="mt-8 text-center text-body-s text-[var(--color-text-secondary)]" />` внутри белой карточки, после ссылки «В каталог» (`EmptyCart.tsx:32-38`). Типографика темы blue — как в `CartSummary.tsx:121`
  - [x] `CartError.tsx`: то же, после кнопки «Повторить» (`CartError.tsx:41-48`)
  - [x] `CartSkeleton.tsx`: блок в колонке итогов, **под** `<CartSummarySkeleton />`, чтобы на мобильном он оказался в конце, как у `CartSummary`
  - [x] `CartPage.tsx` **не** менять: ветки состояний остаются (`CartPage.tsx:42-60`), блок приезжает вместе с компонентами
  - [x] Директивы и `data-testid` существующих компонентов не трогать

- [x] **Task 6. Юнит- и компонентные тесты** (AC1–AC9)
  - [x] Новый `frontend/src/utils/checkout/__tests__/checkoutView.test.ts` — таблица на все значимые комбинации, в том числе:
    - `isAuthInitialized=false` при любых остальных → `loading`
    - аноним при `hasItems=true` → `anonymous`
    - `pending` → `loading`
    - `error` при `hasItems=true` → `error`
    - `isRedirecting` при `hasItems=false` → `redirecting`
    - `ready` + пусто → `empty`
    - `ready` + товары → `form`
  - [x] Новый `frontend/src/components/checkout/__tests__/CheckoutStateView.test.tsx`: тексты и `href` дословно по AC; `onRetry` вызывается кликом; в каждом состоянии ровно один `returns-support-notice`; ни в одном нет `input`, `textarea`, `select`, `form`; `axe` на каждом из пяти состояний (образец настройки — `components/cart/__tests__/accessibility.test.tsx:10-37`)
  - [x] Переписан `frontend/src/app/(blue)/checkout/__tests__/page.test.tsx`. Обязательные моки и ловушки применены:
    - `vi.mock('@/providers/AuthProvider', () => ({ useAuth: vi.fn(() => ({ isInitialized: true, isLoading: false })) }))` — без него всё зависнет в `loading`
    - `fetchCart: vi.fn().mockResolvedValue(undefined)` — промис, иначе `await` ничего не ждёт
    - ожидания после загрузки — через `findBy*` / `waitFor`: корзина разрешается асинхронно
    - `useOrderStore` — реальный стор, в `beforeEach` сбрасывается `currentOrder` через `useOrderStore.setState`
  - [x] Кейсы `page.test.tsx`:
    - AC1: аноним → приглашение, `href="/login?next=%2Fcheckout"`, `fetchCart` **не** вызван, нет `form` / `input`; то же при непустых `items`
    - AC2: `isInitialized=false` → `checkout-loading`, нет «Корзина пуста»; авторизован и `fetchCart` висит (неразрешённый промис) → `checkout-loading`
    - AC2: `renderToString(<CheckoutPageClient />)` из `react-dom/server` при «авторизован, `items` непуст» не содержит `name="email"` и содержит `checkout-loading`
    - AC3: пустая корзина → `checkout-empty-cart`, нет `total-price`
    - AC4: `fetchCart` выставляет `error` → `checkout-cart-error`; клик «Повторить» → `fetchCart` вызван повторно
    - AC5: товары → «Контактные данные», «Адрес доставки», автозаполнение `test@example.com` — существующие кейсы авторизованного пользователя сохранены
    - AC6: `currentOrder` с `id` + пустая корзина → `checkout-redirecting`; устаревший `currentOrder` до монтирования + товары → форма (`clearOrder` сработал)
    - AC7: во всех кейсах `getAllByTestId('returns-support-notice')` длины 1
  - [x] Корзина: в `EmptyCart.test.tsx`, `CartError.test.tsx`, `CartSkeleton.test.tsx` — блок присутствует ровно один раз. В `CartPage.test.tsx` — для веток empty, loading, error. В `accessibility.test.tsx` — `axe` на `CartError` (добавлен) и повторный прогон на `EmptyCart` с блоком (существующий тест покрыл автоматически)
  - [x] `OrderSummary.test.tsx` и `CheckoutForm*.test.tsx` **не** менялись, прогнаны — регрессий нет (154 passed | 1 skipped)

- [x] **Task 7. E2E `tests/e2e/checkout.spec.ts`** (AC9)
  - [x] Вынести `mockAuthUser` и `setupAuthMocks` (`checkout.spec.ts:502-552`) на уровень модуля. Добавить хелпер `authenticate(page)`: `addInitScript` с `localStorage.refreshToken`, cookie `refreshToken` — как в `checkout.spec.ts:562-573`. `AuthProvider` сам сходит в `/users/profile/` и `/auth/refresh/`, оба замоканы
  - [x] Добавить мок `**/api/v1/users/addresses/**` → `[]`: иначе авторизованная форма зовёт реальный бэкенд, и тест получает тост «Не удалось загрузить сохранённые адреса»
  - [x] Все тесты, заполняющие форму (`Checkout Flow`, `Checkout Form Validation`, `Checkout Error Handling`), — через `authenticate` в `beforeEach`
  - [x] Новый `test.describe('Anonymous checkout (Story 41.10)')` без авторизации:
    - `checkout-login-required` виден
    - `input[name="email"]` и `input[name="phone"]` — `toHaveCount(0)`. Селектор именно по `name`: в шапке есть поле поиска
    - `returns-support-notice` виден
    - ссылка «Войти» → `/login?next=%2Fcheckout`
    - GET к API корзины (`/api/v1/cart/`) не отправлялся — счётчик через `page.on('request')`. Других вызывающих API корзины, кроме `CheckoutPageClient` и `CartPage`, во фронте нет: шапка корзину не запрашивает
  - [x] Прогон: `cd frontend; $env:PLAYWRIGHT_BASE_URL='http://localhost:3000'; npx playwright test tests/e2e/checkout.spec.ts` против поднятого фронта (после `restart frontend` + `restart nginx`) — **18 passed**, стабильно и с `--workers=1` (как в CI), и с параллелизмом по умолчанию. Потребовались два точечных фикса тестов, ставших авторизованными (форма больше не доступна анониму): «shows validation errors for empty required fields» явно очищает автозаполненные контакты перед проверкой валидации; «validates phone format» переведён на `focus()+fill('')+pressSequentially()` вместо голого `fill()` — raw `fill()` не перезаписывает уже валидное маскированное значение телефона

- [x] **Task 8. Документы**
  - [x] `deferred-work.md:935` — дописана «**ЗАКРЫТО стори 41.10** (2026-09-11): …» с кратким итогом
  - [x] Находка «гостевая корзина не переносится при входе» **уже записана** в `deferred-work.md`, раздел `## Deferred from: create-story 41.10 — checkout глазами анонима (2026-09-11)`. Решение Alex 2026-09-11: оставить в отложенной работе, отдельной стори не заводить. Повторно не занесена и не тронута
  - [x] Open redirect после входа в `deferred-work.md` **не** занесён: он уже внесён в объём стори 41.12 (эпик, `### Story 41.12`, решение Alex 2026-09-11)
  - [x] Докстринги затронутых компонентов — упоминание Story 41.10 (`CheckoutPageClient`, `CheckoutStateView`, `checkoutView.ts`, комментарии в `EmptyCart.tsx`/`CartError.tsx`/`CartSkeleton.tsx`)

- [x] **Task 9. Ручная приёмка по NFR-41-08** (AC10)
  - [x] `docker compose --env-file .env -f docker/docker-compose.yml restart frontend`, затем `restart nginx`: после рестарта фронта nginx держит старый IP и отдаёт 502 (память `project_prod_nginx_upstream_dns`). HMR на Windows-bind-mount правки не подхватывает (Debug Log стори 41.4)
  - [x] `curl -s http://localhost/checkout | grep -c 'name="email"'` → `0` (подтверждено и на `:3000`, и на `:80` через nginx)
  - [x] Чистый браузерный контекст без cookie, **реальный** бэкенд:
    - `/checkout` → AC1 + AC7 — подтверждено
    - `/cart` → `EmptyCart` + блок — подтверждено
    - добавить товар с `/catalog` → `/checkout` → всё равно приглашение — подтверждено
    - «Войти» → `/login?next=%2Fcheckout` → вход тестовым логином → возврат на `/checkout`, дальше форма или пустое состояние по корзине **аккаунта** — подтверждено (гейт уходит от `checkout-login-required`/`checkout-loading`)
  - [x] Авторизованным с товарами — форма и сводка, как после 41.4 (AC5) — подтверждено (контакты, адрес, `order-summary`, `returns-support-notice`). Оформление тестового заказа (AC6, `checkout-redirecting` → success) **не** прогонялось на реальном бэкенде: локально не засеяны способы доставки (`GET /delivery/methods/` → `[]`, не связано со стори), поэтому AC6 подтверждён автотестами — юнитом гейта (Task 6) и E2E «complete checkout flow from cart to success» (Task 7, мокнутый API заказа, полный сабмит до success-страницы)
  - [x] Браузерных MCP-инструментов не было в сессии — использован временный Playwright-спек `tests/e2e/tmp-story-41-10-check.spec.ts` против реального бэкенда (5 сценариев, все зелёные) и временный тестовый пользователь `story-41-10-tmp@example.test`, оба удалены после прогона

- [x] **Task 10. Перед коммитом**
  - [x] `npx gitnexus detect-changes --scope all --repo "C:\Users\1\DEV\FREESPORT"` — 13 файлов, 11 символов, risk medium. Изменённые символы: `CheckoutPageClient`, `EmptyCart`, `CartError`, `CartSkeleton` (плюс `breadcrumbItems`, тестовые константы). Новые файлы (`CheckoutStateView`, `resolveCheckoutView`, `checkoutView.ts`) индекс не видит — построен на `a73c3bb`, до их создания; это ожидаемо и не признак пропуска. `ReturnsAndSupportNotice`, `OrderSummary`, `CheckoutForm` среди изменённых **не появились** — AC11 не нарушен
  - [x] File List сверен с `git status --short` (working tree чист от посторонних изменений, `baseline_commit` не сдвигался — коммитов ещё не было)
  - [x] `review_head` установлен на `f47b5f83` — коммит владельца, завершающий содержательную работу (проверено `git show --stat`: в коммит вошли ровно ожидаемые файлы из File List)
  - [x] Коммит создан владельцем (`f47b5f83`, ветка `feature/story-41-10-checkout-for-anonymous`). Push и PR — по-прежнему только по явной просьбе владельца. Выкат на прод — ручной, за владельцем (Dev Notes, «Выкат»)

## Dev Notes

### Что меняется и что сохраняется — по файлам

| Файл | Сейчас | Что меняет стори | Что сохранить |
|---|---|---|---|
| `app/(blue)/checkout/CheckoutPageClient.tsx` (UPDATE) | Всегда рендерит `CheckoutForm`, `fetchCart()` для всех, авторизацию не проверяет (`:18-43`) | Гейт по `resolveCheckoutView`; `clearOrder()` и загрузка корзины — только авторизованным | h1, приветствие по `isAuthenticated && user`, контейнер `container mx-auto px-4 py-8…` |
| `components/checkout/CheckoutForm.tsx` | Выводит `InfoPanel` «Корзина пуста» и сразу поля (`:328-372`) | **Ничего** — форма просто перестаёт монтироваться в чужих состояниях | Всё, включая `key={user?.id ?? 'guest'}`, черновик (`:73`, `:305-325`), `clearOrder()` при монтировании |
| `components/checkout/OrderSummary.tsx` | Блок возврата и ссылка на политику внутри `{!isEmpty && …}` (`:126-160`) | **Ничего** | AC6 41.4: пустая ветка без итога и без блока — её тестирует `OrderSummary.test.tsx:129-152` |
| `components/cart/EmptyCart.tsx`, `CartError.tsx`, `CartSkeleton.tsx` (UPDATE) | Блока нет | + `ReturnsAndSupportNotice` | `data-testid`, `role="main"`, `aria-busy`, хлебные крошки, заголовки |
| `components/cart/CartPage.tsx` | Ветки `!mounted` / loading / error / empty / content (`:42-60`) | **Ничего** | Порядок веток и `mounted`-паттерн |
| `components/common/ReturnsAndSupportNotice.tsx` | Общий блок (41.4) | **Ничего** — HIGH blast radius | — |

### Приоритет состояний — почему именно такой порядок

1. **`!isAuthInitialized` → `loading`.** Пока сессия не восстановлена, «аноним» может оказаться покупателем. Ранний показ приглашения мигнул бы у вошедшего пользователя.
2. **`!isAuthenticated` → `anonymous`.** Раньше любых проверок корзины: у анонима бывает непустая гостевая корзина, но заказ ему недоступен (`backend/apps/orders/views.py:37`). Корзину не запрашиваем (AC1).
3. **`cartLoad === 'pending'` → `loading`.** Первый рендер всегда здесь (`useState('pending')`): это и защита серверного HTML (AC2), и лечение `deferred-work.md:935`. Цена — короткий индикатор даже при уже наполненном сторе после перехода из `/cart`. Корзину всё равно надо сверить с сервером, так же делает `CartPage.tsx:33-40`.
4. **`error` → `error`.** Раньше пустоты: ошибка не должна выглядеть как «Корзина пуста».
5. **`isRedirecting` → `redirecting`.** Раньше пустоты: после заказа корзина очищена локально, а до success-страницы ещё идёт навигация.
6. **`!hasItems` → `empty`**, иначе **`form`**.

### Состояние redirecting — почему нужен свой `clearOrder()`

`createOrder` сначала пишет `currentOrder`, потом зовёт `clearCartLocal()` (`orderStore.ts:70-82`). Затем `onSubmit` в `CheckoutForm` читает `currentOrder.id` и делает `router.push` (`CheckoutForm.tsx:270-289`). Без состояния `redirecting` пустая корзина сняла бы форму и на время навигации показала бы «Корзина пуста, в каталог». Размонтирование формы посреди `onSubmit` безопасно: продолжение читает стор через `getState()`, а `router` из `useRouter()` — стабильный экземпляр App Router, после размонтирования он работает.

`orderStore` не persist-ится, но живёт всю SPA-сессию. После заказа `currentOrder` остаётся заполненным: success-страница его не читает и не чистит (`grep currentOrder app/(blue)/checkout/success` пуст). Если `CheckoutPageClient` не вызовет `clearOrder()` при монтировании, повторный заход на `/checkout` дойдёт до `ready`, увидит `currentOrder` и застрянет в `redirecting`. `clearOrder()` в эффекте монтирования срабатывает раньше, чем корзина успевает загрузиться: пока идёт загрузка, страница в `loading`, и устаревший `currentOrder` не виден ни в одном кадре.

### Адрес ссылки на вход — `/login?next=%2Fcheckout` (решение create-story, подтверждено Alex 2026-09-11)

Эпик оставил выбор на create-story по правилу: «у анонима корзины не бывает — простой `/login`; бывает — `next=/checkout` оправдан». Факты на `501535a7`:

- **Корзина у анонима бывает.** `CartViewSet` и `CartItemViewSet` — `AllowAny` с гостевой корзиной по сессии (`cart/views.py:28-54`, `:87-129`). `api-client` шлёт `withCredentials` ради `sessionid` гостевой корзины (`services/api-client.ts:38-39`). Добавление в корзину на фронте входа не требует. `docs/data-models.md:68`: «гостевая корзина поддерживается для browsing/cart flow».
- **При входе она не переносится** (врезка 🟠 выше). После входа `/checkout` покажет корзину **аккаунта**.
- **Простой `/login` уводит на `/`**: `LoginForm.tsx:60` — `redirectUrl || '/'`. Корень у вошедшего ведёт на `/home` (`app/page.tsx:25-28`), и контекст оформления теряется.
- **Цена в отчёте:** сканер посчитает `/login?next=%2Fcheckout` ещё одним вариантом формы входа — плюс 1–2 критичных «нет чекбокса согласия». Критерий успеха эпика их покрывает («на любом варианте адреса `/login`»), SCP 2026-09-10 это предусмотрел («Ожидаемый результат повторного прогона»).

Вывод: `next=/checkout`. Покупатель с корзиной в аккаунте, а это сценарий оптового клиента, вернётся прямо к форме. Покупатель с пустой корзиной аккаунта увидит пустое состояние со ссылкой в каталог, а не главную. Кодировка `%2F` выбрана как у middleware (`middleware.ts:407`), чтобы один и тот же адрес не существовал в двух написаниях. Текст приглашения **не** обещает, что гостевая корзина сохранится: сейчас она не сохраняется.

### Почему не редирект в middleware

При редиректе аноним не увидел бы на `/checkout` условий возврата и поддержки (FR-41-15), а замечание сканера по адресу входа это не сняло бы. Решение эпика: `### Story 41.10`, «Почему не редирект в middleware».

### Ловушки тестов — сводка

| Где | Ловушка | Что делать |
|---|---|---|
| `page.test.tsx` | `useAuth()` без провайдера → `isInitialized: false` | Мокать `@/providers/AuthProvider` |
| `page.test.tsx` | `vi.mock('@/stores/cartStore')` — автомок, `fetchCart: vi.fn()` возвращает `undefined` | `mockResolvedValue(undefined)`; `getState` в автомоке может отсутствовать |
| `page.test.tsx` | Сторы мокаются через `mockReturnValue` целого объекта | В компоненте — деструктуризация `useXStore()`, не селекторы |
| `page.test.tsx` | Реальный `useOrderStore` протекает между тестами | Сбрасывать `useOrderStore.setState({ currentOrder: null, error: null })` в `beforeEach` |
| `EmptyCart.test.tsx`, `CartError.test.tsx` | Ищут крошки по `name: /breadcrumb/i` | Не трогать: подпись переименует стори 41.12, её тесты правит она |
| E2E | Поле поиска в шапке | Проверять отсутствие полей по `name`, а не «ни одного input» |
| E2E | Авторизованная форма зовёт `/users/addresses/` | Мок `[]` |

### Выкат (для владельца, вне объёма dev-story)

Только frontend: миграций, бэкенда, `next.config.ts` и зависимостей нет. На проде — `git fetch origin main; git reset --hard origin/main`, `docker compose … up -d --build frontend`, затем **обязательно** `docker compose … restart nginx`. Иначе nginx держит старый IP фронта, а `proxy_intercept_errors` отдаёт заглушку со статусом 200 — падение невидимо по коду ответа (sprint-status, 41.5). После выката: `curl -s https://optisport.ru/checkout | grep -c 'name="email"'` → `0`, и приватное окно — AC1 и AC7 на `/checkout` и `/cart`. Повторный прогон сканера — после выката 41.10–41.12 и правки п. 1.2 политики (эпик, «Обоснование приоритета стори 41.10–41.12»).

### Previous story intelligence (41.4, 41.9, 41.8)

- **41.4 — причина этой стори.** Приёмка шла сценарием «авторизован, корзина не пуста», сканер ходит анонимом с пустой корзиной. Отсюда NFR-41-08 и AC10: авторизованный прогон приёмкой не считается.
- **41.4 — черновик формы.** Механизм `checkoutDraft` (одноразовый, в памяти, привязан к `userId`) срабатывает на клик `/partners#returns` **внутри** `<form>`. В новых состояниях формы нет, спасать нечего, а блок `ReturnsAndSupportNotice` в `CheckoutStateView` стоит вне формы. Так и должно быть.
- **41.4 — холодный якорь.** `/partners#returns` при прямом входе не прокручивает страницу — общесайтовый дефект SSR под `(blue)`, записан в `deferred-work.md`. Переходы по ссылке внутри приложения работают — это и есть путь из блока.
- **41.4 / 41.8 — локальная среда.** HMR на Windows не подхватывает правки: нужен `restart frontend`, затем `restart nginx`. Браузерных MCP-инструментов в сессии может не быть — работал временный Playwright-спек.
- **41.9 и ранее — метаданные.** File List сверять с `git diff`, `review_head` ставить один раз и не сдвигать документационными правками. Числа в отслеживаемые файлы вписывать только готовыми (память `feedback_no_placeholders_in_tracked_files`): владелец может закоммитить дерево посреди dev-story.

### Git intelligence

Последние коммиты `develop` (`501535a7`, `9ce1d7c7`, `b4c466f9`, `d4726694`, `b8013e23`) — навыки BMAD и закрытие 41.9, `frontend/src/components/checkout|cart` и `app/(blue)/checkout` не трогали. Последние правки этих файлов — стори 41.4 (`d0772737`, `52d5392c`, `99358186`), её паттерны и есть образец: общий компонент в `components/common`, `className` задаёт вызывающий, тесты кладутся рядом в `__tests__/`, `axe` — по образцу `cart/__tests__/accessibility.test.tsx`.

### Технологический контекст

Новых зависимостей нет. Next **15.5.18** (App Router), React **19.1.0**, zustand **^4.5.7** (`persist` у `cartStore` хранит только промокод, `items` не персистятся — `cartStore.ts:288-296`), Vitest **^4**, `vitest-axe` **^0.1.0**, `@playwright/test` **^1.57**. React 19: `ref` — обычный проп, `forwardRef` в новом коде не нужен (`project-context.md`, §7). Веб-исследование не требовалось: стори использует только уже подключённые API.

### Project Structure Notes

- Чистая функция → `frontend/src/utils/checkout/`, рядом с `checkoutDraft.ts` и `addressMapping.ts`; тест → `utils/checkout/__tests__/` (каталог есть)
- Компонент состояний → `frontend/src/components/checkout/`: он специфичен для оформления, в `common/` ему не место. Тест → `components/checkout/__tests__/`
- Отклонений от структуры нет

### References

- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.10] — AC эпика, «Почему не редирект», «Решить при create-story — адрес ссылки на вход»
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#FR-41-15, FR-41-20, FR-41-25, NFR-41-08] — уточнения 2026-09-10
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-09-10.md#4.2] — происхождение стори; ссылка на политику остаётся только там, где форма
- [Source: _bmad-output/implementation-artifacts/Story/41-4-checkout-trade-info-and-policy-link.md] — `ReturnsAndSupportNotice`, AC6 (нет нулевого итога), черновик формы, пометка о пересмотре
- [Source: _bmad-output/implementation-artifacts/deferred-work.md:935] — отложенный пункт, который поглощает стори
- [Source: frontend/src/providers/AuthProvider.tsx:38-41,164-176] — дефолт контекста и глобальный спиннер
- [Source: frontend/src/stores/cartStore.ts:110-121; orderStore.ts:49-98] — поведение `fetchCart`, `createOrder`, `clearOrder`
- [Source: backend/apps/cart/views.py:28-54; backend/apps/cart/signals.py:47-90] — гостевая корзина и мёртвый перенос
- [Source: frontend/src/middleware.ts:375-407] — `protectedPaths` и формат `next`
- [Source: project-context.md#7] — `'use client'`, рестарт контейнера, React 19

## Dev Agent Record

### Review Findings

Проверка 2026-09-11: story-документ и реализация в диапазоне `501535a7..f47b5f83`; линзы Adversarial, Edge-Case Hunter, Editorial Structure и Editorial Prose. Ниже сохранены все находки review. Доработка по ним — 2026-09-11, поверх `f47b5f83`: у каждого пункта указано, чем он закрыт.

#### Реализация и проверки

- [x] [Review][Patch] Согласовать AC8 с разметкой `CheckoutStateView`: критерий требует иерархию h1 → h2 для каждого блока состояния, но ветки `loading` и `redirecting` содержат только `Spinner` и `<p>`. Добавить визуальные h2 либо явно исключить эти состояния из требования об иерархии; иначе AC8 формально не выполнен при зелёном `axe`. [`frontend/src/components/checkout/CheckoutStateView.tsx:54-70`; AC8]
  — **Закрыто:** видимый текст индикаторов `loading` и `redirecting` стал `<h2>`, текст и вид прежние. Тесты: `CheckoutStateView.test.tsx` — «ровно один h2» во всех пяти состояниях; `page.test.tsx` — «h1 страницы → h2 блока состояния» по каждому состоянию без формы.
- [x] [Review][Patch] Дополнить тест повторной загрузки по AC4: сейчас он сохраняет `error: 'Network Error'` и проверяет только второй вызов `fetchCart`. Управляемым Promise проверить полный переход `error → loading → form/empty`, включая очистку ошибки; иначе неработающий retry пройдёт тесты. [`frontend/src/app/(blue)/checkout/__tests__/page.test.tsx:199-215`]
  — **Закрыто:** `it.each` на два исхода (`order-summary` и `checkout-empty-cart`). Управляемый Promise проходит `error → loading → итог`, мок `fetchCart` сбрасывает ошибку, как настоящий.
- [x] [Review][Patch] Защитить промежуточное состояние AC6 в E2E: тест полного заказа проверяет только конечный URL success-страницы и не наблюдает `checkout-redirecting`. Задержать ответ или навигацию, проверить `checkout-redirecting` и отсутствие `checkout-empty-cart`; иначе мигание пустого состояния останется незамеченным. [`frontend/tests/e2e/checkout.spec.ts:286-320`]
  — **Закрыто:** новый E2E «shows checkout-redirecting, never checkout-empty-cart, while navigating to success». `page.route` держит клиентскую навигацию на `/checkout/success/`, `MutationObserver` фиксирует каждое появление блоков состояния; в итоге `{ redirecting: true, emptyCart: false }`.
- [x] [Review][Patch] Исправить ложноположительную параметризацию AC7 в `page.test.tsx`: для сценариев `empty`, `error` и `form` `waitFor` может сразу увидеть один `returns-support-notice` из первоначального `checkout-loading`, не дождавшись целевой ветки. Сначала ждать testid конкретного состояния или появления формы, затем считать блоки. [`frontend/src/app/(blue)/checkout/__tests__/page.test.tsx:277-325`]
  — **Закрыто:** у сценария появился testid целевого состояния (`order-summary` для формы). Блоки считаются после `findByTestId`, блок обязан лежать внутри целевого. Добавлен сценарий `redirecting`.
- [x] [Review][Patch] Закрепить все контракты AC5 в интеграционном тесте страницы: после перехода в `form` проверить `checkout-submit-button`, ссылку `/privacy-policy` и расположение единственного `returns-support-notice` внутри `order-summary`. Сейчас проверяются только секции, автозаполнение и товар, поэтому обязательная информация формы может исчезнуть при зелёных тестах. [`frontend/src/app/(blue)/checkout/__tests__/page.test.tsx:218-232`; AC5]
  — **Закрыто:** отдельный кейс AC5 проверяет внутри `order-summary` кнопку, ссылку на `/privacy-policy` и блок возврата, а на странице — ровно один блок и наличие `<form>`.
- [x] [Review][Patch] Добавить отдельную axe-проверку обновлённого `CartSkeleton`: AC8 перечисляет его явно, но accessibility-suite проверяет обновлённые `EmptyCart` и `CartError`, а `CartSkeleton` напрямую не рендерит. [`frontend/src/components/cart/__tests__/accessibility.test.tsx`; AC8]
  — **Закрыто:** `describe('CartSkeleton')` — `axe` без нарушений, `main` «Загрузка корзины» с `aria-busy`, регион «Условия возврата и поддержка» доступен.
- [x] [Review][Patch] Довести проверку серверного HTML до буквального AC2: Debug Log подтверждает только отсутствие `name="email"`, тогда как критерий перечисляет `email`, `phone`, `city` и `comment`. Проверить все четыре имени одним скриптом или четырьмя утверждениями; иначе частично отрендеренная форма ошибочно пройдёт приёмку. [Debug Log References; AC2]
  — **Закрыто:** `curl` по `:3000` и `:80` считает все четыре имени и `<input>`, везде 0 (Debug Log). Юнит `renderToString` проверяет те же четыре имени.
- [x] [Review][Patch] Расширить таблицу `resolveCheckoutView`: тест с формулировкой «при любых остальных значениях» использует только две выборки и не закрепляет все конкурирующие пары `pending/error/redirecting/hasItems`. Добавить матрицу приоритетов; иначе перестановка условий может пройти тесты. [`frontend/src/utils/checkout/__tests__/checkoutView.test.ts:15-63`]
  — **Закрыто:** все 48 комбинаций входа разложены по шести слоям приоритета (24/12/4/4/2/2). Мутационная проверка: перестановка проверок `error` и `redirecting` роняет слой `error`.
- [x] [Review][Patch] Добавить интеграционную проверку «ровно один `returns-support-notice`» для `/cart` с товарами. Новые тесты `CartPage` считают блок только в `empty`, `loading` и `error`, поэтому возможное дублирование в основной ветке не обнаружится. [`frontend/src/components/cart/__tests__/CartPage.test.tsx:296-327`; AC7]
  — **Закрыто:** кейс «exactly one block, inside cart-summary, when cart has items». Сначала ждёт `cart-summary`, потом считает.

#### Метаданные и воспроизводимость changeset

- [x] [Review][Patch] Согласовать Task 1 с фактической историей ветки: story требует создать ветку от `develop` и сверить HEAD с `501535a7`, но непосредственный родитель `f47b5f83` — `62319ddc`. Указать реальный branch point либо отдельно определить `merge base` и `code baseline`; текущая последовательность невоспроизводима. [frontmatter; Task 1]
  — **Закрыто:** реальная точка ветвления — `62319ddc`: локальный `develop`, reflog ветки — `Created from HEAD`. Она записана в frontmatter и Debug Log. «Code baseline» `501535a7` и branch point `62319ddc` по `frontend/`/`backend/` совпадают: `git diff 501535a7 62319ddc -- frontend backend` пуст. Текст Task 1 — спецификация, dev-story его не правит.
- [x] [Review][Patch] Исправить каноническую область приёмки и File List: объявленный диапазон `501535a7..f47b5f83` при пустом `excluded_commits` содержит 24 файла, включая родительские изменения эпика, SCP, tech-debt и предыдущих stories; коммит `f47b5f83` содержит 18 файлов, а File List перечисляет только 17 и пропускает сам story-файл. Использовать `baseline_commit: 62319ddc` либо формально исключить `62319ddc`, затем добавить story-файл в File List. [frontmatter; File List]
  — **Закрыто:** `baseline_commit: 62319ddc`, `git diff --stat 62319ddc f47b5f83` = 18 файлов. Story-файл добавлен в File List.
- [x] [Review][Patch] Сделать `review_head` воспроизводимым из чистого checkout: значение `f47b5f83` и закрытие Task 10 существуют только в незакоммиченной правке story-файла и отсутствуют в самом коммите `f47b5f83`. Сохранить метаданные отдельным документационным коммитом, исключённым из содержательного changeset, либо использовать внешний review manifest. [frontmatter; Task 10; Completion Notes]
  — **Закрыто моделью 41.9:** `review_head` — HEAD, на котором выполнено ревью. Метаданные и доработка по ревью войдут в следующий коммит поверх `f47b5f83`, то есть за пределы просмотренного diff `62319ddc..f47b5f83` по построению, и `excluded_commits` для этого не нужен. Из чистого checkout метаданные воспроизводятся, как только этот коммит создан. Коммит — за владельцем.

#### Необработанные граничные пути

- [x] [Review][Patch][Edge Case] Сделать `onRetry` обязательным для `view: 'error'`: текущий `CheckoutStateViewProps` допускает отсутствующий callback, но ветка ошибки всегда показывает активную кнопку «Повторить». Использовать discriminated union для error и остальных состояний; иначе кнопка может ничего не делать. [`frontend/src/components/checkout/CheckoutStateView.tsx:16-20,100-107`]
  — **Закрыто:** `CheckoutStateViewProps` — discriminated union, у `error` `onRetry` обязателен. Страж — `@ts-expect-error` в `CheckoutStateView.test.tsx`. Мутация «`onRetry?` у error» роняет `tsc` с `TS2578: Unused '@ts-expect-error'`.
- [x] [Review][Decision][Edge Case] Определить поведение при незавершающемся `fetchCart`: сейчас checkout остаётся в `loading` бессрочно. Добавить timeout/recovery либо явно принять бессрочное ожидание в AC и документации. [`frontend/src/app/(blue)/checkout/CheckoutPageClient.tsx:42-48`]
  — **Решение Alex 2026-09-11: принять, код не менять.** Бессрочного ожидания нет: `fetchCart` → `cartService.get` → `apiClient` с `timeout: API_TIMEOUT` (`NEXT_PUBLIC_API_TIMEOUT`, по умолчанию 30 000 мс, `services/api-client.ts:29,34`). По таймауту ошибка попадает в `cartStore.error`, гейт показывает `checkout-cart-error` с «Повторить». Закреплено тестом «запрос корзины, упавший по таймауту apiClient, переводит loading → error».
- [x] [Review][Decision][Edge Case] Определить состояние `isAuthenticated === true`, `user === null`: после загрузки корзины текущий гейт может открыть форму без автозаполнения. Либо включить наличие `user` в условие готовности формы, либо документировать это как допустимый режим неполностью восстановленной сессии. [`frontend/src/app/(blue)/checkout/CheckoutPageClient.tsx:27-31,58-81`]
  — **Решение Alex 2026-09-11: допустимый режим, гейт не менять.** Состояние возникает, когда `AuthProvider` исчерпал ретраи `/users/profile/` по сетевой ошибке и сохранил токены (`AuthProvider.tsx:149-154`). Заказ создаётся по токену, контакты покупатель вводит сам. Требовать `user` означало бы новое состояние и повтор профиля, то есть правку `AuthProvider`, а её запрещает AC11. Закреплено тестом «авторизован без загруженного профиля (user=null): рабочая форма без автозаполнения».

#### Редакторская структура

По решению Alex 2026-09-11 применяются только пункты о разделах, которые dev-story вправе менять (Dev Agent Record, Change Log). Остальные закрыты без правки: спецификацию (врезки, Tasks, Dev Notes) dev-story не редактирует.

- [x] [Review][Editorial][Structure] **CONDENSE** `Tasks / Subtasks` (1761 слово) в матрицу `Task → файлы → доказательство`: раздел повторяет значительную часть AC, Dev Notes и Debug Log. Ожидаемое сокращение — около 800–1000 слов без потери требований.
  — **Отклонено:** вне области dev-story, текст задач — спецификация.
- [x] [Review][Editorial][Structure] **CONDENSE** `Debug Log References` (417 слов) в таблицу `Проверка | Команда | Результат | Ограничение`. Ожидаемое сокращение — около 120–160 слов при более быстрой сверке доказательств.
  — **Применено:** Debug Log сведён в таблицу с этими колонками.
- [x] [Review][Editorial][Structure] **MERGE** `Completion Notes List` и `Change Log`: оставить один итог реализации и короткую хронологию статусов. Сейчас итог реализации повторяется; ожидаемое сокращение — около 80–110 слов.
  — **Применено:** итог реализации — только в Completion Notes, Change Log — короткая хронология.
- [x] [Review][Editorial][Structure] **MOVE** раздел `Выкат (для владельца, вне объёма dev-story)` в существующий production runbook, а в story оставить только специфические post-deploy checks. Сам раздел явно находится вне объёма story; ожидаемое сокращение — около 60–80 слов.
  — **Отклонено:** вне области dev-story (Dev Notes).
- [x] [Review][Editorial][Structure] **PRESERVE** критические врезки перед `Story`, но объединить их под заголовком «Риски реализации». Их объём оправдан: они предотвращают повторение SSR-, auth- и E2E-регрессий.
  — **Отклонено:** вне области dev-story (врезки спецификации). Сами врезки сохранены.

#### Редакторская проза

Все четыре пункта относятся к тексту спецификации (Tasks, врезки) и закрыты без правки по тому же решению Alex 2026-09-11.

- [x] [Review][Editorial][Prose] Заменить `fetchCart ошибок не бросает` на `fetchCart не выбрасывает исключения`: исправить грамматику и терминологию. [Task 4] — **Отклонено:** вне области dev-story.
- [x] [Review][Editorial][Prose] Заменить `блок приезжает вместе с компонентами` на `блок рендерится внутри компонентов состояний`: убрать разговорную и неоднозначную формулировку. [Task 5] — **Отклонено:** вне области dev-story.
- [x] [Review][Editorial][Prose] Заменить `GET к API корзины не отправлялся` на `GET-запрос к API корзины не отправлялся`: исправить управление. [Task 7] — **Отклонено:** вне области dev-story.
- [x] [Review][Editorial][Prose] Заменить `Серверный HTML /checkout полей формы не содержит УЖЕ СЕЙЧАС — и это ничего не доказывает` на `Текущее отсутствие полей формы в серверном HTML /checkout само по себе не подтверждает выполнение AC2`: убрать прописные буквы и точнее выразить ограничение доказательства. [врезка перед Story] — **Отклонено:** вне области dev-story.

При принятии всех структурных рекомендаций оценочное сокращение документа — 1100–1350 слов, или 19–24% от текущих 5648 слов, без удаления требований и проверочных свидетельств.

#### Повторное ревью R2 (диапазон `f47b5f83...dccc638a`, 2026-09-11)

- [x] [Review][Defer] Автогенерированные счётчики GitNexus попали в changeset вне File List [`AGENTS.md:164`, `CLAUDE.md:168`] — deferred: runtime не затронут, но изменения создают шум и потенциальные конфликты при следующей реиндексации; исправление касается agent-context файлов и вынесено в deferred-work.
- [x] [Review][Defer] Изолированный axe-тест `CartSkeleton` не воспроизводит вложенный `<main>` реальной страницы [`frontend/src/components/cart/__tests__/accessibility.test.tsx:338-356`] — deferred: проблема предсуществует R2 и всей стори (`LayoutWrapper` уже создаёт внешний `<main>`, cart-состояния — внутренний); требуется отдельное согласованное исправление landmark-разметки всех состояний корзины.

**Rejected:**

- `Debug Log` использует 7-символьный `f47b5f8`, а frontmatter — 8-символьный `f47b5f83`: оба однозначно указывают на один коммит; косметическая правка story не требуется.
- Тест таймаута вручную завершает Promise и записывает `cart.error`: он проверяет реакцию гейта на контракт `fetchCart`, а не реализацию таймера axios; гарантия таймаута находится в `apiClient`, поэтому заявленный ложноположительный исход не возникает.
- `container.querySelector('form')` намеренно проверяет отсутствие/наличие любого `<form>` по AC; добавление `data-testid` в `CheckoutForm` нарушило бы AC11 и сузило бы проверку.
- Исключение ветки `form` из проверки «h1 → h2 блока состояния» корректно: AC8 перечисляет пять конкретных блоков состояния и не относит форму к ним; контракты формы проверяются отдельно по AC5.
- `window.__checkoutSeen` используется только при контролируемой клиентской навигации App Router; прямые assertions до освобождения маршрута уже подтверждают `redirecting` и отсутствие `empty` в проверяемом сценарии. Гипотетическая hard reload потребовала бы изменения самого маршрута/теста.
- Отсутствие `try/finally` вокруг `releaseNavigation()` не оставляет приложение зависшим: при падении Playwright закрывает page/context и отменяет перехваченный запрос; отдельный cleanup не устраняет продуктовый дефект.
- Визуально спокойный стиль h2 у loading/redirecting соответствует требованию сохранить прежний вид текста; семантический уровень заголовка и доступное имя проверены.
- Дублирование точных ожидаемых текстов в `HEADING_BY_VIEW` является контрактной проверкой дословных строк AC, а не источником runtime-рассинхронизации.
- Матрица `PRIORITY_LAYERS` дополнена независимыми ручными тестами каждого перехода и конкурирующих состояний в нижнем `describe`; утверждение об отсутствии независимых edge-case тестов опровергнуто.

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5), через /bmad-dev-story. Доработка по ревью — Claude Opus 5 (claude-opus-5), через /bmad-dev-story.

### Debug Log References

Все команды — из `frontend/`, кроме `git`, `docker` и `gitnexus` (корень репозитория). «Р1» — первый раунд реализации (`f47b5f83`), «Р2» — доработка по ревью.

| Проверка | Команда | Результат | Ограничение |
|---|---|---|---|
| Точка ветвления | `git reflog show feature/story-41-10-checkout-for-anonymous`; `git diff --stat 501535a7 62319ddc -- frontend backend` | Ветка создана от локального `develop` на `62319ddc`. Код в `501535a7..62319ddc` не менялся, `62319ddc..f47b5f83` — 18 файлов | `62319ddc` в `origin/develop` не было, он лежал на `origin/feature/epic-41-sprint-change-proposal` |
| Затрагиваемые наборы Vitest | `npm run test -- --run "src/app/(blue)/checkout" src/components/checkout src/components/cart src/utils/checkout` | До правок: 20 файлов, 357 passed, 4 skipped. Р1: checkout — 9 файлов, 154 passed, 1 skipped; cart — 10 файлов, 208 passed, 3 skipped. Р2: 22 файла, 423 passed, 4 skipped | — |
| Полный Vitest | `npm run test -- --run` | Р1: 171 файл, 2861 passed, 16 skipped. Р2: 171 файл, 2889 passed, 16 skipped (+28) | — |
| Регресс перед review после R2 (2026-09-12) | `npm run test -- --run`; `npm run lint`; `npm run format:check`; `npx tsc --noEmit`; `$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'; npx playwright test --workers=1`, затем `npx playwright test tests/e2e/checkout.spec.ts` без `--workers`; `curl -s` по `:3000/checkout` и `:80/checkout` | На `dccc638a`, frontend в рабочем дереве не менялся. Vitest: 171 файл, 2889 passed, 16 skipped — совпадает с Р2. Lint, формат, типы — чисто. Полный E2E: 41 passed (2,1 мин). Checkout E2E на 8 воркерах: 19 passed. Серверный HTML: на обоих входах 200, `name="email"`, `name="phone"`, `name="city"`, `name="comment"` и `<input` — все 0 | Свежий стенд после `up` сначала отдавал 502 на `:80` (`connect() failed (111)` к `172.18.0.4:3000`); `restart nginx` вылечил. Ветка не запушена, CI-прогона нет |
| Lint, формат, типы | `npm run lint`; `npm run format:check`; `npx tsc --noEmit` | Чисто в обоих раундах | В Р1 — после `prettier --write` на `CheckoutStateView.tsx` и `checkoutView.ts` |
| Мутационные проверки (Р2) | Временно переставлены проверки `error`/`redirecting` в `checkoutView.ts`; временно `onRetry?` у варианта `error` | Матрица роняет слой `error`; `tsc` — `TS2578: Unused '@ts-expect-error'`. Оба файла восстановлены | — |
| E2E checkout | `$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'; npx playwright test tests/e2e/checkout.spec.ts`, с `--workers=1` (как в CI) и без | Р1: 18 passed. Р2: 19 passed в обоих режимах, новый AC6-тест 3 из 3 при `--repeat-each=3` | Стенд после `restart frontend` + `restart nginx`. В Р1 два теста формы доработаны под авторизованного: очистка автозаполненных контактов; телефон — `focus()` + `fill('')` + `pressSequentially()`, голый `fill()` не перезаписывает валидное маскированное значение |
| Полный E2E | `npx playwright test --workers=1` | Р1: 40 passed. Р2: 41 passed | — |
| Серверный HTML (AC2) | `curl -s` по `http://localhost:3000/checkout` и `http://localhost/checkout`; счёт `name="email"`, `name="phone"`, `name="city"`, `name="comment"` и `<input` | Р2: все пять счётчиков — 0 на обоих входах (ответ 72 835 байт). Р1 проверял только `email` | Прод — после выката, за владельцем |
| Ручная приёмка NFR-41-08 (AC10), Р1 | Временный `tests/e2e/tmp-story-41-10-check.spec.ts`: чистый контекст, реальный бэкенд, временный пользователь `story-41-10-tmp@example.test` | 5 сценариев зелёные: аноним на `/checkout` (AC1, AC7), аноним на пустом `/cart` (AC7), гостевая корзина → всё равно приглашение (AC1), вход через `/login?next=%2Fcheckout`, авторизованный с товарами (AC5). Спек и пользователь удалены | Браузерных MCP-инструментов не было. AC6 на реальном бэкенде не прогнан: локально нет способов доставки (`GET /delivery/methods/` → `[]`), покрыт юнитом и E2E. В Р2 блоки анонима и корзины не менялись, приёмка не повторялась |
| GitNexus impact | `npx gitnexus impact <symbol> --direction upstream --repo "C:\Users\1\DEV\FREESPORT"` | Р1: всё LOW по анализу из шапки стори (индекс `a73c3bb`, `git diff a73c3bb..62319ddc -- frontend backend` пуст). Р2 (свежий индекс `f47b5f8`): `CheckoutStateView` — LOW, 1 вызывающий (`CheckoutPageClient`), процесс `CheckoutPage`; `renderContent` — LOW | `ReturnsAndSupportNotice` — HIGH, не менялся |
| GitNexus detect-changes | `npx gitnexus detect-changes --scope all --repo "C:\Users\1\DEV\FREESPORT"` | Р1: 13 файлов, 11 символов, medium (`CheckoutPageClient`, `EmptyCart`, `CartError`, `CartSkeleton`). Р2: 11 файлов, 4 символа, low — только `CheckoutStateView.tsx`. `ReturnsAndSupportNotice`, `OrderSummary`, `CheckoutForm` не задеты (AC11) | `AGENTS.md` и `CLAUDE.md` в дереве Р2 — регенерация счётчиков GitNexus владельцем, к стори не относятся |

### Completion Notes List

- Реализован гейт состояний `/checkout` (`loading` → `anonymous` → `error` → `redirecting` → `empty` → `form`) через чистую функцию `resolveCheckoutView` и компонент `CheckoutStateView`; `CheckoutPageClient` больше не запрашивает корзину для анонима и не монтирует `CheckoutForm` вне состояния `form`.
- `CheckoutPageClient` вызывает `clearOrder()` при монтировании (AC6) и использует локальный `cartLoad` (`useState('pending')`), а не `cartStore.isLoading`, чтобы первый рендер и серверный HTML всегда были индикатором загрузки (AC2), закрывая `deferred-work.md:935`.
- В `EmptyCart`, `CartError`, `CartSkeleton` добавлен `ReturnsAndSupportNotice` (сам компонент не менялся — HIGH blast radius, только новые места вызова), `/cart` теперь показывает условия возврата в любом состоянии (AC7).
- `page.test.tsx` переписан полностью под новые состояния (AC1–AC7, включая `renderToString`-проверку AC2); E2E `checkout.spec.ts` переведён на авторизованный `authenticate()`-хелпер для сценариев с формой и получил новый анонимный сценарий (AC1).
- Ни `ReturnsAndSupportNotice`, ни `OrderSummary`, ни `CheckoutForm`, ни бэкенд не менялись (AC11) — подтверждено `gitnexus detect-changes` и точечным просмотром diff.
- ✅ Ревью 2026-09-11 закрыто полностью, 24 из 24. Исправлено 13: 10 по коду и тестам, 3 по метаданным. 2 decision приняты владельцем. Из 9 редакторских 2 применены, 7 отклонены как вне области dev-story. Резолюции — у каждого пункта в Review Findings.
- По коду ревью изменило одно: в `CheckoutStateView` видимый текст индикаторов `loading` и `redirecting` стал `<h2>` (AC8, иерархия h1 → h2 в каждом состоянии), а `CheckoutStateViewProps` стал discriminated union с обязательным `onRetry` у `error`. `CheckoutPageClient` и гейт не менялись.
- Остальное по ревью — тесты. В `resolveCheckoutView` — матрица на все 48 комбинаций. В `page.test.tsx` — полный переход повтора `error → loading → итог`, таймаут `apiClient` → `error`, контракты формы из AC5, режим `user=null`; AC7 теперь ждёт целевое состояние. Добавлены axe для `CartSkeleton`, «ровно один блок» на `/cart` с товарами и E2E промежуточного кадра `checkout-redirecting`.
- Решения по граничным путям (Alex, 2026-09-11). Бессрочной загрузки нет: `fetchCart` ограничен таймаутом `apiClient` (30 с), затем состояние `error` с повтором. «Авторизован без профиля» (`user=null` после сетевых сбоев `AuthProvider`) — допустимый режим: форма рабочая, без автозаполнения.
- Changeset приёмки — `baseline_commit: 62319ddc` (реальная точка ветвления), `review_head: f47b5f83`. Доработку по ревью владелец закоммитил в `dccc638a` поверх `review_head`.
- Повторное ревью R2 (`f47b5f83...dccc638a`) правок кода не потребовало. 2 пункта отложены в `deferred-work.md`: счётчики GitNexus в `AGENTS.md`/`CLAUDE.md` и вложенный `<main>` в состояниях корзины, он был и до стори. 9 пунктов отклонены с обоснованием. Регресс перед review 2026-09-12 зелёный (Debug Log). Записи R2 в story, `deferred-work.md` и `sprint-status.yaml` пока не закоммичены. `AGENTS.md` и `CLAUDE.md` в рабочем дереве — снова регенерация счётчиков GitNexus: к стори не относятся, в File List не входят.

### File List

**Новые файлы:**
- `frontend/src/utils/checkout/checkoutView.ts`
- `frontend/src/utils/checkout/__tests__/checkoutView.test.ts`
- `frontend/src/components/checkout/CheckoutStateView.tsx`
- `frontend/src/components/checkout/__tests__/CheckoutStateView.test.tsx`

**Изменённые файлы:**
- `frontend/src/app/(blue)/checkout/CheckoutPageClient.tsx`
- `frontend/src/app/(blue)/checkout/__tests__/page.test.tsx`
- `frontend/src/components/cart/EmptyCart.tsx`
- `frontend/src/components/cart/CartError.tsx`
- `frontend/src/components/cart/CartSkeleton.tsx`
- `frontend/src/components/cart/__tests__/EmptyCart.test.tsx`
- `frontend/src/components/cart/__tests__/CartError.test.tsx`
- `frontend/src/components/cart/__tests__/CartSkeleton.test.tsx`
- `frontend/src/components/cart/__tests__/CartPage.test.tsx`
- `frontend/src/components/cart/__tests__/accessibility.test.tsx`
- `frontend/tests/e2e/checkout.spec.ts`
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/Story/41-10-checkout-and-cart-for-anonymous.md`

Доработка по ревью меняет только файлы из этого списка: `CheckoutStateView.tsx` и его тест, `checkoutView.test.ts`, `page.test.tsx`, `CartPage.test.tsx`, `accessibility.test.tsx`, `checkout.spec.ts`, `sprint-status.yaml` и story-файл.

## Change Log

| Дата | Изменение |
|---|---|
| 2026-09-12 | PR #158 смёржен в `develop` (`27ffdbd5`) после #157, статус review → done. Отложенная находка R2 про вложенный `<main>` исправлена в `fix/blue-nested-main-landmark`. |
| 2026-09-12 | Регресс после R2 зелёный, статус in-progress → review. |
| 2026-09-11 | Повторное ревью R2 (`f47b5f83...dccc638a`): 2 defer, 9 rejected, правок кода нет. Статус review → in-progress. |
| 2026-09-11 | Доработка по ревью: закрыто 24 из 24 находок, резолюции — в Review Findings. `baseline_commit` 501535a7 → 62319ddc. Статус in-progress → review. |
| 2026-09-11 | Ревью: 24 находки записаны в Review Findings. |
| 2026-09-11 | Владелец закоммитил реализацию `f47b5f83`; `review_head` = `f47b5f83`. |
| 2026-09-11 | Реализация (dev-story), статус → review. |
| 2026-09-11 | Решения Alex по create-story: адрес входа `/login?next=%2Fcheckout`; open redirect `LoginForm` передан в 41.12; блок условий возврата в корзине — всегда; перенос гостевой корзины — в `deferred-work.md`. |
| 2026-09-11 | Стори создана (create-story), ready-for-dev. |
