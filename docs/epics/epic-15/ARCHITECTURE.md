# Эпик 15: Checkout - Архитектурная диаграмма

**Версия:** 1.0.0
**Дата:** 2025-12-14

---

## Архитектура компонентов

```mermaid
graph TB
    subgraph "User Interface"
        CheckoutPage["/checkout page.tsx"]
        CheckoutForm["CheckoutForm.tsx"]
        ContactSection["ContactSection.tsx"]
        AddressSection["AddressSection.tsx"]
        DeliveryOptions["DeliveryOptions.tsx"]
        PaymentMethods["PaymentMethods.tsx"]
        OrderSummary["OrderSummary.tsx"]
        SuccessPage["/checkout/success/[orderId] page.tsx"]
    end

    subgraph "State Management (Zustand)"
        OrderStore["orderStore.ts"]
        CartStore["cartStore (Эпик 14)"]
        AuthStore["authStore (Эпик 13)"]
    end

    subgraph "Services Layer"
        OrdersService["ordersService.ts"]
        DeliveryService["deliveryService.ts"]
        PaymentService["paymentService.ts"]
        APIClient["api-client.ts"]
    end

    subgraph "Validation"
        CheckoutSchema["checkoutSchema.ts (Zod)"]
        ReactHookForm["React Hook Form 7.62.0"]
    end

    subgraph "Backend API"
        OrdersAPI["/orders/create<br/>/orders/confirm"]
        DeliveryAPI["/delivery/calculate"]
        PaymentAPI["/payment/methods"]
        CartAPI["/cart/"]
        ProfileAPI["/profile/addresses"]
    end

    subgraph "External Services"
        CDEK["CDEK API"]
        Boxberry["Boxberry API"]
        YuKassa["YuKassa Payment Gateway"]
    end

    CheckoutPage --> CheckoutForm
    CheckoutForm --> ContactSection
    CheckoutForm --> AddressSection
    CheckoutForm --> DeliveryOptions
    CheckoutForm --> PaymentMethods
    CheckoutForm --> OrderSummary

    CheckoutForm --> ReactHookForm
    ReactHookForm --> CheckoutSchema

    CheckoutForm --> OrderStore
    CheckoutForm --> CartStore
    CheckoutForm --> AuthStore

    OrderStore --> OrdersService
    DeliveryOptions --> DeliveryService
    PaymentMethods --> PaymentService

    OrdersService --> APIClient
    DeliveryService --> APIClient
    PaymentService --> APIClient

    APIClient --> OrdersAPI
    APIClient --> DeliveryAPI
    APIClient --> PaymentAPI
    APIClient --> CartAPI
    APIClient --> ProfileAPI

    DeliveryAPI --> CDEK
    DeliveryAPI --> Boxberry
    PaymentAPI --> YuKassa

    OrderStore --> SuccessPage

    style CheckoutPage fill:#0060FF,stroke:#0047CC,color:#fff
    style CheckoutForm fill:#00B7FF,stroke:#0095D6,color:#fff
    style OrderStore fill:#00AA5B,stroke:#008A47,color:#fff
    style OrdersService fill:#F5A623,stroke:#D68A1F,color:#fff
    style APIClient fill:#E53935,stroke:#C62828,color:#fff
```

---

## Data Flow диаграмма

```mermaid
sequenceDiagram
    actor User
    participant CheckoutForm
    participant ReactHookForm
    participant OrderStore
    participant OrdersService
    participant APIClient
    participant Backend
    participant ExternalAPI
    participant CartStore
    participant SuccessPage

    User->>CheckoutForm: Заполняет форму
    CheckoutForm->>ReactHookForm: Валидация (Zod schema)
    ReactHookForm-->>CheckoutForm: Валидация OK

    User->>CheckoutForm: Выбирает адрес доставки
    CheckoutForm->>OrdersService: calculateDelivery(address)
    OrdersService->>APIClient: POST /delivery/calculate
    APIClient->>Backend: Request
    Backend->>ExternalAPI: CDEK/Boxberry API
    ExternalAPI-->>Backend: Стоимость доставки
    Backend-->>APIClient: Response
    APIClient-->>OrdersService: Delivery options
    OrdersService-->>CheckoutForm: Обновить стоимость

    User->>CheckoutForm: Нажимает "Оформить заказ"
    CheckoutForm->>OrderStore: createOrder(formData)
    OrderStore->>OrdersService: create(orderData)
    OrdersService->>APIClient: POST /orders/create
    APIClient->>Backend: Create order request
    Backend-->>APIClient: orderId, status
    APIClient-->>OrdersService: Order created
    OrdersService-->>OrderStore: Success

    OrderStore->>CartStore: clearCart()
    CartStore-->>OrderStore: Cart cleared

    OrderStore-->>CheckoutForm: Redirect to success
    CheckoutForm->>SuccessPage: Navigate(/checkout/success/orderId)
    SuccessPage->>Backend: GET /orders/{orderId}
    Backend-->>SuccessPage: Order details
    SuccessPage-->>User: Показать детали заказа
```

