# Локальная установка и запуск FREESPORT Platform с помощью Docker

Эта инструкция предназначена для разработчиков, которые хотят запустить FREESPORT Platform локально с использованием Docker и Docker Compose.

## 📋 Требования

- **Docker** версии 20.10+ и **Docker Compose** версии 2.0+
- **Git** для клонирования репозитория
- Не менее **8 ГБ** оперативной памяти
- Не менее **10 ГБ** свободного дискового пространства

## 🚀 Быстрый старт

Для быстрого запуска выполните следующие команды:

```bash
# 1. Клонирование репозитория
git clone https://github.com/AlexMobiCraft/FREESPORT.git
cd FREESPORT

# 2. Создание SSL сертификатов (требуется для HTTPS)
# Для Linux/macOS:
./scripts/server/create-ssl-certs.sh

# Для Windows (PowerShell):
.\scripts\server\create-ssl-certs.ps1

# 3. Запуск всех сервисов
docker compose -f docker/docker-compose.yml up -d

# 4. Проверка статуса
docker compose -f docker/docker-compose.yml ps
```

После выполнения этих команд платформа будет доступна по адресу:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8001/api/v1
- Nginx (прокси): https://localhost (с самоподписанным сертификатом)

## 📋 Подробная пошаговая инструкция

### Шаг 1: Подготовка окружения

1. **Убедитесь, что Docker и Docker Compose установлены:**

```bash
# Проверка версии Docker
docker --version

# Проверка версии Docker Compose
docker compose version
```

2. **Клонируйте репозиторий проекта:**

```bash
git clone https://github.com/AlexMobiCraft/FREESPORT.git
cd FREESPORT
```

### Шаг 2: Создание SSL сертификатов (для HTTPS)

Nginx настроен на работу с HTTPS, поэтому необходимо создать SSL сертификаты:

1. **Создайте самоподписанные SSL сертификаты:**

**Для Linux/macOS:**
```bash
# Из корневой директории проекта выполните:
./scripts/server/create-ssl-certs.sh
```

**Для Windows:**
```powershell
# Из корневой директории проекта выполните в PowerShell:
.\scripts\server\create-ssl-certs.ps1
```

**Требования для Windows:**
- Установленный OpenSSL (входит в состав Git for Windows)
- PowerShell 5.1 или новее

Эти скрипты создадут самоподписанные сертификаты в директории `docker/nginx/ssl/`:
- `cert.pem` - сертификат
- `key.pem` - приватный ключ

**Важно:** Для локальной разработки эти сертификаты подойдут, но браузеры будут показывать предупреждение о безопасности.

### Шаг 3: Сборка и запуск контейнеров

1. **Перейдите в директорию с Docker конфигурациями:**

```bash
cd docker
```

2. **Соберите и запустите все контейнеры:**

```bash
# Запуск всех сервисов в фоновом режиме
docker compose -f docker/docker-compose.yml up -d

# Или для просмотра логов в реальном времени
docker compose -f docker/docker-compose.yml up
```

3. **Дождитесь запуска всех сервисов (может занять несколько минут при первом запуске):**

```bash
# Проверка статуса всех контейнеров
docker compose -f docker/docker-compose.yml ps
```

Ожидаемый результат:

```text
NAME                  IMAGE                  COMMAND                  SERVICE             CREATED              STATUS              PORTS
freesport-backend     backend                "gunicorn --bind 0.…"   backend             About a minute ago   Up About a minute   0.0.0.0:8001->8000/tcp
freesport-frontend    frontend               "npx next start"         frontend            About a minute ago   Up About a minute   0.0.0.0:3000->3000/tcp
freesport-nginx       nginx:alpine           "/docker-entrypoint.…"   nginx               About a minute ago   Up About a minute   0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
freesport-db          postgres:15-alpine    "docker-entrypoint.s…"   db                  About a minute ago   Up About a minute   0.0.0.0:5432->5432/tcp
freesport-redis       redis:7-alpine         "redis-server --appe…"   redis               About a minute ago   Up About a minute   0.0.0.0:6379->6379/tcp
freesport-celery      backend                "celery -A freesport…"   celery              About a minute ago   Up About a minute
freesport-celery-beat backend                "celery -A freesport…"   celery-beat         About a minute ago   Up About a minute
```

### Шаг 3: Инициализация базы данных

1. **Выполните миграции базы данных:**

