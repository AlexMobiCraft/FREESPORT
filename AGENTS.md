# Руководство для AI-агентов проекта FREESPORT

- Отвечай и веди документацию исключительно на русском языке
- communication_language: Russian
- document_output_language: Russian

## Кастомные маркеры pytest для выборочного запуска тестов

В проекте используются кастомные маркеры pytest для классификации и выборочного запуска тестов:

- **`unit`**: Юнит-тесты бэкенда (модульные тесты)
- **`integration`**: Интеграционные тесты
- **`data_dependent`**: Тесты, зависящие от внешних данных

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

## Критические правила и runbook'и

Постоянные инварианты и продакшен-инструкции вынесены в отдельные rule-файлы:

- [`.windsurf/rules/security-and-git.md`](file:///c:/Users/1/DEV/FREESPORT/.windsurf/rules/security-and-git.md) — запрет прямого пуша в public remote, обновление продакшена.
- [`.windsurf/rules/production-operations.md`](file:///c:/Users/1/DEV/FREESPORT/.windsurf/rules/production-operations.md) — типовые инциденты: 502, Server Action mismatch, restart nginx.
- [`.windsurf/rules/order-numbering.md`](file:///c:/Users/1/DEV/FREESPORT/.windsurf/rules/order-numbering.md) — форматы мастер/субзаказов и поиск в админке.
- [`.windsurf/rules/1c-import-diagnostics.md`](file:///c:/Users/1/DEV/FREESPORT/.windsurf/rules/1c-import-diagnostics.md) — диагностика ошибок полной выгрузки 1С.

## Справочная информация

Справочная информация о проекте (архитектура, стек, команды запуска и тесты) находится в файле [PROJECT_INFO.md](file:///c:/Users/tkachenko/DEV/FREESPORT/docs/PROJECT_INFO.md).

## GitNexus — Code Intelligence (CLI)

> **Авторитетный источник правил GitNexus — этот раздел, а не автогенерируемый блок ниже.**
> MCP-сервер `gitnexus` отключён намеренно: его команда `npx -y gitnexus@latest mcp` падает с
> `npm error Invalid Version`, инструменты `gitnexus_*` в сессии не появляются. Всё — через Bash.
> `npx gitnexus analyze` перезапишет блок между маркерами MCP-версией; **игнорируй её** — этот раздел вне маркеров и переживает регенерацию.

Проект проиндексирован GitNexus как **FREESPORT**. Используй CLI, чтобы понимать код,
оценивать последствия правок и безопасно навигировать.

> Если `npx gitnexus status` показывает `stale` — попроси пользователя выполнить `! npx gitnexus analyze`.

### Обязательно

- **Перед изменением любого символа** (функции, класса, метода) — `npx gitnexus impact <symbol> --direction upstream`;
  сообщи пользователю blast radius: прямые вызывающие, затронутые процессы, уровень риска.
- **Перед коммитом** — `npx gitnexus detect-changes --scope all`: убедись, что затронуты только ожидаемые символы и потоки.
- **Предупреди пользователя**, если impact вернул `"risk": "HIGH"` или `"CRITICAL"`, — до внесения правок.
- **Для исследования незнакомого кода** — `npx gitnexus query "<концепция>"` вместо grep по всей базе.
- **Полный контекст символа** (вызывающие, вызываемые, процессы) — `npx gitnexus context <symbol>`.

### Запрещено

- НЕ редактировать функцию/класс/метод, не выполнив `impact`.
- НЕ игнорировать риск HIGH или CRITICAL.
- НЕ переименовывать символы через find-and-replace. Команды `rename` в CLI нет:
  собери все места через `impact` и `context`, затем правь точечно и осознанно.
- НЕ коммитить без `detect-changes`.
- НЕ вызывать инструменты `gitnexus_*` — MCP-сервер отключён, вызов гарантированно провалится.

### Команды

| Задача | Команда |
|---|---|
| Статус и свежесть индекса | `npx gitnexus status` |
| Переиндексация | `npx gitnexus analyze` |
| Blast radius | `npx gitnexus impact <symbol> [--direction upstream\|downstream] [--depth N] [--include-tests]` |
| Контекст символа | `npx gitnexus context <symbol> [--file <path>] [--content]` |
| Поиск потоков выполнения | `npx gitnexus query "<концепция>" [--limit N] [--goal <text>]` |
| Символы, затронутые изменениями | `npx gitnexus detect-changes [--scope unstaged\|staged\|all\|compare] [--base-ref <ref>]` |
| Произвольный запрос к графу | `npx gitnexus cypher "<query>"` |

Вызывай без тега версии: `npx -y gitnexus@latest ...` падает на резолве `@latest`.
`impact`, `context`, `query`, `cypher` печатают JSON; `status` и `detect-changes` — текст.

### Ограничения CLI

- Команды `rename` нет — переименование только вручную по списку из `impact`/`context`.
- MCP-ресурсов (`gitnexus://repo/...`) нет; их заменяют `query`, `context` и `cypher`.
- `npx gitnexus wiki` требует LLM-провайдер и API-ключ — это не локальная бесплатная команда.
- Символы, добавленные после последней индексации, не находятся: `context` вернёт
  `{"error": "Symbol ... not found"}`. Это признак устаревшего индекса, а не отсутствия кода.

### Skill-файлы

| Задача | Файл |
|---|---|
| Понять архитектуру / «Как работает X?» | `.windsurf/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / «Что сломается, если поменять X?» | `.windsurf/skills/gitnexus-impact-analysis/SKILL.md` |
| Отладка / «Почему X падает?» | `.windsurf/skills/gitnexus-debugging/SKILL.md` |
| Переименование и рефакторинг | `.windsurf/skills/gitnexus-refactoring/SKILL.md` |
| Справочник по командам и схеме графа | `.windsurf/skills/gitnexus-guide/SKILL.md` |
| Индекс, статус, очистка, wiki | `.windsurf/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **FREESPORT** (9573 symbols, 15745 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
