# Epic 3 Execution Plan & Progress Tracking

**Проект:** FREESPORT - Интеграция с 1С  

## 📅 DETAILED EXECUTION TRACKING

### 🟢 ФАЗА 1: Foundation

#### **НЕДЕЛЯ 1: Database Infrastructure**

##### **Task 3.1.1-A: Обновить модели для интеграции**

**📋 Story:** [3.1.1 import-products-structure](../../stories/epic-3/3.1.1.import-products-structure.md) - AC: 1
**Assigned:** *agent dev | **Estimate:** 6ч | **Status:** ⏳ Pending
**Due Date:** 08.09.2025

**Subtasks:**

- [ ] **Brand (существующая модель):**
  - [ ] Добавить поле onec_id с индексом
  - [ ] Создать миграцию add_onec_id_to_brand
  - [ ] Unit тесты (3 теста)

- [ ] **Category (существующая модель):**
  - [ ] Добавить поле onec_id с индексом
  - [ ] Создать миграцию add_onec_id_to_category
  - [ ] Unit тесты (3 теста)

- [ ] **Product (существующая модель):**
  - [ ] Добавить: onec_id, parent_onec_id, sync_status, last_sync_at, error_message
  - [ ] Добавить enum SyncStatus
  - [ ] Создать миграцию add_1c_integration_fields
  - [ ] Добавить индексы
  - [ ] Unit тесты (10 тестов)

- [ ] **ImportSession (новая модель):**
  - [ ] Добавить в конец models.py
  - [ ] Определить enums: ImportType, ImportStatus
  - [ ] Создать миграцию add_import_session
  - [ ] Unit тесты (5 тестов)

**Progress:** 0% □□□□□□□□□□  
**Notes:** _Задача не начата. Требуется обновление моделей и создание миграций._  
**⚠️ ВАЖНО:** Модели Brand, Category, Product УЖЕ СУЩЕСТВУЮТ в models.py - нужно только добавить поля

---

##### **Task 3.1.1-B: Создать сервисный слой**

**📋 Story:** [3.1.1](../../stories/epic-3/3.1.1.import-products-structure.md) - AC: 2
**Assigned:** *agent dev | **Estimate:** 12ч | **Status:** ⏳ Pending
**Due Date:** 10.09.2025

**Subtasks:**

- [ ] Создать директорию `backend/apps/products/services/`
- [ ] Создать `services/__init__.py`
- [ ] Создать `services/parser.py` с классом XMLDataParser
- [ ] Создать `services/processor.py` с классом ProductDataProcessor
- [ ] Реализовать методы XMLDataParser (parse_goods_xml, parse_offers_xml, parse_prices_xml, parse_rests_xml)
- [ ] Реализовать методы ProductDataProcessor (create_product_placeholder, enrich_product_from_offer, update_product_prices, update_product_stock)
- [ ] Unit тесты для XMLDataParser (10 тестов)
- [ ] Unit тесты для ProductDataProcessor (15 тестов)

**Progress:** 0% □□□□□□□□□□  
**Dependencies:** Task 3.1.1-A completed
**Notes:** _Требуется создание сервисного слоя и реализация всех методов парсера (включая parse_rests_xml для Story 3.1.5)._

---

##### **Task 3.1.1-C: Создать базовую команду**

**📋 Story:** [3.1.1](../../stories/epic-3/3.1.1.import-products-structure.md) - AC: 3, 5
**Assigned:** *agent dev | **Estimate:** 8ч | **Status:** ⏳ Pending
**Due Date:** 12.09.2025

**Subtasks:**

- [ ] Создать `backend/apps/products/management/commands/import_catalog_from_1c.py`
- [ ] Реализовать параметр `--data-dir` (обязательный)
- [ ] Реализовать флаг `--dry-run`
- [ ] Реализовать валидацию структуры директории (goods/, offers/, prices/, rests/)
- [ ] Реализовать создание `ImportSession` в начале
- [ ] Реализовать оркестрацию XMLDataParser и ProductDataProcessor
- [ ] Реализовать последовательность: goods → offers → prices → rests
- [ ] Реализовать обновление статуса `ImportSession` (completed/failed)
- [ ] Реализовать логирование в `ImportSession.report_details`
- [ ] Integration тесты (8 тестов)

