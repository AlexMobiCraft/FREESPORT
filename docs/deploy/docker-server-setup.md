# Инструкция по установке Docker и развертыванию FREESORT Platform

## Обзор

FREESPORT - это современная API-First E-commerce платформа для B2B/B2C продаж спортивных товаров, включающая:
- **Backend**: Django 5.2 + Django REST Framework
- **Frontend**: Next.js 14+ + TypeScript
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7.0+
- **Queue**: Celery + Redis
- **Proxy**: Nginx

## Требования к серверу

### Минимальные системные требования
- **CPU**: 2 ядра
- **RAM**: 4 ГБ
- **Storage**: 20 ГБ SSD
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+

### Рекомендуемые системные требования для production
- **CPU**: 4+ ядер
- **RAM**: 8+ ГБ
- **Storage**: 50+ ГБ SSD
- **OS**: Ubuntu 22.04 LTS

## Шаг 1: Подготовка сервера

### 1.1 Обновление системы

#### Для Ubuntu/Debian:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget gnupg lsb-release software-properties-common ca-certificates
```

#### Для CentOS/RHEL:
```bash
sudo yum update -y
sudo yum install -y curl wget gnupg
```

### 1.2 Настройка файрвола

#### Ubuntu (UFW):
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

#### CentOS (firewalld):
```bash
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 1.3 Создание пользователя для развертывания (рекомендуется)

```bash
sudo adduser freesport
sudo usermod -aG sudo freesport
sudo su - freesport
```

## Шаг 2: Установка Docker

### 2.1 Установка Docker Engine

#### Для Ubuntu:
```bash
# Добавление официального GPG ключа Docker
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавление репозитория Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

#### Для CentOS/RHEL:
```bash
# Добавление репозитория Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Установка Docker Engine
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 2.2 Запуск и настройка Docker

```bash
# Запуск Docker
sudo systemctl start docker
sudo systemctl enable docker

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Проверка установки
docker --version
docker compose version
```

## Шаг 3: Установка Docker Compose (если не установлен с плагином)

### 3.1 Установка Docker Compose standalone

```bash
# Скачивание последней версии Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Предоставление прав на выполнение
sudo chmod +x /usr/local/bin/docker-compose

# Проверка установки
docker-compose --version
```

## Шаг 4: Установка дополнительных инструментов

### 4.1 Git

```bash
# Ubuntu/Debian
sudo apt install -y git

# CentOS/RHEL
sudo yum install -y git
```

### 4.2 Node.js (для локальной разработки frontend)

```bash
# Установка Node.js 18 LTS через NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Проверка установки
node --version
npm --version
```

### 4.3 Python (для локальной разработки backend)

```bash
# Ubuntu/Debian (Python 3.11)
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# CentOS/RHEL
sudo dnf install -y python3.11 python3.11-pip python3.11-devel

# Проверка установки
python3.11 --version
```

## Шаг 5: Подготовка проекта к развертыванию

### 5.1 Клонирование репозитория

```bash
# Клонирование проекта
git clone https://github.com/AlexMobiCraft/FREESPORT.git freesport
cd freesport

# Проверка структуры проекта
ls -la
```

### 5.2 Настройка переменных окружения

```bash
# Копирование примера файла окружения
cp .env.prod.example .env.prod

# Редактирование и заполнение переменных окружения
nano .env.prod

# Проверка заполнения критичных переменных (например, REDIS_PASSWORD)
grep -E "^(SECRET_KEY|DB_PASSWORD|REDIS_PASSWORD)=" .env.prod
```

> **Важно:** не переименовывайте `.env.prod` в `.env`. Храните этот файл в корне репозитория (рядом с `.env.prod.example`) и запускайте `docker compose` с флагом `--env-file ../.env.prod`, если команда выполняется из каталога `docker/`, либо используйте относительный путь `docker/docker-compose.prod.yml`, если команды выполняются из корня проекта.

### 5.3 Создание директорий для данных

```bash
# Создание необходимых директорий
mkdir -p data/import_1c
mkdir -p logs
mkdir -p backend/static
```

## Шаг 6: Развертывание платформы

### 6.1 Сборка и запуск контейнеров

```bash
# Сборка Docker образов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml build

# Предварительная проверка итоговой конфигурации (опционально, но рекомендуется)
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml config

# Запуск всех сервисов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d

# Проверка статуса контейнеров
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml ps
```

