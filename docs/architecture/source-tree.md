# Структура исходного кода

Этот документ описывает структуру каталогов и файлов проекта, их назначение и ключевые компоненты.

## Общая структура

```text
freesport/
│
├── .github/                    # Настройки GitHub Actions
│   └── workflows/              # CI/CD пайплайны
│       ├── backend-ci.yml      # CI для бэкенда
│       ├── frontend-ci.yml     # CI для фронтенда
│       └── main.yml            # Основной пайплайн (деплой)
│
├── backend/                    # Django бэкенд
│   ├── apps/                   # Django приложения
│   │   ├── cart/               # Корзина покупок
│   │   ├── common/             # Общие компоненты
│   │   ├── orders/             # Заказы
│   │   ├── pages/              # Статические страницы
│   │   ├── products/           # Товары и каталог
│   │   └── users/              # Пользователи и аутентификация
│   ├── freesport/              # Основные настройки проекта
│   │   ├── settings/           # Настройки для разных окружений
│   │   ├── celery.py           # Конфигурация Celery
│   │   ├── urls.py             # Главный роутинг
│   │   ├── asgi.py             # ASGI конфигурация
│   │   └── wsgi.py             # WSGI конфигурация
│   ├── tests/                  # Каталог с тестами
│   │   ├── unit/               # Юнит-тесты
│   │   ├── integration/        # Интеграционные тесты
│   │   ├── functional/         # Функциональные тесты
│   │   ├── performance/        # Тесты производительности
│   │   ├── legacy/             # Устаревшие тесты
│   │   └── fixtures/           # Фикстуры для тестов
│   ├── manage.py               # Утилита для управления Django
│   └── requirements.txt        # Зависимости Python
│
├── frontend/                   # Next.js фронтенд
│   ├── public/                 # Статические файлы
│   ├── src/                    # Исходный код фронтенда
│   │   ├── app/                # Страницы (Next.js App Router)
│   │   ├── components/         # React компоненты
│   │   ├── hooks/              # Кастомные React хуки
│   │   ├── services/           # Сервисы для работы с API
│   │   ├── stores/             # State management
│   │   └── types/              # TypeScript типы
│   ├── package.json            # Зависимости Node.js
│   └── next.config.js          # Конфигурация Next.js
│
├── docs/                       # Общая документация проекта
│   ├── architecture/           # Архитектурные решения (42 документа)
│   │   └── ai-implementation/  # Детали реализации AI
│   ├── database/               # Схемы и миграции БД
│   ├── decisions/              # ADR (11 документов)
│   ├── epics/                  # Описание эпиков (4 документа)
│   ├── implementation/         # Детали реализации (2 документа)
│   ├── prd/                    # PRD и спецификации (7 документов)
│   ├── qa/                     # Документация по тестированию (20 документов)
│   ├── releases/               # Информация о релизах
│   ├── stories/                # User Stories (37 документов)
│   ├── arhiv/                  # Архивные документы
│   └── [корневые файлы]        # Brief.md, PRD.md, api-spec.yaml и др.
│
├── scripts/                    # Скрипты автоматизации
│   ├── run-tests-docker.ps1    # Запуск тестов в Docker (PowerShell)
│   ├── ssh_server.ps1          # Скрипт для SSH
│   └── update_server_code.ps1  # Скрипт обновления кода на сервере
│
├── docker/                     # Docker конфигурации
│   ├── nginx/                  # Конфигурация Nginx
│   └── init-db.sql/            # Скрипты инициализации БД
│
├── .bmad-core/                 # BMad методология
│   ├── agents/                 # Определения агентов
│   ├── agent-teams/            # Команды агентов
│   ├── checklists/             # Чек-листы
│   └── data/                   # Данные методологии
│
├── .windsurf/                  # Windsurf workflows
│   └── workflows/              # Рабочие процессы (11 файлов)
│
├── docker-compose.yml          # Конфигурация Docker Compose (production)
├── docker-compose.test.yml     # Конфигурация Docker Compose (тесты)
├── Makefile                    # Команды для управления проектом
├── README.md                   # Основная информация о проекте
├── pyrightconfig.json          # Конфигурация Pyright
├── pytest.ini                  # Конфигурация pytest
└── .gitignore                  # Файлы, исключенные из Git
```

## Ключевые каталоги

### `backend/`

Бэкенд, построенный на Django. Содержит всю серверную логику, API и управление базой данных.

- **`apps/`**: Модульная структура, где каждое приложение отвечает за свою бизнес-логику:
  - `users/` — пользователи и аутентификация
  - `products/` — товары и каталог
    - `services/` — сервисы для импорта и обработки данных (parser.py, processor.py)
    - `management/commands/` — Django management команды для импорта данных
  - `orders/` — заказы
  - `cart/` — корзина покупок
  - `common/` — общие компоненты
  - `pages/` — статические страницы