```bash
docker compose -f docker/docker-compose.yml exec backend python manage.py migrate
```

2. **Создайте суперпользователя (опционально):**

```bash
docker compose -f docker/docker-compose.yml exec backend python manage.py createsuperuser
```

3. **Соберите статические файлы:**

```bash
docker compose -f docker/docker-compose.yml exec backend python manage.py collectstatic --no-input
```

### Шаг 4: Проверка работоспособности

1. **Проверьте доступность сервисов:**

```bash
# Проверка API
curl http://localhost:8001/api/v1/

# Проверка фронтенда
curl http://localhost:3000

# Проверка Nginx
curl http://localhost
```

2. **Проверьте логи при необходимости:**

```bash
# Просмотр логов всех сервисов
docker compose logs

# Просмотр логов конкретного сервиса
docker compose logs backend
docker compose logs frontend
docker compose logs db
```

## 🛠️ Управление контейнерами

### Основные команды

```bash
# Запуск всех сервисов
docker compose -f docker/docker-compose.yml up -d

# Остановка всех сервисов
docker compose -f docker/docker-compose.yml down

# Перезапуск всех сервисов
docker compose -f docker/docker-compose.yml restart

# Перезапуск конкретного сервиса
docker compose -f docker/docker-compose.yml restart backend

# Просмотр статуса
docker compose -f docker/docker-compose.yml ps

# Просмотр логов
docker compose logs -f  # с отслеживанием в реальном времени
docker compose logs backend  # конкретного сервиса
```

### Работа с базой данных

```bash
# Подключение к PostgreSQL
docker compose -f docker/docker-compose.yml exec db psql -U postgres -d freesport

# Создание резервной копии БД
docker compose -f docker/docker-compose.yml exec db pg_dump -U postgres freesport > backup.sql

# Восстановление из резервной копии
docker compose -f docker/docker-compose.yml exec -T db psql -U postgres freesport < backup.sql
```

### Работа с Redis

```bash
# Подключение к Redis CLI
docker compose -f docker/docker-compose.yml exec redis redis-cli -a redis123

# Проверка состояния Redis
docker compose -f docker/docker-compose.yml exec redis redis-cli -a redis123 ping
```

### Работа с Django

```bash
# Выполнение миграций
docker compose -f docker/docker-compose.yml exec backend python manage.py migrate

# Создание суперпользователя
docker compose -f docker/docker-compose.yml exec backend python manage.py createsuperuser

# Сбор статических файлов
docker compose -f docker/docker-compose.yml exec backend python manage.py collectstatic --no-input

# Запуск shell Django
docker compose -f docker/docker-compose.yml exec backend python manage.py shell

# Проверка состояния Django
docker compose -f docker/docker-compose.yml exec backend python manage.py check
```

### Работа с Celery

```bash
# Просмотр активных задач Celery
docker compose -f docker/docker-compose.yml exec celery celery -A freesport inspect active

# Просмотр статистики Celery
docker compose -f docker/docker-compose.yml exec celery celery -A freesport inspect stats
```

## 🔧 Разработка с Docker

### Монтирование исходного кода

Конфигурация Docker Compose уже настроена для разработки с монтированием исходного кода:

- Backend: `../backend:/app` - изменения в коде бэкенда применяются без пересборки
- Frontend: `../frontend:/app` - изменения в коде фронтенда применяются без пересборки

### Пересборка образов

При изменении зависимостей или Dockerfile:

```bash
# Пересборка всех образов
docker compose -f docker/docker-compose.yml build --no-cache

# Пересборка конкретного образа
docker compose -f docker/docker-compose.yml build backend
```

### Отладка

```bash
# Вход в контейнер backend
docker compose -f docker/docker-compose.yml exec backend bash

# Вход в контейнер frontend
docker compose -f docker/docker-compose.yml exec frontend sh

# Вход в контейнер базы данных
docker compose -f docker/docker-compose.yml exec db bash
```

## 📊 Мониторинг

### Проверка здоровья сервисов

```bash
# Проверка здоровья всех контейнеров
docker compose -f docker/docker-compose.yml ps

# Детальная информация о контейнере
docker compose -f docker/docker-compose.yml inspect backend
```

### Просмотр использования ресурсов

```bash
# Просмотр использования ресурсов контейнерами
docker compose -f docker/docker-compose.yml stats

# Просмотр использования дискового пространства
docker system df
```

## 🔄 Обновление проекта

