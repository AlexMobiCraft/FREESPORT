# Scripts для FREESPORT Platform

Утилиты для автоматизации разработки и валидации документации.

## 📚 Скрипты валидации документации

Все скрипты поддерживают общий файл исключений `scripts/docs_exclude_patterns.txt`.
В нём перечисляются пути (относительно корня репозитория), которые следует пропускать при проверках.
Дополнительно можно передать собственные шаблоны через параметр `--exclude` — они объединятся с глобальным списком.

### docs_validator.py

Основной скрипт валидации документации. Проверяет качество, актуальность и консистентность документов.

**Возможности:**

- ✅ Проверка кросс-ссылок между документами
- ✅ Валидация покрытия API endpoints документацией
- ✅ Поиск устаревших терминов и TODO
- ✅ Проверка структуры документов (наличие обязательных секций)
- ✅ Проверка актуальности дат

**Использование:**

```powershell
# Полная валидация
python scripts/docs_validator.py validate

# Исключить каталоги legacy и миграций
python scripts/docs_validator.py validate --exclude docs/legacy/** backend/**/migrations/**

# Только поиск устаревших терминов
python scripts/docs_validator.py obsolete

# Только проверка кросс-ссылок
python scripts/docs_validator.py cross-links

# Только проверка покрытия API
python scripts/docs_validator.py api-coverage
```

**Через Makefile:**

```powershell
make docs-validate          # Полная валидация
make docs-search-obsolete   # Поиск устаревших терминов
make docs-check-api         # Проверка покрытия API
```

**Пример вывода:**

```
🔍 Проверка кросс-ссылок между документами
✅ Все кросс-ссылки валидны (56 файлов проверено)

🔍 Поиск устаревших терминов и временных заглушек
⚠️  ПРЕДУПРЕЖДЕНИЕ: Найдено 12 устаревших терминов

📊 ИТОГОВЫЙ ОТЧЕТ ВАЛИДАЦИИ
Статистика:
  ❌ Ошибок: 0
  ⚠️  Предупреждений: 2
  ✅ Успешных проверок: 3
```

---

## 📦 Работа с импортом 1С

### sync_import_data.ps1

PowerShell скрипт для копирования файлов `data/import_1c` на сервер разработки.

**Использование:**

```powershell
# Копирование данных на сервер по умолчанию
pwsh .\scripts\sync_import_data.ps1

# Указание альтернативного пути и сервера
pwsh .\scripts\sync_import_data.ps1 -User alex -IP 192.168.1.140 -RemoteDataPath "~/projects/FREESPORT/data/import_1c"
```

**Что делает скрипт:**

- **Подготавливает ключ SSH** через `Start-SshAgentIfNeeded()`.
- **Гарантирует наличие директории** на стороне сервера функцией `Ensure-RemoteDirectory()`.
- **Копирует содержимое каталога** `data/import_1c` recursive через `scp` в указанную директорию.

После синхронизации можно запускать `run_catalog_import.ps1` для импорта данных.

### run_catalog_import_with_backup.ps1

PowerShell-скрипт для запуска импорта каталога из 1С внутри Docker Compose с автоматическим созданием бэкапа базы данных.

**Использование:**

```powershell
pwsh .\scripts\run_catalog_import_with_backup.ps1 `
  -ComposeFile "docker-compose.yml" `
  -DataDir "/app/data/import_1c" `
  -ChunkSize 500 `
  -BackupOutput "backend/backup_db/backup_$(Get-Date -Format yyyyMMdd_HHmmss).sql"
```

**Основные параметры:**

- **ComposeFile** — путь к `docker-compose` файлу (по умолчанию `docker-compose.test.yml`).
- **DataDir** — директория с XML-файлами внутри контейнера backend.
- **ChunkSize** — размер пакета для bulk-операций команды импорта.
- **BackupOutput** — путь к файлу резервной копии (если не указан, используется стандартный каталог `backend/backup_db`).
- **SkipMigrate / SkipBackup / SkipImport** — переключатели для пропуска соответствующих шагов.
- **ImportArgs** — дополнительный массив аргументов, который передаётся команде `import_products_from_1c` (например, `@("--file-type", "goods")`).

**Последовательность действий:**

- **Запускает сервисы** из указанного `docker-compose` файла с ожиданием Healthcheck.
- **Применяет миграции**, если не передан флаг `-SkipMigrate`.
- **Создаёт бэкап** через `python manage.py backup_db`, если не указан `-SkipBackup`.
- **Запускает импорт** каталога с отключением повторного бэкапа внутри команды (`--skip-backup`).
- **Выводит прогресс** по шагам импорта и завершает работу с итоговым статусом.

---

## 🚀 Обновление серверного кода

### update_server_code.ps1

PowerShell скрипт для актуализации удалённого окружения разработки (`ssh`, `git pull`, синхронизация `.env`, перезапуск `docker compose`).

**Использование:**

```powershell
# Базовый запуск (используется текущая git-ветка)
pwsh .\\scripts\\update_server_code.ps1

# Явный выбор ветки и локального .env
pwsh .\\scripts\\update_server_code.ps1 -Branch develop -EnvFileLocal "backend/.env.test"

# Настройка другого сервера
pwsh .\\scripts\\update_server_code.ps1 -User alex -IP 192.168.1.140 -ProjectPathRemote "~/projects/FREESPORT"
```

**Переменная `FREESPORT_PROJECT_ROOT`:**

