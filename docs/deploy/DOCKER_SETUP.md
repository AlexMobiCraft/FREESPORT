# Установка Docker и развертывание FREESPORT Platform

Эта страница содержит краткое руководство по установке Docker и развертыванию платформы FREESPORT на сервере 5.35.124.149 для домена freesport.ru.

## 🚀 Быстрый старт

### Вариант 1: Полная автоматическая настройка (рекомендуется)

```bash
# Скачивание и запуск скрипта полной настройки сервера
curl -fsSL https://raw.githubusercontent.com/AlexMobiCraft/FREESPORT/main/scripts/deploy/server-setup.sh | sudo bash
```

### Вариант 2: Пошаговая установка

#### 1. Автоматическая установка Docker

```bash
# Скачивание и запуск скрипта установки Docker
curl -fsSL https://raw.githubusercontent.com/AlexMobiCraft/FREESPORT/main/scripts/deploy/install-docker.sh | sudo bash

# Перезаход в систему для применения изменений
exit  # и снова login
```

#### 2. Развертывание платформы

```bash
# Клонирование проекта
git clone https://github.com/AlexMobiCraft/FREESPORT.git freesport
cd freesport

# Установка прав на выполнение скриптов
chmod +x scripts/deploy/*.sh

# Настройка переменных окружения
cp .env.prod.example .env.prod
nano .env.prod  # Обязательно измените пароли!

# Развертывание платформы
./scripts/deploy/deploy.sh init
```

## 📋 Подробная инструкция

### Шаг 1: Требования к серверу

- **CPU**: 2+ ядра
- **RAM**: 4+ ГБ
- **Storage**: 20+ ГБ SSD
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **IP**: 5.35.124.149
- **Домен**: freesport.ru

### Шаг 2: Установка Docker

#### Полная автоматическая настройка (рекомендуется)
```bash
curl -fsSL https://raw.githubusercontent.com/AlexMobiCraft/FREESPORT/main/scripts/deploy/server-setup.sh | sudo bash
```

#### Только установка Docker
```bash
sudo ./scripts/deploy/install-docker.sh
```

#### Ручная установка
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### Шаг 3: Настройка проекта

```bash
# Клонирование репозитория
git clone https://github.com/AlexMobiCraft/FREESPORT.git freesport
cd freesport

# Настройка переменных окружения
cp .env.prod.example .env.prod
nano .env.prod
```

**Важно:** Измените в `.env.prod`:
- `SECRET_KEY` - сгенерируйте новый ключ
- `DB_PASSWORD` - установите надежный пароль
- `REDIS_PASSWORD` - установите надежный пароль
- `ALLOWED_HOSTS` - уже настроено для freesport.ru и IP 5.35.124.149
- `CORS_ALLOWED_ORIGINS` - уже настроено для freesport.ru

### Шаг 4: Развертывание

```bash
# Инициализация проекта
./scripts/deploy/deploy.sh init

# Проверка статуса
./scripts/deploy/deploy.sh status
```

### Шаг 5: Настройка SSL (опционально)

```bash
# Установка Certbot
sudo apt install -y certbot python3-certbot-nginx

# Получение SSL сертификата
sudo certbot --nginx -d freesport.ru
```

## 🛠️ Управление платформой

### Основные команды

```bash
# Обновление платформы
./scripts/deploy/deploy.sh update

# Создание резервной копии
./scripts/deploy/deploy.sh backup

# Восстановление из резервной копии
./scripts/deploy/deploy.sh restore backups/20231201_120000

# Проверка статуса
./scripts/deploy/deploy.sh status

# Проверка работоспособности
./scripts/deploy/health-check.sh

# Просмотр логов
docker compose -f docker/docker-compose.prod.yml logs -f

# Перезапуск сервисов
docker compose -f docker/docker-compose.prod.yml restart
```

### Полезные команды Docker

```bash
# Просмотр запущенных контейнеров
docker ps

# Вход в контейнер backend
docker compose -f docker/docker-compose.prod.yml exec backend bash

# Подключение к базе данных
docker compose -f docker/docker-compose.prod.yml exec db psql -U postgres -d freesport

# Очистка системы
docker system prune -a
```

## 🔍 Проверка работоспособности

После развертывания выполните проверку:

```bash
# Проверка здоровья всех сервисов
curl https://freesport.ru/api/v1/health/

# Комплексная проверка
./scripts/deploy/health-check.sh
```

## 📚 Документация

- [Полная инструкция по установке](docker-server-setup.md)
- [Быстрое развертывание](quick-deployment.md)
- [Проверка работоспособности](health-check.md)
- [Документация скриптов](../../scripts/deploy/README.md)
- [Основная документация проекта](../../README.md)

## 🆘 Решение проблем

### Проблема: Permission denied
```bash
# Установка прав на выполнение
chmod +x scripts/deploy/*.sh
```

### Проблема: Docker не работает
```bash
# Перезаход в систему
exit  # и снова login

# Или
newgrp docker
```

### Проблема: Контейнеры не запускаются
```bash
# Проверка логов
docker compose -f docker/docker-compose.prod.yml logs

# Пересборка образов
docker compose -f docker/docker-compose.prod.yml build --no-cache
```

### Проблема: Нет доступа к сайту
```bash
# Проверка файрвола
sudo ufw status

# Проверка Nginx
docker compose -f docker/docker-compose.prod.yml exec nginx nginx -t
```

## 🔄 Автоматизация

### Настройка автоматического обновления
```bash
# Добавление в cron для ежедневного обновления в 3:00
echo "0 3 * * * /path/to/freesport/scripts/deploy/deploy.sh update" | crontab -

# Добавление в cron для ежедневного резервного копирования в 2:00
echo "0 2 * * * /path/to/freesport/scripts/deploy/deploy.sh backup" | crontab -
```

### Настройка мониторинга
```bash
# Добавление в cron для проверки каждые 5 минут
echo "*/5 * * * * /path/to/freesport/scripts/deploy/health-check.sh" | crontab -
```

## 🔒 Безопасность

1. **Измените все пароли** в файле `.env.prod`
2. **Используйте SSH ключи** для доступа к серверу
3. **Настройте файрвол** для ограничения доступа
4. **Регулярно обновляйте** систему и Docker
5. **Создавайте резервные копии** на регулярной основе

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи контейнеров
2. Обратитесь к документации
3. Создайте issue в репозитории проекта

---

**Готово!** После выполнения этих шагов у вас будет полностью работающая платформа FREESPORT.