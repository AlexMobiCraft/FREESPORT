# Добавление отслеживания прогресса Celery задач в админке

## Проблема

На странице "Сессии импорта" (`/admin/integrations/integrationimportsession/`) не отображался прогресс выполнения асинхронного импорта через Celery. Пользователь не мог понять:

- Запустился ли импорт
- Выполняется ли он сейчас
- Завершился ли успешно
- Произошла ли ошибка

## Решение

Добавлена система отслеживания статуса Celery задач в реальном времени:

### 1. Новое поле в модели ImportSession

**Файл:** `backend/apps/products/models.py`

Добавлено поле `celery_task_id` для связи сессии импорта с Celery задачей:

```python
celery_task_id = models.CharField(
    "ID задачи Celery",
    max_length=255,
    null=True,
    blank=True,
    db_index=True,
    help_text="UUID задачи Celery для отслеживания прогресса",
)
```

### 2. Сохранение Task ID при запуске импорта

**Файл:** `backend/apps/integrations/admin.py`

При запуске импорта создается новая сессия и сохраняется Task ID:

```python
# Создаем новую сессию импорта для отслеживания
session = ImportSession.objects.create(
    import_type=ImportSession.ImportType.CATALOG,
    status=ImportSession.ImportStatus.STARTED,
)

# Запускаем асинхронную задачу Celery
task = run_selective_import_task.delay(selected_types, str(data_dir))

# Сохраняем task_id в сессию
session.celery_task_id = task.id
session.save(update_fields=["celery_task_id"])
```

### 3. Отображение статуса Celery задачи

**Файл:** `backend/apps/integrations/admin.py`

Добавлена новая колонка "Celery Task" в список сессий:

```python
@admin.display(description="Celery Task")
def celery_task_status(self, obj: IntegrationImportSession) -> str:
    """Отображение статуса Celery задачи в реальном времени"""
    if not obj.celery_task_id:
        return '-'

    task_result = AsyncResult(obj.celery_task_id)
    state = task_result.state

    # PENDING, STARTED, SUCCESS, FAILURE, RETRY
    # Отображается с иконками и цветами
```

**Статусы:**

- ⏳ **В очереди** (PENDING) - серый
- ▶️ **Выполняется** (STARTED) - синий
- ✅ **Завершено** (SUCCESS) - зеленый
- ❌ **Ошибка** (FAILURE) - красный
- 🔄 **Повтор** (RETRY) - оранжевый

### 4. Автообновление страницы

**Файл:** `backend/static/admin/js/import_session_auto_refresh.js`

JavaScript автоматически обновляет таблицу каждые 5 секунд, если есть активные задачи:

- Обновляет только данные таблицы (не перезагружает всю страницу)
- Показывает индикатор времени последнего обновления
- Работает только если есть задачи в статусе "В очереди" или "Выполняется"

## Миграция базы данных

Создана миграция для добавления поля `celery_task_id`:

```bash
# Создание миграции
docker-compose -f docker/docker-compose.yml exec backend python manage.py makemigrations products --name add_celery_task_id_to_import_session

# Применение миграции
docker-compose -f docker/docker-compose.yml exec backend python manage.py migrate products
```

## Использование

### Запуск импорта

1. Откройте админ-панель: `http://localhost:8001/admin`
2. Перейдите в "Интеграции" → "Сессии импорта"
3. Нажмите "🚀 Запустить импорт из 1С"
4. Выберите типы данных и нажмите "▶️ Запустить импорт"
5. Появится сообщение с Task ID и ID сессии

### Отслеживание прогресса

На странице списка сессий вы увидите:

| ID  | Тип импорта     | Статус    | Celery Task    | Начало | Окончание | Длительность  |
| --- | --------------- | --------- | -------------- | ------ | --------- | ------------- |
| 123 | Каталог товаров | ⏳ Начато | ▶️ Выполняется | 16:30  | -         | В процессе... |

Страница автоматически обновляется каждые 5 секунд, показывая актуальный статус.