**Progress:** 0% □□□□□□□□□□  
**Dependencies:** Task 3.1.1-B completed
**Notes:** _Базовая команда с --data-dir, будет дополнена в Story 3.1.2_

**Пример использования:**
```bash
python manage.py import_catalog_from_1c --data-dir="backend/tests/fixtures/1c-data"
```

---

##### **Task 3.1.1-D: Ролевое ценообразование**

**📋 Story:** [3.1.1](../../stories/epic-3/3.1.1.import-products-structure.md) - AC: 4
**Assigned:** *agent dev | **Estimate:** 6ч | **Status:** ⏳ Pending
**Due Date:** 13.09.2025

**Subtasks:**

- [ ] Создать модель PriceType (onec_id, name, user_role, is_active)
- [ ] Создать миграцию add_price_type
- [ ] Реализовать парсинг priceLists.xml
- [ ] Реализовать маппинг цен на роли (Опт 1→opt1_price, Опт 2→opt2_price, РРЦ→recommended_retail_price)
- [ ] Реализовать fallback: federation_price → recommended_retail_price
- [ ] Unit тесты (10 тестов)

**Progress:** 0% □□□□□□□□□□  
**Dependencies:** Task 3.1.1-C completed
**Notes:** _Критично для корректного отображения цен по ролям_

---

##### **Task 3.2.1-A: Дополнить User модель (Фаза 1 от Story 3.2.1)**

**📋 Story:** [3.2.1 import-existing-customers](../../stories/epic-3/3.2.1.import-existing-customers.md) - AC: 2
**Assigned:** *agent dev | **Estimate:** 4ч | **Status:** ⏳ Pending
**Due Date:** 10.09.2025

**Subtasks:**

- [ ] Добавить `onec_id = CharField(max_length=100, unique=True, null=True)` (из Story AC: 2)
- [ ] Добавить `sync_status = CharField(choices=SYNC_STATUSES, default='pending')`
- [ ] Добавить `created_in_1c = BooleanField(default=False)`
- [ ] Добавить `needs_1c_export = BooleanField(default=False)` (из Story)
- [ ] Добавить `last_sync_at = DateTimeField(null=True, blank=True)`
- [ ] Добавить `sync_error_message = TextField(blank=True)` (из Story)
- [ ] Создать миграцию с индексами
- [ ] Обновить тесты пользователей

**Progress:** 0% □□□□□□□□□□
**Notes:** _ЧАСТИЧНО покрывает Story 3.2.1 - только модель, требуются дополнительные tasks_
**⚠️ ВНИМАНИЕ:** Story 3.2.1 требует команду импорта, маппинг ролей, валидаторы (см. AC: 1,3,5,6,7)
**Dependencies:** Task 3.1.1-A completed

---

#### **НЕДЕЛЯ 2: Command Infrastructure (14.09 - 21.09)**

##### **Task 3.1.2-A: Создать команды-заглушки (Mock реализация для Stories 3.1.1, 3.1.2, 3.2.1)**

**📋 Stories:** [3.1.1](../../stories/epic-3/3.1.1.import-products-structure.md) AC:1 + [3.1.2](../../stories/epic-3/3.1.2.loading-scripts.md) AC:1,2 + [3.2.1](../../stories/epic-3/3.2.1.import-existing-customers.md) AC:1
**Assigned:** *agent dev | **Estimate:** 8ч | **Status:** ⏳ Pending
**Due Date:** 16.09.2025

**Subtasks:**

- [ ] Создать `import_catalog_from_1c` команду (Story 3.1.1 AC:1) с моковыми данными
- [ ] Создать `import_customers_from_1c` заглушку (Story 3.2.1 AC:1)
- [ ] Создать `load_test_catalog` (Story 3.1.2 AC:1) с реальными тестовыми данными
- [ ] Создать `sync_customers_with_1c` каркас (Story 3.2.3 preparation)
- [ ] Добавить progress bars и logging (Story 3.1.1 AC:6, Story 3.2.1 AC:6)
- [ ] Создать базовые тесты команд (Story 3.1.1 AC:7, Story 3.2.1 AC:7)