---

## Интеграционная карта

```mermaid
graph LR
    subgraph "Эпик 15: Checkout"
        Checkout[Checkout Flow]
    end

    subgraph "Эпик 10: Фундамент"
        UIKit[UI Kit Components]
        APIClient2[API Client]
        Zustand[Zustand Setup]
    end

    subgraph "Эпик 13: Аутентификация"
        AuthStore2[authStore]
        JWTTokens[JWT Tokens]
        ProtectedRoutes[Protected Routes]
    end

    subgraph "Эпик 14: Корзина"
        CartStore2[cartStore]
        CartItems[Cart Items]
        Promo[Promo Codes]
    end

    subgraph "Backend API"
        OrdersEndpoint[Orders API]
        DeliveryEndpoint[Delivery API]
        PaymentEndpoint[Payment API]
    end

    Checkout --> UIKit
    Checkout --> APIClient2
    Checkout --> Zustand

    Checkout --> AuthStore2
    Checkout --> JWTTokens
    Checkout --> ProtectedRoutes

    Checkout --> CartStore2
    Checkout --> CartItems
    Checkout --> Promo

    Checkout --> OrdersEndpoint
    Checkout --> DeliveryEndpoint
    Checkout --> PaymentEndpoint

    style Checkout fill:#0060FF,stroke:#0047CC,color:#fff
    style UIKit fill:#00B7FF,stroke:#0095D6,color:#fff
    style AuthStore2 fill:#00AA5B,stroke:#008A47,color:#fff
    style CartStore2 fill:#F5A623,stroke:#D68A1F,color:#fff
    style OrdersEndpoint fill:#E53935,stroke:#C62828,color:#fff
```

---

## Component Hierarchy

```
CheckoutPage (page.tsx)
└── CheckoutForm
    ├── ContactSection
    │   ├── Input (firstName, lastName)
    │   ├── Input (email, phone)
    │   └── ValidationMessages
    │
    ├── AddressSection
    │   ├── Select (saved addresses)
    │   ├── Input (street, city, zip)
    │   └── Button (save new address)
    │
    ├── DeliveryOptions
    │   ├── RadioGroup
    │   │   ├── CourierOption
    │   │   ├── PickupOption
    │   │   └── PostOption
    │   ├── DeliveryCostCalculator
    │   └── DeliveryTimeEstimate
    │
    ├── PaymentMethods
    │   ├── RadioGroup
    │   │   ├── CardOption (YuKassa)
    │   │   ├── CashOption
    │   │   └── B2BInvoiceOption (только для B2B)
    │   └── PaymentMethodsLoader
    │
    ├── OrderSummary
    │   ├── CartItemsList (из cartStore)
    │   ├── PromoCodeInput
    │   ├── DeliveryPriceDisplay
    │   └── TotalPriceDisplay
    │
    └── SubmitButton
        ├── LoadingSpinner
        └── SuccessRedirect
```

---

## State Management Flow

```mermaid
stateDiagram-v2
    [*] --> Idle: Страница загружена

    Idle --> FillingForm: Пользователь заполняет форму
    FillingForm --> ValidatingForm: Ввод данных
    ValidatingForm --> FillingForm: Есть ошибки
    ValidatingForm --> CalculatingDelivery: Выбран адрес

    CalculatingDelivery --> FillingForm: Стоимость рассчитана
    CalculatingDelivery --> Error: API ошибка

    FillingForm --> SubmittingOrder: Нажата кнопка "Оформить"

    SubmittingOrder --> CreatingOrder: Отправка API запроса
    CreatingOrder --> OrderCreated: Заказ создан
    CreatingOrder --> Error: API ошибка

    OrderCreated --> ClearingCart: Очистка корзины
    ClearingCart --> RedirectingToSuccess: Корзина очищена

    RedirectingToSuccess --> [*]: Показать success страницу

    Error --> FillingForm: Повторить попытку
    Error --> [*]: Критическая ошибка
```

---

## File Structure Tree

