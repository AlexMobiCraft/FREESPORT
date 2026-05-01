---
status: ready-for-dev
area: 1c-integration
type: dev-task
created: 2026-05-01
updated: 2026-05-01
related:
  - docs/prd/1c-order-exchange.md
  - docs/integrations/1c/architecture.md
  - docs/integrations/1c/analysis-orders-xml.md
  - docs/architecture/request-to-1c-developer.md
---

# Задание для dev-агента: реализовать загрузку статусов заказов для 1С-Битрикс через `mode=info`

## Цель

Исправить ошибку в 1С:

> Не удалось прочитать данные, загруженные с сервера

Ошибка возникает при нажатии кнопки **"Загрузить с сайта"** в настройках обмена заказами модуля **"1С-Битрикс. Управление сайтом"**, в таблице сопоставления **"Статусы заказов"**.

Нужно доработать backend FREESPORT так, чтобы endpoint обмена с 1С поддерживал стандартный для Bitrix режим:

```text
type=sale&mode=info
```

и возвращал XML-справочник статусов заказов в формате, совместимом с 1С-Битрикс.

## Связанные решения и документы

- **PRD обмена заказами:** [docs/prd/1c-order-exchange.md](../../prd/1c-order-exchange.md)
- **Архитектура 1С-интеграции:** [docs/integrations/1c/architecture.md](./architecture.md)
- **Анализ XML заказов и справочников:** [docs/integrations/1c/analysis-orders-xml.md](./analysis-orders-xml.md)
- **Вопросы к 1С-разработчику:** [docs/architecture/request-to-1c-developer.md](../../architecture/request-to-1c-developer.md)

## Статус актуализации документации

Задание синхронизировано с обновлёнными документами проекта:

- В PRD добавлено функциональное требование `FR2A` для `type=sale&mode=info`.
- В архитектуре 1С-интеграции `mode=info` добавлен в HTTP-протокол и Transport Layer.
- В XML-анализе зафиксировано отличие справочника `mode=info` от файла `orders.xml`.
- В запросе к 1С-разработчику добавлены вопросы по кнопке **"Загрузить с сайта"** и формату обратной передачи статусов.

Этот файл можно использовать как входное ТЗ для dev-агента без дополнительной переработки.

## Контекст проблемы

В текущей реализации `ICExchangeView` поддерживает основные режимы обмена:

- **`checkauth`**: авторизация 1С на сайте.
- **`init`**: инициализация обмена и получение параметров сервера.
- **`query`**: получение заказов с сайта.
- **`file`**: загрузка файла от 1С на сайт.
- **`import`**: обработка ранее загруженного файла.
- **`success`**: подтверждение успешной выгрузки заказов.
- **`complete`**: завершение обмена.
- **`deactivate`**: служебный режим деактивации.

Но **не поддерживает `mode=info`**.

Стандартный компонент Bitrix `sale.export.1c` имеет отдельную ветку:

```php
elseif($_GET["mode"] == "info")
```

В этом режиме Bitrix отдаёт XML-справочник:

- **статусы заказов сайта**;
- **платёжные системы**.

Именно этот режим используется 1С для автозаполнения таблиц сопоставления.

Сейчас 1С, вероятно, получает от FREESPORT ответ вида:

```text
failure
Unknown mode
```

или иной не-XML ответ, из-за чего показывает ошибку чтения данных.

## Что нужно сделать

### 1. Найти точку входа обмена с 1С

Основной файл:

```text
backend/apps/integrations/onec_exchange/views.py
```

Класс:

```python
ICExchangeView
```

Нужно найти место, где маршрутизируются режимы `mode`.

Сейчас там есть обработка вида:

```python
elif mode == "query":
    return self.handle_query(request)
```

Нужно добавить обработку:

```python
elif mode == "info":
    return self.handle_info(request)
```

### 2. Реализовать `handle_info`

Добавить метод в `ICExchangeView`, который будет возвращать XML-справочник в формате Bitrix.

Ожидаемая структура XML:

