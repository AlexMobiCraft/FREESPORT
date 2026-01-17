---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
inputDocuments: 
  - docs/PRD.md
  - docs/architecture.md
  - docs/architecture/
  - docs/front-end-spec.md
  - docs/stories/
---

# FREESPORT - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for FREESPORT, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.
Reflecting the actual project structure: **Backend First -> UX -> Frontend**.

## Requirements Inventory

### Functional Requirements

FR1: Каталог товаров с многоуровневой структурой.
FR2: Упрощенная фильтрация товаров (только по цене и размеру).
FR3: Базовая сортировка товаров (только по цене).
FR4: Базовый поиск по названию товара.
FR5: Отображение цен в зависимости от роли (retail, opt1/2/3, trainer, federation) + инфо-цены (RRP/MSRP) для B2B.
FR6: Корзина с логикой склейки одинаковых позиций (без дубликатов).
FR7: Процесс оформления заказа (checkout) на одной или двух страницах + "быстрый заказ" для B2C.
FR8: Базовая админ-панель для управления заказами и пользователями.
FR9: Двусторонняя интеграция с 1С (остатки, цены, выгрузка заказов, статусы).
FR10: Ролевая модель пользователей (Оптовый, Тренер, Федерация, Розница).
FR11: Личный кабинет (Профиль, Мои заказы, Адрес доставки, Избранное).
FR12: B2B разделы ЛК (Управление компанией, История счетов).
FR13: Персонализированные рекламные баннеры на главной по ролям.
FR14: Полная мобильная адаптивность ключевых страниц.
FR15: Единая дизайн-система для B2B и B2C.
FR16: Верификация B2B клиентов через загрузку документов и модерацию админом.

### NonFunctional Requirements

NFR1: Скорость загрузки < 3 сек, Google PageSpeed Insights > 70.
NFR2: Защита от XSS, SQL-инъекций, CSRF.
NFR3: Использование защищенного соединения HTTPS.
NFR4: Масштабируемая архитектура.
NFR5: Соответствие ФЗ-152 "О персональных данных".
NFR6: Документация API OpenAPI 3.1 (Swagger) с версионированием.
NFR7: Авторизация через JWT токены.
NFR8: Отказоустойчивость импорта из 1С (сессии импорта, Circuit Breaker).
NFR9: Идемпотентность операций синхронизации.

### FR Coverage Map

FR1: Epic 2 & 10 - Catalog API & UI
FR2: Epic 2 & 14 - Filtering API & Logic
FR3: Epic 2 - Sorting API
FR4: Epic 2 - Search API
FR5: Epic 2 - Pricing Logic
FR6: Epic 2 & 26 - Cart API & UI
FR7: Epic 2 & 15 - Order API & UI
FR8: Epic 9 - Admin Panel
FR9: Epic 3 - 1C Integration
FR10: Epic 2 - User Roles
FR11: Epic 2 & 23 - User Profile
FR12: Epic 3 & 8 - B2B Features
FR13: Epic 17 - Banners
FR14: Epic 10+ - Mobile Adaptation
FR15: Epic 10 & 24 - Design System
FR16: Epic 2 & 29 - B2B Verification

## Epic List (Complete Project Roadmap)

### Phase 1: Foundation & Backend Core

* **Epic 1: Project Foundation & Database** - Setup infrastructure, DB, Monorepo.
* **Epic 2: Core API Development** - Auth, Users, Catalog, Cart, Orders API.
* **Epic 3: 1C Integration System** - Import Catalog, Stocks, Customers.
* **Epic 3.1: 1C Import Refactoring** - Optimization of import scripts.
* **Epic 4: Pricing Logic** (Reserved) - Advanced pricing rules.
* **Epic 9: Admin Panel & Operations** - Custom admin for B2B moderation & import monitoring.

### Phase 2: Frontend Foundation & Core UI

* **Epic 10: Frontend Foundation** - UI Kit, State Management, Vitest.
* **Epic 11: Main Page & CMS** - Hero section, Dynamic blocks.
* **Epic 12: Product Detail Page UI** - Gallery, Options, Add to Cart.
* **Epic 13: Product Variants Refactoring** - Backend/Frontend sync for SKU variants.
* **Epic 14: Attributes & Filters** - EAV models, Faceted search UI.
* **Epic 15: Checkout & Orders** - Checkout form, Delivery integration.
* **Epic 16: Shopping Cart Logic** - Frontend cart state & calculations.
* **Epic 17: Dynamic Banners** - Banner management & display.
* **Epic 18: Search Functionality** - Global search with history.
* **Epic 19: Static Pages** - About, Delivery, Partners pages.
* **Epic 20: News Section** - News list & detail pages.
* **Epic 21: Blog Section** - Blog implementation.