- **`backend/`**: Устаревшая папка с настройками (используется `freesport/`).
- **`freesport/`**: Ядро Django-проекта с основными настройками (`settings/`, `urls.py`, `asgi.py`, `wsgi.py`).
- **`tests/`**: Набор тестов для проверки корректности работы API и бизнес-логики:
  - `unit/` — юнит-тесты
  - `integration/` — интеграционные тесты
    - `test_management_commands/` — тесты для management команд
  - `functional/` — функциональные тесты
  - `performance/` — тесты производительности
  - `legacy/` — устаревшие тесты
  - `fixtures/` — фикстуры для тестов

### `frontend/`

Фронтенд, построенный на Next.js. Отвечает за пользовательский интерфейс и взаимодействие с API.

- **`src/app/`**: Страницы приложения (Next.js App Router).
- **`src/components/`**: Переиспользуемые UI-компоненты (кнопки, формы, карточки товаров).
- **`src/services/`**: Сервисы для работы с API.
- **`src/stores/`**: Хранилища состояния (state management).
- **`src/types/`**: TypeScript типы и интерфейсы.
- **`src/hooks/`**: Кастомные React хуки.

### `docs/`

Централизованное хранилище всей документации проекта.

- **`architecture/`**: Описание архитектуры (42 документа), включая:
  - Нумерованные документы (01-20): введение, модели данных, API, компоненты, tech stack, архитектура системы, интеграции, workflows, БД, тестирование, безопасность, обработка ошибок, мониторинг, CI/CD, деплой, AI, производительность, B2B, окружение разработки, интеграция с 1C
  - `ai-implementation/` — детали реализации AI-функционала
  - Дополнительные документы: coding standards, tech stack, source tree, index и др.
- **`database/`**: ER-диаграммы, описание моделей данных.
- **`decisions/`**: Записи о принятых архитектурных решениях (ADR) — 11 документов.
- **`epics/`**: Описание эпиков (4 документа).
- **`stories/`**: User Stories (37 документов).
- **`implementation/`**: Детали реализации (2 документа).
- **`releases/`**: Информация о релизах.
- **`prd/`**: Product Requirements Documents (7 документов).
- **`qa/`**: Документация по тестированию (20 документов).
- **`arhiv/`**: Архивные документы.
- Корневые файлы: `Brief.md`, `PRD.md`, `api-spec.yaml`, `api-views-documentation.md`, `brownfield-architecture.md`, `architecture.md`, `docker-configuration.md`, `front-end-spec.md`, `index.md`, `test-catalog-api.md`, `testing-docker.md` и др.

### `scripts/`

Скрипты для автоматизации рутинных задач. Все скрипты написаны на PowerShell (`.ps1`):

- **`run-tests-docker.ps1`**: Запуск тестов в Docker-контейнерах.
- **`ssh_server.ps1`**: Скрипт для подключения к серверу по SSH.
- **`update_server_code.ps1`**: Автоматическое обновление кода на сервере.

### `.github/workflows/`

Определение пайплайнов CI/CD для автоматической сборки, тестирования и развертывания приложения:

- **`backend-ci.yml`**: CI пайплайн для бэкенда — линтинг (flake8), type checking (mypy), security checks (bandit), запуск тестов с PostgreSQL и Redis.
- **`frontend-ci.yml`**: CI пайплайн для фронтенда — линтинг (ESLint), type checking (TypeScript), сборка проекта, запуск тестов.
- **`main.yml`**: Основной пайплайн — комплексная проверка всего проекта, включая бэкенд и фронтенд.

### `docker/`

Дополнительные конфигурации для Docker:

- **`nginx/`**: Конфигурационные файлы Nginx для production окружения.
- **`init-db.sql/`**: SQL-скрипты для инициализации базы данных.

### `.bmad-core/`

Файлы методологии BMad (Business Model Analysis and Design) для управления проектом:

- **`agents/`**: Определения агентов (analyst, architect, dev, pm, po, qa, sm, ux-expert и др.) — 10 файлов.
- **`agent-teams/`**: Конфигурации команд агентов для различных задач — 4 файла.
- **`checklists/`**: Чек-листы для различных процессов (architect, change, pm и др.) — 6 файлов.
- **`data/`**: Базы знаний и методологические материалы — 6 файлов.

### `.windsurf/`

Workflows для Windsurf IDE:

- **`workflows/`**: Рабочие процессы (analyst, architect, bmad-master, dev, docs-workflow, pm, po, qa, sm, ux-expert и др.) — 11 файлов.

## Дополнительные файлы

### Корневые конфигурационные файлы

- **`Makefile`**: Команды для управления проектом (запуск, тестирование, деплой).
- **`docker-compose.yml`**: Конфигурация для production окружения.
- **`docker-compose.test.yml`**: Конфигурация для тестового окружения.
- **`pyrightconfig.json`**: Настройки type checker для Python.
- **`pytest.ini`**: Конфигурация pytest для запуска тестов.
- **`CLAUDE.md`**, **`GEMINI.md`**: Инструкции для AI-ассистентов.
- **`COMMIT_INSTRUCTIONS.md`**: Правила оформления коммитов.