- **Локально** переменная не требуется — используется дефолтный путь `C:/Users/38670/DEV_WEB/FREESPORT` из `docker-compose.test.yml`.
- **При удалённом запуске** скрипт автоматически устанавливает `FREESPORT_PROJECT_ROOT` по значению `-ProjectPathRemote` (например, `/home/alex/FREESPORT`) на время перезапуска `docker compose`.
- **При ручном использовании Docker context** можно задать переменную самостоятельно:

```powershell
$env:FREESPORT_PROJECT_ROOT="/home/alex/FREESPORT"
docker --context freesport-remote compose -f docker-compose.test.yml up -d
Remove-Item Env:FREESPORT_PROJECT_ROOT
```

---

### docs_link_checker.py

Детальная проверка всех ссылок в markdown документах.

**Возможности:**

- ✅ Проверка локальных ссылок на файлы
- ✅ Проверка якорей (anchors) в ссылках
- ✅ Проверка внешних URL (опционально)
- ✅ Генерация отчета в markdown формате

**Использование:**

```powershell
# Базовая проверка
python scripts/docs_link_checker.py

# С проверкой внешних URL (медленно)
python scripts/docs_link_checker.py --external

# С сохранением отчета
python scripts/docs_link_checker.py --report docs/link-check-report.md

# С исключением раздела решений
python scripts/docs_link_checker.py --exclude docs/decisions/**
```

**Через Makefile:**

```powershell
make docs-check-links
```

**Пример вывода:**

```
🔗 ПРОВЕРКА КРОСС-ССЫЛОК В ДОКУМЕНТАЦИИ
Найдено 56 markdown файлов

📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ
Проверено файлов: 56
Проверено ссылок: 342
Ошибок: 3
Предупреждений: 1

❌ ОШИБКИ:
1. stories/epic-3/3.2.2.conflict-resolution.md:60
   Ссылка: [SyncConflict](docs/architecture/02-data-models.md#syncconflict)
   Ошибка: Якорь '#syncconflict' не найден в 02-data-models.md
```

---

### docs_index_generator.py

Автоматическая генерация и обновление индексов документации.

**Возможности:**

- ✅ Обновление главного индекса `docs/index.md`
- ✅ Генерация README.md в каждой категории
- ✅ Автоматическое извлечение заголовков и описаний
- ✅ Подсчет статистики документации

**Использование:**

```powershell
# Обновить все индексы
python scripts/docs_index_generator.py

# Показать изменения без записи
python scripts/docs_index_generator.py --dry-run

# Только показать статистику
python scripts/docs_index_generator.py --stats

# Пропустить раздел legacy
python scripts/docs_index_generator.py --exclude docs/legacy/**
```

**Через Makefile:**

```powershell
make docs-update-index
```

**Пример вывода:**

```
📝 ОБНОВЛЕНИЕ ГЛАВНОГО ИНДЕКСА
✅ Обновлен: docs/index.md

📚 ОБНОВЛЕНИЕ README В КАТЕГОРИЯХ
✅ Создан/обновлен: stories/epic-3/README.md
✅ Создан/обновлен: decisions/README.md

📊 СТАТИСТИКА ДОКУМЕНТАЦИИ
Общая информация:
  Всего файлов: 72
  Общий размер: 1247.3 KB
  Дата обновления: 12.10.2025

По категориям:
  architecture: 22 файлов
  decisions: 10 файлов
  stories: 37 файлов
```

---

## 🔧 Скрипты тестирования

### run-tests-docker.ps1

PowerShell скрипт для запуска тестов в Docker контейнерах.

**Использование:**

```powershell
# Запуск всех тестов
.\scripts\run-tests-docker.ps1

# Только unit-тесты
.\scripts\run-tests-docker.ps1 -TestType unit

# Только integration-тесты
.\scripts\run-tests-docker.ps1 -TestType integration
```

---

## 🚀 Интеграция в workflow

### Pre-commit hook

Добавьте в `.git/hooks/pre-commit`:

```bash
#!/bin/sh
# Валидация документации перед коммитом

echo "🔍 Проверка документации..."
python scripts/docs_validator.py cross-links || {
    echo "❌ Документация содержит ошибки!"
    echo "Запустите: make docs-validate"
    exit 1
}

echo "✅ Документация валидна"
```

### GitHub Actions

Пример workflow для CI/CD:

```yaml
name: Documentation Validation

on:
  pull_request:
    paths:
      - "docs/**"
      - "backend/**"

jobs:
  validate-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Validate documentation
        run: |
          python scripts/docs_validator.py validate
          python scripts/docs_link_checker.py
```

---

## 📋 Требования

**Python:** 3.8+

**Зависимости:** Нет (используются только стандартные библиотеки)

---

## 🐛 Troubleshooting

### Ошибка: "Директория docs не найдена"

Убедитесь, что запускаете скрипт из корня проекта:

```powershell
cd c:\Users\38670\DEV_WEB\FREESPORT
python scripts/docs_validator.py validate
```

### Ошибка кодировки на Windows

Скрипты используют UTF-8. Если возникают проблемы:

```powershell
$env:PYTHONIOENCODING="utf-8"
python scripts/docs_validator.py validate
```

### Цвета не отображаются в PowerShell

Используйте Windows Terminal или добавьте в PowerShell:

```powershell
$env:TERM="xterm-256color"
```

---

## 📚 Дополнительная информация

- **Workflow документации:** `.windsurf/workflows/docs-workflow.md`
- **Makefile команды:** `make help`
- **Архитектура проекта:** `docs/architecture/`

---

**Последнее обновление:** 12.10.2025
