# Затронутый код и выкат

## Код

| Файл | Что меняется |
|---|---|
| `backend/apps/orders/signals.py` | Обе задачи ставятся через `transaction.on_commit(..., robust=True)`. Прежний `try/except` и логи перенести внутрь колбэка: снаружи после коммита они не защищают. Номер заказа — в тексте сообщения: штатный лог `robust` даёт только `<lambda>` без номера. |
| `backend/apps/orders/tasks.py` | `send_order_notification_email`: собрать получателей как общий список + ответственный менеджер без дублей по `email.lower()`; проверка «нет получателей» — после объединения. Номер заказа в предупреждении — в тексте сообщения: `extra=` в прод-формат логов не попадает. |
| `backend/freesport/settings/base.py` | Настройки Celery, см. «Таймауты брокера». |
| `backend/apps/common/supervisor_admin.py` | Подсказка у флага `notify_new_orders` в форме `SupervisorNotificationRecipientAdmin`. Не через `help_text` модели: это `AlterField` и миграция. |
| `docs/architecture/02-data-models.md` | Уточнить: `notify_new_orders` — общий список, ответственный менеджер клиента добавляется автоматически, независимо от флага. |
| `AGENTS.md`, раздел «Неочевидное в коде» | Строка `orders/`: задачи ставятся через `on_commit`, письмо получает и ответственный менеджер. |

Форма вызова уже есть в `backend/apps/users/services/verify_b2b_application.py:376`. Колбэк на каждую задачу отдельный: `robust=True` изолирует сбой одной от другой.

Менеджер берётся так: `order.user.responsible_manager`, только если он входит в `responsible_manager_candidates()` (`apps/users/staff_roles.py`) и у него есть email. Деление ссылок `/admin/` и `/manager/` остаётся в `split_by_manager_section`: кандидат попадает в `/manager/` автоматически.

`Order.DoesNotExist` в задачах остаётся: после `on_commit` эта ветка больше не штатная. Заказы других путей создания (автокоммит, админка) `on_commit` выполняет сразу или после их транзакции.

## Таймауты брокера

Celery по умолчанию ждёт Redis долго: результат-бэкенд подключается ещё до публикации (`on_task_call`) и повторяет 20 раз, а `redis_socket_timeout` равен 120 с. Настройки проекта этого не меняют. Брокер и бэкенд — один Redis, поэтому вызов `.delay` виснет в запросе оформления заказа.

Замер в образе бэкенда на Linux (Celery 5.4.0, kombu 5.5.4, redis 5.0.1), время одного `.delay`, в заказе их два, `gunicorn --timeout 60`:

| Сбой | Сейчас | С настройками ниже |
|---|---|---|
| Соединение отклонено | 19 с | 0,2 с |
| Имя не разрешается | 70 с | 7 с |
| Соединение принято, ответа нет | больше 170 с | 9 с |

Значения для `base.py`:

```python
_CELERY_REDIS_RETRY = {"max_retries": 1, "interval_start": 0, "interval_step": 0.2, "interval_max": 0.2}
CELERY_BROKER_TRANSPORT_OPTIONS = {"socket_connect_timeout": 2, "socket_timeout": 3}
CELERY_REDIS_SOCKET_CONNECT_TIMEOUT = 2
CELERY_REDIS_SOCKET_TIMEOUT = 3
CELERY_TASK_PUBLISH_RETRY_POLICY = _CELERY_REDIS_RETRY
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {"retry_policy": _CELERY_REDIS_RETRY}
```

Воркер с этими значениями на живом Redis выполнил 6 задач из 6 и после 40 с простоя работал без переподключений. Перезапуск Redis под нагрузкой не проверялся: это пункт CAP-2.

Настройки общие: то же получат все задачи проекта, включая повторы `self.retry` и запись результатов в воркере. При коротком сбое Redis они раньше сдадутся, зато не будут держать запрос.

Полный отказ Redis этим не лечится: `ProxyAwareAnonRateThrottle` и `ProxyAwareUserRateThrottle` читают кэш в том же Redis ещё до создания заказа. Настройки закрывают сбой между этой проверкой и фиксацией заказа и не дают запросу зависнуть на постановке задач.

## Тесты

| Файл | Что сделать |
|---|---|
| `backend/tests/integration/test_onec_export.py:736` | `test_signal_dispatches_celery_tasks`: создание внутри `django_capture_on_commit_callbacks(execute=True)` |
| `backend/tests/integration/test_orders_api.py:240` | Тот же приём вокруг `client.post`; добавить сценарий брокера из CAP-2 с `caplog` |
| Новый тест настроек Celery | CAP-2: локальный сокет принимает соединение и молчит, `.delay` с настройками проекта падает быстрее 15 с |
| `backend/tests/unit/test_order_numbering.py:175` | Проверяет только «не вызвано»: заменить на захват колбэков, иначе тест пройдёт впустую |
| `backend/tests/unit/test_notification_recipient.py` | Сценарии CAP-3 и CAP-4 |
| Новый тест на `OrderCreateService` | CAP-1: порядок относительно коммита, откат, наличие позиций на момент постановки |

Колбэки выполнять внутри `patch(...)`: задачи импортируются в момент срабатывания сигнала. Фикстуры с заглушками задач (`test_manager_orders_section.py:129`, `test_manager_orders_admin.py:93`, `test_supervisor_summary.py:35`) менять не нужно, в них на вызовы не смотрят; подтвердить прогоном.

## GitNexus

`impact` для `send_order_notification_email` и `send_order_confirmation_email`: связей нет, риск `UNKNOWN` (задачи и сигналы индекс не отслеживает). Перечень выше собран текстовым поиском.

## Выкат

1. Релиз по обычной схеме: PR в `develop`, синк в `main`. Миграций нет. Настройки Celery читают `backend`, `celery` и `celery-beat`: проверить, что релиз пересоздал все три.
2. После релиза с подтверждения владельца включить `notify_new_orders` у `managermsk3@freesportopt.ru` в разделе руководителя. Журнал правку не зафиксирует: запись от 29.10.2026 не оставила следа ни в `django_admin_log`, ни в `common_auditlog`.
3. Проверить по первому реальному заказу: спросить у получателей, пришло ли письмо. Ключи `celery-task-meta-*` в Redis хранятся 24 часа: если заказ свежий, искать результаты `True` рядом с `created_at` заказа. Логи worker теряются при пересоздании контейнера. Контрольный заказ не создавать: он уйдёт в рабочую 1С.

## Откат

`gh workflow run deploy.yml -f image_tag=<sha прошлого релиза>`. Флаг руководителя откат не затрагивает.