**Progress:** 0% □□□□□□□□□□
**Notes:** _Все команды, моковые данные и тесты еще предстоит реализовать._
**Dependencies:** Tasks 3.1.1-A, 3.2.1-A, 3.1.4-A completed

---

##### **Task 3.1.3: Создать comprehensive тестовые данные (Реализация Story 3.1.3)**

**📋 Story:** [3.1.3 test-catalog-loading](../../stories/epic-3/3.1.3.test-catalog-loading.md) - AC: 1,2,3,4,5,6
**Assigned:** *agent qa | **Estimate:** 12ч | **Status:** ⏳ Pending
**Due Date:** 18.09.2025

**Subtasks:**

- [ ] Создать 500+ товаров со всеми ценами (7 ролей) - (Story AC: 2,3)
- [ ] Создать 50+ категорий с иерархической структурой - (Story AC: 4)
- [ ] Создать 20+ брендов с описаниями - (Story AC: 5)
- [ ] Создать тестовых пользователей всех 7 ролей - (Story AC: 6)
- [ ] Создать моковые остатки и статусы синхронизации - (Story AC: 3)
- [ ] Создать fixtures для тестов - (Story AC: 1)
- [ ] Документировать тестовые данные - (Story Definition of Done)

**Progress:** 0% □□□□□□□□□□
**Notes:** _ПОЛНОСТЬЮ покрывает Story 3.1.3 - готово к параллельной работе_
**Dependencies:** Можно начинать параллельно с разработкой моделей

---

### 🔴 ФАЗА 2: Waiting & Preparation (21.09 - 05.10.2025)

#### **Advanced Preparation Tasks**

##### **Task 3.4.1: Test Data Scenarios (Реализация Stories 3.4.1, 3.4.2, 3.4.3)**

**📋 Stories:** [3.4.1](../../stories/epic-3/3.4.1.test-data-scenarios.md) + [3.4.2](../../stories/epic-3/3.4.2.conflict-scenarios-testing.md) + [3.4.3](../../stories/epic-3/3.4.3.data-integrity-checks.md)
**Assigned:** *agent dev | **Estimate:** 16ч | **Status:** ⏳ Pending
**Due Date:** 25.09.2025

**Subtasks:**

- [ ] Создать сценарии тестирования синхронизации (Story 3.4.1 AC: 1,2,3)
- [ ] Создать моковые конфликтные ситуации (Story 3.4.2 AC: 1,2,3,4)
- [ ] Создать тестовые edge cases (Story 3.4.2 AC: 5,6,7)
- [ ] Реализовать data integrity checks (Story 3.4.3 AC: 1,2,3,4,5)
- [ ] Реализовать mock API для тестирования (Story 3.4.1 AC: 4)
- [ ] Документировать тестовые сценарии (All stories Definition of Done)

**Progress:** 0% □□□□□□□□□□
**Notes:** _ПОЛНОСТЬЮ покрывает Stories 3.4.1-3.4.3 - критично для тестирования интеграции_
**Dependencies:** Независимая задача, можно делать параллельно

---

##### **Task 3.5.1-A: Monitoring Infrastructure (Реализация Stories 3.5.1, 3.5.2)**

**📋 Stories:** [3.5.1 monitoring-system](../../stories/epic-3/3.5.1.monitoring-system.md) + [3.5.2 error-notifications](../../stories/epic-3/3.5.2.error-notifications.md)
**Assigned:** *agent dev | **Estimate:** 12ч | **Status:** ⏳ Pending
**Due Date:** 30.09.2025

**Subtasks:**

