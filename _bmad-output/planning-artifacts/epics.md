---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - docs/prd/1c-order-exchange.md
  - docs/integrations/1c/architecture.md
  - docs/architecture-backend.md
---

# FREESPORT - 1C Order Exchange - Epic Breakdown

## Overview

Декомпозиция требований модуля обмена заказами с 1С (двусторонний обмен: экспорт заказов, импорт статусов) в эпики и user stories.

## Requirements Inventory

### Functional Requirements

**FR1: Экспорт заказов (Сайт -> 1С)**

- FR1.1: Реализовать `mode=query` для выгрузки заказов в XML (1С запрашивает URL, получает XML)
- FR1.2: Все новые заказы передаются одним файлом (пакетная передача)
- FR1.3: Поддержка ZIP-сжатия (`zip=yes`) при запросе от 1С
- FR1.4: Корневой тег XML: `<КоммерческаяИнформация>` (CommerceML 3.1)
- FR1.5: Каждый заказ должен быть обернут в тег `<Контейнер>`, содержащий тег `<Документ>` с `<ХозОперация>Заказ товара</ХозОперация>`
- FR1.6: Блок `<Контрагенты>` с ИНН (поиск в 1С по ИНН или наименованию)
- FR1.7: Блок `<Товары>` с `onec_id` для связи товаров
- FR1.8: Подтверждение `mode=success` — помечать заказы `sent_to_1c=true` только после сигнала

**FR2: Импорт статусов (1С -> Сайт)**

- FR2.1: Обработка файла `orders.xml` через `mode=file` (входящий поток из 1С)
- FR2.2: Парсинг заказов по `<Номер>` или `<Ид>`
- FR2.3: Обновление статуса по `<ЗначениеРеквизита>` с маппингом (Отгружен→shipped, Доставлен→delivered и т.д.)
- FR2.4: Сохранение дат оплаты/отгрузки из реквизитов

**FR3: Модель данных Order**

- FR3.1: Добавить поле `sent_to_1c: BooleanField` в модель Order
- FR3.2: Добавить поле `sent_to_1c_at: DateTimeField` в модель Order
- FR3.3: Добавить поле `status_1c: CharField` для оригинального статуса из 1С

### NonFunctional Requirements

- NFR1: Формат XML — строго CommerceML 3.1
- NFR2: Кодировка UTF-8 или windows-1251 (по заголовку 1С), стандартно UTF-8
- NFR3: Безопасность — аутентификация 1С через технического пользователя `1c_user` (Basic Auth при `mode=checkauth`), все запросы в рамках сессии
- NFR4: Хранение файлов — XML генерируются "на лету", копии для отладки в `MEDIA_ROOT/1c_exchange/logs/`

### Additional Requirements

- Service Layer паттерн: бизнес-логика в `services.py`, не во views — OrderExportService, OrderImportService должны быть сервисами
- Celery: тяжёлые задачи (импорт) через Celery, но `mode=query` — синхронный (1С ждёт HTTP-ответ)
- ImportSession: операции импорта оборачиваются в сессии для атомарности
- Parser/Processor разделение: парсинг XML отделён от бизнес-логики обработки
- Audit Trail: полное логирование всех операций импорта/экспорта
- Idempotency: повторная обработка не должна нарушать целостность
- Status Mapping: 6 статусов с маппингом (pending→Принят, shipped→Отгружен и т.д.)
- Risk mitigations: обработка отсутствия ИНН, защита от дублирования заказов, ZIP для больших XML

### FR Coverage Map

| FR | Epic | Описание |
|----|------|----------|
| FR3.1, FR3.2, FR3.3 | Epic 4 | Поля модели Order для отслеживания синхронизации с 1С |
| FR1.1 | Epic 4 | mode=query endpoint для выгрузки заказов |
| FR1.2 | Epic 4 | Пакетная передача всех новых заказов одним файлом |
| FR1.3 | Epic 4 | ZIP-сжатие при запросе от 1С |
| FR1.4, FR1.5 | Epic 4 | XML структура CommerceML 3.1 (КоммерческаяИнформация, Документ) |
| FR1.6 | Epic 4 | Контрагенты с ИНН |
| FR1.7 | Epic 4 | Товары с onec_id |
| FR1.8 | Epic 4 | mode=success подтверждение отправки |
| FR2.1 | Epic 5 | Приём orders.xml через mode=file |
| FR2.2 | Epic 5 | Парсинг заказов по Номер/Ид |
| FR2.3 | Epic 5 | Маппинг статусов 1С → FREESPORT |
| FR2.4 | Epic 5 | Сохранение дат оплаты/отгрузки |

## Epic List

### Epic 4: Экспорт заказов в 1С