```
src/
├── app/
│   └── checkout/
│       ├── page.tsx                           # Главная checkout страница (Story 15.1)
│       ├── layout.tsx                         # Layout с защитой (требует auth)
│       ├── success/
│       │   └── [orderId]/
│       │       └── page.tsx                   # Success страница (Story 15.5)
│       └── __tests__/
│           ├── page.test.tsx                  # Unit-тесты checkout page
│           └── success.test.tsx               # Unit-тесты success page
│
├── components/
│   └── checkout/
│       ├── CheckoutForm.tsx                   # Главная форма (Story 15.1)
│       ├── ContactSection.tsx                 # Контактные данные
│       ├── AddressSection.tsx                 # Адрес доставки
│       ├── DeliveryOptions.tsx                # Способы доставки (Story 15.3)
│       ├── PaymentMethods.tsx                 # Способы оплаты (Story 15.4)
│       ├── OrderSummary.tsx                   # Итоговая сумма
│       └── __tests__/
│           ├── CheckoutForm.test.tsx
│           ├── ContactSection.test.tsx
│           ├── AddressSection.test.tsx
│           ├── DeliveryOptions.test.tsx
│           ├── PaymentMethods.test.tsx
│           └── OrderSummary.test.tsx
│
├── services/
│   ├── ordersService.ts                       # API orders (Story 15.2)
│   │   ├── createOrder()
│   │   ├── confirmOrder()
│   │   └── getOrderById()
│   ├── deliveryService.ts                     # API delivery (Story 15.3)
│   │   ├── calculateDelivery()
│   │   └── getDeliveryOptions()
│   ├── paymentService.ts                      # API payment (Story 15.4)
│   │   ├── getPaymentMethods()
│   │   └── initializePayment()
│   └── __tests__/
│       ├── ordersService.test.ts              # MSW моки
│       ├── deliveryService.test.ts
│       └── paymentService.test.ts
│
├── stores/
│   └── orderStore.ts                          # Zustand store (Story 15.2)
│       ├── currentOrder
│       ├── isSubmitting
│       ├── error
│       ├── createOrder()
│       ├── confirmOrder()
│       └── clearOrder()
│
├── schemas/
│   └── checkoutSchema.ts                      # Zod валидация (Story 15.1)
│       ├── contactSchema
│       ├── addressSchema
│       ├── deliverySchema
│       ├── paymentSchema
│       └── checkoutFormSchema
│
├── types/
│   ├── order.ts                               # TypeScript типы
│   │   ├── Order
│   │   ├── OrderItem
│   │   └── OrderStatus
│   ├── delivery.ts
│   │   ├── DeliveryOption
│   │   ├── DeliveryMethod
│   │   └── DeliveryCalculation
│   └── payment.ts
│       ├── PaymentMethod
│       ├── PaymentStatus
│       └── PaymentProvider
│
├── __mocks__/
│   └── handlers/
│       ├── ordersHandlers.ts                  # MSW моки для orders
│       ├── deliveryHandlers.ts                # MSW моки для delivery
│       └── paymentHandlers.ts                 # MSW моки для payment
│
└── tests/
    └── e2e/
        └── checkout.spec.ts                   # Playwright E2E (Story 15.6)
            ├── Add to cart flow
            ├── Checkout form filling
            ├── Order creation
            └── Success page display
```

---

## API Integration Map

| Service | Endpoint | Method | Purpose | Story |
|---------|----------|--------|---------|-------|
| **ordersService** | `/orders/create` | POST | Создание заказа | 15.2 |
| **ordersService** | `/orders/confirm` | POST | Подтверждение заказа | 15.2 |
| **ordersService** | `/orders/{id}` | GET | Получение деталей | 15.5 |
| **deliveryService** | `/delivery/calculate` | POST | Расчёт доставки | 15.3 |
| **deliveryService** | `/delivery/options` | GET | Способы доставки | 15.3 |
| **paymentService** | `/payment/methods` | GET | Способы оплаты | 15.4 |
| **paymentService** | `/payment/initialize` | POST | Инициализация платежа | 15.4 |
| **cartService** | `/cart/` | GET | Получение корзины | 15.1 |
| **profileService** | `/profile/addresses` | GET | Адреса пользователя | 15.1 |

---

## Performance Optimization Strategy

```mermaid
graph TB
    subgraph "Code Splitting"
        LazyLoad["Lazy Load Delivery/Payment Components"]
        DynamicImport["Dynamic Import для тяжёлых библиотек"]
    end

    subgraph "Caching"
        DeliveryCache["Cache delivery options (5 min)"]
        PaymentCache["Cache payment methods (session)"]
        AddressCache["Cache user addresses (10 min)"]
    end

    subgraph "Debouncing"
        DeliveryDebounce["Debounce delivery calculation (500ms)"]
        ValidationDebounce["Debounce form validation (300ms)"]
    end

    subgraph "Bundle Optimization"
        TreeShaking["Tree Shaking unused code"]
        Minification["Minification & Compression"]
        ImageOptimization["Next.js Image optimization"]
    end

    LazyLoad --> Performance[Target: PageSpeed > 70]
    DynamicImport --> Performance
    DeliveryCache --> Performance
    PaymentCache --> Performance
    AddressCache --> Performance
    DeliveryDebounce --> Performance
    ValidationDebounce --> Performance
    TreeShaking --> Performance
    Minification --> Performance
    ImageOptimization --> Performance

    style Performance fill:#00AA5B,stroke:#008A47,color:#fff
```