```xml
<?xml version="1.0" encoding="windows-1251"?>
<Справочник>
  <Cтатусы>
    <Элемент>
      <Ид>ОжидаетОбработки</Ид>
      <Название>ОжидаетОбработки</Название>
    </Элемент>
    <Элемент>
      <Ид>Подтвержден</Ид>
      <Название>Подтвержден</Название>
    </Элемент>
    <Элемент>
      <Ид>Отгружен</Ид>
      <Название>Отгружен</Название>
    </Элемент>
    <Элемент>
      <Ид>Доставлен</Ид>
      <Название>Доставлен</Название>
    </Элемент>
    <Элемент>
      <Ид>Отменен</Ид>
      <Название>Отменен</Название>
    </Элемент>
    <Элемент>
      <Ид>Возвращен</Ид>
      <Название>Возвращен</Название>
    </Элемент>
  </Cтатусы>
  <ПлатежныеСистемы />
</Справочник>
```

Важное замечание:

- **Тег статусов в Bitrix выглядит как `Cтатусы`**: первая буква визуально похожа на русскую `С`, но в исходном языковом файле Bitrix может быть латинская `C`.
- Для максимальной совместимости нужно воспроизвести формат как в Bitrix:
  - корень: `Справочник`;
  - блок статусов: `Cтатусы`;
  - блок платёжных систем: `ПлатежныеСистемы`;
  - элемент: `Элемент`;
  - идентификатор: `Ид`;
  - название: `Название`.

### 3. Источник статусов

Минимально допустимый вариант — использовать ключи из текущего маппинга 1С → FREESPORT.

Файл:

```text
backend/apps/orders/constants.py
```

Константа:

```python
STATUS_MAPPING
```

Текущие значения:

```python
STATUS_MAPPING: dict[str, str] = {
    "ОжидаетОбработки": "processing",
    "Подтвержден": "confirmed",
    "Отгружен": "shipped",
    "Доставлен": "delivered",
    "Отменен": "cancelled",
    "Возвращен": "refunded",
}
```

Рекомендация:

- Для `mode=info` отдавать именно ключи `STATUS_MAPPING`.
- В XML указывать одинаковое значение в `Ид` и `Название`.
- Это снижает риск, что 1С отправит обратно значение, которое backend не сможет распознать.

Дополнительно проверить необходимость включения статуса:

```text
Не согласован
```

Почему:

- Сейчас `OrderExportService` по умолчанию отправляет в 1С реквизит `Статус заказа` со значением `Не согласован`.
- Это значение задано в настройках по умолчанию экспорта заказов.
- Если 1С ожидает увидеть в справочнике все статусы, которые сайт может отправить в XML заказа, то `Не согласован` тоже нужно включить.

Файл для проверки:

```text
backend/apps/orders/services/order_export.py
```

Место:

```python
self._add_requisite(doc_props, "Статус заказа", order_defaults["STATUS"])
```

и:

```python
"STATUS": defaults.get("STATUS", "Не согласован")
```

Решение по `Не согласован` принять после проверки текущей логики и тестов. Если сомнений нет — лучше включить в справочник, чтобы 1С могла сопоставить и этот начальный статус.

### 4. Не сломать существующий обмен

Нельзя менять поведение режимов:

- **`checkauth`**;
- **`init`**;
- **`query`**;
- **`file`**;
- **`import`**;
- **`success`**.

Особенно важно не сломать:

- **экспорт заказов в 1С через `mode=query`**;
- **подтверждение экспорта через `mode=success`**;
- **импорт статусов из 1С через `mode=file`**.

## Файлы проекта, которые нужно изучить

### Основной endpoint обмена

```text
file:///c:/Users/1/DEV/FREESPORT/backend/apps/integrations/onec_exchange/views.py
```

Что смотреть:

- **класс**: `ICExchangeView`;
- **обработку параметров**: `type` и `mode`;
- **методы**:
  - `handle_query`;
  - `handle_success`;
  - `handle_import`;
  - `_handle_orders_xml`;
- **текущий формат ответов для 1С**;
- **текущую работу с кодировкой XML**.

### Сервис экспорта заказов сайт → 1С

```text
file:///c:/Users/1/DEV/FREESPORT/backend/apps/orders/services/order_export.py
```

