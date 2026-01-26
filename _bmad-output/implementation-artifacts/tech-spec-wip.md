---
title: '1C Import Archiving'
slug: '1c-import-archiving'
created: '2026-01-26'
status: 'in-progress'
stepsCompleted: [1]
tech_stack: []
files_to_modify: []
code_patterns: []
test_patterns: []
---

# Tech-Spec: 1C Import Archiving

**Created:** 2026-01-26

## Overview

### Problem Statement

После успешной загрузки данных из 1С, исходные XML файлы остаются в папке импорта. Это может приводить к накоплению старых данных и путанице. Необходимо архивировать обработанные файлы.

### Solution

Реализовать механизм архивирования, который после успешного импорта перемещает файлы из `import_1c/` в ZIP-архив в папке `arhiv/`. Имя архива должно содержать текущую дату и время. Исходная структура директорий в `import_1c/` должна сохраняться, но файлы должны быть удалены.

### Scope

**In Scope:**
- Модификация процесса завершения импорта 1С.
- Создание ZIP-архива с именем `YYYY-MM-DD_HH-MM-SS.zip`.
- Сохранение архива в `backend/data/arhiv/` (предположительно).
- Очистка файлов в `backend/data/import_1c/` с сохранением структуры папок.

**Out of Scope:**
- Изменения в логике парсинга XML.
- Архивация при ошибках импорта (если не оговорено иное).

## Context for Development

### Codebase Patterns

*   Используется `VariantImportProcessor` для управления процессом.
*   `FileStreamService` управляет файлами сессии (возможно, пригодятся утилиты, но здесь работа с исходной директорией `ONEC_DATA_DIR`).

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `backend/apps/products/management/commands/import_products_from_1c.py` | Command entry point, `finalize_session` call site |
| `backend/config/settings/base.py` | `ONEC_DATA_DIR` definition |

### Technical Decisions

*   Использовать стандартную библиотеку `zipfile` или `shutil`.
*   Архивация должна быть атомарной (или максимально надежной) операцией в конце `handle()`.

## Implementation Plan

### Tasks

(TBD in Step 3)

### Acceptance Criteria

(TBD in Step 3)

## Additional Context

### Dependencies

None

### Testing Strategy

Use `dry-run` or specific test flags to verify structure creation without destroying data initially?
Need unit/integration test for the archiver function.

### Notes

Assumption: `ONEC_DATA_DIR` is the source. Target is `../arhiv` relative to it? Or `backend/data/arhiv` explicitly?