### Phase 3: Advanced UI & Refinement

* **Epic 22: Auth Flow Refactoring** - Optimization of login/register flows.
* **Epic 23: User Profile UI** - Personal cabinet implementation.
* **Epic 24: Design System Update** - New color palette & UI Kit refactor.
* **Epic 25: Image Import Optimization** - Selective image importing.
* **Epic 26: Cart Page UI** - Dedicated cart page implementation.
* **Epic 27: Legacy Code Cleanup** - Removal of deprecated import logic.
* **Epic 28: Auth UI Core** - Login, Register, Password Reset UI.
* **Epic 29: B2B Registration Flow** - Role selection & Email verification.
* **Epic 30: Logout Backend** - JWT Blacklist implementation.
* **Epic 31: Logout Frontend** - Frontend logout logic.

---

## Detailed Stories

### Epic 1: Project Foundation & Database

Establish the technical groundwork.

* **Story 1.1:** Git & Monorepo Setup
* **Story 1.2:** Dev Environment
* **Story 1.3:** Django Structure
* **Story 1.4:** Next.js Structure
* **Story 1.5:** CI/CD Setup
* **Story 1.6:** Docker Containers
* **Story 1.7:** Testing Setup
* **Story 1.8:** Database Design
* **Story 1.9:** Design Brief

### Epic 2: Core API Development

Implement essential API endpoints.

* **Story 2.1:** Swagger Docs
* **Story 2.2:** User Mgmt API
* **Story 2.3:** Profile API
* **Story 2.4:** Catalog API
* **Story 2.5:** Product Detail API
* **Story 2.6:** Cart API
* **Story 2.7:** Order API
* **Story 2.8:** Search API
* **Story 2.9:** Filter API
* **Story 2.10:** Pages API

### Epic 3: 1C Integration System

Bidirectional synchronization.

* **Story 3.1:** Import Products Structure
* **Story 3.2:** Customer Sync
* **Story 3.3:** Loading Scripts
* **Story 3.4:** Conflict Resolution
* **Story 3.5:** Monitoring

### Epic 3.1: 1C Import Refactoring

Optimization and cleanup of import logic.

* **Story 3.1.1:** Refactor Import Structure
* **Story 3.1.2:** Optimize Loading Scripts
* **Story 3.1.3:** Catalog Loading Tests
* **Story 3.1.4:** Fix Price Import Logic (RRP/MSRP)

### Epic 9: Admin Panel & Operations

Custom tools for administration.

* **Story 9.1:** User Management Admin
* **Story 9.2:** Order Management Admin
* **Story 9.3:** Import Monitoring UI
* **Story 9.4:** Dashboard Widgets
* **Story 9.5:** Selective Import UI
* **Story 9.6:** Import Page Creation
* **Story 9.7:** Sessions Page Refactor
* **Story 9.8:** Admin Testing

### Epic 10: Frontend Foundation

Core frontend architecture.

* **Story 10.1:** Env & Layout
* **Story 10.2:** UI Kit Implementation
* **Story 10.3:** State Management
* **Story 10.4:** Vitest Setup

### Epic 11: Main Page & CMS

Customer-facing main page.

* **Story 11.0:** Product Badges
* **Story 11.1:** Hero Section
* **Story 11.2:** Dynamic Blocks
* **Story 11.3:** Subscribe Form

### Epic 12: Product Detail Page UI

Detailed view of products.

* **Story 12.1:** Product Detail View
* **Story 12.2:** Product Options
* **Story 12.3:** Add to Cart UI
* **Story 12.4:** Product Gallery
* **Story 12.5:** Related Products
* **Story 12.6:** Responsive Layout

### Epic 13: Product Variants Refactoring

Handling of SKU variants.

* **Story 13.1:** Backend Models (ProductVariant)
* **Story 13.2:** Refactor Import for Variants
* **Story 13.3:** API Extension
* **Story 13.4:** Production Migration
* **Story 13.5:** Variants UI Mock & Integration

### Epic 14: Attributes & Filters

Advanced product data.