Что смотреть:

- **генерацию CommerceML XML**;
- **реквизит `Статус заказа`**;
- **дефолтное значение `Не согласован`**;
- **`SCHEMA_VERSION`**;
- **метод `_get_order_defaults`**.

### Маппинг статусов 1С → FREESPORT

```text
file:///c:/Users/1/DEV/FREESPORT/backend/apps/orders/constants.py
```

Что смотреть:

- **`STATUS_MAPPING`**;
- **`STATUS_MAPPING_LOWER`**;
- **`ORDER_STATUSES`**;
- **`FINAL_STATUSES`**;
- **`ACTIVE_STATUSES`**;
- **`ALLOWED_REQUISITES`**.

### Сервис импорта статусов из 1С

```text
file:///c:/Users/1/DEV/FREESPORT/backend/apps/orders/services/order_status_import.py
```

Что смотреть:

- **`OrderStatusImportService`**;
- **парсинг реквизита `СтатусЗаказа` / `Статус Заказа`**;
- **использование `STATUS_MAPPING`**;
- **обработку неизвестных статусов**;
- **защиту от регрессии статуса**.

## Документация проекта

### PRD по обмену заказами с 1С

```text
file:///c:/Users/1/DEV/FREESPORT/docs/prd/1c-order-exchange.md
```

Особенно разделы:

- **экспорт заказов сайт → 1С**;
- **импорт статусов 1С → сайт**;
- **таблица `Status Mapping`**.

### Анализ XML заказов

```text
file:///c:/Users/1/DEV/FREESPORT/docs/integrations/1c/analysis-orders-xml.md
```

Особенно:

- **реквизит `Статус заказа`**;
- **формат CommerceML**;
- **замечания по статусам**.

### Архитектура интеграции 1С

```text
file:///c:/Users/1/DEV/FREESPORT/docs/integrations/1c/architecture.md
```

### Запрос к 1С-разработчику

```text
file:///c:/Users/1/DEV/FREESPORT/docs/architecture/request-to-1c-developer.md
```

Особенно разделы про:

- **статусы заказов**;
- **обратную передачу статусов из 1С**;
- **требования к 1С-разработчику**.

### Вики FREESPORT: интеграция 1С

```text
file:///c:/Users/1/DEV/FREESPORT_WIKI/FREESPORT%20WIKI/wiki/views/1c-integration.md
```

### Вики FREESPORT: сущность заказа

```text
file:///c:/Users/1/DEV/FREESPORT_WIKI/FREESPORT%20WIKI/wiki/entities/order.md
```

## Внешняя документация и найденные источники

### Официальный протокол обмена с сайтом 1С

```text
https://v8.1c.ru/tekhnologii/obmen-dannymi-i-integratsiya/standarty-i-formaty/protokol-obmena-s-saytom/
```

Что подтверждает:

- **последовательность обмена**;
- **`checkauth`**;
- **`init`**;
- **`query`**;
- **`success`**;
- **`file`**;
- **общий формат HTTP-обмена с сайтом**.

### Документация Bitrix по компоненту `sale.export.1c`

```text
https://dev.1c-bitrix.ru/user_help/components/magazin/export_zakaz/sale_export_1c.php
```

Что подтверждает:

- **компонент Bitrix для экспорта заказов в CommerceML**;
- **параметры обмена заказами**;
- **связь с типовым механизмом 1С-Битрикс**.

### Типовые ошибки обмена 1С-Битрикс

```text
https://dev.1c-bitrix.ru/learning/course/index.php?COURSE_ID=131&LESSON_ID=4933
```

Что полезно:

- **общие рекомендации по диагностике обмена**;
- **важность корректных ответов сайта**;
- **типовые проблемы чтения/обработки данных**.

### Исходник стандартного Bitrix admin endpoint `1c_exchange.php`

```text
https://raw.githubusercontent.com/devsandk/bitrix_utf8/master/bitrix/modules/sale/admin/1c_exchange.php
```

Что подтверждает:

- **`type=sale` подключает компонент `bitrix:sale.export.1c`**;
- **обмен заказами идёт через стандартный Bitrix-компонент**.