### 6.2 Выполнение миграций базы данных

```bash
# Выполнение миграций
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate

# Создание суперпользователя
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py createsuperuser

# Сбор статических файлов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### 6.3 Проверка работоспособности

```bash
# Проверка логов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs -f

# Проверка доступности сервисов через Nginx
curl -I http://localhost/api/v1/health/
curl http://localhost:3000/

# Проверка API напрямую из контейнера backend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend \
  curl http://127.0.0.1:8000/api/v1/health/

# Проверка состояния Celery worker
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs celery
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec celery celery -A freesport inspect active

# Проверка состояния Celery beat
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs celery-beat
```

## Шаг 7: Настройка Production окружения

### 7.1 Настройка SSL сертификатов (Let's Encrypt)

#### Подготовка окружения

```bash
# Установка необходимых пакетов
sudo apt update
sudo apt install -y certbot

# Разрешаем внешние подключения к 80/443 (если включён ufw)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Каталог, куда будут копироваться сертификаты для контейнера nginx
mkdir -p docker/ssl
```

#### Получение сертификата (standalone режим)

> контейнер nginx должен быть остановлен, чтобы certbot занял порт 80

```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml stop nginx

sudo certbot certonly --standalone \
  -d freesport.ru -d www.freesport.ru \
  --agree-tos --no-eff-email \
  -m admin@freesport.ru
```

Сертификаты появятся в каталоге `/etc/letsencrypt/live/freesport.ru/`.

#### Копирование сертификатов в проект

```bash
sudo cp /etc/letsencrypt/live/freesport.ru/fullchain.pem docker/ssl/fullchain.pem
sudo cp /etc/letsencrypt/live/freesport.ru/privkey.pem docker/ssl/privkey.pem
sudo chmod 600 docker/ssl/privkey.pem
```

#### Обновление конфигурации nginx

Убедитесь, что в `docker/nginx/conf.d/default.conf` прописаны HTTPS и HTTP-блоки:

```nginx
server {
    listen 443 ssl;
    server_name freesport.ru www.freesport.ru;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers EECDH+AESGCM:EECDH+CHACHA20;

    # далее дублируем location из HTTP-блока
}

server {
    listen 80;
    server_name freesport.ru www.freesport.ru;
    return 301 https://$host$request_uri;
}
```

#### Перезапуск nginx и проверка

```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d nginx

docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec nginx nginx -t

curl -I https://freesport.ru/
curl -k -I https://localhost/api/v1/health/
```

#### Продление сертификата

Certbot создаёт systemd timer, но после продления нужно заново скопировать файлы и перезапустить nginx:

```bash
sudo certbot renew --dry-run

sudo cp /etc/letsencrypt/live/freesport.ru/fullchain.pem docker/ssl/fullchain.pem
sudo cp /etc/letsencrypt/live/freesport.ru/privkey.pem docker/ssl/privkey.pem

docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart nginx
```

### 7.2 Настройка автоматического обновления

```bash
# Создание скрипта для обновления
nano scripts/update.sh
```

```bash
#!/bin/bash
# Скрипт обновления платформы

cd /path/to/freesport

# Скачивание последних изменений
git pull origin main

# Пересборка и перезапуск контейнеров
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Выполнение миграций
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Сбор статических файлов
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

echo "Обновление завершено"
```

```bash
# Предоставление прав на выполнение
chmod +x scripts/update.sh

# Добавление в cron для ежедневного обновления в 3:00
echo "0 3 * * * /path/to/freesport/scripts/update.sh" | crontab -
```

## Шаг 8: Мониторинг и обслуживание

### 8.1 Настройка логирования

```bash
# Создание директории для логов
mkdir -p logs/nginx
mkdir -p logs/backend
mkdir -p logs/frontend

