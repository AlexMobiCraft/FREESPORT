# Индекс документации FREESPORT

Добро пожаловать в документацию проекта FREESPORT - API-First E-commerce платформы для B2B/B2C продаж спортивных товаров с интеграцией 1С.

## Корневые документы

### [Project Brief: Интернет портал компании](./Brief.md)

Комплексный бриф проекта по созданию единой API-First платформы для 5 торговых марок с B2B функционалом. Описывает проблематику, архитектурные решения, целевые персоны и техническую базу на Django/React.

### [Product Requirements Document (PRD)](./PRD.md)

Подробные функциональные и нефункциональные требования проекта FREESPORT. Включает цели, бэкграунд, UI/UX спецификацию, технические предположения, временные рамки и детализированные эпики разработки на 28 недель.

### [API Views Документация](./api-views-documentation.md)

Детальное описание всех API endpoints платформы по приложениям. Документирует Products API, Cart API, Orders API, Users API, Common API и Pages API с методами, логикой и особенностями каждого компонента.

### [API Specification (OpenAPI 3.0.3)](./api-spec.yaml)

OpenAPI спецификация FREESPORT Platform API для RESTful взаимодействия B2B/B2C платформы спортивных товаров с JWT аутентификацией и версионированием.

### [Архитектурная документация](./architecture.md)

Масштабная техническая документация системы FREESPORT - API-First E-commerce платформы. Покрывает технологический стек, модели данных, API спецификацию, интеграции, безопасность и производительность.

### [Docker Configuration для FREESPORT Platform](./docker-configuration.md)

Комплексное руководство по Docker конфигурации проекта. Описывает архитектуру контейнеров, исправления инфраструктуры, настройки портов, команды использования и оптимизации для разработки и тестирования.

### [Спецификация UI/UX FREESPORT](./front-end-spec.md)

Комплексная спецификация пользовательского интерфейса и опыта для B2B/B2C платформы. Включает целевые персоны, информационную архитектуру, библиотеку компонентов, каркасы страниц и административную панель с TypeScript интерфейсами.

### [Структура категорий товара](./Структура%20категорий%20товара.md)

Иерархическая структура категорий товаров по видам спорта: СПОРТ (туризм, фитнес, плавание, игры, единоборства, гимнастика), ДЕТСКИЙ ТРАНСПОРТ, ОБОРУДОВАНИЕ и СУВЕНИРНАЯ ПРОДУКЦИЯ.

### [Каталог тестов API - Структура и организация](./test-catalog-api.md)

Исчерпывающий обзор организации тестового покрытия API платформы. Описывает структуру тестовых каталогов, типы тестов, соглашения по именованию, конфигурацию pytest и метрики качества.

### [Тестирование в Docker для FREESPORT Platform](./testing-docker.md)

Подробное руководство по настройке и использованию Docker-based тестирования. Покрывает архитектуру тестовой среды, конфигурацию сервисов, автоматизацию, мониторинг и лучшие практики тестирования.

### [Отчет о выполненной работе: Доработка архитектурной документации](./Отчет_для_заказчика.md)

Комплексный отчет о проделанной работе по доработке архитектурной документации, включающий обновления Epic 3, модели данных, API спецификации, ER-диаграммы и готовность к разработке интеграции с 1С.

### [Список задач для проверки](./Проверить-.txt)

Рабочий список задач разработчика для проверки различных компонентов проекта: структуры Next.js, производительности, моделей данных, интеграций и workflow процессов.

## Architecture

Документы в директории `architecture/` содержат детальную техническую документацию системы:

### [1. Введение](./architecture/01-introduction.md)

Общий обзор архитектуры FREESPORT платформы и основные принципы построения.

### [2. Модели Данных](./architecture/02-data-models.md)

Подробное описание моделей Django с поддержкой B2B/B2C и интеграции с 1С.

### [3. Спецификация API](./architecture/03-api-specification.md)

Полная OpenAPI 3.1 спецификация REST API с поддержкой многоуровневого ценообразования.

### [4. Структура Компонентов](./architecture/04-component-structure.md)

Архитектура Frontend (Next.js) и Backend (Django) компонентов с модульной организацией.

### [5. Технологический Стек](./architecture/05-tech-stack.md)

Детальный обзор используемых технологий: Django 4.2, Next.js 14+, PostgreSQL 15+, Redis 7.0+.

### [6. Высокоуровневая Архитектура](./architecture/06-system-architecture.md)

Системная архитектура с диаграммами развертывания и сетевого взаимодействия.

### [7. Внешние Интеграции](./architecture/07-external-integrations.md)

Интеграция с 1С, ЮКасса, службами доставки с Circuit Breaker Pattern.

### [8. Основные Рабочие Процессы](./architecture/08-workflows.md)

Workflow процессы регистрации, заказов, синхронизации с 1С и разрешения конфликтов.

