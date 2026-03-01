---
title: 'Фильтрация категорий 1С: импорт только подкатегорий СПОРТ'
slug: 'category-filter-sport-subcategories'
created: '2026-03-01T08:04:19+01:00'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: [Django 5.x, PostgreSQL, Celery, XML/CommerceML 3.1, Python 3.12]
files_to_modify:
  - backend/apps/products/management/commands/cleanup_root_categories.py (NEW)
  - backend/apps/products/services/variant_import.py
  - backend/backend/settings.py
files_to_test:
  - backend/apps/products/tests/unit/test_cleanup_root_categories.py (NEW)
  - backend/apps/products/tests/unit/test_variant_import_migrated.py (UPDATE)
code_patterns:
  - management commands (BaseCommand + --dry-run)
  - VariantImportProcessor.process_categories (двухпроходный алгоритм)
  - Category.parent FK(self, CASCADE)
  - Product.category FK(Category, CASCADE)
test_patterns:
  - pytest + @pytest.mark.django_db
  - management call_command в тестах
adversarial_review: 'completed 2026-03-01, F4/F5/F6/F7/F8/F9 addressed'
---

# Tech-Spec: Фильтрация категорий 1С — импорт только подкатегорий СПОРТ

**Created:** 2026-03-01  
**Status:** ready-for-dev  
**Adversarial Review:** ✅ Completed

## Overview

### Problem Statement

Парсер `groups.xml` (CommerceML 3.1) импортирует **все** категории из 1С, включая корневую «СПОРТ» и другие корневые категории. В БД сайта появляется лишний уровень иерархии и посторонние категории.

### Solution

1. **Cleanup-команда** (выполняется первой): management command для очистки БД
2. **Модификация процессора**: фильтрация в `process_categories()` при импорте

### Scope

**In Scope:** cleanup command, модификация process_categories, настройка settings, тесты  
**Out of Scope:** parse_groups_xml, UI/Frontend, миграции Django

### Confirmed Assumptions

- ✅ Товары привязаны **только** к подкатегориям СПОРТ, **не** к самой СПОРТ (проверено вручную)
- ✅ Backup/rollback не нужен — данные можно перезалить полной выгрузкой из 1С

## Context for Development

### ⚠️ CASCADE-зависимости

| Модель | FK | on_delete | Риск |
| ------ | -- | --------- | ---- |
| `Category.parent` | FK self | CASCADE | Удаление родителя → удалит ВСЕХ потомков |
| `Product.category` | FK Category | CASCADE | Удаление категории → удалит ВСЕ товары |

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `backend/apps/products/services/variant_import.py:1340-1434` | `process_categories()` — МОДИФИЦИРУЕТСЯ |
| `backend/apps/products/models.py:168-289` | Category (CASCADE parent) + Product (CASCADE category) |
| `backend/apps/products/management/commands/import_products_from_1c.py:329-349` | `_import_categories()` — вызывает process_categories |
| `backend/backend/settings.py:197` | Аналогичный паттерн для ONEC_DATA_DIR |
| `backend/tests/fixtures/1c-data/groups/groups.xml` | Тестовые данные XML |
| `backend/apps/products/tests/unit/test_variant_import_migrated.py` | Существующие тесты |

## Implementation Plan

### Tasks

- [ ] **Task 1: Добавить ROOT_CATEGORY_NAME в settings**
  - File: `backend/backend/settings.py`
  - Action: Добавить `ROOT_CATEGORY_NAME = os.environ.get("ROOT_CATEGORY_NAME", "СПОРТ")` рядом с `ONEC_DATA_DIR` (строка ~197)
  - Notes: Аналогичный паттерн: env-переменная с default