---

## Security Architecture

```mermaid
graph TB
    subgraph "Client Security"
        HTTPS["HTTPS Only"]
        CSP["Content Security Policy"]
        CSRF["CSRF Tokens"]
        ZodValidation["Zod Input Validation"]
    end

    subgraph "Authentication"
        JWTAuth["JWT в HttpOnly Cookies"]
        RefreshToken["Refresh Token Strategy"]
        RouteGuard["Protected Route Middleware"]
    end

    subgraph "Payment Security"
        PCI["PCI DSS Compliance (YuKassa)"]
        Tokenization["Payment Tokenization"]
        NoCardStorage["No Card Data Storage"]
    end

    subgraph "API Security"
        RateLimit["Rate Limiting"]
        InputSanitization["Input Sanitization"]
        APIValidation["Backend Validation"]
    end

    HTTPS --> Secure[Secure Checkout]
    CSP --> Secure
    CSRF --> Secure
    ZodValidation --> Secure
    JWTAuth --> Secure
    RefreshToken --> Secure
    RouteGuard --> Secure
    PCI --> Secure
    Tokenization --> Secure
    NoCardStorage --> Secure
    RateLimit --> Secure
    InputSanitization --> Secure
    APIValidation --> Secure

    style Secure fill:#E53935,stroke:#C62828,color:#fff
```

---

## Testing Pyramid

```mermaid
graph TB
    subgraph "E2E Tests (Playwright)"
        E2E1["Critical Flow: Cart → Checkout → Success"]
        E2E2["Delivery Calculation"]
        E2E3["Payment Method Selection"]
        E2E4["B2B/B2C Scenarios"]
    end

    subgraph "Integration Tests (MSW)"
        INT1["ordersService API calls"]
        INT2["deliveryService API calls"]
        INT3["paymentService API calls"]
        INT4["Error handling & Retry"]
    end

    subgraph "Unit Tests (Vitest + RTL)"
        UNIT1["CheckoutForm component"]
        UNIT2["Zod validation schemas"]
        UNIT3["orderStore (Zustand)"]
        UNIT4["All sections (Contact, Address, etc.)"]
        UNIT5["Services logic"]
    end

    E2E1 --> Coverage[Target: 80%+ Coverage]
    E2E2 --> Coverage
    E2E3 --> Coverage
    E2E4 --> Coverage
    INT1 --> Coverage
    INT2 --> Coverage
    INT3 --> Coverage
    INT4 --> Coverage
    UNIT1 --> Coverage
    UNIT2 --> Coverage
    UNIT3 --> Coverage
    UNIT4 --> Coverage
    UNIT5 --> Coverage

    style Coverage fill:#00AA5B,stroke:#008A47,color:#fff
```

---

## Monitoring Dashboard

```mermaid
graph LR
    subgraph "Business Metrics"
        Conv1["Конверсия корзина → checkout"]
        Conv2["Конверсия checkout → success"]
        AvgTime["Среднее время оформления"]
        Dropoff["Drop-off по секциям"]
    end

    subgraph "Technical Metrics"
        APILatency["API Response Times"]
        ErrorRate["4xx/5xx Error Rates"]
        ClientErrors["Client-side Errors (Sentry)"]
        Performance["RUM Performance (LCP, FID, CLS)"]
    end

    subgraph "Alerts"
        CriticalAlert["❗ Critical: Order creation errors > 5%"]
        WarningAlert["⚠️ Warning: API latency > 1s"]
        InfoAlert["ℹ️ Info: Drop-off rate > 50%"]
    end

    Conv1 --> Dashboard[Monitoring Dashboard]
    Conv2 --> Dashboard
    AvgTime --> Dashboard
    Dropoff --> Dashboard
    APILatency --> Dashboard
    ErrorRate --> Dashboard
    ClientErrors --> Dashboard
    Performance --> Dashboard

    Dashboard --> CriticalAlert
    Dashboard --> WarningAlert
    Dashboard --> InfoAlert

    style Dashboard fill:#7C3AED,stroke:#6D28D9,color:#fff
```

---

**Автор:** John (PM Agent) 📋
**Дата:** 2025-12-14
**Версия:** 1.0.0
