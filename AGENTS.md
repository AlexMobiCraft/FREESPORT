# Руководство для AI-агентов проекта FREESPORT

- Отвечай и веди документацию исключительно на русском языке
- communication_language: Russian
- document_output_language: Russian

## Кастомные маркеры pytest для выборочного запуска тестов

В проекте используются кастомные маркеры pytest для классификации и выборочного запуска тестов:

- **`unit`**: Юнит-тесты бэкенда (модульные тесты)
- **`integration`**: Интеграционные тесты
- **`data_dependent`**: Тесты, зависящие от внешних данных

### Примеры использования:

```bash
# Запуск только unit-тестов
pytest -m unit

# Запуск только интеграционных тестов
pytest -m integration

# Запуск тестов, не зависящих от внешних данных
pytest -m "not data_dependent"

# Запуск всех тестов с покрытием
pytest -v --cov=apps --cov-report=term-missing
```

## Команды Makefile для работы с документацией

Проект включает специализированные команды для управления документацией:

### Валидация и синхронизация документации:

- **`docs-validate`**: Полная валидация документации

  ```bash
  make docs-validate
  ```

- **`docs-sync-api`**: Сверка API (код ↔ документация)

  ```bash
  make docs-sync-api
  ```

- **`docs-sync-decisions`**: Сверка решений (docs ↔ код)

  ```bash
  make docs-sync-decisions
  ```

- **`docs-sync-all`**: Выполнить все синхронизации
  ```bash
  make docs-sync-all
  ```

### Проверка документации:

- **`docs-check-links`**: Проверка кросс-ссылок

  ```bash
  make docs-check-links
  ```

- **`docs-check-api`**: Проверка покрытия API

  ```bash
  make docs-check-api
  ```

- **`docs-search-obsolete`**: Поиск устаревших терминов
  ```bash
  make docs-search-obsolete
  ```

### Управление индексами:

- **`docs-update-index`**: Обновление индекса документации

  ```bash
  make docs-update-index
  ```

- **`docs-update-index-apply`**: Обновление индексов с записью
  ```bash
  make docs-update-index-apply
  ```

## Конфигурация ESLint и Prettier для frontend

Конфигурация **ESLint** и **Prettier** для frontend является встроенной в **Next.js** и не требует отдельных конфигурационных файлов. Это означает:

- ESLint и Prettier уже преднастроены в проекте Next.js
- Правила форматирования и линтинга применяются автоматически при сборке
- Для форматирования кода используются команды из Makefile:
  - `make format` - форматирование через Docker
  - `make format-fast` - быстрое форматирование
  - `make format-local` - локальное форматирование (требует venv)

## Дополнительные важные замечания

### Тестирование:

- Для запуска unit-тестов используется команда `make test-unit`
- Для запуска интеграционных тестов используется команда `make test-integration`
- Все тесты запускаются через `make test` с использованием Docker-контейнеров

### Структура тестов:

- Юнит-тесты располагаются внутри каждого Django-приложения
- Интеграционные тесты находятся в директории `/backend/tests`
- Тесты для компонентов frontend находятся рядом с ними в директориях `__tests__`

### Работа с окружением:

- Все команды Makefile работают через Docker для обеспечения консистентности окружения
- Локальное выполнение возможно при наличии настроенного виртуального окружения (venv)

## Работа в среде Windows и Terminal

### PowerShell Chaining

В среде Windows PowerShell для объединения команд используй `;` вместо `&&`.
_Например:_ `git add .; git commit -m "..."; git push`

### Правила работы с терминалом и SSH (защита от зависаний)

- **Запуск из подпапок**: Чтобы избежать зависаний терминала из-за индексации Git/Oh-My-Posh в корне проекта, ВСЕГДА запускай команды из подпапки (например, `scripts/` или `backend/`). Git автоматически найдет корень проекта.
- **SSH Authentication**: Используй только SSH-ключи через `ssh-agent`. Избегай интерактивных запросов пароля, так как они приводят к зависанию агента.
- **Production Git Updates**: При обновлении кода на продакшен-сервере НИКОГДА не используй `git pull`. ВСЕГДА используй: `git fetch origin main; git reset --hard origin/main`, чтобы избежать конфликтов и ошибки `divergent branches`.
- **Session Hygiene**: Если команды начинают выполняться медленно, используй опцию "Close Completely" при перезагрузке Antigravity, чтобы очистить зомби-процессы.
- **Command Shell**: Для простых системных задач (echo, dir, move) используй `cmd /c` вместо PowerShell, так как он запускается быстрее.

## Правила разработки Frontend

- **ВАЖНО**: После внесения изменений во фронтенд-код (`frontend/src/`), необходимо ПЕРЕЗАПУСТИТЬ Docker-контейнер, чтобы изменения отразились в браузере:

  ```bash
  # Обычный перезапуск (для проблем с hot-reload)
  docker compose --env-file .env -f docker/docker-compose.yml restart frontend

  # Полная пересборка (при изменении зависимостей или конфига)
  docker compose --env-file .env -f docker/docker-compose.yml up -d --build frontend
  ```

## Разработка и тестирование Backend

- **Локальное тестирование**: Для запуска `pytest` локально необходимо предварительно инициировать (активировать) виртуальное окружение.
  _Пример (в PowerShell из корня проекта):_
  ```powershell
  .\backend\venv\Scripts\Activate.ps1
  pytest <путь_к_тесту>
  ```
- **Тестирование через Docker**: При необходимости запустить тесты внутри Docker-контейнера:
  _Пример команды:_
  `docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest <путь_к_тесту>`

## Справочная информация

Справочная информация о проекте (архитектура, стек, команды запуска и тесты) находится в файле [PROJECT_INFO.md](file:///c:/Users/tkachenko/DEV/FREESPORT/docs/PROJECT_INFO.md).

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **FREESPORT** (8488 symbols, 13895 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/FREESPORT/context` | Codebase overview, check index freshness |
| `gitnexus://repo/FREESPORT/clusters` | All functional areas |
| `gitnexus://repo/FREESPORT/processes` | All execution flows |
| `gitnexus://repo/FREESPORT/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
