# Epic 3 Execution Plan & Progress Tracking

**Проект:** FREESPORT - Интеграция с 1С

## 📅 DETAILED EXECUTION TRACKING

### 🟢 ФАЗА 1: Foundation

#### **НЕДЕЛЯ 1: Database Infrastructure**

##### **Task 3.1.1-A: Обновить модели для интеграции**

**📋 Story:** [3.1.1 import-products-structure](../../stories/epic-3/3.1.1.import-products-structure.md) - AC: 1
**Assigned:** \*agent dev | **Estimate:** 6ч | **Status:** ⏳ Pending
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
**Assigned:** \*agent dev | **Estimate:** 12ч | **Status:** ⏳ Pending
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
**Assigned:** \*agent dev | **Estimate:** 8ч | **Status:** ⏳ Pending
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
**Assigned:** \*agent dev | **Estimate:** 6ч | **Status:** ⏳ Pending
**Due Date:** 13.09.2025

**Subtasks:**

- [ ] Создать модель PriceType (onec_id, name, user_role, is_active)
- [ ] Создать миграцию add_price_type
- [ ] Реализовать парсинг priceLists.xml
- [ ] Реализовать маппинг цен на роли (Опт 1→opt1_price, Опт 2→opt2_price,  
       Опт 3→opt3_price, РРЦ→recommended_retail_price)
- [ ] Реализовать fallback: federation_price → recommended_retail_price
- [ ] Unit тесты (10 тестов)

**Progress:** 0% □□□□□□□□□□  
**Dependencies:** Task 3.1.1-C completed
**Notes:** _Критично для корректного отображения цен по ролям_

---

##### **Task 3.2.1-A: Дополнить User модель и создать CustomerSyncLog (Фаза 1 от Story 3.2.1)**

**📋 Story:** [3.2.1.0 import-existing-customers](../../stories/epic-3/3.2.1.0.import-existing-customers.md) - AC: 3
**Assigned:** \*agent dev | **Estimate:** 6ч | **Status:** ⏳ Pending
**Due Date:** 10.09.2025

**Subtasks:**

**User модель (расположение: `backend/apps/users/models.py`):**

- [ ] Добавить `onec_id = CharField(max_length=100, unique=True, null=True, db_index=True)`
- [ ] Добавить `sync_status = CharField(max_length=20, choices=SYNC_STATUSES, default='pending')`
- [ ] Добавить `created_in_1c = BooleanField(default=False)`
- [ ] Добавить `needs_1c_export = BooleanField(default=False)`
- [ ] Добавить `last_sync_at = DateTimeField(null=True, blank=True)`
- [ ] Добавить `sync_error_message = TextField(blank=True)`
- [ ] Создать миграцию с индексом на `onec_id`

**CustomerSyncLog модель (расположение: `backend/apps/common/models.py`):**

- [ ] Создать модель с полями: session, user, onec_id, operation_type, status, error_message, details, created_at
- [ ] Добавить enum классы: OperationType (created/updated/skipped/error), StatusType (success/failed/warning)
- [ ] Создать индексы: [session, operation_type], [onec_id], [status]
- [ ] Создать миграцию для CustomerSyncLog
- [ ] Unit тесты для обеих моделей (8 тестов)

**Progress:** 0% □□□□□□□□□□
**Notes:** _ЧАСТИЧНО покрывает Story 3.2.1 v1.4 - только модели, требуется Task 3.2.1-B для полной реализации_
**⚠️ ВНИМАНИЕ:** Story 3.2.1 также требует команду импорта, парсер/процессор, маппинг ролей (см. Task 3.2.1-B)
**Dependencies:** Task 3.1.1-A completed (ImportSession model)
**⚠️ КРИТИЧНО:** Эта задача ДОЛЖНА быть выполнена ПОСЛЕ Task 3.1.1-A, так как CustomerSyncLog требует ForeignKey на ImportSession

---

#### **НЕДЕЛЯ 2: Command Infrastructure (14.09 - 21.09)**

##### **Task 3.1.2-A: Расширение команды import_catalog_from_1c и создание backup команд**

**📋 Story:** [3.1.2](../../stories/epic-3/3.1.2.loading-scripts.md) AC:1,5,6,7,8
**Assigned:** \*agent dev | **Estimate:** 10ч | **Status:** ⏳ Pending
**Due Date:** 16.09.2025