* **Story 14.1:** Attribute Models
* **Story 14.2:** Import Attributes
* **Story 14.3:** Deduplication
* **Story 14.4:** Link Attributes
* **Story 14.5:** API Enhancement
* **Story 14.6:** Facets UI

### Epic 15: Checkout & Orders

Conversion flow.

* **Story 15.1:** Checkout Form
* **Story 15.2:** Order API Integration
* **Story 15.3:** Delivery Integration
* **Story 15.4:** Success Page
* **Story 15.5:** E2E Testing

### Epic 16: Shopping Cart Logic

Frontend cart state.

* **Story 16.1:** Cart Logic Implementation
* **Story 16.2:** Add/Remove Items
* **Story 16.3:** Persistence

### Epic 17: Dynamic Banners

Marketing banners.

* **Story 17.1:** Banner Models (Admin)
* **Story 17.2:** Banner API
* **Story 17.3:** Frontend Banner Integration
* **Story 17.4:** Documentation

### Epic 18: Search Functionality

Global search.

* **Story 18.1:** Header Search Integration
* **Story 18.2:** Search Results Page
* **Story 18.3:** Search History
* **Story 18.4:** Catalog Search Integration

### Epic 19: Static Pages

Informational content.

* **Story 19.1:** Info Page Components
* **Story 19.2:** Homepage Teasers
* **Story 19.3:** About Page
* **Story 19.4:** Partners Page
* **Story 19.5:** Delivery Page
* **Story 19.6:** Navigation Update

### Epic 20: News Section

Company news.

* **Story 20.1:** News API
* **Story 20.2:** News Pages
* **Story 20.3:** News Teaser
* **Story 20.4:** Docs Update

### Epic 21: Blog Section

Content marketing.

* **Story 21.1:** Blog Backend Models
* **Story 21.2:** Blog API
* **Story 21.3:** Frontend Blog Pages
* **Story 21.4:** Documentation

### Epic 22: Auth Flow Refactoring

Optimization of existing flows.

* **Story 22.1:** Auth Flow Optimization
* **Story 22.2:** Register Optimization

### Epic 23: User Profile UI

Personal cabinet.

* **Story 23.1:** Profile Layout
* **Story 23.2:** Edit Profile Form
* **Story 23.3:** Change Password Form

### Epic 24: Design System Update

Visual refresh.

* **Story 24.1:** Design Tokens Update
* **Story 24.2:** UI Kit Refactor
* **Story 24.3:** Page Components Update
* **Story 24.4:** Documentation Sync
* **Story 24.5:** Testing Deployment

### Epic 25: Image Import Optimization

Performance tuning.

* **Story 25.1:** Admin Images Import Type
* **Story 25.2:** Celery Task Image Import
* **Story 25.3:** Monitoring

### Epic 26: Cart Page UI

Dedicated cart page.

* **Story 26.1:** Cart Page Layout
* **Story 26.2:** Cart Item Card
* **Story 26.3:** Cart Summary
* **Story 26.4:** Promo Code Integration
* **Story 26.5:** Cart Page Tests

### Epic 27: Legacy Code Cleanup

Technical debt removal.

* **Story 27.1:** Migrate Missing Methods
* **Story 27.2:** Unify Image Paths
* **Story 27.3:** Update Celery Tasks
* **Story 27.4:** Deprecate Legacy Commands
* **Story 27.5:** Remove Legacy Code
* **Story 27.6:** Documentation Audit

### Epic 28: Auth UI Core

Essential auth pages.

* **Story 28.1:** Core Auth Logic
* **Story 28.2:** B2B Registration Form
* **Story 28.3:** Password Reset Flow
* **Story 28.4:** Protected Routes
* **Story 28.5:** Password Visibility

### Epic 29: B2B Registration Flow

Business specific onboarding.

* **Story 29.1:** Role Selection UI
* **Story 29.2:** Backend Verification Logic
* **Story 29.3:** Email Server Configuration
* **Story 29.4:** Email Notification System

### Epic 30: Logout Backend

Security enhancement.

* **Story 30.1:** JWT Token Blacklist Setup
* **Story 30.2:** Logout View Serializer
* **Story 30.3:** Logout API Docs
* **Story 30.4:** Logout Tests

### Epic 31: Logout Frontend

Security UI.

* **Story 31.1:** Logout Button
* **Story 31.2:** AuthService Logout
* **Story 31.3:** Logout Redirect
* **Story 31.4:** Logout Tests