Менеджеры 1С автоматически получают заказы покупателей с сайта через стандартный протокол обмена CommerceML 3.1. Заказы содержат данные контрагента (с ИНН), товары (с onec_id) и реквизиты. Поддерживается ZIP-сжатие и подтверждение доставки (mode=success).

**FRs covered:** FR3.1, FR3.2, FR3.3, FR1.1, FR1.2, FR1.3, FR1.4, FR1.5, FR1.6, FR1.7, FR1.8
**NFRs covered:** NFR1, NFR2, NFR3, NFR4
**Тестирование:** Unit-тесты сервисов (OrderExportService, XML-генерация) + Integration-тесты (mode=query, mode=success endpoints) по стандартам 10-testing-strategy.md

#### Story 4.1: Поля модели Order для интеграции с 1С

As a **разработчик**,
I want **добавить поля sent_to_1c, sent_to_1c_at, status_1c в модель Order**,
So that **система может отслеживать статус синхронизации каждого заказа с 1С**.

**Acceptance Criteria:**

**Given** модель Order существует
**When** применяется миграция с новыми полями
**Then** Order имеет поля: `sent_to_1c` (BooleanField, default=False), `sent_to_1c_at` (DateTimeField, null=True), `status_1c` (CharField, max_length=50, blank=True)
**And** поля видны в Django Admin
**And** unit-тест проверяет дефолтные значения полей (FR3.1, FR3.2, FR3.3)

#### Story 4.2: Сервис генерации XML заказов (OrderExportService)

> [!IMPORTANT]
> **Developer Notice (CommerceML 3.1):**
> Реализация должна строго соответствовать схеме 3.1.
> Обратить внимание на использование тега `<Контейнер>` для группировки документов (отличие от 2.10).
> Проверить текущую заглушку в `views.py` перед началом работы.

As a **система интеграции**,
I want **сервис, формирующий XML заказов в формате CommerceML 3.1**,
So that **1С может распознать и обработать заказы с сайта**.

**Acceptance Criteria:**

**Given** существуют неотправленные заказы (sent_to_1c=False) с товарами и контрагентом
**When** вызывается `OrderExportService.generate_xml()`
**Then** XML содержит корневой тег `<КоммерческаяИнформация ВерсияСхемы="3.1">` (FR1.4)
**And** каждый заказ обёрнут в `<Документ>` с `<ХозОперация>Заказ товара</ХозОперация>` (FR1.5)
**And** блок `<Контрагенты>` содержит `<ИНН>` при наличии tax_id у пользователя, иначе тег опускается (FR1.6)
**And** блок `<Товары>` содержит `<Ид>` с onec_id каждого товара (FR1.7)
**And** все заказы передаются одним XML-документом (FR1.2)
**And** XML кодирован в UTF-8 (NFR2)
**And** unit-тесты проверяют: корректность XML-структуры, обработку заказа без ИНН, формирование нескольких заказов в одном документе
**And** сервис реализован в `services.py` согласно Service Layer паттерну

#### Story 4.3: View-обработчики mode=query и mode=success

> [!IMPORTANT]
> **Developer Notice (Partial Implementation):**
> Базовый класс `ICExchangeView` уже существует (реализован в рамках Transport Layer).
> Необходимо дополнить методы `handle_query` (сейчас заглушка) и реализовать `handle_success`.
> Убедитесь, что `handle_query` использует `OrderExportService` с поддержкой 3.1.

As a **1С система**,
I want **запрашивать заказы через mode=query и подтверждать получение через mode=success**,
So that **заказы передаются по стандартному протоколу обмена с гарантией доставки**.

**Acceptance Criteria:**

**Given** 1С аутентифицирована через существующий mode=checkauth (NFR3)
**When** 1С отправляет GET-запрос `?type=sale&mode=query`
**Then** ответ содержит XML со всеми заказами где sent_to_1c=False (FR1.1)

**Given** 1С запрашивает `?type=sale&mode=query&zip=yes`
**When** обработчик формирует ответ
**Then** XML возвращается в ZIP-архиве с Content-Type: application/zip (FR1.3)

**Given** 1С успешно приняла заказы
**When** 1С отправляет GET-запрос `?type=sale&mode=success`
**Then** все ранее выгруженные заказы помечаются sent_to_1c=True и sent_to_1c_at=now() (FR1.8)

**And** копии XML сохраняются в `MEDIA_ROOT/1c_exchange/logs/` для отладки (NFR4)
**And** integration-тесты: запрос mode=query возвращает валидный XML, mode=success обновляет флаги заказов, zip=yes возвращает архив

#### Story 4.4: Integration-тесты полного цикла экспорта