### [9. Схема Базы Данных](./architecture/09-database-schema.md)

PostgreSQL схема с секционированием, индексами и поддержкой многоуровневого ценообразования.

### [10. Стратегия Тестирования](./architecture/10-testing-strategy.md)

Comprehensive testing strategy с изоляцией тестов, pytest, Factory Boy и Playwright.

### [11. Безопасность и Производительность](./architecture/11-security-performance.md)

Стратегии обеспечения безопасности и оптимизации производительности системы.

### [12. Стратегия Обработки Ошибок](./architecture/12-error-handling.md)

Централизованная система обработки ошибок и мониторинга исключений.

### [13. Мониторинг и Наблюдаемость](./architecture/13-monitoring.md)

Системы мониторинга, метрик и observability для production среды.

### [14. CI/CD и Развертывание](./architecture/14-cicd-deployment.md)

Конфигурация непрерывной интеграции и развертывания с GitHub Actions.

### [15. Руководство по Развертыванию](./architecture/15-deployment-guide.md)

Пошаговое руководство по развертыванию платформы в production среде.

### [16. Руководство по Внедрению ИИ](./architecture/16-ai-implementation-guide.md)

Стратегия интеграции AI/ML возможностей в платформу.

### [17. SLA Производительности](./architecture/17-performance-sla.md)

Соглашение об уровне обслуживания и метрики производительности.

### [18. Workflow B2B Верификации](./architecture/18-b2b-verification-workflow.md)

Процесс верификации B2B пользователей и активации оптовых цен.

### [19. Среда Разработки](./architecture/19-development-environment.md)

Настройка и конфигурация среды разработки.

### [20. Архитектура интеграции с 1С](./architecture/20-1c-integration.md)

Детальная архитектура интеграции с 1С:Управление торговлей с разрешением конфликтов.

### [Стандарты Кодирования](./architecture/coding-standards.md)

Конвенции и стандарты написания кода для проекта.

### [План Обновления Документации](./architecture/documentation-update-plan.md)

Стратегия поддержки актуальности архитектурной документации.

### [FREESPORT Platform - Архитектурная Документация](./architecture/index.md)

Главная индексная страница архитектурной документации с навигацией.

### [Запрос к разработчику 1С](./architecture/request-to-1c-developer.md)

Техническое задание для разработки интеграционных endpoint'ов в 1С.

### [Дерево исходного кода](./architecture/source-tree.md)

Структура каталогов и файлов проекта с описанием назначения.

### [Технологический Стек](./architecture/tech-stack.md)

Подробное описание выбранных технологий и их обоснование.

## Database

Документы в директории `database/` содержат схемы и диаграммы базы данных:

### [FREESPORT База Данных ER-Диаграмма](./database/er-diagram.md)

Подробная ER-диаграмма базы данных с связями между сущностями.

## Decisions

Документы в директории `decisions/` содержат принятые архитектурные и технические решения:

### [Архитектурные и технические решения FREESPORT](./decisions/README.md)

Обзор принятых архитектурных и технических решений по проекту.

### [Сводка решений](./decisions/SUMMARY.md)

Краткое резюме всех принятых технических решений.

### [Story 2.1: API Documentation (Swagger) - Принятые технические решения](./decisions/story-2.1-api-documentation-decisions.md)

Решения по внедрению Swagger/OpenAPI документации с drf-spectacular.

### [Story 2.2: User Management API - Принятые технические решения](./decisions/story-2.2-user-management-api-decisions.md)

Архитектурные решения по API управления пользователями и ролевой системе.

### [Story 2.3: Personal Cabinet API - Принятые технические решения](./decisions/story-2.3-personal-cabinet-api-decisions.md)

Решения по архитектуре личного кабинета с поддержкой B2B/B2C функций.

### [Story 2.4: Catalog API - Принятые технические решения](./decisions/story-2.4-catalog-api-decisions.md)

Архитектурные решения по API каталога товаров с многоуровневым ценообразованием.

### [Story 2.5: Product Detail API - Принятые технические решения](./decisions/story-2.5-product-detail-api-decisions.md)

Решения по детальному API товаров с ролевым отображением цен и характеристик.

### [Story 2.6: Cart API - Принятые технические решения](./decisions/story-2.6-cart-api-decisions.md)

Архитектурные решения по API корзины для авторизованных и гостевых пользователей.

### [Story 2.7: Order API - Принятые технические решения](./decisions/story-2.7-order-api-decisions.md)

Решения по API заказов с поддержкой B2B/B2C процессов и интеграции с 1С.

### [Story 2.8: Search API - Принятые технические решения](./decisions/story-2.8-search-api-decisions.md)

Архитектурные решения по поиску товаров с полнотекстовым поиском на PostgreSQL.

## PRD

Документы в директории `prd/` содержат требования к продукту:

### [Product Requirements Document (PRD)](./prd/index.md)

Основной документ требований к продукту FREESPORT Platform.

