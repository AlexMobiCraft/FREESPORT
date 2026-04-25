# Исправление: Двойной запуск Celery задач

## Проблема

При запуске импорта через админ-панель создавались и запускались **две одинаковые Celery задачи** вместо одной.

## Причина

В шаблоне `import_selection.html` использовался цикл по `queryset` для создания скрытых полей `_selected_action`:

```html
{% for obj in queryset %}
<input type="hidden" name="_selected_action" value="{{ obj.pk }}" />
{% endfor %}
```

Если пользователь выбирал 2 сессии импорта в списке и нажимал action "🚀 Запустить импорт из 1С", то:

1. Создавалось 2 скрытых поля `_selected_action`
2. Django admin обрабатывал action для каждого выбранного объекта
3. Создавалось 2 новые сессии импорта
4. Запускалось 2 Celery задачи одновременно

## Решение

### 1. Убрана зависимость от queryset

**Файл:** `backend/apps/integrations/admin.py`

Удалена проверка `queryset.exists()`, так как action не зависит от выбранных объектов:

```python
# БЫЛО:
if not queryset.exists():
    self.message_user(request, "...", level="INFO")
    return None

# СТАЛО:
# Проверка удалена - action работает независимо от выбора
```

### 2. Исправлен шаблон intermediate page

**Файл:** `backend/templates/admin/integrations/import_selection.html`

Заменен цикл по queryset на одно фиксированное поле:

```html
<!-- БЫЛО: -->
{% for obj in queryset %}
<input type="hidden" name="_selected_action" value="{{ obj.pk }}" />
{% endfor %}

<!-- СТАЛО: -->
<input type="hidden" name="_selected_action" value="0" />
```

Теперь всегда создается только **одно скрытое поле**, независимо от количества выбранных сессий.

## Результат

✅ **Запускается только одна Celery задача** при нажатии на action  
✅ **Создается только одна сессия импорта**  
✅ **Нет дублирования процессов**  
✅ **Redis lock работает корректно**

## Тестирование

### Шаг 1: Выберите несколько сессий

1. Откройте `http://localhost:8001/admin/integrations/integrationimportsession/`
2. Выберите **2-3 сессии** в списке (поставьте галочки)
3. Выберите action "🚀 Запустить импорт из 1С"
4. Нажмите "Go"

### Шаг 2: Проверьте количество задач

1. На intermediate page нажмите "▶️ Запустить импорт"
2. Проверьте логи Celery:
   ```powershell
   docker-compose -f docker/docker-compose.yml logs -f celery
   ```
3. Должна быть **только одна** строка:
   ```
   [Task <task_id>] Запуск выборочного импорта: ['catalog']
   ```

### Шаг 3: Проверьте количество сессий

1. Обновите страницу списка сессий
2. Должна появиться **только одна новая сессия** с Task ID

## Измененные файлы

1. ✅ `backend/apps/integrations/admin.py` - убрана проверка queryset
2. ✅ `backend/templates/admin/integrations/import_selection.html` - исправлен шаблон

## Деплой

### Локально

```powershell
# Перезапустить backend
docker-compose -f docker/docker-compose.yml restart backend
```

### Продакшн

```bash
ssh root@5.35.124.149
cd /root/freesport

# Перезапустить backend
docker-compose -f docker/docker-compose.prod.yml restart backend
```

## Дополнительная защита

Помимо этого исправления, уже реализованы:

1. **Redis distributed lock** - предотвращает одновременный запуск импортов
2. **JavaScript защита от двойного клика** - блокирует кнопку после первого клика
3. **Celery retry механизм** - автоматические повторные попытки при ошибках

## Контакты

При возникновении проблем обращайтесь к разработчику:

- **Developer:** James (Dev Agent)
- **Fix:** Двойной запуск Celery задач
- **Date:** 2025-11-04
