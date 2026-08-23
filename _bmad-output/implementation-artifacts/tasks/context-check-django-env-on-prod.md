# Контекст для агента: проверить DJANGO_ENVIRONMENT / ENVIRONMENT на продакшен-сервере FREESPORT

> Самодостаточный промпт для агента с чистым контекстным окном. Передай его содержимое целиком.

---

## Твоя задача

Провести **диагностику** (без внесения правок на сервере) корневой причины, по которой health-endpoint продакшена FREESPORT возвращает `"environment":"development"` вместо ожидаемого `"production"$. Подтвердить гипотезу о корневой причине, собрать фактические значения переменных на сервере и предложить вариант фикса в коде (применять фикс НЕ нужно — только описать).

## Контекст проекта

**FREESPORT** — Django REST API backend + Next.js frontend, деплой через Docker Compose на VPS.

### Параметры продакшен-сервера

- **Host:** `5.35.124.149`
- **User:** `root`
- **Project Path:** `/home/freesport/freesport/`
- **Compose File:** `docker/docker-compose.prod.yml`
- **Env File:** `.env.prod` (находится в корне проекта на сервере, в репозитории есть только `.env.prod.example`)
- **Локальный репозиторий:** `C:\Users\1\DEV\FREESPORT\` (Windows, PowerShell)

### SSH-доступ

Подключение по SSH без пароля (ssh-agent). Команды выполнять из локальной подпапки `scripts/` (чтобы избежать зависаний терминала из-за индексации Git/Oh-My-Posh в корне проекта).

**Шаблон команды** (одинарные кавычки на уровне PowerShell → bash получает строку как есть; внутри SSH-строки используй `&&` для bash):

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml <подкоманда>'
```

> ВАЖНО: всегда используй `cd /home/freesport/freesport &&` перед `docker compose` — команда ищет `.env.prod` относительно текущей директории. Абсолютный путь `--env-file /home/freesport/freesport/.env.prod` обеспечивает надёжность.

### Что уже известно (не переоткрывай)

#### 1. Health endpoint

Файл `backend/apps/common/views.py`, строки 81-84:

```python
"status": "healthy",
"version": "1.0.0",
"environment": getattr(settings, "ENVIRONMENT", "development"),
```

То есть health отдаёт `settings.ENVIRONMENT`, а если такого атрибута нет — fallback `"development"$. Фактический ответ продакшена: `{"status":"healthy","version":"1.0.0","environment":"development"}`.

#### 2. Логика выбора settings-модуля

Файл `backend/freesport/settings/__init__.py` (полное содержимое):

```python
"""
FREESPORT Django Settings
Import appropriate settings based on environment
"""

import os

from decouple import config

# Determine which settings to use
ENVIRONMENT = config("DJANGO_ENVIRONMENT", default="development")

if ENVIRONMENT == "production":
    from .production import *
elif ENVIRONMENT == "staging":
    from .staging import *
else:
    from .development import *
```

Здесь `ENVIRONMENT` определяется через `DJANGO_ENVIRONMENT` (через `python-decouple`, читает `.env`/переменные окружения) и **затем** импортируется соответствующий модуль через `*`. Этот файл выполняется только если `DJANGO_SETTINGS_MODULE=freesport.settings` (без суффикса).

#### 3. Жёсткий DJANGO_SETTINGS_MODULE в prod-compose

Файл `docker/docker-compose.prod.yml`, сервис `backend` (строка ~46-47):

```yaml
environment:
  - DJANGO_SETTINGS_MODULE=freesport.settings.production
```

То же самое для сервисов `celery-worker` (строка ~184-185) и `celery-beat` (строка ~233-234).

**Следствие:** `__init__.py` НЕ выполняется — Django напрямую грузит `freesport.settings.production`. Переменная `ENVIRONMENT` в `settings` не определяется.

#### 4. production.py не задаёт ENVIRONMENT

Файл `backend/freesport/settings/production.py` (106 строк, первая строка `from .base import *`). В нём **нет** строки `ENVIRONMENT = "production"$. Есть только `DEBUG = False` и продакшен-настройки (БД, CORS, кеш, логирование, email). То есть `settings.ENVIRONMENT` отсутствует → `getattr(..., "development")` возвращает дефолт.

#### 5. .env.prod.example

Файл `.env.prod.example`, строка 2:

```
DJANGO_ENVIRONMENT=production
```

То есть переменная окружения называется **`DJANGO_ENVIRONMENT`** (не `DJANGO_ENV`, не `ENVIRONMENT`). Она читается только в `__init__.py`, который на проде не выполняется из-за жёсткого `DJANGO_SETTINGS_MODULE`.

#### 6. development.py

Файл `backend/freesport/settings/development.py` содержит `DEBUG = True` и тоже не задаёт `ENVIRONMENT`. То есть даже в dev-режиме через `__init__.py` `ENVIRONMENT` попадает в settings только как локальная переменная модуля `__init__`, а не как атрибут `settings` (после `from .development import *` имя `ENVIRONMENT` импортируется в namespace модуля `__init__`, который и становится `settings` — поэтому в dev это работает, а в prod через прямой `DJANGO_SETTINGS_MODULE=freesport.settings.production` — нет).

### Гипотеза корневой причины

На продакшене `DJANGO_SETTINGS_MODULE=freesport.settings.production` обходит `__init__.py`, где `ENVIRONMENT` определяется из `DJANGO_ENVIRONMENT$. Модуль `production.py` не задаёт `ENVIRONMENT`, поэтому `settings.ENVIRONMENT` отсутствует, и health-endpoint отдаёт fallback `"development"$. Это **баг отображения**, не фактическая среда: `DEBUG=False`, production-настройки БД/кеша/CORS применяются корректно.