- [ ] Создать класс `CustomerSyncMonitor` (Story 3.5.1 AC: 1)
- [ ] Настроить метрики синхронизации (Story 3.5.1 AC: 2,6)
- [ ] Реализовать дашборд мониторинга в **существующей Grafana** (Story 3.5.1 AC: 3)
- [ ] Настроить алерты через **существующий Prometheus + Sentry** (Story 3.5.1 AC: 4, Story 3.5.2 AC: 1,2,3)
- [ ] Создать health check endpoints (Story 3.5.1 AC: 5)
- [ ] Интеграция с **существующим стеком Prometheus/Grafana** (Story 3.5.1 AC: 7)
- [ ] Реализовать email notifications через Sentry (Story 3.5.2 AC: 4,5)
- [ ] Тесты мониторинга (Both stories AC: 6,7)

**Progress:** 0% □□□□□□□□□□
**Notes:** _ПОЛНОСТЬЮ покрывает Stories 3.5.1-3.5.2 - интеграция с существующим мониторингом_
**🎯 TECH STACK:** Использует существующий стек Sentry + Grafana + Prometheus (см. `docs/architecture/05-tech-stack.md`)
**Dependencies:** Можно реализовать с моками, потом адаптировать под реальное API

---

### 🔵 ФАЗА 3: Integration Sprint (после ответов от 1С)

**Status:** ⏳ **ОЖИДАНИЕ** - Ожидаем данные от 1С для начала интеграции.

#### **Critical Blocking Factors:**

- [ ] **DATA_FORMAT_BLOCKER:** Статус уточняется. Формат ожидается как XML (CommerceML 3.1).
- [ ] **PRICE_MAPPING_BLOCKER:** Статус уточняется. Типы цен требуют подтверждения в `priceLists.xml`.
- [ ] **CUSTOMER_SYNC_BLOCKER:** Статус уточняется. Ждем структуру контрагентов из `contragents.xml`.
- [ ] **API_METHOD_BLOCKER:** Статус уточняется. Нужно подтвердить способ передачи файлов.

**Информация по типам цен (из `priceLists.xml`):**

- `Опт 1` -> `wholesale_level1`
- `Опт 2` -> `wholesale_level2`
- `Опт 3` -> `wholesale_level3`
- `Тренерская` -> `trainer`
- `РРЦ` -> `retail` / `RRP`
- `МРЦ` -> `MSRP`
- **Внимание:** Тип цены для `federation_rep` не найден. Требуется уточнение или использование одной из существующих.

##### **Task 3.1.1-B: Реальные парсеры данных (Завершение Story 3.1.1)**

**📋 Story:** [3.1.1 import-products-structure](../../stories/epic-3/3.1.1.import-products-structure.md) - AC: 2,3,7
**Assigned:** *agent dev | **Estimate:** 12ч | **Status:** ⏳ Pending
**Due Date:** _18.09.2025_

**Subtasks:**

- [ ] Реализовать парсер формата от 1С (Story AC: 2) - XML/JSON поддержка
- [ ] Добавить валидацию структуры данных (Story AC: 3) - валидаторы товаров
- [ ] Реализовать error handling для некорректных данных (Story AC: 3)
- [ ] Создать маппинг полей 1С → Django модели (Story AC: 2)
- [ ] Comprehensive тестирование парсера (Story AC: 7)

**Progress:** 0% □□□□□□□□□□
**🔴 Blocking Factor:** Нет.
**Notes:** _Завершает полную реализацию Story 3.1.1 после Task 3.1.1-A_

---

##### **Task 3.1.2-B: Реальная загрузка из файлов 1С (Завершение Story 3.1.2)**

**📋 Story:** [3.1.2 loading-scripts](../../stories/epic-3/3.1.2.loading-scripts.md) - AC: 2 (реальные файлы)
**Assigned:** *agent dev | **Estimate:** 8ч | **Status:** ⏳ Pending
**Due Date:** _18.09.2025_

**Subtasks:**

- [ ] Обновить команду `load_test_catalog` для реальных файлов (Story AC: 2)
- [ ] Добавить параметр `--file` для загрузки из файла 1С
- [ ] Реализовать `--chunk-size` для пакетной обработки больших файлов
- [ ] Добавить `--skip-validation` для быстрой загрузки
- [ ] Создать валидацию структуры файлов от 1С
- [ ] Тестирование с реальными данными от 1С

