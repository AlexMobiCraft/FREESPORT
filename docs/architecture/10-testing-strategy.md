# 10. Стратегия Тестирования

### Пирамида тестирования

```
                  E2E Tests
                 /        \
            Integration Tests
               /            \
          Frontend Unit  Backend Unit
```

**Testing Philosophy:** Стратегия тестирования FREESPORT основана на классической пирамиде тестирования с упором на быстрые unit-тесты в основании и критически важные E2E тесты на вершине.

### Организация тестов

#### Frontend Tests

```
frontend/
├── __tests__/                     # Jest unit tests
│   ├── components/               # Component tests
│   │   ├── ProductCard.test.tsx
│   │   ├── Cart.test.tsx
│   │   └── UserProfile.test.tsx
│   ├── hooks/                    # Custom hooks tests
│   │   ├── useAuth.test.ts
│   │   ├── useCart.test.ts
│   │   └── useProducts.test.ts
│   ├── services/                 # API service tests
│   │   ├── authService.test.ts
│   │   ├── productService.test.ts
│   │   └── orderService.test.ts
│   └── utils/                    # Utility function tests
│       ├── formatPrice.test.ts
│       ├── validation.test.ts
│       └── api-client.test.ts
├── __mocks__/                    # Mock implementations
│   ├── api-responses/
│   └── localStorage.js
└── jest.config.js                # Jest configuration
```

**Frontend Testing Stack:**
- **Jest**: Unit testing framework
- **React Testing Library**: Component testing
- **MSW (Mock Service Worker)**: API mocking
- **Jest Environment**: jsdom для браузерной среды

#### Backend Tests

```
backend/
├── tests/                        # Django tests
│   ├── unit/                     # Unit tests
│   │   ├── models/              # Model tests
│   │   │   ├── test_user.py
│   │   │   ├── test_product.py
│   │   │   └── test_order.py
│   │   ├── serializers/         # Serializer tests
│   │   │   ├── test_user_serializers.py
│   │   │   └── test_product_serializers.py
│   │   └── services/            # Business logic tests
│   │       ├── test_auth_service.py
│   │       ├── test_cart_service.py
│   │       └── test_order_service.py
│   ├── integration/              # Integration tests
│   │   ├── test_api_endpoints.py
│   │   ├── test_1c_integration.py
│   │   └── test_yukassa_integration.py
│   └── fixtures/                 # Test data fixtures
│       ├── products.json
│       ├── users.json
│       └── orders.json
├── conftest.py                   # pytest configuration
└── pytest.ini                   # pytest settings
```

**Backend Testing Stack:**
- **pytest**: Primary testing framework
- **pytest-django**: Django integration
- **Factory Boy**: Test data generation
- **pytest-mock**: Mocking utilities
- **Django Test Database**: Isolated test database

#### E2E Tests

```
e2e/
├── tests/                        # Playwright E2E tests
│   ├── auth/                     # Authentication flows
│   │   ├── b2b-registration.spec.ts
│   │   ├── b2c-login.spec.ts
│   │   └── password-recovery.spec.ts
│   ├── catalog/                  # Product catalog tests
│   │   ├── product-search.spec.ts
│   │   ├── product-filtering.spec.ts
│   │   └── product-details.spec.ts
│   ├── checkout/                 # Order placement tests
│   │   ├── b2b-checkout.spec.ts
│   │   ├── b2c-checkout.spec.ts
│   │   └── payment-flow.spec.ts
│   └── admin/                    # Admin panel tests
│       ├── order-management.spec.ts
│       └── user-management.spec.ts
├── fixtures/                     # Test data
├── page-objects/                 # Page Object Pattern
│   ├── HomePage.ts
│   ├── ProductPage.ts
│   └── CheckoutPage.ts
├── utils/                        # Test utilities
└── playwright.config.ts          # Playwright configuration
```

**E2E Testing Stack:**
- **Playwright**: Primary E2E framework
- **TypeScript**: Type-safe test scripts
- **Page Object Model**: Maintainable test structure
- **Multiple Browsers**: Chrome, Firefox, Safari testing

### Примеры тестов

#### Frontend Component Test с ценообразованием по ролям

```typescript
// ProductCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ProductCard } from '../ProductCard';
import { CartProvider } from '../../contexts/CartContext';

const mockProduct = {
  id: 1,
  name: 'Test Product',
  retail_price: 1200,
  opt1_price: 1000,
  trainer_price: 950,
  recommended_retail_price: 1300, // RRP для B2B
  max_suggested_retail_price: 1400, // MSRP для B2B
  main_image: '/test-image.jpg',
  stock_quantity: 50
};

describe('ProductCard', () => {
  it('displays retail pricing for B2C users', () => {
    render(
      <CartProvider>
        <ProductCard product={mockProduct} userRole="retail" />
      </CartProvider>
    );

    expect(screen.getByText('1 200 ₽')).toBeInTheDocument();
    expect(screen.queryByText('РРЦ:')).not.toBeInTheDocument(); // RRP не показывается B2C
    expect(screen.queryByText('Макс. цена:')).not.toBeInTheDocument(); // MSRP не показывается B2C
  });

  it('displays wholesale pricing and RRP/MSRP for B2B users', () => {
    render(
      <CartProvider>
        <ProductCard product={mockProduct} userRole="wholesale_level1" showRRP={true} showMSRP={true} />
      </CartProvider>
    );

    // Показывает оптовую цену как основную
    expect(screen.getByText('1 000 ₽')).toBeInTheDocument();
    
    // Показывает RRP и MSRP для B2B пользователей (FR5)
    expect(screen.getByText('РРЦ: 1 300 ₽')).toBeInTheDocument();
    expect(screen.getByText('Макс. цена: 1 400 ₽')).toBeInTheDocument();
  });

  it('displays trainer pricing for trainers', () => {
    render(
      <CartProvider>
        <ProductCard product={mockProduct} userRole="trainer" />
      </CartProvider>
    );

    expect(screen.getByText('950 ₽')).toBeInTheDocument();
    expect(screen.getByText('Цена для тренеров')).toBeInTheDocument();
  });
});
```

#### Backend API Test с тестированием ролевого ценообразования

```python