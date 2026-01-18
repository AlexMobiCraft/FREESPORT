# FREESPORT Platform Documentation

## Project Overview

- **Type:** Multi-part E-commerce Platform
- **Architecture:** Headless (Next.js Frontend + Django REST API Backend)
- **Primary Languages:** TypeScript, Python
- **Status:** Active Development

## Quick Reference

### Frontend (`/frontend`)
- **Framework:** Next.js 15.5.7 (App Router)
- **UI:** React 19.1.0, Tailwind CSS 4
- **State:** Zustand
- **Testing:** Vitest, Playwright

### Backend (`/backend`)
- **Framework:** Django 5.2.7
- **API:** Django REST Framework 3.14
- **Database:** PostgreSQL 15
- **Async:** Celery + Redis

## Documentation Index

### Architecture & Design
- [Architecture Overview](./architecture.md) _(To be generated)_
- [Frontend Source Tree](./source-tree-analysis-frontend.md)
- [Backend Source Tree](./source-tree-analysis-backend.md)
- [Integration Architecture](./integration-architecture.md)
- [Data Models](./data-models-backend.md)
- [API Contracts](./api-contracts-backend.md)

### Guides
- [Development Guide](./development-guide.md)
- [Deployment Guide](./deploy/index.md) _(To be generated)_
- [Testing Guide](./testing-docker.md)

### Product Context
- [Product Requirements (PRD)](./PRD.md)
- [Project Brief](./Brief.md)
- [UI/UX Specification](./front-end-spec.md)

### Existing Docs
- [API Views Documentation](./api-views-documentation.md)
- [API Specification (OpenAPI)](./api-spec.yaml)
- [Docker Configuration](./docker-configuration.md) _(To be generated)_
- [Architecture Detail](./architecture/index.md)

## Getting Started

1. **Clone repository**
2. **Setup Environment**: Copy `.env.example` to `.env`
3. **Start Docker**: `docker compose -f docker/docker-compose.yml up -d`
4. **Access**:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000