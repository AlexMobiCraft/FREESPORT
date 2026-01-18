# API Contracts - Backend

## Products API

Base URL: `/api/v1/products/`

### Endpoints

- **GET /products/**
  - Filters: `category`, `brand`, `min_price`, `max_price`, `in_stock`, `search`.
  - Flags: `is_hit`, `is_new`, `is_sale`.
  - Ordering: `price`, `-price`, `name`, `-created_at`.
  - Response: Paginated list of products.

- **GET /products/{slug}/**
  - Detailed product view with all variants.
  - Returns `ApiProductDetailResponse` structure.

- **GET /products/search/**
  - Full-text search.
  - Params: `q={query}`.

- **GET /categories/tree/**
  - Returns hierarchical category tree.

- **GET /brands/**
  - Returns list of active brands.

## Cart API

Base URL: `/api/v1/cart/`

- **GET /**: Get current user's cart.
- **POST /add/**: Add item (variant_id, quantity).
- **POST /update/**: Update item quantity.
- **POST /remove/**: Remove item.
- **POST /clear/**: Empty cart.

## Orders API

Base URL: `/api/v1/orders/`

- **POST /**: Create new order.
- **GET /**: List user orders.
- **GET /{id}/**: Order details.
- **POST /{id}/cancel/**: Cancel order.

## Auth API

Base URL: `/api/v1/auth/`

- **POST /register/**: Register new user.
- **POST /login/**: Obtain JWT pair.
- **POST /refresh/**: Refresh access token.
- **GET /me/**: Current user profile.
