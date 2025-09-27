# FREESPORT Platform - Архитектурная Документация

## Оглавление

### 📋 Основные архитектурные документы

1. **[Введение](architecture/01-introduction.md)** - Обзор проекта и технический контекст
2. **[Модели Данных](architecture/02-data-models.md)** - Структуры данных и связи между сущностями
3. **[Спецификация API](architecture/03-api-specification.md)** - REST API endpoints и схемы данных
4. **[Структура Компонентов](architecture/04-component-structure.md)** - Архитектура компонентов системы
5. **[Технологический Стек](architecture/05-tech-stack.md)** - Используемые технологии и инструменты
6. **[Системная Архитектура](architecture/06-system-architecture.md)** - Высокоуровневая архитектура
7. **[Внешние Интеграции](architecture/07-external-integrations.md)** - Интеграции с внешними сервисами
8. **[Рабочие Процессы](architecture/08-workflows.md)** - Основные бизнес-процессы
9. **[Схема Базы Данных](architecture/09-database-schema.md)** - Структура базы данных
10. **[Стратегия Тестирования](architecture/10-testing-strategy.md)** - Подходы к тестированию
11. **[Безопасность и Производительность](architecture/11-security-performance.md)** - Меры безопасности и оптимизация
12. **[Обработка Ошибок](architecture/12-error-handling.md)** - Стратегии обработки ошибок
13. **[Мониторинг и Наблюдаемость](architecture/13-monitoring.md)** - Системы мониторинга
14. **[CI/CD и Развертывание](architecture/14-cicd-deployment.md)** - Процессы развертывания
15. **[Руководство по Развертыванию](architecture/15-deployment-guide.md)** - Детальное руководство по развертыванию
16. **[AI Implementation Guide](architecture/16-ai-implementation-guide.md)** - Руководство по внедрению AI
17. **[Performance SLA](architecture/17-performance-sla.md)** - Соглашения об уровне производительности
18. **[B2B Verification Workflow](architecture/18-b2b-verification-workflow.md)** - Процесс верификации B2B клиентов
19. **[Development Environment](architecture/19-development-environment.md)** - Настройка среды разработки
20. **[Архитектура интеграции с 1С](architecture/20-1c-integration.md)** - Интеграция с 1С:Управление торговлей

### 📚 Дополнительные документы

- **[Стандарты Кодирования](architecture/coding-standards.md)** - Правила написания кода
- **[Технологический Стек (детально)](architecture/tech-stack.md)** - Подробное описание технологий
- **[Структура Исходного Кода](architecture/source-tree.md)** - Организация файлов проекта
- **[Запрос к программисту 1С](architecture/request-to-1c-developer.md)** - Техническое ТЗ для интеграции с 1С

### 🎯 Ключевые особенности архитектуры

- **API-First подход** с Django REST Framework
- **Монорепо структура** для управления несколькими брендами
- **Роле-ориентированное ценообразование** для B2B/B2C
- **Двусторонняя интеграция с 1С** (товары, клиенты, заказы)
- **Microservice-ready архитектура** для масштабирования
- **Comprehensive testing strategy** с 70%+ покрытием

### 📅 История изменений

- **2025-09-05:** Добавлена архитектура интеграции с 1С, включая синхронизацию покупателей
- **2025-08-23:** Исправления Docker конфигурации и система изоляции тестов
- **2025-08-16:** Первоначальная версия архитектурной документации

---

> **Примечание:** Для начала работы рекомендуется ознакомиться с документами в порядке их нумерации, начиная с [Введения](architecture/01-introduction.md).