**Progress:** 0% □□□□□□□□□□
**🔴 Blocking Factor:** Нет.
**Notes:** _Дополняет существующую команду load_test_catalog реальной загрузкой файлов_

---

##### **Task 3.2.1-B: Реальная синхронизация клиентов (Завершение Story 3.2.1)**

**📋 Story:** [3.2.1 import-existing-customers](../../stories/epic-3/3.2.1.import-existing-customers.md) - AC: 3,5,6,7
**Assigned:** *agent dev | **Estimate:** 16ч | **Status:** ⏳ Pending
**Due Date:** _22.09.2025_

**Subtasks:**

- [ ] Создать маппинг ролей 1С → роли платформы (Story AC: 3) - `CustomerRoleMapper`
- [ ] Реализовать команду import с реальным API (Story AC: 1) - завершение `import_customers_from_1c`
- [ ] Добавить обработку дублей и конфликтов (Story AC: 7) - поиск дубликатов
- [ ] Настроить logging в `CustomerSyncLog` (Story AC: 6)
- [ ] Интеграционные тесты (Story AC: 7)

**Progress:** 0% □□□□□□□□□□
**🔴 Blocking Factor:** Нет.
**Notes:** _Завершает полную реализацию Story 3.2.1 после Task 3.2.1-A_

---

##### **Task 3.2.3: Bidirectional Sync (Реализация Story 3.2.3)**

**📋 Story:** [3.2.3 bidirectional-sync](../../stories/epic-3/3.2.3.bidirectional-sync.md) - AC: 1,2,3,4,5,6,7
**Assigned:** *agent dev | **Estimate:** 20ч | **Status:** ⏳ Pending
**Due Date:** _29.09.2025_

**Subtasks:**

- [ ] Создать `CustomerExportService` для передачи в 1С (Story AC: 1,2)
- [ ] Настроить Celery задачи для асинхронного экспорта (Story AC: 3,4)
- [ ] Добавить Django signals для автоматической синхронизации (Story AC: 5)
- [ ] Реализовать status tracking и retry logic (Story AC: 6)
- [ ] E2E тестирование двусторонней синхронизации (Story AC: 7)

**Progress:** 0% □□□□□□□□□□
**🔴 Blocking Factor:** Нет.
**Notes:** _ПОЛНОСТЬЮ реализует Story 3.2.3 - критично для полной интеграции_

---

##### **Task 3.2.2 + 3.3.1: Conflict Resolution (Реализация Stories 3.2.2, 3.3.1)**

**📋 Stories:** [3.2.2 conflict-resolution](../../stories/epic-3/3.2.2.conflict-resolution.md) + [3.3.1 customer-identity-algorithms](../../stories/epic-3/3.3.1.customer-identity-algorithms.md)
**Assigned:** *agent dev | **Estimate:** 24ч | **Status:** ⏳ Pending
**Due Date:** _06.10.2025_

**Subtasks:**

- [ ] Создать `CustomerConflictResolver` класс (Story 3.2.2 AC: 1,2)
- [ ] Реализовать алгоритмы нечеткого поиска (Story 3.3.1 AC: 1,2,3)
- [ ] Создать `CustomerIdentityResolver` с ML подходами (Story 3.3.1 AC: 4,5)
- [ ] Настроить Django Admin для модерации конфликтов (Story 3.2.2 AC: 4,5,6)
- [ ] Тестирование conflict resolution (Story 3.2.2 AC: 7, Story 3.3.1 AC: 6,7)

**Progress:** 0% □□□□□□□□□□
**🔴 Blocking Factor:** Нет.
**Notes:** _Комбинированная реализация Stories 3.2.2 + 3.3.1 - алгоритмы идентификации дублей_

---

## 📞 EXTERNAL DEPENDENCIES TRACKING

### 🔴 КРИТИЧЕСКИЙ БЛОКЕР: Ответы от программиста 1С

**Запрос отправлен:** 05.09.2025
**Ожидаемый ответ:** 12-19.09.2025 (1-2 недели)
**Последний follow-up:** _Нет_
**Status:** 🔴 Active

**Ключевые вопросы в запросе:**