**Subtasks:**

- [ ] Расширить `import_catalog_from_1c` параметрами --chunk-size, --skip-validation, --file-type, --clear-existing (Story 3.1.2 AC:1)
- [ ] Добавить progress bars и logging (Story 3.1.2 AC:5)
- [ ] Создать команду `backup_db` (Story 3.1.2 AC:6)
- [ ] Создать команду `restore_db` (Story 3.1.2 AC:7)
- [ ] Создать команду `rotate_backups` (Story 3.1.2 AC:8)
- [ ] Создать базовые тесты команд (Story 3.1.2)

**Progress:** 0% □□□□□□□□□□
**Notes:** _Работа с реальными данными из data/import_1c, тестовые команды не требуются_
**Dependencies:** Tasks 3.1.1-A, 3.1.1-B, 3.1.1-C completed

---

##### **Task 3.1.3: Валидация импорта реального каталога из 1С (Реализация Story 3.1.3)**

**📋 Story:** [3.1.3 test-catalog-loading](../../stories/epic-3/3.1.3.test-catalog-loading.md) - AC: 1,2,3,4,5
**Assigned:** \*agent qa | **Estimate:** 10ч | **Status:** ⏳ Pending
**Due Date:** 18.09.2025

**Subtasks:**

- [ ] Запустить полный импорт из data/import_1c/ и валидировать результаты (Story AC: 1)
  - [ ] Валидировать импорт ≥5000 товаров из goods*1*\*.xml
  - [ ] Валидировать импорт категорий из groups*1_1*\*.xml
  - [ ] Валидировать импорт цен из prices*1*\*.xml
- [ ] Валидировать ценообразование для всех 7 ролей (Story AC: 2)
  - [ ] Проверить маппинг типов цен из priceLists\_\*.xml
  - [ ] Проверить fallback логику для отсутствующих цен
- [ ] Проверить технические характеристики из propertiesGoods\_\*.xml (Story AC: 3)
  - [ ] Валидировать структуру JSON specifications
  - [ ] Проверить массивы размеров/цветов
- [ ] Валидировать целостность данных (Story AC: 4)
  - [ ] Проверить связи Product→Category→Brand
  - [ ] Проверить отсутствие orphan records
  - [ ] Проверить onec_id уникальность
- [ ] Создать comprehensive integration тесты в test_real_catalog_import.py (Story AC: 5)
  - [ ] test_import_real_goods(), test_import_real_categories()
  - [ ] test_import_real_prices(), test_real_data_integrity()
  - [ ] test_specifications_from_properties(), test_api_returns_real_products()
- [ ] Валидировать API /products/ с реальными данными (Story DoD)
- [ ] Проверить отображение реального каталога в Django admin (Story DoD)

**Progress:** 0% □□□□□□□□□□
**Notes:** _Используем РЕАЛЬНЫЕ данные из data/import_1c/ (~6200 товаров) вместо синтетических. Команда import_catalog_from_1c из Story 3.1.2 уже готова. Sprint Change Proposal approved 19.10.2025._
**Dependencies:** Tasks 3.1.1-A, 3.1.1-B, 3.1.1-C, 3.1.2-A completed

---

### 🔴 ФАЗА 2: Waiting & Preparation (21.09 - 05.10.2025)

#### **Advanced Preparation Tasks**

##### **Task 3.4.1: Test Data Scenarios (Реализация Stories 3.4.1, 3.4.2, 3.4.3)**

**📋 Stories:** [3.4.1](../../stories/epic-3/3.4.1.test-data-scenarios.md) + [3.4.2](../../stories/epic-3/3.4.2.conflict-scenarios-testing.md) + [3.4.3](../../stories/epic-3/3.4.3.data-integrity-checks.md)
**Assigned:** \*agent dev | **Estimate:** 16ч | **Status:** ⏳ Pending
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
**Assigned:** \*agent dev | **Estimate:** 12ч | **Status:** ⏳ Pending
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
**Assigned:** \*agent dev | **Estimate:** 12ч | **Status:** ⏳ Pending
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

##### **Task 3.1.2-B: Тестирование импорта с реальными данными 1С**