### Просмотр деталей

Кликните на сессию для просмотра деталей:

- **ID задачи Celery** - UUID задачи для отслеживания в логах
- **Детали отчета** - статистика импорта (created, updated, skipped, errors)
- **Сообщение об ошибке** - текст ошибки, если импорт завершился неудачно

## Отслеживание в логах Celery

Для детального мониторинга используйте логи Celery:

```powershell
# Просмотр логов Celery worker
docker-compose -f docker/docker-compose.yml logs -f celery

# Поиск по Task ID
docker-compose -f docker/docker-compose.yml logs celery | findstr "8f392b98-e21b-485b-889f-25f4fd8fc317"
```

В логах вы увидите:

```
[Task 8f392b98-e21b-485b-889f-25f4fd8fc317] Запуск выборочного импорта: ['catalog']
[Task 8f392b98-e21b-485b-889f-25f4fd8fc317] Начало импорта: catalog
[Task 8f392b98-e21b-485b-889f-25f4fd8fc317] Импорт catalog завершен: Каталог импортирован
```

## Деплой на продакшн

### Шаг 1: Применить миграции

```bash
ssh root@5.35.124.149
cd /root/freesport

# Применить миграцию
docker-compose -f docker/docker-compose.prod.yml exec backend python manage.py migrate products
```

### Шаг 2: Собрать статические файлы

```bash
# Собрать статику (для JavaScript файла)
docker-compose -f docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### Шаг 3: Перезапустить backend

```bash
docker-compose -f docker/docker-compose.prod.yml restart backend
```

## Измененные файлы

1. ✅ `backend/apps/products/models.py` - добавлено поле `celery_task_id`
2. ✅ `backend/apps/integrations/admin.py` - добавлен метод `celery_task_status` и сохранение Task ID
3. ✅ `backend/static/admin/js/import_session_auto_refresh.js` - автообновление страницы
4. ✅ `backend/apps/products/migrations/0013_add_celery_task_id_to_import_session.py` - миграция БД

## Преимущества

✅ **Прозрачность** - видно, что импорт запущен и выполняется  
✅ **Реальное время** - статус обновляется автоматически каждые 5 секунд  
✅ **Без перезагрузки** - AJAX обновление без полной перезагрузки страницы  
✅ **Детальная информация** - Task ID для отслеживания в логах  
✅ **Визуальная индикация** - иконки и цвета для быстрого понимания статуса

## Известные ограничения

⚠️ **Нет процента выполнения** - показывается только статус (в очереди/выполняется/завершено)  
⚠️ **Требуется Redis** - для получения статуса задачи через Celery API  
⚠️ **Автообновление только на странице списка** - на странице редактирования нужно обновлять вручную

## Дальнейшие улучшения (Post-MVP)

1. **Прогресс-бар** - показывать процент выполнения (требует изменений в Celery задаче)
2. **WebSocket** - real-time обновления без AJAX polling
3. **История задач** - архив всех запущенных задач с возможностью повторного запуска
4. **Уведомления** - push-уведомления при завершении импорта

## Тестирование

### Локально

1. Запустите импорт через админку
2. Откройте DevTools (F12) → Console
3. Должно появиться сообщение: `✅ Автообновление статуса Celery задач активировано (интервал: 5 сек)`
4. Наблюдайте за изменением статуса в колонке "Celery Task"
5. В правом нижнем углу должен появляться индикатор: `🔄 Обновлено: 16:35:42`

### Продакшн

После деплоя проверьте:

- Миграция применена: `docker-compose -f docker/docker-compose.prod.yml exec backend python manage.py showmigrations products`
- Статика собрана: проверьте наличие файла в `/app/staticfiles/admin/js/import_session_auto_refresh.js`
- Импорт работает: запустите тестовый импорт и проверьте отображение статуса

## Контакты

При возникновении проблем обращайтесь к разработчику:

- **Developer:** James (Dev Agent)
- **Feature:** Отслеживание прогресса Celery задач
- **Date:** 2025-11-04
