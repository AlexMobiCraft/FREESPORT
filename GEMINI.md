# Gemini Added Memories

- Communicate in Russian.

# Command Validation Rules

- **CRITICAL**: Before executing any terminal command via `run_command`, verify that the `CommandLine` parameter:
  1. Starts with a valid command name (e.g., `docker`, `npm`, `python`, `git`) using only **Latin characters**
  2. Contains **NO Cyrillic characters** (like `с`, `а`, `о`, `е` which look similar to Latin `c`, `a`, `o`, `e`)
  3. Has **NO leading special characters or whitespace** before the command

# **Project Overview**

This is a full-stack e-commerce platform for selling sporting goods, designed as an API-first solution for both B2B and B2C sales. The project is a monorepo with a Django backend and a Next.js frontend.

## **Project Architecture**

- **API-First + SSR/SSG Approach:** Ensures SEO optimization and high performance. The decoupling of frontend and backend allows for independent development cycles.  
- **Next.js Hybrid Rendering:** Utilizes Static Site Generation (SSG) for static pages, Server-Side Rendering (SSR) for dynamic content, and Incremental Static Regeneration (ISR) for catalogs.  
- **BFF (Backend for Frontend) Layer:** Next.js API Routes act as an intermediary layer to aggregate data and enhance security between the client and the main API.  
- **Monorepo Structure:** Simplifies management of shared components, configurations, and dependencies across the entire platform.

**Technology Stack:**

**Backend:**

- **Framework:** Django 4.2 LTS with Django REST Framework 3.14+  
- **Database:** PostgreSQL 15+ (with table partitioning and JSONB support)  
- **Cache:** Redis 7.0+ (for caching and sessions)  
- **Authentication:** JWT tokens with a refresh strategy  
- **Async Tasks:** Celery with Celery Beat for background jobs and scheduling  
- **API Documentation:** drf-spectacular for OpenAPI 3.1.0 specification

**Frontend:**

- **Framework:** Next.js 15.5.7 with TypeScript 5.0+  
- **UI Library:** React 19.1.0  
- **State Management:** Zustand 4.5.7 (state management)  
- **Styling:** Tailwind CSS 4.0  
- **Form Management:** React Hook Form 7.62.0  
- **Testing:** Vitest 2.1.5 and React Testing Library  16.3.0
- **API Mocking:** MSW 2.12.2

**Infrastructure:**

- **Web Server/Proxy:** Nginx (for reverse proxy, SSL, load balancing)  
- **Containerization:** Docker and Docker Compose  
- **CI/CD:** GitHub Actions

## **Django App Structure**

The project uses a modular Django apps architecture:

- apps/banners/: Управление баннерами Hero-секции с таргетингом по группам пользователей (гости, авторизованные, тренеры, оптовики, федералы).
- apps/users/: Manages users and a role-based system (7 roles: retail, wholesale_level1-3, trainer, federation_rep, admin).  
- apps/products/: Handles the product catalog, brands, and categories with multi-level pricing.  
- apps/orders/: Contains the order system supporting both B2B/B2C processes.  
- apps/cart/: Manages the shopping cart for both authenticated and guest users.  
- apps/common/: Includes shared utilities, components, and auditing tools.

## **Key Data Models**

- **User Model:** Features a role-based system with 7 distinct user roles, each with different pricing tiers. Includes B2B-specific fields like company_name and tax_id.  
- **Product Model:** Supports multi-level pricing corresponding to user roles. Includes informational prices for B2B (RRP, MSRP), uses a JSONB field for dynamic product specifications, integrates with an ERP via onec_id, and has computed properties like is_in_stock.  
- **Order Model:** Designed to handle both B2B and B2C workflows, capturing a snapshot of product data at the time of purchase. It integrates with payment systems and includes order statuses with an audit trail.

## **Building and Running**

### **Docker**

The recommended way to run the project is with Docker Compose.

**Local Development:**

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d
```

**Production:**

```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d
```

**Stop and remove all services:**

```bash
# Local
docker compose --env-file .env -f docker/docker-compose.yml down

