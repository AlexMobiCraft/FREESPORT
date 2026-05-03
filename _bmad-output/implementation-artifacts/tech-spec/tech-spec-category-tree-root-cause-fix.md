---
title: "Корневое исправление публичного дерева категорий после импорта 1С"
slug: "category-tree-root-cause-fix"
type: "tech-spec"
created: "2026-05-03"
status: "ready-for-dev"
approved_by: "Alex"
approved_at: "2026-05-03"
approval_source: "_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-03.md"
tech_stack: ["Django 5.x", "PostgreSQL", "Next.js", "CommerceML 3.1", "Python 3.12"]
files_to_modify:
  - "backend/apps/products/services/variant_import.py"
  - "backend/apps/products/views.py"
  - "backend/apps/products/serializers.py"
  - "backend/apps/products/management/commands/*.py"
  - "backend/apps/products/tests/unit/*"
  - "backend/apps/products/tests/integration/*"
  - "frontend/src/services/categoriesService.ts"
  - "frontend/src/components/home/QuickLinksSection.tsx"
  - "frontend/src/app/(blue)/catalog/page.tsx"
---

# Tech-Spec: Корневое исправление публичного дерева категорий после импорта 1С

**Status:** ready-for-dev  
**Approved:** 2026-05-03, через `sprint-change-proposal-2026-05-03.md`

> Важно: предыдущая spec `tech-spec-category-filter-sport-subcategories.md` superseded для контракта категорий. Старую команду `cleanup_root_categories`, которая reparent-ит детей `СПОРТ` в `parent=None` и удаляет саму `СПОРТ`, нельзя использовать как repair-команду для нового контракта.

## Intent

После заливки данных из 1С в пустую локальную БД витрина использует некорректное дерево категорий:

- `/catalog` строится из корней `parent=None`, но среди них есть техкатегории вида `Категория <uuid>`
- главная страница показывает все корни из `/categories-tree/`, а не только публичные разделы каталога
- якорная категория `СПОРТ` отсутствует в БД, хотя присутствует в `groups.xml`

Нужно решить проблему в корне: отделить полное дерево 1С от публичного дерева витрины и исключить повторное появление placeholder-категорий в навигации.

## Problem Statement

Текущий импорт категорий основан на старом допущении: `СПОРТ` не хранится в БД сайта, а её прямые дети поднимаются в `parent=None`. Одновременно импорт товаров может создавать placeholder-категории, если `goods.xml` ссылается на `category_id`, которого нет среди уже созданных категорий. В новой БД это приводит к тому, что placeholder-узлы становятся реальными корнями каталога и получают тысячи товаров.

Итог: backend хранит смешанную структуру, а frontend честно отображает этот сломанный источник истины.

## Target Contract

- `Category` хранит полное дерево 1С, включая якорный узел `СПОРТ`
- витрина не запрашивает "все корни", а запрашивает "публичное дерево каталога"
- публичное дерево начинается с прямых потомков `СПОРТ`
- placeholder-категории и служебная категория `Без категории` не попадают в публичное дерево
- товар не может создавать новую публичную категорию только потому, что в `goods.xml` встретился неизвестный `category_id`

## Scope

**In Scope**

- пересмотр логики `process_categories()` и `_get_or_create_category()`
- новый backend-контракт публичного дерева категорий
- cleanup/repair существующих категорий и товаров в локальной БД
- точечная адаптация `/catalog` и home quick links под новый API-контракт
- unit/integration tests для импорта, cleanup и API

**Out of Scope**

- редизайн каталога или главной
- изменение CommerceML-парсера вне задач категорий
- массовая переработка админки категорий
- `electric`-ветка фронтенда

## Design Decisions

### 1. Хранить `СПОРТ` в БД

Старое поведение, при котором якорь не создаётся на сайте, должно быть отменено. Импорт категорий сохраняет полный путь из `groups.xml`, чтобы данные в БД соответствовали реальному дереву 1С.

### 2. Ввести понятие публичного дерева

`/categories-tree/` должен возвращать не "все категории с `parent=None`", а публичные разделы каталога. Источником публичных корней являются прямые дети категории `СПОРТ`.

### 3. Запретить публичные placeholder-категории

Если товар ссылается на неизвестный `category_id`, нельзя создавать обычную категорию `Категория <uuid>` и включать её в витрину. Допустимы только два сценария:

- товар пропускается как ошибочный импорт с явным логированием
- товар уходит в скрытую техническую категорию, исключённую из публичного дерева

Для первой реализации рекомендуется второй вариант как более безопасный для сохранности товаров.

### 4. Починить уже импортированные данные

Нужен management command, который:

- находит placeholder-категории вида `Категория <uuid>`
- отделяет публичные категории от технических
- переносит товары из placeholder-корней в скрытую техкатегорию или в восстановленные реальные категории, если соответствие удалось определить
- гарантирует, что в публичных корнях после выполнения остаются только потомки `СПОРТ`

## Implementation Plan

### Task 1. Пересобрать импорт дерева категорий

- File: `backend/apps/products/services/variant_import.py`
- Action:
  - убрать поведение, при котором `СПОРТ` пропускается при импорте
  - сохранять полный путь `СПОРТ -> child -> descendant`
  - обновить логику `allowed_category_ids`, чтобы она больше не превращала детей `СПОРТ` в абсолютные корни БД

### Task 2. Изменить обработку неизвестных `category_id` у товаров

- File: `backend/apps/products/services/variant_import.py`
- Action:
  - убрать создание публичных placeholder-категорий по шаблону `Категория {uuid}`
  - ввести скрытую техкатегорию для нерезолвленных ссылок или явный skip с логированием
  - логировать количество товаров, попавших в fallback

### Task 3. Ввести API публичного дерева категорий

- Files: `backend/apps/products/views.py`, `backend/apps/products/serializers.py`
- Action:
  - обновить `/categories-tree/` так, чтобы он возвращал публичные корни как детей `СПОРТ`
  - исключить из ответа техкатегории и `uncategorized`
  - сохранить вложенность и существующие поля, чтобы фронтенд менялся минимально

### Task 4. Создать cleanup command для уже испорченной БД

- File: `backend/apps/products/management/commands/fix_category_tree_public_roots.py` (NEW)
- Action:
  - dry-run аудит: показать `СПОРТ`, публичные ветки, placeholder-категории, товары в них
  - execute-режим: восстановить якорь, убрать placeholder-корни из публичного дерева, перенести или изолировать товары
  - вывести итоговый отчёт по количеству исправленных категорий и товаров

### Task 5. Точечно адаптировать frontend к новому контракту

- Files: `frontend/src/services/categoriesService.ts`, `frontend/src/components/home/QuickLinksSection.tsx`, `frontend/src/app/(blue)/catalog/page.tsx`
- Action:
  - считать `/categories-tree/` уже публичным деревом
  - убрать предположение "если корень один, это `СПОРТ`, иначе показываем все корни"
  - в сервисе дерева передавать `page_size`, если API останется пагинируемым

### Task 6. Добавить тесты и регрессионные проверки

- Files: backend/frontend category tests
- Action:
  - тест: `СПОРТ` сохраняется в БД после импорта
  - тест: `/categories-tree/` возвращает только публичные ветки
  - тест: placeholder-категория не становится публичным корнем
  - тест: quick links и `/catalog` используют одинаковый публичный источник данных

## Acceptance Criteria

- Given пустая БД и полный импорт `groups.xml + goods.xml`, when импорт завершён, then категория `СПОРТ` существует в БД как корневой узел
- Given тот же импорт, when вызывается `/categories-tree/`, then ответ содержит публичные категории как потомков `СПОРТ`, а не все `parent=None`
- Given товар с неизвестным `category_id`, when выполняется импорт, then не создаётся новая публичная категория вида `Категория <uuid>`
- Given в БД есть placeholder-категории из старого импорта, when выполняется cleanup command, then они исключаются из публичного дерева и не отображаются на витрине
- Given главная страница и `/catalog`, when они загружают дерево категорий, then обе страницы показывают одинаковый публичный набор разделов
- Given повторный импорт после исправления, when данные перезаливаются в пустую БД, then проблема с UUID-корнями не воспроизводится
- Given cleanup/repair выполнен по новому контракту, when проверяется БД, then `СПОРТ` существует как корневой узел и не отображается как публичный root в `/categories-tree/`
- Given старая команда `cleanup_root_categories`, when рассматривается repair-путь для новой БД, then она не используется без изменения семантики, потому что удаляет якорь `СПОРТ`

## Risks

- изменение формы дерева может затронуть breadcrumbs и deep-link переходы по `slug`
- перенос товаров из placeholder-категорий требует аккуратного fallback, чтобы не потерять каталог
- старые тесты, построенные на допущении `children of СПОРТ => parent=None`, нужно осознанно переписать

## Verification

- `docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest apps/products -m unit`
- `docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest apps/products -m integration`
- ручная проверка API:
  - `/api/v1/categories-tree/`
  - `/api/v1/products/visible-categories/?in_stock=true`
- ручная проверка UI:
  - `/catalog`
  - главная quick links

## Notes

- Эта spec намеренно пересматривает реализованное ранее решение из `tech-spec-category-filter-sport-subcategories.md`
- Предыдущее допущение "якорь `СПОРТ` не создаётся на сайте" признано несовместимым с корректным восстановлением дерева в новой пустой БД
- Утверждённый Sprint Change Proposal: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-03.md`