# Настройка ротации логов
sudo nano /etc/logrotate.d/freesport
```

```
/path/to/freesport/logs/*/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 freesport freesport
    postrotate
        docker compose restart nginx
    endscript
}
```

### 8.2 Резервное копирование

```bash
# Создание скрипта резервного копирования
nano scripts/backup.sh
```

```bash
#!/bin/bash
# Скрипт резервного копирования

BACKUP_DIR="/backup/freesport"
DATE=$(date +%Y%m%d_%H%M%S)

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

# Резервное копирование базы данных
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres freesport > $BACKUP_DIR/db_backup_$DATE.sql

# Резервное копирование медиа файлов
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz data/

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Резервное копирование завершено: $DATE"
```

```bash
# Предоставление прав на выполнение
chmod +x scripts/backup.sh

# Добавление в cron для ежедневного резервного копирования в 2:00
echo "0 2 * * * /path/to/freesport/scripts/backup.sh" | crontab -
```

## Шаг 9: Оптимизация производительности

### 9.1 Настройка Docker

```bash
# Оптимизация Docker daemon
sudo nano /etc/docker/daemon.json
```

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

```bash
# Перезапуск Docker
sudo systemctl restart docker
```

### 9.2 Настройка системных параметров

```bash
# Оптимизация системных параметров
sudo nano /etc/sysctl.conf
```

```
# Увеличение лимитов для производительности
fs.file-max = 2097152
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.core.netdev_max_backlog = 5000
vm.swappiness = 10
```

```bash
# Применение параметров
sudo sysctl -p
```

## Шаг 10: Безопасность

### 10.1 Настройка безопасности Docker

```bash
# Ограничение доступа к Docker socket
sudo chmod 660 /var/run/docker.sock
sudo chown root:docker /var/run/docker.sock

# Настройка Docker Content Trust
export DOCKER_CONTENT_TRUST=1
```

### 10.2 Регулярное обновление

```bash
# Создание скрипта обновления системы
nano scripts/system-update.sh
```

```bash
#!/bin/bash
# Скрипт обновления системы

# Обновление пакетов
sudo apt update && sudo apt upgrade -y

# Обновление Docker
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Перезапуск сервисов
sudo systemctl restart docker

echo "Система обновлена"
```

```bash
# Предоставление прав на выполнение
chmod +x scripts/system-update.sh

# Добавление в cron для еженедельного обновления в 4:00 каждое воскресенье
echo "0 4 * * 0 /path/to/freesport/scripts/system-update.sh" | crontab -
```

## Полезные команды

### Управление контейнерами
```bash
# Просмотр запущенных контейнеров
docker compose -f docker-compose.prod.yml ps

# Просмотр логов
docker compose -f docker-compose.prod.yml logs -f [service_name]

# Перезапуск сервиса
docker compose -f docker-compose.prod.yml restart [service_name]

# Остановка всех сервисов
docker compose -f docker-compose.prod.yml down

# Полная очистка
docker compose -f docker-compose.prod.yml down -v --remove-orphans
docker system prune -a
```

### Работа с базой данных
```bash
# Подключение к базе данных
docker compose -f docker-compose.prod.yml exec db psql -U postgres -d freesport

# Создание бэкапа БД
docker compose -f docker-compose.prod.yml exec db pg_dump -U postgres freesport > backup.sql

# Восстановление БД из бэкапа
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres freesport < backup.sql
```

### Отладка
```bash
# Вход в контейнер backend
docker compose -f docker-compose.prod.yml exec backend bash

# Вход в контейнер frontend
docker compose -f docker-compose.prod.yml exec frontend sh

# Просмотр потребления ресурсов
docker stats
```

## Возможные проблемы и их решение

### Проблема: Недостаточно прав для Docker
**Решение:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Проблема: Контейнеры не могут подключиться к сети
**Решение:**
```bash
# Проверка сетевых настроек
docker network ls
docker network inspect freesport-network

# Пересоздание сети
docker compose -f docker-compose.prod.yml down
docker network prune
docker compose -f docker-compose.prod.yml up -d
```

### Проблема: Недостаточно места на диске
**Решение:**
```bash
# Очистка Docker
docker system prune -a
docker volume prune

# Очистка логов
sudo journalctl --vacuum-time=7d
```

### Проблема: База данных не запускается
**Решение:**
```bash
# Проверка логов контейнера БД
docker compose -f docker-compose.prod.yml logs db

# Проверка прав на директорию данных
sudo chown -R 999:999 postgres_data/
```

## Заключение

После выполнения всех этих шагов у вас будет полностью настроенное окружение для развертывания и работы с FREESPORT Platform. Регулярно выполняйте обновления и резервные копирования для обеспечения стабильной работы системы.

Для дополнительной информации обратитесь к:
- [Официальной документации Docker](https://docs.docker.com/)
- [Документации проекта FREESPORT](../../README.md)
- [API документации](../api-spec.yaml)