### Исходник компонента Bitrix `sale.export.1c`

```text
https://raw.githubusercontent.com/devsandk/bitrix_utf8/master/bitrix/components/bitrix/sale.export.1c/component.php
```

Ключевое место:

```php
elseif($_GET["mode"] == "info")
{
    ?><<?="?"?>xml version="1.0" encoding="windows-1251"<?="?"?>>
    <<?=GetMessage("CC_BSC1_DI_GENERAL")?>>
        <<?=GetMessage("CC_BSC1_DI_STATUSES")?>>
        <?
        $dbStatus = CSaleStatus::GetList(array("SORT" => "ASC"), array("LID" => LANGUAGE_ID), false, false, array("ID", "NAME"));
        while ($arStatus = $dbStatus->Fetch())
        {
            ?>
            <<?=GetMessage("CC_BSC1_DI_ELEMENT")?>>
                <<?=GetMessage("CC_BSC1_DI_ID")?>><?=$arStatus["ID"]?></<?=GetMessage("CC_BSC1_DI_ID")?>>
                <<?=GetMessage("CC_BSC1_DI_NAME")?>><?=htmlspecialcharsbx($arStatus["NAME"])?></<?=GetMessage("CC_BSC1_DI_NAME")?>>
            </<?=GetMessage("CC_BSC1_DI_ELEMENT")?>>
            <?
        }
        ?>
        </<?=GetMessage("CC_BSC1_DI_STATUSES")?>>
        <<?=GetMessage("CC_BSC1_DI_PS")?>>
        ...
        </<?=GetMessage("CC_BSC1_DI_PS")?>>
    </<?=GetMessage("CC_BSC1_DI_GENERAL")?>><?
}
```

Это основной источник, подтверждающий необходимость `mode=info`.

### Языковой файл компонента Bitrix

```text
https://raw.githubusercontent.com/devsandk/bitrix_utf8/master/bitrix/components/bitrix/sale.export.1c/lang/ru/component.php
```

Ключевые константы:

```php
$MESS["CC_BSC1_DI_GENERAL"] = "Справочник";
$MESS["CC_BSC1_DI_STATUSES"] = "Cтатусы";
$MESS["CC_BSC1_DI_PS"] = "ПлатежныеСистемы";
$MESS["CC_BSC1_DI_ELEMENT"] = "Элемент";
$MESS["CC_BSC1_DI_ID"] = "Ид";
$MESS["CC_BSC1_DI_NAME"] = "Название";
```

Именно эти теги нужно использовать в XML-ответе.

### Дополнительная статья по обмену заказами Bitrix ↔ 1С

```text
https://www.gkexchange.ru/manuals/obmen-zakazami-ut-11-2-i-bus/
```

Полезно для общего понимания:

- **обмен заказами строится вокруг CommerceML**;
- **настройки 1С зависят от данных, полученных с сайта**;
- **статусы и служебные реквизиты нужно проверять по реальному XML**.

### Дополнительная статья по настройке обмена заказами Bitrix ↔ 1С

```text
https://www.aviant.ru/about/articles/nastroyka-obmena-zakaz-bitrix-1s/
```

Полезно для диагностики:

- **важность корректной настройки статусов**;
- **проверка XML обмена**;
- **типовые проблемы интеграции**.

## Предлагаемые критерии приёмки

### AC1. Endpoint поддерживает `mode=info`

При запросе:

```text
GET <exchange_endpoint>?type=sale&mode=info
```

backend возвращает HTTP `200` и XML-ответ, а не:

```text
failure
Unknown mode
```

### AC2. XML совместим с Bitrix-форматом

Ответ содержит:

```xml
<Справочник>
  <Cтатусы>
    <Элемент>
      <Ид>...</Ид>
      <Название>...</Название>
    </Элемент>
  </Cтатусы>
  <ПлатежныеСистемы>
    ...
  </ПлатежныеСистемы>
</Справочник>
```

Блок `ПлатежныеСистемы` должен присутствовать, даже если он пустой.

### AC3. Кодировка совместима с 1С

