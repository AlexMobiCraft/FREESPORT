# Отладка: Множественное создание сессий импорта

## Проблема

При выборе "Цены товаров" создавалось **3 сессии** вместо одной:

- 2 сессии "Каталог товаров"
- 1 сессия "Цены товаров"

## Внесенные изменения

### 1. Правильный тип сессии

**Файл:** `backend/apps/integrations/admin.py`

Теперь сессия создается с правильным типом на основе выбранных данных:

```python
# Определяем тип сессии на основе выбранных типов
session_type_map = {
    "catalog": ImportSession.ImportType.CATALOG,
    "stocks": ImportSession.ImportType.STOCKS,
    "prices": ImportSession.ImportType.PRICES,
    "customers": ImportSession.ImportType.CUSTOMERS,
}

primary_type = selected_types[0] if selected_types else "catalog"
session_import_type = session_type_map.get(primary_type, ImportSession.ImportType.CATALOG)
```

### 2. Логирование для отладки

Добавлено детальное логирование каждого запроса с уникальным ID:

```python
request_id = str(uuid.uuid4())[:8]
logger.info(f"[Request {request_id}] Попытка запуска импорта: {selected_types}")
logger.info(f"[Request {request_id}] Импорт запущен успешно. Session ID: {session.pk}, Task ID: {task.id}")
```

## Тестирование

### Шаг 1: Очистите текущие сессии

Удалите все тестовые сессии через админку или базу данных.

### Шаг 2: Запустите импорт с логированием

1. Откройте `http://localhost:8001/admin/integrations/integrationimportsession/`
2. **Выберите ОДНУ сессию** (или не выбирайте ничего)
3. Нажмите "🚀 Запустить импорт из 1С"
4. Выберите **ТОЛЬКО "Цены товаров"**
5. Нажмите "▶️ Запустить импорт"

### Шаг 3: Проверьте логи backend

```powershell
# Смотрим логи backend для поиска Request ID
docker-compose -f docker/docker-compose.yml logs backend | Select-String "Request"
```

Вы должны увидеть:

```
[Request abc123de] Попытка запуска импорта: ['prices']
[Request abc123de] Импорт запущен успешно. Session ID: 16, Task ID: ...
```

**Важно:** Должен быть **ТОЛЬКО ОДИН** Request ID!

Если вы видите несколько Request ID (например, `abc123de`, `xyz789fg`), значит метод вызывается несколько раз.

### Шаг 4: Проверьте количество сессий

Обновите страницу списка сессий. Должна появиться **ТОЛЬКО ОДНА** новая сессия с типом "Цены товаров".

### Шаг 5: Проверьте логи Celery

```powershell
docker-compose -f docker/docker-compose.yml logs celery | Select-String "run_selective_import_task.*received"
```

Должна быть **ТОЛЬКО ОДНА** строка с `received`.

## Возможные причины множественного вызова

Если проблема сохраняется, проверьте:

### 1. Множественные скрытые поля в форме

Откройте DevTools (F12) → Network → найдите POST запрос к `/admin/integrations/integrationimportsession/`

Проверьте Form Data:

```
action: trigger_selective_import
_selected_action: 0
import_types: prices
apply: Запустить импорт
```

**Проблема:** Если есть несколько полей `_selected_action`, значит шаблон всё ещё генерирует их в цикле.

### 2. Двойной клик

Проверьте, что JavaScript блокирует кнопку после первого клика:

```javascript
// В DevTools Console
document.querySelector('button[name="apply"]').disabled;
// Должно быть: true (после клика)
```

### 3. Browser back/forward

Если пользователь нажимает "Назад" в браузере и снова "Запустить импорт", может создаться дубликат.

**Решение:** Добавить проверку на дублирование по времени (не запускать, если последний импорт был менее 5 секунд назад).

### 4. Gunicorn workers

Если несколько Gunicorn workers обрабатывают один и тот же запрос (race condition).

**Решение:** Redis lock должен предотвращать это, но проверьте логи на наличие нескольких Request ID.

## Дополнительная защита (если проблема сохраняется)

Добавьте проверку на дублирование по времени:

```python
# В _run_sequential_import, после получения lock
last_import = ImportSession.objects.filter(
    status__in=["started", "in_progress"]
).order_by("-started_at").first()

if last_import:
    time_since_last = timezone.now() - last_import.started_at
    if time_since_last.total_seconds() < 5:
        logger.warning(f"[Request {request_id}] Импорт был запущен {time_since_last.total_seconds()}s назад, пропускаем")
        self.message_user(request, "⚠️ Импорт уже запущен недавно", level="WARNING")
        return
```

## Результаты тестирования

После применения исправлений запишите результаты:

- [ ] Создается только одна сессия
- [ ] Тип сессии соответствует выбранным данным
- [ ] В логах только один Request ID
- [ ] В логах Celery только одна задача `received`
- [ ] Redis lock работает корректно

## Контакты

При возникновении проблем обращайтесь к разработчику:

- **Developer:** James (Dev Agent)
- **Debug:** Множественное создание сессий
- **Date:** 2025-11-04