As a **команда разработки**,
I want **E2E тесты полного цикла экспорта заказов**,
So that **мы уверены в корректности работы всей цепочки: создание заказа → XML-генерация → HTTP-выгрузка → подтверждение**.

**Acceptance Criteria:**

**Given** тестовый заказ с товарами (onec_id) и контрагентом (с ИНН и без)
**When** выполняется полный цикл: query → парсинг XML ответа → success
**Then** заказ помечен sent_to_1c=True
**And** XML валиден по схеме CommerceML 3.1
**And** тесты используют Factory Boy с `get_unique_suffix()`, маркеры `@pytest.mark.integration`, `@pytest.mark.django_db`
**And** AAA-паттерн (Arrange/Act/Assert) во всех тестах
**And** покрытие критических модулей >= 90%

### Epic 5: Импорт статусов заказов из 1С

Покупатели видят актуальный статус своего заказа (обработка, отгрузка, доставка), который автоматически обновляется при получении orders.xml из 1С. Маппинг статусов: Отгружен→shipped, Доставлен→delivered, Отменен→cancelled. Сохраняются даты оплаты и отгрузки.

**FRs covered:** FR2.1, FR2.2, FR2.3, FR2.4
**NFRs covered:** NFR1, NFR2, NFR3
**Тестирование:** Unit-тесты сервисов (OrderStatusImportService, XML-парсинг, маппинг статусов) + Integration-тесты (mode=file endpoint, полный цикл обновления статуса) по стандартам 10-testing-strategy.md

#### Story 5.1: Сервис импорта статусов (OrderStatusImportService)

As a **система интеграции**,
I want **сервис, парсящий orders.xml из 1С и обновляющий статусы заказов**,
So that **статусы заказов на сайте соответствуют актуальным данным из 1С**.

**Acceptance Criteria:**

**Given** XML-файл orders.xml в формате CommerceML 3.1 с тегами `<Контейнер>`, содержащими `<Документ>`
**When** вызывается `OrderStatusImportService.process(xml_data)`
**Then** заказ найден по `<Номер>` или `<Ид>` (FR2.2)
**And** статус обновлён по маппингу: Отгружен→shipped, Доставлен→delivered, ОжидаетОбработки→processing, Отменен→cancelled (FR2.3)
**And** оригинальный статус из 1С сохранён в поле `status_1c`
**And** даты оплаты и отгрузки извлечены из `<ЗначениеРеквизита>` и сохранены (FR2.4)
**And** при неизвестном статусе — логируется предупреждение, заказ не обновляется
**And** при отсутствии заказа по ID — логируется ошибка, обработка продолжается
**And** unit-тесты: парсинг XML, маппинг всех 6 статусов, обработка отсутствующего заказа, извлечение дат
**And** сервис реализован в `services.py`, парсинг XML отделён от бизнес-логики (Parser/Processor)

#### Story 5.2: View-обработчик mode=file для orders.xml

As a **1С система**,
I want **отправлять файл orders.xml с обновлёнными статусами через mode=file**,
So that **статусы заказов на сайте обновляются автоматически при обработке в 1С**.

**Acceptance Criteria:**

**Given** 1С аутентифицирована через существующий mode=checkauth (NFR3)
**When** 1С отправляет POST `?type=sale&mode=file&filename=orders.xml` с XML в теле запроса
**Then** файл распознаётся как orders.xml (по filename) и маршрутизируется в OrderStatusImportService (FR2.1)
**And** ответ: `success` при успешной обработке
**And** обработка идемпотентна — повторная отправка того же файла не ломает данные
**And** копия файла сохраняется в `MEDIA_ROOT/1c_exchange/logs/` для отладки (NFR4)
**And** integration-тесты: POST с XML обновляет статус заказа в БД, повторная отправка не создаёт ошибок

#### Story 5.3: Integration-тесты полного цикла импорта статусов

As a **команда разработки**,
I want **E2E тесты полного цикла: экспорт заказа → симуляция ответа 1С → импорт статуса**,
So that **двусторонний обмен заказами с 1С работает корректно от начала до конца**.

**Acceptance Criteria:**

**Given** заказ экспортирован в 1С (sent_to_1c=True)
**When** 1С отправляет orders.xml со статусом «Отгружен» для этого заказа
**Then** статус заказа обновлён на `shipped`, `status_1c` = «Отгружен»
**And** тест проверяет все 4 статуса маппинга (processing, shipped, delivered, cancelled)
**And** тест проверяет извлечение дат оплаты и отгрузки
**And** тест проверяет обработку невалидного XML (ошибка парсинга, неизвестный заказ)
**And** Factory Boy с `get_unique_suffix()`, маркеры `@pytest.mark.integration`, `@pytest.mark.django_db`
**And** AAA-паттерн во всех тестах