Ответ должен быть совместим с 1С-Битрикс.

Рекомендуемый вариант:

```text
Content-Type: text/xml; charset=windows-1251
```

XML declaration:

```xml
<?xml version="1.0" encoding="windows-1251"?>
```

Если текущая инфраструктура обмена уже централизованно перекодирует ответы в `windows-1251`, использовать существующий механизм, а не дублировать.

### AC4. Список статусов содержит значения, которые backend умеет принимать обратно

Минимальный список:

```text
ОжидаетОбработки
Подтвержден
Отгружен
Доставлен
Отменен
Возвращен
```

Рассмотреть добавление:

```text
Не согласован
```

если это значение реально отправляется сайтом в 1С при экспорте заказа.

### AC5. Существующий обмен заказами не сломан

Должны продолжать работать:

- **`mode=checkauth`**;
- **`mode=init`**;
- **`mode=query`**;
- **`mode=success`**;
- **`mode=file`**.

### AC6. В 1С кнопка "Загрузить с сайта" больше не падает

После деплоя и настройки endpoint в 1С:

- открыть настройки обмена заказами;
- перейти к сопоставлению статусов;
- нажать **"Загрузить с сайта"**;
- таблица должна заполниться статусами из XML;
- ошибка чтения данных не должна появляться.

## Тесты

Добавить unit/regression-тесты для `ICExchangeView`.

Проверить:

1. `mode=info` возвращает `200`.
2. Ответ содержит XML declaration.
3. Ответ содержит `<Справочник>`.
4. Ответ содержит `<Cтатусы>`.
5. Ответ содержит все ожидаемые статусы.
6. Ответ содержит `<ПлатежныеСистемы`.
7. Ответ не содержит `failure`.
8. Существующий unknown mode по-прежнему возвращает ожидаемый failure-ответ.

Команды проекта для тестов:

```powershell
make test-unit
```

или точечно через Docker:

```powershell
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest <путь_к_тесту>
```

Если запуск локально:

```powershell
.\backend\venv\Scripts\Activate.ps1
pytest <путь_к_тесту>
```

## Диагностика перед реализацией

Перед реализацией желательно проверить логи backend/nginx при нажатии в 1С кнопки **"Загрузить с сайта"**.

Ожидаемый запрос:

```text
type=sale&mode=info
```

Если в логах виден именно этот запрос, это подтверждает корень проблемы.

## Диагностика после реализации

После реализации проверить вручную через браузер, curl или Postman:

```text
<exchange_endpoint>?type=sale&mode=info
```

Ожидаемый результат:

- **валидный XML**;
- **корректная кодировка**;
- **список статусов**;
- **наличие блока `ПлатежныеСистемы`**;
- **отсутствие `failure`**.

Затем проверить из 1С:

- открыть настройки обмена с сайтом;
- перейти к таблице сопоставления статусов заказов;
- нажать **"Загрузить с сайта"**;
- убедиться, что статусы появились в таблице.

## Ограничения

Не нужно в рамках этой задачи:

- **переписывать весь обмен заказами**;
- **менять `OrderStatusImportService`, если `mode=info` достаточно для заполнения таблицы в 1С**;
- **менять бизнес-логику статусов заказов**;
- **менять `Order.status` после `mode=success`**;
- **менять экспорт заказов через `mode=query`, кроме случаев, если тесты явно покажут необходимость добавить `Не согласован` в справочник**.

## Рекомендуемый итог реализации

Добавить в `ICExchangeView` метод наподобие:

```python
def handle_info(self, request):
    ...
```

и подключить его в маршрутизацию `mode`.

Формировать XML из единого источника статусов, предпочтительно из:

```python
STATUS_MAPPING.keys()
```

с опциональным добавлением дефолтного экспортного статуса из `OrderExportService` / настроек `ONEC_EXCHANGE.ORDER_DEFAULTS.STATUS`.

## Ожидаемый результат для бизнеса

После доработки 1С сможет автоматически загрузить с сайта список статусов заказов, заполнить таблицу сопоставления и продолжить настройку обмена без ручного редактирования недоступных полей.
