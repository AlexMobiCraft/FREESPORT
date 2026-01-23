# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records (ADRs) that document significant architectural decisions made during the development of FREESPORT.

## What is an ADR?

An ADR captures a single architecture decision along with its context, consequences, and rationale. Each record is immutable once accepted - if a decision needs to change, a new ADR should be created that supersedes the old one.

## ADR Template

Each ADR should follow this structure:
- **Status:** Proposed | Accepted | Deprecated | Superseded
- **Date:** Decision date
- **Context:** What is the issue we're facing?
- **Decision:** What decision did we make?
- **Consequences:** What are the positive and negative outcomes?

## Index of ADRs

### Integration & External Systems

- **[ADR-002: 1C Integration Strategy](../../_bmad-output/planning-artifacts/architecture.md#adr-002-стратегия-интеграции-с-1с)** - Асинхронная синхронизация на основе файлов XML (CommerceML)
- **[ADR-008: Use Django Session Key for 1C sessid](./ADR-008-1c-sessid-session-key-not-csrf.md)** - Clarifies that `sessid` in 1C protocol is Django Session ID, not CSRF token (2026-01-23)

### API & Authentication

- **[ADR-001: API-First и паттерн BFF](../../_bmad-output/planning-artifacts/architecture.md#adr-001-api-first-и-паттерн-bff)** - Разделенная архитектура с Django REST API и Next.js BFF
- **[ADR-004: Ценообразование на основе ролей](../../_bmad-output/planning-artifacts/architecture.md#adr-004-ценообразование-на-основе-ролей)** - Динамическая сериализация цен в DRF

### Frontend & UX

- **[ADR-003: Гибридный интерфейс администратора](../../_bmad-output/planning-artifacts/architecture.md#adr-003-гибридный-интерфейс-администратора)** - Django Admin для CRUD + кастомная админ-панель
- **[ADR-005: Гибридная динамическая валидация B2B](../../_bmad-output/planning-artifacts/architecture.md#adr-005-гибридная-динамическая-валидация-b2b)** - Бэкенд отдает правила через API

### Infrastructure & Deployment

- **[ADR-006: Стратегия деплоя Recreate](../../_bmad-output/planning-artifacts/architecture.md#adr-006-стратегия-деплоя-recreate-с-предохранителями)** - Использование стратегии Recreate с healthchecks
- **[ADR-007: Организация монорепозитория](../../_bmad-output/planning-artifacts/architecture.md#adr-007-организация-монорепозитория-decoupled-monorepo)** - Decoupled Monorepo без Turborepo

## How to Create a New ADR

1. Copy the ADR template (create from ADR-008 structure)
2. Number it sequentially (next available: ADR-009)
3. Write in clear, concise language
4. Include code examples and references
5. Update this README index
6. Link from relevant documentation

## References

- [ADR GitHub Organization](https://adr.github.io/) - ADR best practices
- [Architecture Decision Record Template](https://github.com/joelparkerhenderson/architecture-decision-record)
