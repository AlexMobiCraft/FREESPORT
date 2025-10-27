# Быстрое развертывание FREESPORT Platform

Эта инструкция предназначена для быстрого развертывания платформы на сервере с уже установленным Docker.

## Предварительные требования

- Сервер с Ubuntu 20.04+ или CentOS 8+
- Установленный Docker и Docker Compose
- Доменное имя freesport.ru
- IP адрес: 5.35.124.149
- Git

## Шаг 1: Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker (если еще не установлен)
curl -fsSL https://raw.githubusercontent.com/AlexMobiCraft/FREESPORT/main/scripts/deploy/install-docker.sh | sudo bash

# Установка Git
sudo apt install -y git
```

## Шаг 2: Клонирование и настройка проекта

```bash
# Клонирование проекта
git clone https://github.com/AlexMobiCraft/FREESPORT.git freesport
cd freesport

# Создание production конфигурации
cp .env.prod.example .env.prod

# Редактирование переменных окружения
nano .env.prod
```

> **Важно:** храните `.env.prod` в корне репозитория и запускайте `docker compose` с флагом `--env-file .env.prod` (при выполнении команд из корня). Если переходите в каталог `docker/`, используйте `--env-file ../.env.prod`.

**Обязательно измените в файле `.env.prod`:**
- `SECRET_KEY` - сгенерируйте новый ключ
- `DB_PASSWORD` - установите надежный пароль
- `REDIS_PASSWORD` - установите надежный пароль
- `ALLOWED_HOSTS` - уже настроено для freesport.ru и IP 5.35.124.149
- `CORS_ALLOWED_ORIGINS` - уже настроено для freesport.ru
- `NEXT_PUBLIC_API_URL` - уже настроено для freesport.ru

## Шаг 3: Настройка Nginx для SSL

```bash
# Создание директории для SSL сертификатов
mkdir -p docker/ssl

# Временная конфигурация Nginx (до получения SSL)
mkdir -p docker/nginx/conf.d
```

## Шаг 4: Развертывание

```bash
# Установка прав на выполнение скриптов
chmod +x scripts/deploy/*.sh

# Сборка и запуск контейнеров
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build

# Выполнение миграций
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate

# Создание суперпользователя
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py createsuperuser

# Сбор статических файлов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Проверка статуса
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml ps
```

## Шаг 5: Настройка SSL с Let's Encrypt

```bash
# Установка Certbot
sudo apt install -y certbot python3-certbot-nginx

# Получение SSL сертификата
sudo certbot --nginx -d freesport.ru -d www.freesport.ru

# Настройка автоматического обновления сертификата
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

## Шаг 6: Проверка работоспособности

```bash
# Проверка доступности сайта
curl -I https://freesport.ru

# Проверка API
curl https://freesport.ru/api/v1/health/

# Просмотр логов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs -f
```

## Управление развертыванием

### Обновление платформы

```bash
# Скачивание обновлений
git pull origin main

# Пересборка и перезапуск
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml down
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build

# Выполнение миграций
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate

# Сбор статических файлов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### Резервное копирование

```bash
# Создание бэкапа базы данных
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db pg_dump -U postgres freesport > backup_$(date +%Y%m%d).sql

# Создание бэкапа медиа файлов
tar -czf media_backup_$(date +%Y%m%d).tar.gz data/
```

### Восстановление из бэкапа

```bash
# Восстановление базы данных
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS freesport;"
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -c "CREATE DATABASE freesport;"
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres freesport < backup_20231201.sql

# Восстановление медиа файлов
tar -xzf media_backup_20231201.tar.gz
```

## Полезные команды

```bash
# Просмотр статуса контейнеров
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml ps

# Просмотр логов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs -f [service_name]

# Перезапуск сервиса
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart [service_name]

# Вход в контейнер
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend bash

# Подключение к базе данных
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec db psql -U postgres -d freesport

# Остановка всех сервисов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml down

# Полная очистка
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml down -v --remove-orphans
docker system prune -a
```

## Решение проблем

### Проблема: Контейнеры не запускаются

```bash
# Проверка логов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs

# Проверка конфигурации
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml config
```

### Проблема: Нет доступа к сайту

```bash
# Проверка работы Nginx
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec nginx nginx -t

# Перезапуск Nginx
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart nginx
```

### Проблема: Ошибки базы данных

```bash
# Проверка подключения к БД
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py dbshell

# Повторное выполнение миграций
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate
```

## Мониторинг

### Проверка потребления ресурсов

```bash
# Статистика Docker
docker stats

# Информация о системе
df -h
free -h
top
```

### Настройка оповещений

```bash
# Создание скрипта проверки работоспособности
nano scripts/health-check.sh
```

```bash
#!/bin/bash
# Проверка работоспособности сервисов

# Проверка доступности сайта
if ! curl -f -s https://freesport.ru > /dev/null; then
    echo "Сайт недоступен" | mail -s "FREESPORT Alert" admin@freesport.ru
fi

# Проверка работы API
if ! curl -f -s https://freesport.ru/api/v1/health/ > /dev/null; then
    echo "API недоступен" | mail -s "FREESPORT Alert" admin@freesport.ru
fi
```

```bash
# Добавление в cron для проверки каждые 5 минут
echo "*/5 * * * * /path/to/freesport/scripts/health-check.sh" | crontab -
```

## Следующие шаги

После успешного развертывания:

1. Настройте регулярные резервные копии
2. Настройте мониторинг и оповещения
3. Оптимизируйте производительность
4. Настройте CI/CD для автоматического развертывания
5. Изучите [полную документацию](docker-server-setup.md) для дополнительной настройки

## Поддержка

При возникновении проблем:

1. Проверьте логи контейнеров
2. Обратитесь к документации проекта
3. Создайте issue в репозитории