## Что нужно сделать

### Шаг 1. Подтвердить фактические значения на сервере

Выполни по SSH (используй here-doc для многострочного Python, чтобы избежать проблем с экранированием вложенных кавычек):

```powershell
ssh root@5.35.124.149 'cat > /tmp/check_env.py << "EOF"
from django.conf import settings
print("DJANGO_SETTINGS_MODULE =", settings.DJANGO_SETTINGS_MODULE)
print("DEBUG =", settings.DEBUG)
print("ENVIRONMENT attr =", getattr(settings, "ENVIRONMENT", "<MISSING>"))
import os
print("env DJANGO_ENVIRONMENT =", os.environ.get("DJANGO_ENVIRONMENT", "<UNSET>"))
print("env DJANGO_SETTINGS_MODULE =", os.environ.get("DJANGO_SETTINGS_MODULE", "<UNSET>"))
EOF
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T backend python manage.py shell -c "exec(open(\"/tmp/check_env.py\").read())"'
```

> Если `manage.py shell -c` с `exec(open(...))` не сработает, альтернатива: скопировать скрипт внутрь контейнера через `docker cp` либо запустить `python -c` с одной строкой через `;`. Сообщи об ошибке и попробуй вариант.

После выполнения удали временный файл:

```powershell
ssh root@5.35.124.149 'rm /tmp/check_env.py'
```

### Шаг 2. Проверить .env.prod на сервере

```powershell
ssh root@5.35.124.149 'grep -E "^(DJANGO_ENVIRONMENT|DJANGO_SETTINGS_MODULE|DEBUG)" /home/freesport/freesport/.env.prod || echo "NO MATCHES"'
```

> `.env.prod` содержит секреты (SECRET_KEY, пароли). НЕ выводи содержимое целиком и НЕ коммить его. Используй только `grep` по конкретным ключам.

### Шаг 3. Проверить compose-переменные backend

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T backend env | grep -E "^(DJANGO_SETTINGS_MODULE|DJANGO_ENVIRONMENT|DEBUG)" | sort'
```

### Шаг 4. Сопоставить с локальным кодом

Прочитай локально (пути относительно `C:\Users\1\DEV\FREESPORT\`):
- `backend/apps/common/views.py` (health endpoint, строки ~75-90)
- `backend/freesport/settings/__init__.py` (логика выбора модуля)
- `backend/freesport/settings/production.py` (нет `ENVIRONMENT`)
- `backend/freesport/settings/development.py` (нет `ENVIRONMENT`, `DEBUG=True`)
- `docker/docker-compose.prod.yml` (секции `environment:` для backend/celery-worker/celery-beat)

### Шаг 5. Сформулировать отчёт

В отчёте укажи:
1. **Фактические значения с сервера** (вывод шагов 1-3): `DJANGO_SETTINGS_MODULE`, `DEBUG`, наличие/отсутствие `ENVIRONMENT` в settings, значение `DJANGO_ENVIRONMENT` в env-переменных контейнера и в `.env.prod`.
2. **Подтверждение/опровержение гипотезы**: действительно ли `production.py` грузится напрямую и `ENVIRONMENT` отсутствует в `settings`?
3. **Корневая причина** одной фразой.
4. **Влияние**: влияет ли это на что-то кроме health-endpoint? (Например, есть ли в коде другие `getattr(settings, "ENVIRONMENT", ...)` или `if settings.ENVIRONMENT == ...` — проверь через `grep` по `backend/`.)
5. **Предлагаемый фикс** (не применять!): минимум 2 варианта с оценкой trade-offs:
   - **Вариант A:** добавить `ENVIRONMENT = "production"` в `production.py` (и аналогично `ENVIRONMENT = "staging"` в `staging.py`, `ENVIRONMENT = "development"` в `development.py`). Минимально инвазивно, не трогает compose.
   - **Вариант B:** убрать жёсткий `DJANGO_SETTINGS_MODULE` из `docker-compose.prod.yml` и положиться на `__init__.py` + `DJANGO_ENVIRONMENT=production` в `.env.prod$. Меняет точку входа settings, выше риск.
   - Укажи, какой вариант предпочтительнее и почему.
6. **Рекомендация по тесту**: какой тест добавить, чтобы регрессия ловилась (например, unit-тест на `settings.ENVIRONMENT` для prod-модуля, или assertion в `test_health`).

## Ограничения

- **НЕ вноси правки на сервере** (никаких `docker compose restart/up`, редактирования `.env.prod` или кода на VPS). Только чтение и диагностика.
- **НЕ коммить изменения** в локальный репозиторий. Если решишь предложить код-фикс, оформи его как сниппет в отчёте, без записи в файлы.
- **НЕ выводи секреты** из `.env.prod` (SECRET_KEY, пароли, токены). Только нечувствительные ключи (`DJANGO_ENVIRONMENT`, `DJANGO_SETTINGS_MODULE`, `DEBUG`).
- **НЕ выполняй `git push`** ни в какой remote.
- Перед запуском `python manage.py shell` убедись, что контейнер `backend` healthy (`docker compose ... ps`).
- Все ответы и документация — **на русском языке** (правило проекта).

## Ожидаемый результат

Структурированный отчёт на русском с разделами: «Фактические значения», «Корневая причина», «Влияние», «Предлагаемый фикс», «Рекомендация по тесту». Без применения правок.
