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
# GitNexus — Code Intelligence (CLI)

Проект индексирован GitNexus как **FREESPORT**. Используй CLI-команды `npx gitnexus` для анализа кода, оценки влияния и навигации. MCP-сервер GitNexus может быть недоступен в некоторых IDE-сессиях, поэтому CLI — основной способ.

> **ВАЖНО:** Команды `npx gitnexus` запускай из подпапки (например, `backend/` или `scripts/`), не из корня проекта — см. правила работы с терминалом выше.

> Если индекс устарел, запусти `npx gitnexus analyze` перед использованием других команд.

## Always Do

- **ОБЯЗАТЕЛЬНО запускай impact-анализ перед редактированием любого символа.** Перед изменением функции, класса или метода выполни:
  ```bash
  npx gitnexus impact <symbolName> --direction upstream
  ```
  и сообщи пользователю blast radius (прямые callers, затронутые процессы, уровень риска).
- **ОБЯЗАТЕЛЬНО запускай detect-changes перед коммитом** для проверки, что изменения затрагивают только ожидаемые символы и потоки выполнения:
  ```bash
  npx gitnexus detect-changes --scope all
  ```
- **ОБЯЗАТЕЛЬНО предупреди пользователя**, если impact-анализ возвращает HIGH или CRITICAL риск.
- При исследовании незнакомого кода используй query для поиска потоков выполнения вместо grep:
  ```bash
  npx gitnexus query "<концепция или ключевое слово>"
  ```
- Для полного контекста конкретного символа (callers, callees, потоки выполнения):
  ```bash
  npx gitnexus context <symbolName>
  ```

## Never Do

- НИКОГДА не редактируй функцию, класс или метод без предварительного `npx gitnexus impact <symbolName> --direction upstream`.
- НИКОГДА не игнорируй предупреждения HIGH или CRITICAL риска из impact-анализа.
- НИКОГДА не переименовывай символы через find-and-replace — используй `npx gitnexus context <oldName>` для поиска всех ссылок, затем аккуратно переименовывай вручную.
- НИКОГДА не коммить изменения без `npx gitnexus detect-changes --scope all`.

## CLI-команды

| Команда | Назначение |
|---------|-----------|
| `npx gitnexus status` | Проверка актуальности индекса |
| `npx gitnexus analyze` | Построение/обновление индекса |
| `npx gitnexus impact <target> --direction upstream` | Blast radius: что сломается при изменении символа |
| `npx gitnexus detect-changes --scope all` | Маппинг git diff на символы и потоки выполнения |
| `npx gitnexus query "<запрос>"` | Поиск потоков выполнения по концепции |
| `npx gitnexus context <name>` | 360° контекст символа: callers, callees, процессы |
| `npx gitnexus cypher "<Cypher>"` | Прямые Cypher-запросы к графу знаний |
| `npx gitnexus list` | Список всех индексированных репозиториев |
| `npx gitnexus wiki` | Генерация документации из графа |

## Skill-файлы для подробных инструкций

| Задача | Skill-файл |
|--------|-----------|
| Архитектура / "Как работает X?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "Что сломается?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Трассировка багов / "Почему X не работает?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Рефакторинг / переименование | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| CLI-команды (analyze, status, clean, wiki) | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