**📋 Story:** [3.1.2 loading-scripts](../../stories/epic-3/3.1.2.loading-scripts.md) - AC: 2,3,4
**Assigned:** \*agent dev | **Estimate:** 6ч | **Status:** ⏳ Pending
**Due Date:** _18.09.2025_

**Subtasks:**

- [ ] Валидация реальных файлов из data/import_1c (Story AC: 2)
- [ ] Тестирование загрузки категорий с иерархией из groups.xml
- [ ] Тестирование связей между товарами, категориями и брендами (Story AC: 3)
- [ ] Тестирование обработки дубликатов по onec_id (Story AC: 4)
- [ ] Создание integration тестов с реальными данными
- [ ] Performance тестирование на полном каталоге

**Progress:** 0% □□□□□□□□□□
**🔴 Blocking Factor:** Нет. Реальные данные доступны в data/import*1c
**Notes:** *Используем реальные данные из 1С вместо генерации тестовых. Структура включает сегментированные файлы (goods*1*\_.xml, offers\_\_.xml), изображения в goods/import*files/[XY]/, справочники contragents, propertiesGoods, propertiesOffers*

---

##### **Task 3.2.1-B: Реальная синхронизация клиентов (Завершение Story 3.2.1 v1.4)**

**📋 Story:** [3.2.1.0 import-existing-customers](../../stories/epic-3/3.2.1.0.import-existing-customers.md) - AC: 1,2,4,5,6,7
**Assigned:** \*agent dev | **Estimate:** 20ч | **Status:** ⏳ Pending
**Due Date:** _22.09.2025_

**Subtasks:**

**Архитектура Парсер/Процессор (Story AC: 2):**

- [ ] Создать `CustomerDataParser` в `apps/users/services/parser.py`
  - [ ] Метод `parse()` для парсинга CommerceML 3.1 (`<КоммерческаяИнформация>` → `<Контрагенты>` → `<Контрагент>`)
  - [ ] Обработка полей: `<Ид>`, `<Наименование>`, `<ПолноеНаименование>`, `<ОфициальноеНаименование>`, `<ИНН>`, `<КПП>`
  - [ ] Обработка `<Представители>`, `<АдресРегистрации>`, `<Контакты>`, `<РасчетныеСчета>`
  - [ ] Определение типа клиента (юр.лицо/ИП/физ.лицо) по наличию КПП и ИНН
  - [ ] Unit тесты (3 теста: валидный XML, пустой файл, некорректный XML)

- [ ] Создать `CustomerDataProcessor` в `apps/users/services/processor.py`
  - [ ] Метод `process_customers()` с поддержкой chunk_size
  - [ ] Метод `process_customer()` для обработки одного клиента
  - [ ] Метод `map_role()` с маппингом: Опт 1→wholesale_level1, Опт 2→wholesale_level2, Опт 3→wholesale_level3, Тренерская→trainer, РРЦ→retail
  - [ ] Создание/обновление User с установкой полей: onec_id, created_in_1c, sync_status, last_sync_at
  - [ ] Логирование в CustomerSyncLog для каждой операции (created/updated/skipped/error)
  - [ ] Обработка дубликатов по onec_id и email
  - [ ] Валидация email и обязательных полей
  - [ ] Unit тесты (4 теста: маппинг ролей, создание клиента, обновление, пропуск невалидного)

**Команда import_customers_from_1c (Story AC: 1):**

- [ ] Создать `apps/users/management/commands/import_customers_from_1c.py`
- [ ] Параметры: `--file` (required), `--chunk-size` (default=100), `--dry-run`
- [ ] Валидация: проверка существования файла, проверка chunk_size > 0
- [ ] Проверка активных сессий импорта (concurrent execution protection)
- [ ] Создание ImportSession с типом CUSTOMERS
- [ ] Использование CustomerDataParser и CustomerDataProcessor
- [ ] Транзакционная обработка с rollback при ошибках
- [ ] Вывод статистики: total, created, updated, skipped, errors
- [ ] Поддержка dry-run режима
- [ ] Integration тесты (3 теста: успешный импорт, dry-run, обработка ошибок)

**Performance оптимизации (Story v1.4 - метрики производительности):**

