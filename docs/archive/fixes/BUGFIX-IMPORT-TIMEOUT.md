# Исправление проблемы с таймаутами и двойным запуском импорта из 1С

## Проблема

При запуске импорта из 1С через админ-панель возникали следующие проблемы:

1. **WORKER TIMEOUT** - Gunicorn worker завершался через 30 секунд
2. **Двойной запуск процессов** - одновременно запускались 2 процесса импорта
3. **Зависание процессов** - процессы не завершались корректно
4. **Ошибки в логах**:
   ```
   [2025-11-04 14:42:41 +0300] [1] [CRITICAL] WORKER TIMEOUT (pid:44)
   [2025-11-04 14:42:41 +0300] [44] [INFO] Worker exiting (pid: 44)
   [2025-11-04 14:42:41 +0300] [1] [ERROR] Worker (pid:44) exited with code 1
   ```

## Причины

1. **Синхронная обработка** - `call_command()` в Django admin action блокировал Gunicorn worker
2. **Дефолтный timeout** - Gunicorn worker timeout = 30 секунд (слишком мало для импорта 498+ товаров)
3. **Отсутствие защиты от двойного клика** - пользователь мог случайно кликнуть дважды
4. **Длительный импорт** - обработка XML файлов занимает 2-5 минут

## Решение

### 1. Асинхронный импорт через Celery

**Создан файл:** `backend/apps/integrations/tasks.py`

Celery задача `run_selective_import_task` выполняет импорт в фоновом режиме:

- Не блокирует Gunicorn worker
- Поддерживает retry механизм (до 3 попыток)
- Логирует прогресс с Task ID
- Прерывает цепочку при ошибке

**Изменен файл:** `backend/apps/integrations/admin.py`

Admin action теперь запускает Celery задачу вместо синхронного `call_command()`:

```python
task = run_selective_import_task.delay(selected_types, str(data_dir))
self.message_user(
    request,
    f"✅ Импорт запущен в фоновом режиме (Task ID: {task.id}). "
    f"Отслеживайте прогресс в разделе 'Сессии импорта'.",
    level="SUCCESS",
)
```

### 2. Увеличение Gunicorn timeout

**Изменен файл:** `backend/Dockerfile`

Увеличен timeout с 30 до 300 секунд (5 минут):

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4",
     "--worker-class", "sync", "--timeout", "300", "--graceful-timeout", "300",
     "--max-requests", "1000", "--max-requests-jitter", "100",
     "--preload", "--access-logfile", "-", "--error-logfile", "-",
     "freesport.wsgi:application"]
```

### 3. Защита от двойного клика

**Изменен файл:** `backend/templates/admin/integrations/import_selection.html`

Добавлен JavaScript для предотвращения двойного клика:

- Блокирует кнопку после первого клика
- Меняет текст на "⏳ Запуск импорта..."
- Валидирует выбор хотя бы одного чекбокса
- Автоматически разблокирует через 5 секунд (на случай ошибки)

### 4. Comprehensive тесты

**Создан файл:** `backend/tests/integration/test_async_import_tasks.py`

Покрытие тестами:

- Успешный импорт одного типа
- Последовательный импорт нескольких типов
- Прерывание цепочки при ошибке
- Валидация настроек и файлов
- Механизм retry

## Инструкции для деплоя

### Шаг 1: Пересборка Docker образа

```powershell
# Локально (для тестирования)
cd c:\Users\38670\DEV_WEB\FREESPORT
docker-compose -f docker-compose.yml build backend

# Или на сервере
ssh root@5.35.124.149
cd /root/freesport
docker-compose -f docker/docker-compose.prod.yml build backend
```

### Шаг 2: Перезапуск контейнеров

```bash
# Остановить текущие контейнеры
docker-compose -f docker/docker-compose.prod.yml down

# Запустить с новым образом
docker-compose -f docker/docker-compose.prod.yml up -d

