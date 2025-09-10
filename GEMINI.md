## Gemini Added Memories
- Communicate in Russian.

# **Project Overview**

This is a full-stack e-commerce platform for selling sporting goods, designed as an API-first solution for both B2B and B2C sales. The project is a monorepo with a Django backend and a Next.js frontend.

## **Project Architecture**

* **API-First + SSR/SSG Approach:** Ensures SEO optimization and high performance. The decoupling of frontend and backend allows for independent development cycles.  
* **Next.js Hybrid Rendering:** Utilizes Static Site Generation (SSG) for static pages, Server-Side Rendering (SSR) for dynamic content, and Incremental Static Regeneration (ISR) for catalogs.  
* **BFF (Backend for Frontend) Layer:** Next.js API Routes act as an intermediary layer to aggregate data and enhance security between the client and the main API.  
* **Monorepo Structure:** Simplifies management of shared components, configurations, and dependencies across the entire platform.

**Technology Stack:**

**Backend:**

* **Framework:** Django 4.2 LTS with Django REST Framework 3.14+  
* **Database:** PostgreSQL 15+ (with table partitioning and JSONB support)  
* **Cache:** Redis 7.0+ (for caching and sessions)  
* **Authentication:** JWT tokens with a refresh strategy  
* **Async Tasks:** Celery with Celery Beat for background jobs and scheduling  
* **API Documentation:** drf-spectacular for OpenAPI 3.1.0 specification

**Frontend:**

* **Framework:** Next.js 14+ with TypeScript 5.0+  
* **UI Library:** React 19.1.0  
* **State Management:** Zustand  
* **Styling:** Tailwind CSS 4.0  
* **Form Management:** React Hook Form  
* **Testing:** Jest and React Testing Library

**Infrastructure:**

* **Web Server/Proxy:** Nginx (for reverse proxy, SSL, load balancing)  
* **Containerization:** Docker and Docker Compose  
* **CI/CD:** GitHub Actions

## **Django App Structure**

The project uses a modular Django apps architecture:

* apps/users/: Manages users and a role-based system (7 roles: retail, wholesale_level1-3, trainer, federation_rep, admin).  
* apps/products/: Handles the product catalog, brands, and categories with multi-level pricing.  
* apps/orders/: Contains the order system supporting both B2B/B2C processes.  
* apps/cart/: Manages the shopping cart for both authenticated and guest users.  
* apps/common/: Includes shared utilities, components, and auditing tools.

## **Key Data Models**

* **User Model:** Features a role-based system with 7 distinct user roles, each with different pricing tiers. Includes B2B-specific fields like company_name and tax_id.  
* **Product Model:** Supports multi-level pricing corresponding to user roles. Includes informational prices for B2B (RRP, MSRP), uses a JSONB field for dynamic product specifications, integrates with an ERP via onec_id, and has computed properties like is_in_stock.  
* **Order Model:** Designed to handle both B2B and B2C workflows, capturing a snapshot of product data at the time of purchase. It integrates with payment systems and includes order statuses with an audit trail.

## **Building and Running**

### **Docker**

The recommended way to run the project is with Docker Compose.

# Build and start all services in the background  
docker-compose up -d --build

# Stop and remove all services  
docker-compose down

The following services will be started:

* db: PostgreSQL database  
* redis: Redis cache  
* backend: Django API  
* frontend: Next.js application  
* nginx: Nginx reverse proxy

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

## **Development Conventions**

### **Git Workflow**

* main: Production branch (protected)  
* develop: Main development branch (protected)  
* feature/*: Branches for new features  
* hotfix/*: Branches for critical bug fixes

### **Testing Strategy**

The project follows the classic testing pyramid model.

* **Testing Pyramid:** E2E Tests (Playwright) > Integration Tests (Pytest) > Unit Tests (Pytest, Jest).  
* **Backend Structure:** Tests are organized into unit, integration, and legacy directories.  
* **Pytest Markers:** Tests are marked with `@pytest.mark.unit` and `@pytest.mark.integration` for targeted execution.  
* **Data Generation:** Factory Boy is mandatory for creating realistic test data.  
* **Coverage Requirements:** Overall coverage must be >= 70%; critical modules (auth, orders) must be >= 90%.

**Backend Test Commands**

pytest                # Run all tests  
pytest -m unit        # Run unit tests only  
pytest -m integration # Run integration tests only  
pytest --cov=apps     # Generate a coverage report

**Frontend Test Commands**

npm test                    # Run all tests  
npm test --watch            # Run tests in watch mode  
npm run test:coverage       # Generate a coverage report

### **Code Style**

**Backend**

* **Formatting:** Black  
* **Linting:** Flake8  
* **Import Sorting:** isort  
* **Type Checking:** mypy

**Frontend**

* **Linting:** ESLint  
* **Styling:** Tailwind CSS

## **Environment and Configuration**

* **Django Settings:** Modular settings files are used for different environments (base.py, development.py, production.py).  
* **Environment Variables:** Create .env files from .env.example for backend (DATABASE_URL, SECRET_KEY) and frontend (NEXT_PUBLIC_API_URL).  
* **Important Config Files:** pytest.ini, mypy.ini, docker-compose.yml, package.json, jest.config.js.

## **Integrations**

* **ERP (1C):** Two-way data synchronization for products, orders, and stock levels via Celery tasks.  
* **Payment Gateways:** YuKassa for online payments.  
* **Shipping Services:** CDEK and Boxberry for delivery cost calculation and logistics.