- [ ] Использовать bulk_create/bulk_update для пакетной обработки
- [ ] Оптимизировать запросы к БД (select_related, prefetch_related)
- [ ] Настроить chunk_size для баланса памяти/скорости
- [ ] Целевая производительность: 1000 клиентов за ~1-2 минуты

**Тестирование (Story AC: 7):**

- [ ] Unit тесты для CustomerDataParser (3 теста)
- [ ] Unit тесты для CustomerDataProcessor (4 теста)
- [ ] Integration тесты для команды (3 теста)
- [ ] Тестовые данные в `backend/tests/fixtures/1c-data/customers/`
- [ ] Покрытие ≥90% для критических модулей

**Progress:** 0% □□□□□□□□□□
**🔴 Blocking Factor:** Нет. Реальная структура CommerceML 3.1 получена из `backend/tests/fixtures/1c-data/contragents/contragents.xml`
**Notes:** _Полностью реализует Story 3.2.1 v1.4 после Task 3.2.1-A. Включает все исправления Фаз 1-3._
**📊 Performance Target:** 1000 клиентов за 1-2 минуты, 5000 клиентов за 5-10 минут

---

##### **Task 3.2.3: Bidirectional Sync (Реализация Story 3.2.3)**

**📋 Story:** [3.2.3 bidirectional-sync](../../stories/epic-3/3.2.3.bidirectional-sync.md) - AC: 1,2,3,4,5,6,7
**Assigned:** \*agent dev | **Estimate:** 20ч | **Status:** ⏳ Pending
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

##### **Task 3.2.2 + 3.2.1.5: Conflict Resolution (Реализация Stories 3.2.2, 3.2.1.5)**

**📋 Stories:** [3.2.2 conflict-resolution](../../stories/epic-3/3.2.2.conflict-resolution.md) (SP: 8) + [3.2.1.5 customer-identity-algorithms](../../stories/epic-3/3.2.1.5.customer-identity-algorithms.md) (SP: 5)
**Assigned:** \*agent dev | **Estimate:** 16ч | **Status:** ⏳ Pending
**Due Date:** _04.10.2025_

**Subtasks:**

**CustomerIdentityResolver (Story 3.2.1.5 - детерминированная идентификация):**

- [ ] Создать `CustomerIdentityResolver` в `apps/users/services/identity_resolution.py`
- [ ] Реализовать метод `identify_customer(onec_customer_data)` с приоритетами:
  - [ ] Приоритет 1: поиск по `onec_id` (100% точность)
  - [ ] Приоритет 2: поиск по `onec_guid` (100% точность)
  - [ ] Приоритет 3: поиск по `tax_id` (ИНН для B2B)
  - [ ] Приоритет 4: поиск по `email` (для B2C)
- [ ] Реализовать методы нормализации: `normalize_inn()`, `normalize_email()`
- [ ] Логирование всех попыток идентификации в CustomerSyncLog
- [ ] Unit тесты для всех сценариев идентификации (Story 3.2.1.5 AC: 7)

**CustomerConflictResolver (Story 3.2.2 - стратегия onec_wins):**

- [ ] Создать `CustomerConflictResolver` в `apps/users/services/conflict_resolution.py`
- [ ] Реализовать единственную стратегию: `onec_wins` (1C как источник истины)
- [ ] Реализовать метод `resolve_conflict(existing_customer, onec_data, conflict_source)`
- [ ] Обработка сценария `portal_registration`: присвоение статуса 'confirmed_client'
- [ ] Обработка сценария `data_import`: перезапись конфликтующих полей данными из 1С
- [ ] Email уведомления администратору при каждом конфликте
- [ ] Создание записей в SyncConflict с архивом (platform_data + onec_data)
- [ ] Логирование в CustomerSyncLog с детализацией изменений
- [ ] Unit и Integration тесты для обоих сценариев (Story 3.2.2 AC: 7)