### [2. Эпики разработки](./prd/2.md)

Детальное описание эпиков разработки с временными рамками.

### [Epics 1-8](./prd/epics-1-8.md)

Описание основных эпиков проекта от инфраструктуры до интеграций.

### [Goals and Background Context](./prd/goals-and-background-context.md)

Цели проекта, контекст бизнеса и предпосылки создания платформы.

### [Requirements](./prd/requirements.md)

Детальные функциональные и нефункциональные требования к системе.

### [Technical Assumptions](./prd/technical-assumptions.md)

Технические предположения и ограничения проекта.

### [User Interface Design Goals](./prd/user-interface-design-goals.md)

Цели и принципы дизайна пользовательского интерфейса.

## Stories

Документы в директории `stories/` содержат пользовательские истории и задачи разработки:

### [Story 1.1: git-setup](./stories/1.1.git-setup.md)

Настройка Git репозитория, workflow и конвенций разработки.

### [Story 1.2: dev-environment](./stories/1.2.dev-environment.md)

Настройка среды разработки с Docker и локальными инструментами.

### [Story 1.3: django-structure](./stories/1.3.django-structure.md)

Создание модульной структуры Django приложения с apps архитектурой.

### [Story 1.4: nextjs-structure](./stories/1.4.nextjs-structure.md)

Настройка Next.js 14+ структуры с App Router и TypeScript.

### [Story 1.5: cicd-infrastructure](./stories/1.5.cicd-infrastructure.md)

Настройка CI/CD пайплайнов с GitHub Actions и Docker.

### [Story 1.6: docker-containers](./stories/1.6.docker-containers.md)

Конфигурация Docker контейнеров для разработки и production.

### [Story 1.7: testing-environment](./stories/1.7.testing-environment.md)

Настройка comprehensive testing среды с pytest, Jest и Playwright.

### [Story 1.8: database-design](./stories/1.8.database-design.md)

Проектирование PostgreSQL схемы с секционированием и оптимизацией.

### [Story 1.9: design-brief](./stories/1.9.design-brief.md)

Техническое задание на дизайн с учетом B2B/B2C различий.

### [Story 2.1: swagger-documentation](./stories/2.1.swagger-documentation.md)

Внедрение автоматической документации API с помощью Swagger/OpenAPI.

### [Story 2.1.1: swagger-documentation-integration-tests](./stories/2.1.1.swagger-documentation-integration-tests.md)

Интеграционные тесты для Swagger документации.

### [Story 2.1.2: swagger-documentation-viewsets-coverage](./stories/2.1.2.swagger-documentation-viewsets-coverage.md)

Покрытие ViewSets в Swagger документации.

### [Story 2.1.3: swagger-documentation-ci-validation](./stories/2.1.3.swagger-documentation-ci-validation.md)

Валидация Swagger документации в CI/CD пайплайне.

### [Story 2.2: user-management-api](./stories/2.2.user-management-api.md)

Создание API управления пользователями с 7 ролями и B2B верификацией.

### [Story 2.3: personal-cabinet-api](./stories/2.3.personal-cabinet-api.md)

API личного кабинета с адресами, избранным, заказами и профилем компании.

### [Story 2.4: catalog-api](./stories/2.4.catalog-api.md)

API каталога товаров с фильтрацией, поиском и ролевым ценообразованием.

### [Story 2.5: product-detail-api](./stories/2.5.product-detail-api.md)

Детальный API товара с характеристиками и RRP/MSRP для B2B.

### [Story 2.6: cart-api](./stories/2.6.cart-api.md)

API корзины покупок с поддержкой авторизованных и гостевых пользователей.

### [Story 2.7: order-api](./stories/2.7.order-api.md)

API заказов с поддержкой B2B/B2C процессов и экспорта в 1С.

### [Story 2.8: search-api](./stories/2.8.search-api.md)

API поиска товаров с полнотекстовым поиском и умной фильтрацией.

### [Story 2.9: filtering-api](./stories/2.9.filtering-api.md)

Расширенный API фильтрации товаров по категориям, брендам, ценам и характеристикам.

### [Story 2.10: pages-api](./stories/2.10.pages-api.md)

API статических страниц с кэшированием и HTML санитизацией.

---

## Статистика документации

- **Общее количество документов:** 72
- **Корневые документы:** 12
- **Архитектура:** 22 документа
- **База данных:** 1 документ
- **Решения:** 10 документов
- **PRD:** 7 документов
- **Истории:** 20 документов

## Навигация по проекту

Для начала работы с проектом рекомендуется изучить документы в следующем порядке:

1. [Project Brief](./Brief.md) - общее понимание проекта
2. [PRD](./PRD.md) - требования и цели
3. [Архитектурная документация](./architecture.md) - техническая архитектура
4. [Stories](./stories/) - конкретные задачи реализации

**Последнее обновление:** 06.09.2025