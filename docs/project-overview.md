# Project Overview

## Vision
FREESPORT is a comprehensive e-commerce platform designed to unify 5 brands under a single API-first architecture, supporting complex B2B workflows (role-based pricing, bulk orders) alongside a modern B2C experience.

## Executive Summary
The project transitions from a legacy system to a modern Headless Commerce architecture.
- **Frontend**: Next.js 15 App Router (Performance, SEO).
- **Backend**: Django 5.2 (Robustness, Admin, Integrations).
- **Integration**: Deep synchronization with 1C ERP.

## Key Features
- **Multi-Brand Support**: Unified catalog with brand filtering.
- **B2B System**:
    - Role-based pricing (7 tiers).
    - Wholesale checkout flow.
    - Company profile management.
- **Performance**: SSR/SSG hybrid rendering, Redis caching.

## Repository Structure
This is a **monorepo** containing:
- `/backend`: API Server.
- `/frontend`: Web Client.
- `/docker`: Infrastructure as Code.
- `/docs`: Documentation.
