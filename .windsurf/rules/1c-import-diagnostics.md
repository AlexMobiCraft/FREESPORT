---
description: Диагностика ошибок полной выгрузки 1С (CommerceML) в FREESPORT
---

# Диагностика полной выгрузки 1С

## Классы ошибок

При анализе `tmp/Ошибки.mxl` выявлены два независимых класса:

### 1. Ошибки на стороне 1С при чтении изображений

Сообщения вида: `Не удалось получить данные файла ... объекта ...`

Это ошибка на стороне 1С при чтении/получении изображений до отправки на сайт. Backend эти файлы ещё не получает.

### 2. `failure Internal error` при отправке каталоговых ZIP

Временные ZIP: `C:\Users\USR1CV8\AppData\Local\Temp\v8_1138_*.zip`.

В коде FREESPORT такой ответ для каталоговых ZIP формируется в:
`backend/apps/integrations/onec_exchange/views.py::ICExchangeView.handle_file_upload()`
при исключении во время `mode=file`.

## Настройки лимитов

- Backend: `ONEC_EXCHANGE.FILE_LIMIT_BYTES=100MB`.
- Nginx для `/api/`: `client_max_body_size 500M`, `proxy_request_buffering off`, таймауты 300s.

## Точная диагностика

Для установления причины `Internal error` нужен traceback из production `backend` за окно выгрузки. Искать в логах строку `Upload error:`.