# Production  
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml down
```

The following services will be started:

- db: PostgreSQL database  
- redis: Redis cache  
- backend: Django API  
- frontend: Next.js application  
- nginx: Nginx reverse proxy

### **Local Development**

**Backend**

1. Navigate to the backend directory.  
2. Create a virtual environment: python -m venv venv  
3. Activate it: source venv/bin/activate (on Windows, use venv\Scripts\activate)  
4. Install dependencies: pip install -r requirements.txt  
5. Run the development server: python manage.py runserver 8001  
6. Run Celery workers (in separate terminals):  
   celery -A freesport worker --loglevel=info  
   celery -A freesport beat --loglevel=info

**Frontend**

1. Navigate to the frontend directory.  
2. Install dependencies: npm install  
3. Run the development server: npm run dev

## **Project Structure (Frontend)**

- `/news` — Список новостей с пагинацией.
- `/news/[slug]` — Детальная страница новости.
- `services/newsService.ts` — Сервис для работы с News API.

## **Development Conventions**

### **Git Workflow**

- main: Production branch (protected)  
- develop: Main development branch (protected)  
- feature/*: Branches for new features  
- hotfix/*: Branches for critical bug fixes

### **Testing Strategy**

The project follows the classic testing pyramid model, prioritizing fast feedback and reliability.

- **Testing Pyramid:** E2E Tests (Playwright) > Integration Tests (Pytest + APIClient) > Unit Tests (Pytest, Jest).
- **Technology Stack:**
  - **Backend:** `pytest`, `pytest-django`, `Factory Boy` (data generation), `pytest-mock`.
  - **Frontend:** `Vitest`/`Jest`, `React Testing Library`, `MSW` (API mocking).

**Test Organization:**

- **Backend** (`backend/tests/`):
  - `unit/`: Isolated tests (models, services). No DB.
  - `integration/`: Full API/DB interaction tests.
  - `performance/`: Critical path benchmarks.
  - `legacy/`: Deprecated tests (ignored in CI).
- **Frontend**: Tests are co-located with source files (e.g., `Component.test.tsx`).

**Coverage Requirements:**

- **Overall:** >= 70%
- **Critical Modules** (Auth, Orders, 1C Sync): >= 90%
- **Integration Modules:** >= 85%

**Backend Test Commands**

> [!TIP]
> **Recommended:** Run tests via Docker to ensure environment consistency.

```bash
# Run all tests (standard command ignores legacy)
docker compose exec backend pytest --ignore=tests/legacy

# Run unit or integration tests only
docker compose exec backend pytest -m unit
docker compose exec backend pytest -m integration

# Generate coverage report
docker compose exec backend pytest --cov=apps
```

**Frontend Test Commands**

```bash
npm test                    # Run all tests
npm test --watch            # Run tests in watch mode
npm run test:coverage       # Generate a coverage report
```

### **Code Style**

**Backend**

- **Formatting:** Black  
- **Linting:** Flake8  
- **Import Sorting:** isort  
- **Type Checking:** mypy

**Frontend**

- **Linting:** ESLint  
- **Styling:** Tailwind CSS

## **Environment and Configuration**

- **Django Settings:** Modular settings files are used for different environments (base.py, development.py, production.py).  
- **Environment Variables:** Create .env files from .env.example for backend (DATABASE_URL, SECRET_KEY) and frontend (NEXT_PUBLIC_API_URL).  
- **Important Config Files:** pytest.ini, mypy.ini, docker-compose.yml, package.json, jest.config.js.

## **Integrations**

- **ERP (1C):** Two-way data synchronization for products, orders, and stock levels via Celery tasks.
  - **Primary Import Command:** `import_products_from_1c`
    - `python manage.py import_products_from_1c --file-type=all`
    - Supports selective import: `--file-type=goods` (products), `--file-type=prices` (prices), `--file-type=rests` (stock)
  - **Architecture:**
    - Processing: `VariantImportProcessor` (new generation)
    - Parsing: `XMLDataParser`
  - Architecture details: `docs/architecture/import-architecture.md`
  - Real test data available in `data/import_1c/`
- **Payment Gateways:** YuKassa for online payments.  
- **Shipping Services:** CDEK and Boxberry for delivery cost calculation and logistics.
