# Source Tree Analysis

## Project Structure Overview

FREESPORT is a multi-part monorepo consisting of a Django backend and a Next.js frontend, orchestrated via Docker.

```
FREESPORT/
├── backend/                 # Backend Application (Django 5.2)
│   ├── apps/                # Django Apps (Domain Logic)
│   ├── freesport/           # Project Configuration
│   ├── requirements.txt     # Python Dependencies
│   └── Dockerfile           # Backend Container Definition
├── frontend/                # Frontend Application (Next.js 15.5)
│   ├── src/                 # Source Code
│   │   ├── app/             # App Router Pages & Layouts
│   │   ├── components/      # React Components
│   │   └── services/        # API Clients
│   ├── package.json         # JS Dependencies
│   └── Dockerfile           # Frontend Container Definition
├── docker/                  # Infrastructure Configuration
│   ├── docker-compose.yml   # Dev Orchestration
│   └── nginx/               # Reverse Proxy Config
├── docs/                    # Project Documentation (BMAD Standard)
└── .github/                 # CI/CD Workflows
```

## Backend Detail (`backend/`)

The backend follows a modular Django app structure.

```
backend/
├── apps/
│   ├── banners/             # Hero banner management
│   ├── cart/                # Shopping cart logic (Redis-backed)
│   ├── common/              # Shared utilities & mixins
│   ├── delivery/            # Shipping cost calculations (CDEK, Boxberry)
│   ├── integrations/        # External service integrations
│   ├── orders/              # Order processing & payment
│   ├── pages/               # Static content pages management
│   ├── products/            # Product catalog, prices, variants
│   └── users/               # Custom user model, B2B roles, auth
├── freesport/               # Core Settings
│   ├── settings/            # Split settings (base, dev, prod)
│   ├── celery.py            # Celery app config
│   └── urls.py              # Root URL router
└── manage.py                # CLI Entry Point
```

## Frontend Detail (`frontend/`)

The frontend uses Next.js 15 App Router with a feature-based folder structure.

```
frontend/
├── src/
│   ├── app/                 # Routes
│   │   ├── (blue)/          # Main Theme Route Group
│   │   │   ├── catalog/     # Product Catalog
│   │   │   ├── product/     # Product Details
│   │   │   └── ...
│   │   ├── (electric)/      # Alternate Theme Route Group
│   │   └── api/             # BFF / API Routes
│   ├── components/
│   │   ├── business/        # Domain Components (ProductCard, etc.)
│   │   ├── ui/              # Reusable UI Kit (Button, Input, etc.)
│   │   └── layout/          # Header, Footer, Wrappers
│   ├── services/            # API Client Layer (Axios)
│   ├── store/               # State Management (Zustand)
│   └── hooks/               # Custom React Hooks
└── public/                  # Static Assets
```

## Key Configuration Files

*   **`backend/requirements.txt`**: Python dependencies.
*   **`frontend/package.json`**: Node.js dependencies & scripts.
*   **`frontend/next.config.ts`**: Next.js configuration.
*   **`docker/docker-compose.yml`**: Main service orchestration.
