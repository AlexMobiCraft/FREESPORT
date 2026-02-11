---
title: '1C Import Archiving'
slug: '1c-import-archiving'
created: '2026-01-26'
status: 'review'
stepsCompleted: [1, 2, 3]
tech_stack: ['Python 3.10+', 'Django 4.2', 'stdlib zipfile', 'pathlib']
files_to_modify: ['backend/apps/products/management/commands/import_products_from_1c.py', 'backend/apps/products/utils/archiver.py', 'backend/tests/integration/test_1c_archiving.py', 'backend/freesport/settings/base.py']
code_patterns: ['Django Management Command', 'VariantImportProcessor pattern', 'Atomic file operations', 'Staging Strategy']
test_patterns: ['pytest with fs isolation (pyfakefs or tempdir)', 'integration test for command']
---

# Тех-Спек: Архивация импорта 1С

**Дата создания:** 2026-01-26

## Обзор (Overview)

### Постановка задачи (Problem Statement)

После успешной загрузки данных из 1С, исходные XML файлы остаются в папке импорта. Это может приводить к накоплению старых данных и путанице. Необходимо архивировать обработанные файлы.

### Решение (Solution)

Реализовать механизм архивирования, который после успешного импорта перемещает файлы из `import_1c/` в ZIP-архив в папке `arhiv/`. Имя архива должно содержать текущую дату и время. Исходная структура директорий в `import_1c/` должна сохраняться, но файлы должны быть удалены.

### Объем работ (Scope)

**Входит в объем (In Scope):**
- Модификация процесса завершения импорта 1С.
- Создание ZIP-архива с именем `YYYY-MM-DD_HH-MM-SS.zip`.
- Использование стратегии "Атомарное перемещение" (сначала в stading, потом в архив).
- Сохранение архива в директорию, указанную в `ONEC_ARCHIVE_DIR`.
- Очистка файлов в `import_1c/` с сохранением структуры папок.

**Не входит в объем (Out of Scope):**
- Изменения в логике парсинга XML.
- Архивация при ошибках импорта (если не оговорено иное).

## Контекст разработки (Context for Development)

### Паттерны кодовой базы

*   `VariantImportProcessor` используется для бизнес-логики импорта.
*   `Command.handle` управляет потоком выполнения.
*   `ONEC_DATA_DIR` определён в `settings.base.py`.

### Файлы для справки

| Файл | Назначение |
| ---- | ------- |
| `backend/apps/products/management/commands/import_products_from_1c.py` | Точка входа команды. |
| `backend/freesport/settings/base.py` | Конфигурация путей (`ONEC_DATA_DIR`, `ONEC_ARCHIVE_DIR`). |
| `backend/apps/products/utils/archiver.py` | Новая утилита для архивации. |

### Технические решения

*   **Стратегия (F2 - Atomic Move)**:
    1.  Сначала переместить файлы из `import_1c` во временную папку (staging) внутри `arhiv/temp_UUID`. Это минимизирует время блокировки `import_1c`.
    2.  Создать архив из staging папки.
    3.  Удалить staging папку после успешной архивации.
*   **Пути (F5)**: Добавить `ONEC_ARCHIVE_DIR` в `settings.base.py` (default: `ONEC_DATA_DIR/../arhiv`).
*   **I/O (F4)**: Использовать только `pathlib` (`Path.unlink`, `Path.rglob`, `Path.rename`).
*   **Timezone (F3)**: Использовать `django.utils.timezone.now()` для именования архива.
*   **Memory (F6)**: Использовать стандартный `zipfile.write(filename)`, который читает файл потоково, не загружая в RAM. Для больших файлов (>500MB) это безопасно.
*   **Очистка (F7)**: Перемещение файлов автоматически очистит их из источника. Пустые папки в источнике НЕ трогать (оставлять).
*   **Ошибки (F8)**: Ловить специфичные исключения `OSError`, `zipfile.LargeZipFile`. Не перехватывать глобальный `Exception` без нужды.

## План реализации (Implementation Plan)

### Задачи (Tasks)