- [ ] **Task 2: Создать management command cleanup_root_categories**
  - File: `backend/apps/products/management/commands/cleanup_root_categories.py` (NEW)
  - Action: Создать Django management command со следующей логикой:
    1. Аргументы: `--dry-run` (по умолч.), `--root-name` (override settings), `--execute` (для реального запуска)
    2. Шаг 1 — Аудит: найти все корневые категории (parent=None), вывести:
       - Имя категории, количество прямых children, количество всех потомков (рекурсивно)
       - Количество Product привязанных к каждой корневой и всем её потомкам
       - Проверить HomepageCategory записи, связанные с удаляемыми категориями
    3. Шаг 2 — Найти якорную категорию (по имени из settings/аргумента)
    4. Шаг 3 — Reparent: `Category.objects.filter(parent=anchor).update(parent=None)` — перепривязать прямых дочерних якорной на parent=None
    5. Шаг 4 — Удалить якорную категорию (уже без children): `anchor.delete()`. Если есть Product привязанные напрямую к якорной — удалять вместе (CASCADE)
    6. Шаг 5 — Удалить все оставшиеся корневые (parent=None, кроме бывших children якорной): CASCADE удалит их потомков и привязанные Product. Вывести предупреждение о количестве удаляемых товаров
    7. Обернуть шаги 3-6 в `transaction.atomic()`
    8. **[F7] Логирование**: вывести итоговый отчёт (категорий reparented, категорий удалено, товаров удалено каскадно). Записать лог в stdout для сохранения в Docker logs
  - Notes:
    - По умолчанию `--dry-run` (без `--execute` ничего не меняет)
    - Вывод в stdout через `self.style.SUCCESS/WARNING/ERROR`
    - Паттерн из `import_products_from_1c.py`
  - **[F6] Production launch:**
    ```bash
    # Dry-run (проверка):
    docker compose --env-file .env -f docker/docker-compose.yml exec -T backend python manage.py cleanup_root_categories
    
    # Execute (реальный запуск):
    docker compose --env-file .env -f docker/docker-compose.yml exec -T backend python manage.py cleanup_root_categories --execute
    ```

- [ ] **Task 3: Модифицировать process_categories() в variant_import.py**
  - File: `backend/apps/products/services/variant_import.py`
  - Action: В начале метода `process_categories()`:
    1. Получить `ROOT_CATEGORY_NAME` из `django.conf.settings` (с `getattr` default=None)
    2. Определить `root_ids` — set ID категорий из `categories_data` где `parent_id` отсутствует (корневые)
    3. Найти `anchor_id` — ID категории с name == ROOT_CATEGORY_NAME среди корневых
    4. **[F4] Построить `allowed_ids`** — multi-pass алгоритм:
       ```python
       # Flat list может быть НЕ топологически отсортирован
       # Используем iterative set expansion:
       allowed_ids = set()
       # Seed: прямые children якорной
       for cat in categories_data:
           if cat.get("parent_id") == anchor_id:
               allowed_ids.add(cat["id"])
       # Expand: добавлять children уже allowed
       changed = True
       while changed:
           changed = False
           for cat in categories_data:
               pid = cat.get("parent_id")
               if pid and pid in allowed_ids and cat["id"] not in allowed_ids:
                   allowed_ids.add(cat["id"])
                   changed = True
       ```
    5. В ШАГ 1 (создание): пропускать категории с `id in root_ids` (все корневые). Создавать только категории с `id in allowed_ids`
    6. В ШАГ 2 (установка parent): для категорий где `parent_id == anchor_id` → не устанавливать parent (они корневые на сайте). Для `parent_id in root_ids` (другие корневые) → пропускать. Для остальных — обычная логика
    7. **[F8]** Если `ROOT_CATEGORY_NAME` задан но не найден среди корневых — логировать `logger.error()` (не warning!) и продолжить с полным импортом для обратной совместимости. Добавить в `result` ключ `"root_not_found": True` для мониторинга
  - Notes:
    - Если `ROOT_CATEGORY_NAME is None` (не задан) — импортировать как раньше (обратная совместимость), тихо
    - Если задан но не найден — ERROR лог + fallback

- [ ] **Task 4: Тесты для cleanup command**
  - File: `backend/apps/products/tests/unit/test_cleanup_root_categories.py` (NEW)
  - Action: Создать тесты:
    - `test_dry_run_shows_info_without_changes` — dry-run не меняет данные
    - `test_execute_reparents_sport_children` — дочерние СПОРТ получают parent=None
    - `test_execute_deletes_sport_category` — СПОРТ удалена
    - `test_execute_deletes_other_root_categories` — другие корневые удалены с CASCADE
    - `test_products_under_sport_children_preserved` — товары в подкатегориях СПОРТ сохранены
    - `test_products_under_anchor_deleted` — **[F5]** товары привязанные к СПОРТ удаляются каскадно
    - `test_custom_root_name_argument` — работает с --root-name
    - `test_missing_root_category_warning` — предупреждение если якорная не найдена
    - `test_homepage_categories_not_broken` — **[F9]** HomepageCategory записи, привязанные к сохранённым категориям, работают
  - Notes: Использовать `call_command`, `@pytest.mark.django_db`, фабрики Category/Product

