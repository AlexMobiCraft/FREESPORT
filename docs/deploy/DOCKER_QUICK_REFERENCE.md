# Docker Quick Reference - FREESPORT Platform

Эта шпаргалка содержит основные команды для быстрой работы с Docker в проекте FREESPORT.

## 🚀 Быстрый запуск

```bash
# Клонирование и запуск
git clone https://github.com/AlexMobiCraft/FREESPORT.git
cd FREESPORT

# Создание SSL сертификатов (требуется для HTTPS)
# Для Linux/macOS:
./scripts/server/create-ssl-certs.sh

# Для Windows (PowerShell):
pwsh .\scripts\server\create-ssl-certs.ps1

# Запуск контейнеров
docker compose -f docker/docker-compose.yml up -d

# Инициализация БД
docker compose -f docker/docker-compose.yml exec backend python manage.py migrate
docker compose -f docker/docker-compose.yml exec backend python manage.py collectstatic --no-input

# Проверка статуса
docker compose -f docker/docker-compose.yml ps
```

## 📋 Основные команды

### Управление контейнерами

```bash
# Запуск всех сервисов
docker compose -f docker/docker-compose.yml up -d

# Остановка всех сервисов
docker compose -f docker/docker-compose.yml down

# Перезапуск всех сервисов
docker compose -f docker/docker-compose.yml restart

# Просмотр статуса
docker compose -f docker/docker-compose.yml ps

# Просмотр логов
docker compose -f docker/docker-compose.yml logs -f
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

## 🔧 Разработка

### Пересборка образов

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

```bash
# Просмотр использования ресурсов
docker stats

# Просмотр использования дискового пространства
docker system df

# Проверка здоровья всех контейнеров
docker compose -f docker/docker-compose.yml ps
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

## 🔄 Обновление проекта

```bash
# Получение последних изменений
git pull origin main

# Пересборка образов
docker compose -f docker/docker-compose.yml build --no-cache

# Перезапуск сервисов
docker compose -f docker/docker-compose.yml up -d

# Выполнение миграций
docker compose -f docker/docker-compose.yml exec backend python manage.py migrate

# Сбор статических файлов
docker compose -f docker/docker-compose.yml exec backend python manage.py collectstatic --no-input
```

## 🌐 Доступ к сервисам

После запуска сервисы доступны по адресам:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8001/api/v1
- Nginx (прокси): http://localhost:80
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## 🚨 Решение проблем

### Конфликт имен контейнеров

```bash
# Остановка и удаление всех контейнеров
docker compose -f docker/docker-compose.yml down -v

# Принудительное удаление оставшихся контейнеров
docker rm -f freesport-db freesport-redis freesport-backend freesport-frontend freesport-nginx freesport-celery freesport-celery-beat

# Повторный запуск
docker compose -f docker/docker-compose.yml up -d
```

### Проблема: Отсутствуют SSL сертификаты

**Для Linux/macOS:**

```bash
# Создание самоподписанных SSL сертификатов
./scripts/server/create-ssl-certs.sh

# Перезапуск Nginx
docker compose -f docker/docker-compose.yml restart nginx

# Проверка наличия сертификатов
ls -la docker/nginx/ssl/
```

**Для Windows:**

```powershell
# Создание самоподписанных SSL сертификатов
.\scripts\server\create-ssl-certs.ps1

# Перезапуск Nginx
docker compose -f docker/docker-compose.yml restart nginx

# Проверка наличия сертификатов
dir docker\nginx\ssl
```

### Проблема с Nginx (постоянно перезапускается)

```bash
# Проверка логов Nginx
docker compose -f docker/docker-compose.yml logs nginx

# Проверка конфигурации Nginx
docker compose -f docker/docker-compose.yml exec nginx nginx -t

# Перезапуск зависимых сервисов
docker compose -f docker/docker-compose.yml restart backend frontend
```

### Просмотр логов

```bash
# Все логи
docker compose -f docker/docker-compose.yml logs

# Логи конкретного сервиса
docker compose -f docker/docker-compose.yml logs backend
docker compose -f docker/docker-compose.yml logs frontend
docker compose -f docker/docker-compose.yml logs db
```

### Перезапуск с очисткой

```bash
# Полная перезагрузка с очисткой данных
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d
```

---

**Подсказка:** Для удобства можно создать алиасы в shell:

```bash
alias dc='docker compose -f docker/docker-compose.yml'
alias dcb='dc exec backend'
alias dcf='dc exec frontend'
```