- [ ] Задача 1: Добавить настройки путей
  - Файл: `backend/freesport/settings/base.py`
  - Действие:
    - Добавить `ONEC_ARCHIVE_DIR = os.environ.get("ONEC_ARCHIVE_DIR", str(BASE_DIR / "data" / "arhiv"))`
    - Убедиться, что `ONEC_DATA_DIR` тоже определен.

- [ ] Задача 2: Создать утилиту архивации (с staging)
  - Файл: `backend/apps/products/utils/archiver.py`
  - Действие: Реализовать функцию `archive_import_files(source_dir: Path, archive_root: Path, dry_run: bool = False) -> str | None`.
  - Заметки:
    - **Logic**:
      1. Генерировать имя архива: `%Y-%m-%d_%H-%M-%S.zip` (используя `timezone.now()`).
      2. **Dry Run (F9)**: Если `dry_run=True`:
         - Логировать: "Would move files X, Y, Z to staging".
         - Логировать: "Would create archive at {path}".
         - Проверить доступность путей (exists/mkdir).
         - Вернуть предполагаемый путь (или None).
         - НЕ перемещать и НЕ архивировать.
      3. **Staging**: Создать `staging_dir = archive_root / "temp_{uuid}"`.
      4. **Move**: Перебирать файлы в `source_dir` (`rglob('*')`). Если файл:
         - Вычислить относительный путь.
         - Создать структуру папок в `staging_dir`.
         - **Переместить** файл (`path.rename()`) в staging.
         - *Примечание*: Исходные пустые папки остаются в `source_dir`.
      5. **Zip**: Создать zip из `staging_dir`. Использовать `zipfile.write(file_path, arcname=rel_path)`.
      6. **Cleanup**: Удалить `staging_dir` (`shutil.rmtree`).
    - Использовать `pathlib`.
    - Ловить `OSError`, `zipfile.LargeZipFile`.

- [ ] Задача 3: Интегрировать архиватор в команду импорта
  - Файл: `backend/apps/products/management/commands/import_products_from_1c.py`
  - Действие: Изменить метод `handle`.
  - Заметки:
    - Импортировать настройки и архиватор.
    - В конце `try` блока (после success message):
      - Получить `archive_dir` из настроек.
      - Вызвать `archive_import_files(data_dir, archive_dir, dry_run=dry_run)`.
      - Логировать результат.

- [ ] Задача 4: Создать интеграционные тесты
  - Файл: `backend/tests/integration/test_1c_archiving.py`
  - Действие: Создать тесты.
  - Заметки:
    - Тест 1: Успешная архивация. Проверить, что файлы исчезли из source, появились в ZIP, пустые папки остались в source.
    - Тест 2: **Content Verification (F10)**. Распаковать полученный ZIP во временную папку и сравнить список файлов (имена) с ожидаемым.
    - Тест 3: Dry Run. Файлы остались на месте, архив не создан.
    - Тест 4: Проверка именования (timezone).

### Критерии приемки (Acceptance Criteria)

- [ ] AC 1: Атомарность и целостность
  - Дано: импорт завершен.
  - Когда: происходит архивация.
  - Тогда: файлы сначала пропадают из `import_1c` (перемещаются), и только потом появляются в архиве.
  - И: В `import_1c` остается чистое дерево пустых каталогов.

- [ ] AC 2: Пути и настройки
  - Дано: настройки `ONEC_ARCHIVE_DIR` заданы.
  - Когда: запускается команда.
  - Тогда: архив сохраняется именно по этому пути.

- [ ] AC 3: Валидация контента
  - Дано: Архив создан.
  - Когда: его распаковывают.
  - Тогда: Список файлов и папок внутри идентичен исходному набору данных.

## Дополнительный контекст

### Зависимости (Dependencies)

- `pathlib`, `shutil`, `zipfile`, `django.conf.settings`, `django.utils.timezone`.

### Стратегия тестирования (Testing Strategy)

- Использовать `tmp_path` в тестах.
- Проверять отсутствие блокировок файлов (косвенно, через rename).
