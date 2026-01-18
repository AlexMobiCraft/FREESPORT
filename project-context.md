# Project Context: FREESPORT

## Overview
FREESPORT is a full-stack, API-first e-commerce platform designed for both B2B and B2C sales of sporting goods. It features a modular Django backend and a Next.js frontend, with deep integration with 1C ERP.

- **Primary Goal**: A unified platform for 5 brands with role-based pricing and B2B specific workflows.
- **Architecture**: Decoupled Monorepo (Next.js Frontend + Django REST Backend).

## Tech Stack
### Backend (`/backend`)
- **Framework**: Django 5.2.7 + Django REST Framework 3.14.
- **Database**: PostgreSQL 15 (with partitioning and JSONB).
- **Cache/Task Broker**: Redis 7.0 + Celery 5.4.
- **Auth**: JWT (SimpleJWT).

### Frontend (`/frontend`)
- **Framework**: Next.js 15.5.7 (App Router), React 19.1.0.
- **Styling**: Tailwind CSS 4.0.
- **State Management**: Zustand 4.5.7.
- **Icons**: Lucide React.

## Core Domain Models
- **Users**: Role-based system (retail, 3 wholesale levels, trainer, federation, admin). Supports B2B verification.
- **Products**: Multi-level pricing based on user roles. Hybrid image system (variant-specific + product fallback). EAV for specifications.
- **Orders**: Unified B2B/B2C workflow. Order snapshots for items. Payment via YuKassa.
- **1C Integration**: Asynchronous sync via Celery using XML (CommerceML). `onec_id` is the primary key for external mapping.

## Infrastructure
- **Containerization**: Docker & Docker Compose (dev/prod environments).
- **CI/CD**: GitHub Actions.
- **Reverse Proxy**: Nginx.

## Development & Maintenance
- **Master Index**: `docs/index.md`
- **Architecture**: `_bmad-output/planning-artifacts/architecture.md`
- **PRD**: `_bmad-output/planning-artifacts/refined-prd.md`
- **Readiness Report**: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-01-18.md`
- **Testing**: Pytest (Backend), Vitest & Playwright (Frontend).
- **Technical Debt**: Exhaustive scan of codebase deferred for future audit.

## Implementation Status
- **Current Phase**: Phase 4 - Implementation & Stabilization (Bugfix Mode).
- **Epics Status**: Structural review completed. Identified gaps in planning (e.g. missing Epic 8, large Epic 2) but proceeding with existing codebase.
- **Next Steps**: 
    1. Sprint Planning (Bug Triage).
    2. Stabilization of Core API and 1C Integration.
    3. Performance optimization.

## Key Integration Points
1. **Frontend -> Backend**: REST API with JWT.
2. **Backend -> 1C**: XML import/export (asynchronous).
3. **Backend -> YuKassa**: Payment gateway integration.
4. **Backend -> Delivery**: CDEK/Boxberry integration.