```bash
# 1. Получение последних изменений
git pull origin main

# 2. Пересборка образов
docker compose -f docker/docker-compose.yml build --no-cache

# 3. Перезапуск сервисов
docker compose -f docker/docker-compose.yml up -d

# 4. Выполнение миграций
docker compose -f docker/docker-compose.yml exec backend python manage.py migrate

# 5. Сбор статических файлов
docker compose -f docker/docker-compose.yml exec backend python manage.py collectstatic --no-input
```

## 🧹 Очистка

```bash
# Остановка и удаление контейнеров, сетей и томов
docker compose -f docker/docker-compose.yml down -v

# Удаление всех образов проекта
docker compose -f docker/docker-compose.yml down --rmi all

# Полная очистка Docker (осторожно!)
docker system prune -a --volumes
```

## 🚨 Решение проблем

### Проблема: Конфликт имен контейнеров

Если вы видите ошибку вида `Conflict. The container name "/freesport-redis" is already in use`, выполните:

```bash
# 1. Остановка и удаление всех контейнеров проекта
docker compose -f docker/docker-compose.yml down -v

# 2. Удаление оставшихся контейнеров с теми же именами
docker rm -f freesport-db freesport-redis freesport-backend freesport-frontend freesport-nginx freesport-celery freesport-celery-beat

# 3. Повторный запуск
docker compose -f docker/docker-compose.yml up -d
```

### Проблема: Отсутствуют SSL сертификаты

Если вы видите ошибку вида `cannot load certificate "/etc/nginx/ssl/cert.pem": No such file or directory`:

**Для Linux/macOS:**
```bash
# 1. Создайте самоподписанные SSL сертификаты
./scripts/server/create-ssl-certs.sh

# 2. Перезапустите Nginx
docker compose -f docker/docker-compose.yml restart nginx

# 3. Проверьте, что сертификаты созданы
ls -la docker/nginx/ssl/
```

**Для Windows:**
```powershell
# 1. Создайте самоподписанные SSL сертификаты
.\scripts\server\create-ssl-certs.ps1

# 2. Перезапустите Nginx
docker compose -f docker/docker-compose.yml restart nginx

# 3. Проверьте, что сертификаты созданы
dir docker\nginx\ssl
```

### Проблема: Контейнеры не запускаются

```bash
# Проверка логов
docker compose -f docker/docker-compose.yml logs

# Проверка конфигурации
docker compose -f docker/docker-compose.yml config

# Пересборка с очисткой кэша
docker compose -f docker/docker-compose.yml build --no-cache
```

### Проблема: Порт уже занят

```bash
# Проверка, какой процесс использует порт
netstat -tulpn | grep :8001
netstat -tulpn | grep :3000
netstat -tulpn | grep :80

# Изменение портов в docker-compose.yml
```

### Проблема: Недостаточно памяти

```bash
# Увеличение памяти Docker Desktop (в настройках)
# Или уменьшение количества воркеров в docker-compose.yml
```

### Проблема: Nginx постоянно перезапускается

Если контейнер Nginx показывает статус "Restarting", это обычно указывает на ошибки конфигурации:

```bash
# 1. Проверка логов Nginx для определения ошибки
docker compose -f docker/docker-compose.yml logs nginx

# 2. Проверка конфигурации Nginx
docker compose -f docker/docker-compose.yml exec nginx nginx -t

# 3. Если есть ошибки в конфигурации, проверьте файлы:
#    - docker/nginx/nginx.conf
#    - docker/nginx/conf.d/default.conf

# 4. Проверка доступности бэкенда и фронтенда
curl http://localhost:8001/api/v1/
curl http://localhost:3000

# 5. Если проблема в зависимостях, перезапустите их:
docker compose -f docker/docker-compose.yml restart backend frontend
```

### Проблема: База данных не инициализируется

```bash
# Полная перезагрузка с очисткой данных
docker compose down -v
docker compose up -d
```

## 📚 Дополнительная информация

- [Документация по развертыванию на сервере](DOCKER_SETUP.md)
- [Структура проекта](PROJECT_STRUCTURE.md)
- [Проверка работоспособности](health-check.md)

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи контейнеров
2. Убедитесь, что все порты свободны
3. Проверьте доступность дискового пространства
4. Создайте issue в репозитории проекта

---

**Готово!** После выполнения этих шагов у вас будет полностью работающая локальная среда разработки FREESPORT Platform.