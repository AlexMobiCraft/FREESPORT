# Project Overview

This is a full-stack e-commerce platform for selling sporting goods. The project is a monorepo with a Django backend and a Next.js frontend. The platform is designed to be API-first and supports both B2B and B2C sales.

**Backend:**
*   **Framework:** Django 4.2 LTS with Django REST Framework 3.14+
*   **Database:** PostgreSQL 15+
*   **Cache:** Redis 7.0+
*   **Authentication:** JWT tokens with a refresh strategy
*   **API Documentation:** drf-spectacular for OpenAPI 3.1.0 specification

**Frontend:**
*   **Framework:** Next.js 14+ with TypeScript 5.0+
*   **State Management:** Zustand
*   **Styling:** Tailwind CSS
*   **Form Management:** React Hook Form
*   **Testing:** Jest and React Testing Library

**Infrastructure:**
*   **Containerization:** Docker and Docker Compose
*   **CI/CD:** GitHub Actions

# Building and Running

## Docker

The recommended way to run the project is with Docker Compose.

```bash
# Build and start all services in the background
docker-compose up -d --build

# Stop and remove all services
docker-compose down
```

The following services will be started:
*   `db`: PostgreSQL database
*   `redis`: Redis cache
*   `backend`: Django API
*   `frontend`: Next.js application
*   `nginx`: Nginx reverse proxy

## Local Development

### Backend

1.  Navigate to the `backend` directory.
2.  Create a virtual environment: `python -m venv venv`
3.  Activate the virtual environment: `source venv/bin/activate` (on Windows, use `venv\Scripts\activate`)
4.  Install the dependencies: `pip install -r requirements.txt`
5.  Run the development server: `python manage.py runserver 8001`

### Frontend

1.  Navigate to the `frontend` directory.
2.  Install the dependencies: `npm install`
3.  Run the development server: `npm run dev`

# Development Conventions

## Git Workflow

*   `main`: Production branch (protected)
*   `develop`: Main development branch (protected)
*   `feature/*`: Branches for new features
*   `hotfix/*`: Branches for critical bug fixes

## Testing

### Backend

*   Run all tests: `pytest`
*   Run unit tests only: `pytest -m unit`
*   Run integration tests only: `pytest -m integration`
*   Generate a coverage report: `pytest --cov=apps --cov-report=html`

### Frontend

*   Run all tests: `npm test`
*   Run tests in watch mode: `npm test --watch`
*   Generate a coverage report: `npm run test:coverage`

## Code Style

### Backend

*   **Formatting:** Black
*   **Linting:** Flake8
*   **Import Sorting:** isort
*   **Type Checking:** mypy

### Frontend

*   **Linting:** ESLint
*   **Styling:** Tailwind CSS