- [ ] **Task 5: Обновить тесты process_categories()**
  - File: `backend/apps/products/tests/unit/test_variant_import_migrated.py`
  - Action: Добавить тесты:
    - `test_process_categories_skips_root_categories` — корневые не создаются в БД
    - `test_process_categories_imports_sport_children_as_root` — дочерние СПОРТ → parent=None
    - `test_process_categories_imports_deep_descendants` — **[F4]** глубокие потомки (внуки, правнуки) якорной тоже импортируются
    - `test_process_categories_ignores_non_sport_root_descendants` — потомки НЕ-СПОРТ не импортируются
    - `test_process_categories_fallback_without_root_name` — если ROOT_CATEGORY_NAME=None, импортирует всё (тихо)
    - `test_process_categories_error_log_when_root_not_found` — **[F8]** если ROOT_CATEGORY_NAME задан но не найден → error лог + fallback + result["root_not_found"]
  - Notes: Использовать `@override_settings(ROOT_CATEGORY_NAME="СПОРТ")`

### Acceptance Criteria

- [ ] **AC1**: Given БД с категорией «СПОРТ» (parent=None) и её дочерними, when `cleanup_root_categories --dry-run`, then выводится инфо без изменений в БД
- [ ] **AC2**: Given БД с «СПОРТ» → дочерние, when `cleanup_root_categories --execute`, then дочерние СПОРТ получают parent=None
- [ ] **AC3**: Given после reparent, when cleanup завершён, then категория «СПОРТ» удалена из БД
- [ ] **AC4**: Given другие корневые категории (не СПОРТ), when cleanup, then они удалены вместе с потомками и товарами (CASCADE)
- [ ] **AC5**: Given товары привязаны к подкатегориям СПОРТ, when cleanup, then товары **не** удалены (категории сохранены)
- [ ] **AC6**: Given `categories_data` из parse_groups_xml с корневой СПОРТ, when `process_categories()`, then корневые категории **не** создаются в БД
- [ ] **AC7**: Given `categories_data` с children СПОРТ, when `process_categories()`, then дочерние СПОРТ создаются с parent=None
- [ ] **AC8**: Given потомки НЕ-СПОРТ корневых, when `process_categories()`, then они **не** импортируются
- [ ] **AC9**: Given ROOT_CATEGORY_NAME=None (не задан), when `process_categories()`, then импорт работает как раньше (fallback, тихо)
- [ ] **AC10**: Given ROOT_CATEGORY_NAME="СПОРТ" но СПОРТ отсутствует в XML, when `process_categories()`, then `logger.error()` + fallback + result содержит `root_not_found: True` [F8]
- [ ] **AC11**: Given HomepageCategory записи привязаны к подкатегориям СПОРТ, when cleanup, then записи сохранены и корректны [F9]
- [ ] **AC12**: Given cleanup завершён, when просмотр docker logs, then виден итоговый отчёт (reparented/deleted counts) [F7]

## Additional Context

### Dependencies

- Нет внешних зависимостей
- Требуется SSH-доступ к production для запуска cleanup command
- Порядок деплоя: cleanup → деплой нового кода

### Testing Strategy

- **Unit-тесты**: cleanup command (call_command + assertions), process_categories (с mock settings)
- **Ручное тестирование**: `cleanup_root_categories --dry-run` на production перед `--execute`
- **Верификация**: после cleanup проверить количество категорий и товаров через Django shell

### Notes

- **СПОРТ onec_id**: `3d148346-bd77-11e4-afc8-20cf3073dde3` (в тестовом XML)
- `common.models.Category` — **отдельная** модель, НЕ затрагивается
- `HomepageCategory` — proxy, общая таблица `categories`
- Товары привязаны к листовым подкатегориям, **не** к самой СПОРТ (подтверждено)
- Rollback не нужен — данные восстанавливаются полной выгрузкой из 1С