**Progress:** 0% □□□□□□□□□□
**🔴 Blocking Factor:** Нет.
**Notes:** _Упрощенная стратегия: детерминированная идентификация + 1C как единственный источник истины. Без fuzzy matching, без Django Admin модерации._
**⚠️ ВАЖНО:** Все конфликты разрешаются автоматически, email уведомления обязательны, полный audit trail в SyncConflict.

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
- [ ] **Story 3.2.1 Performance:** Импорт 1000 клиентов за ~1-2 минуты
- [ ] **Story 3.2.1 Quality:** Покрытие тестами ≥90% для CustomerDataParser, CustomerDataProcessor, CustomerSyncLog
- [ ] **Story 3.2.1 Concurrent:** Защита от одновременного запуска нескольких команд импорта работает
- [ ] Bidirectional sync функционирует
- [ ] Conflict resolution обрабатывает edge cases
- [ ] Performance targets достигнуты

---

## 📝 DAILY UPDATES LOG

### 2025-10-19 (Сегодня)

- [x] **Sprint Change Proposal 3.1.3 approved** - Story переориентирована на валидацию реального импорта
- [x] Story 3.1.3 обновлена: новые AC, Tasks, DoD для работы с реальными данными из data/import_1c/
- [x] Execution plan Task 3.1.3 обновлен: новые subtasks, estimate снижен до 10ч
- [x] Plan Update History обновлена (v1.7)
- 🎯 **Next:** Начать Task 3.1.1-A (\*agent dev)

### 2025-10-11

- [x] Epic 3 execution plan актуализирован
- [x] Все ошибочные отметки о выполнении сброшены
- [x] Story 3.1.5 валидирована и приведена к формату шаблона
- [x] Story 3.2.1 прошла Фазы 1-3 исправлений (версия 1.4)
- [x] Execution plan обновлен с детальными задачами для Story 3.2.1

### 2025-09-08

- [ ] **Planned:** Завершить Task 3.1.1-A (Product модель)
- [ ] **Planned:** Follow-up программисту 1С

---

## 🔄 PLAN UPDATE HISTORY

**v1.0 (07.09.2025):** Первоначальный план создан
**v1.1 (11.10.2025):** Сброшены ошибочные отметки о выполнении, актуализированы статусы задач
**v1.2 (11.10.2025):** Обновлены Tasks 3.2.1-A и 3.2.1-B с детальными подзадачами после исправлений Story 3.2.1 v1.4 (Фазы 1-3). Добавлены метрики производительности и критерии успеха.
**v1.3 (14.10.2025):** Story 3.3.1 переименована в 3.2.1.5 (customer-identity-algorithms) - это подстория импорта клиентов для логической последовательности. Обновлены все ссылки в execution-plan и stories.
**v1.4 (14.10.2025):** Story 3.2.1 переименована в 3.2.1.0 (import-existing-customers) - базовая история с подсториями 3.2.1.5. Обновлены все ссылки.
**v1.5 (19.10.2025):** **Sprint Change Proposal 3.1.2:** Удалена команда load_test_catalog из Task 3.1.2-A (используем реальные данные из data/import_1c). Task 3.1.2-A обновлен - добавлены команды restore_db и rotate_backups. Task 3.1.2-B переименован в "Тестирование импорта с реальными данными 1С".
**v1.6 (19.10.2025):** Добавлена детальная структура данных data/import_1c/ в Task 3.1.2-B Notes согласно фактической выгрузке из 1С.
**v1.7 (19.10.2025):** **Sprint Change Proposal 3.1.3:** Story 3.1.3 переориентирована с генерации синтетических данных (load_test_catalog) на валидацию реального импорта из data/import_1c/. Task 3.1.3 обновлен - фокус на валидации ~6200 реальных товаров. Estimate снижен с 12ч до 10ч.

---

## 📞 CONTACTS & ESCALATION

**Project Lead:** BMad Orchestrator
**Primary Developer:** *agent dev
**QA Lead:** *agent qa
**Architect:** \*agent architect

**External Dependencies:**

**1С Programmer:** _[контакт нужно добавить]_ - Status: ⏳ Awaiting response

**Next Review:** 12.10.2025 (ежедневный checkpoint)
**Next Milestone Review:** 18.10.2025 (Milestone 1.1)

---

**🚀 ПЛАН АКТИВЕН И ГОТОВ К ИСПОЛНЕНИЮ!**

\*Последнее обновление: 14.10.2025 by PO Agent (реструктуризация: 3.3.1 → 3.2.1.5, 3.2.1 → 3.2.1.0)