- [х] Формат данных каталога (CommerceML/JSON/CSV)
- [х] Способ передачи данных (FTP/HTTP API/файлы)
- [х] Названия типов цен в 1С
- [х] Формат справочника клиентов
- [ ] Требования к заказам для передачи в 1С

**Next Actions:**

- [ ] **12.09.2025:** Первый follow-up если нет ответа
- [ ] **19.09.2025:** Второй follow-up + предложение mock API
- [ ] **26.09.2025:** Эскалация + запуск contingency план

---

## ⚠️ RISK MANAGEMENT STATUS

### 🔴 Active Risks

#### **RISK-001: Задержка ответов от программиста 1С**

**Status:** 🔴 Active | **Probability:** High (60%) | **Impact:** Critical

**Current Mitigation:**

- ✅ Параллельная работа по независимым задачам
- ⏳ Еженедельные follow-up planned
- ⏳ Mock API contingency план готов к активации

**Trigger for Contingency:** Нет ответа к 26.09.2025

#### **RISK-002: Неожиданно сложный формат данных от 1С**

**Status:** 🟡 Monitoring | **Probability:** Medium (40%) | **Impact:** Medium

**Current Mitigation:**

- ✅ Flexible парсер архитектура заложена
- ✅ Дополнительное время в estimates

---

## 📊 WEEKLY PROGRESS SNAPSHOTS

### Week 1 (07.09 - 14.09.2025)

**Target:** Complete Milestone 1.1 (Database models)
**Status:** ⏳ Planned
**Completed:** _Не начато_
**Blockers:** _Нет_
**Notes:** _План требует актуализации перед началом работ_

### Week 2 (14.09 - 21.09.2025)

**Target:** Complete Milestone 1.2 (Commands + test data)
**Status:** ⏳ Planned
**Completed:** _TBD_
**Blockers:** _TBD_
**Notes:** _TBD_

---

## 🎯 SUCCESS CRITERIA CHECKLIST

### Phase 1 Success Criteria

- [ ] Все Django migrations применены без ошибок
- [ ] `load_test_catalog` команда загружает 500+ товаров за <30 сек
- [ ] Тесты покрывают >90% новых компонентов
- [ ] Нет regression в существующей функциональности

### Phase 2 Success Criteria

- [ ] Все моковые API возвращают валидные данные
- [ ] Monitoring dashboard показывает метрики
- [ ] Документация обновлена

### Phase 3 Success Criteria (после ответов 1С)

- [ ] End-to-end синхронизация товаров работает
- [ ] End-to-end синхронизация клиентов работает
- [ ] Bidirectional sync функционирует
- [ ] Conflict resolution обрабатывает edge cases
- [ ] Performance targets достигнуты

---

## 📝 DAILY UPDATES LOG

### 2025-10-11 (Сегодня)

- [x] Epic 3 execution plan актуализирован
- [x] Все ошибочные отметки о выполнении сброшены
- [x] Story 3.1.5 валидирована и приведена к формату шаблона
- 🎯 **Next:** Начать Task 3.1.1-A (*agent dev)

### 2025-09-08

- [ ] **Planned:** Завершить Task 3.1.1-A (Product модель)
- [ ] **Planned:** Follow-up программисту 1С

---

## 🔄 PLAN UPDATE HISTORY

**v1.0 (07.09.2025):** Первоначальный план создан
**v1.1 (11.10.2025):** Сброшены ошибочные отметки о выполнении, актуализированы статусы задач

---

## 📞 CONTACTS & ESCALATION

**Project Lead:** BMad Orchestrator
**Primary Developer:** *agent dev
**QA Lead:** *agent qa
**Architect:** *agent architect

**External Dependencies:**

**1С Programmer:** _[контакт нужно добавить]_ - Status: ⏳ Awaiting response

**Next Review:** 12.10.2025 (ежедневный checkpoint)
**Next Milestone Review:** 18.10.2025 (Milestone 1.1)

---

**🚀 ПЛАН АКТИВЕН И ГОТОВ К ИСПОЛНЕНИЮ!**

*Последнее обновление: 11.10.2025 by Product Owner (актуализация статусов)
