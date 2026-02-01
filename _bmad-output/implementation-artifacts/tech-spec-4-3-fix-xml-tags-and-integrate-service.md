# Tech Spec: Исправление XML-тегов и интеграция OrderExportService в handle_query

**Story:** 4.3 — View-обработчики mode=query и mode=success
**Приоритет:** P1 (блокирует обмен с 1С)
**Затрагиваемые файлы:** `backend/apps/integrations/onec_exchange/views.py`

---

## Проблема

Заглушка `handle_query` (views.py:506-522) возвращает XML с латинскими тегами:

```xml
<Commerceml version="2.10">
</Commerceml>
```

По FR1.4 и стандарту CommerceML 2.10 корневой тег должен быть кириллическим:

```xml
<КоммерческаяИнформация ВерсияСхемы="2.10" ДатаФормирования="...">
</КоммерческаяИнформация>
```

`OrderExportService` (`backend/apps/orders/services/order_export.py`) уже генерирует корректный XML. Задача — заменить заглушку на вызов сервиса.

---

## Что делать

### Шаг 1: Заменить заглушку `handle_query`

**Файл:** `backend/apps/integrations/onec_exchange/views.py`, строки 506-522

**Удалить:**

```python
def handle_query(self, request):
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Commerceml version="2.10">\n'
        '</Commerceml>'
    )
    return HttpResponse(xml_content, content_type="application/xml")
```

**Заменить на:**

```python
import io
import zipfile
from datetime import timezone as tz
from django.utils import timezone
from apps.orders.services.order_export import OrderExportService

def handle_query(self, request):
    """
    Handle order export requests (mode=query).
    Protocol: GET /?mode=query
    Response: XML or ZIP (CommerceML 2.10)
    """
    query_time = timezone.now()
    request.session['last_1c_query_time'] = query_time.isoformat()

    orders = Order.objects.filter(
        sent_to_1c=False,
        created_at__lte=query_time,
    ).select_related('user').prefetch_related(
        'items__variant__product'
    )

    service = OrderExportService()
    xml_content = service.generate_xml(orders)

    # Аудит-лог
    self._save_exchange_log(
        f"orders_query_{query_time.strftime('%Y%m%d_%H%M%S')}.xml",
        xml_content,
    )

    # ZIP если запрошено
    zip_requested = request.query_params.get('zip', 'no') == 'yes'
    if zip_requested:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('orders.xml', xml_content)
        buf.seek(0)
        response = HttpResponse(buf.read(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=orders.zip'
        return response

    return HttpResponse(xml_content, content_type='application/xml; charset=utf-8')
```

### Шаг 2: Пустой ответ (0 заказов)

`OrderExportService.generate_xml(empty_queryset)` уже возвращает валидный пустой XML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="2.10" ДатаФормирования="...">
</КоммерческаяИнформация>
```

Дополнительная обработка не нужна. Если сервис по какой-то причине вернёт пустую строку — логировать ошибку и вернуть пустой контейнер с кириллическими тегами (никогда не `<Commerceml>`).

### Шаг 3: Хелпер аудит-лога

Добавить в `ICExchangeView`:

```python
def _save_exchange_log(self, filename, content, is_binary=False):
    """Сохранить копию обмена для аудита."""
    log_dir = os.path.join(settings.MEDIA_ROOT, '1c_exchange', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    mode = 'wb' if is_binary else 'w'
    encoding = None if is_binary else 'utf-8'
    filepath = os.path.join(log_dir, filename)
    try:
        with open(filepath, mode, encoding=encoding) as f:
            f.write(content)
    except OSError:
        logger.exception("Failed to save exchange log: %s", filepath)
```

### Шаг 4: handle_success

```python
def handle_success(self, request):
    """Mark exported orders as sent after 1C confirms receipt."""
    last_query = request.session.get('last_1c_query_time')
    if not last_query:
        logger.warning("mode=success без предшествующего mode=query")
        return HttpResponse("success", content_type="text/plain")

    from datetime import datetime, timezone as tz
    query_time = datetime.fromisoformat(last_query)

    updated = Order.objects.filter(
        sent_to_1c=False,
        created_at__lte=query_time,
    ).update(
        sent_to_1c=True,
        sent_to_1c_at=timezone.now(),
    )
    logger.info("mode=success: помечено %d заказов как отправленные в 1С", updated)

    return HttpResponse("success", content_type="text/plain")
```

---

## Чеклист проверки

- [ ] Заглушка с `<Commerceml>` удалена — нигде в коде не осталось латинских тегов
- [ ] `handle_query` вызывает `OrderExportService.generate_xml()`
- [ ] Пустой ответ (0 заказов) содержит `<КоммерческаяИнформация>`, а не `<Commerceml>`
- [ ] `zip=yes` возвращает ZIP с `orders.xml` внутри
- [ ] `handle_success` обновляет только заказы до `query_time` (защита от race condition)
- [ ] Аудит-лог сохраняется в `MEDIA_ROOT/1c_exchange/logs/`
- [ ] Тесты проверяют корневой тег XML на кириллицу