# Проверить логи
docker-compose -f docker/docker-compose.prod.yml logs -f backend
docker-compose -f docker/docker-compose.prod.yml logs -f celery
```

### Шаг 3: Проверка работоспособности

1. Откройте админ-панель: `https://5.35.124.149/admin`
2. Перейдите в раздел "Интеграции" → "Сессии импорта"
3. Выберите любую сессию и нажмите "🚀 Запустить импорт из 1С"
4. Выберите типы данных и нажмите "▶️ Запустить импорт"
5. Должно появиться сообщение: "✅ Импорт запущен в фоновом режиме (Task ID: ...)"
6. Проверьте логи Celery worker:
   ```bash
   docker-compose -f docker/docker-compose.prod.yml logs -f celery
   ```

### Шаг 4: Мониторинг импорта

Отслеживайте прогресс в разделе "Сессии импорта":

- Статус должен меняться: `started` → `in_progress` → `completed`
- В логах Celery должны быть записи: `[Task <task_id>] Начало импорта: catalog`

## Тестирование

### Локальное тестирование

```powershell
# Активировать виртуальное окружение
cd c:\Users\38670\DEV_WEB\FREESPORT\backend
.\venv\Scripts\activate

# Запустить тесты
pytest tests/integration/test_async_import_tasks.py -v
pytest tests/integration/test_selective_import_admin.py -v

# Проверить покрытие
pytest tests/integration/test_async_import_tasks.py --cov=apps.integrations.tasks --cov-report=term-missing
```

### Тестирование в Docker

```powershell
# Запустить тесты в Docker
docker-compose -f docker-compose.test.yml run --rm backend pytest tests/integration/test_async_import_tasks.py -v
```

## Откат изменений (если потребуется)

Если возникнут проблемы, можно откатить изменения:

```bash
# Откатить на предыдущий коммит
git revert HEAD

# Пересобрать образ
docker-compose -f docker/docker-compose.prod.yml build backend

# Перезапустить
docker-compose -f docker/docker-compose.prod.yml up -d
```

## Измененные файлы

1. ✅ `backend/apps/integrations/tasks.py` - новый файл с Celery задачей
2. ✅ `backend/apps/integrations/admin.py` - обновлен для асинхронного запуска
3. ✅ `backend/Dockerfile` - увеличен Gunicorn timeout
4. ✅ `backend/templates/admin/integrations/import_selection.html` - добавлена защита от двойного клика
5. ✅ `backend/tests/integration/test_async_import_tasks.py` - новые тесты

## Преимущества решения

✅ **Нет блокировки worker'ов** - импорт выполняется в Celery, не блокирует HTTP запросы  
✅ **Масштабируемость** - можно запускать несколько импортов параллельно (через разные Celery worker'ы)  
✅ **Retry механизм** - автоматические повторные попытки при временных ошибках  
✅ **Мониторинг** - Task ID позволяет отслеживать прогресс в логах  
✅ **Защита от дублирования** - Redis lock + JavaScript предотвращают двойной запуск  
✅ **Graceful degradation** - увеличенный timeout как запасной вариант

## Известные ограничения

⚠️ **Требуется работающий Celery worker** - убедитесь, что контейнер `freesport-celery-worker` запущен  
⚠️ **Требуется Redis** - Celery использует Redis как message broker  
⚠️ **Нет real-time прогресса в UI** - прогресс отслеживается через логи или раздел "Сессии импорта"

## Дальнейшие улучшения (Post-MVP)

1. **WebSocket для real-time прогресса** - показывать прогресс импорта в админ-панели без перезагрузки
2. **Celery progress tracking** - использовать `celery-progress` для отображения прогресс-бара
3. **Email уведомления** - отправлять email при завершении импорта
4. **Scheduled imports** - настроить автоматический импорт по расписанию через Celery Beat

## Контакты

При возникновении проблем обращайтесь к разработчику:

- **Developer:** James (Dev Agent)
- **Story:** 9.5 - Выборочный импорт данных из 1С
- **Date:** 2025-11-04
