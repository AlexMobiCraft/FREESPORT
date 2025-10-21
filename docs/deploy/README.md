# Документация по развертыванию FREESPORT Platform

Эта директория содержит документацию по развертыванию и управлению платформой FREESPORT на сервере 5.35.124.149 с доменом freesport.ru.

## Структура документации

- [`docker-server-setup.md`](docker-server-setup.md) - Полная инструкция по установке Docker и развертыванию платформы
- [`quick-deployment.md`](quick-deployment.md) - Быстрое развертывание для опытных пользователей
- [`health-check.md`](health-check.md) - Проверка работоспособности всех компонентов
- [`ssl-setup.md`](ssl-setup.md) - Настройка SSL сертификатов
- [`backup-restore.md`](backup-restore.md) - Резервное копирование и восстановление
- [`monitoring.md`](monitoring.md) - Настройка мониторинга и оповещений
- [`troubleshooting.md`](troubleshooting.md) - Решение типичных проблем

## Скрипты развертывания

Все скрипты для автоматизации развертывания находятся в директории [`scripts/deploy/`](../../scripts/deploy/):

- [`server-setup.sh`](../../scripts/deploy/server-setup.sh) - Полная настройка сервера с нуля
- [`install-docker.sh`](../../scripts/deploy/install-docker.sh) - Установка Docker и Docker Compose
- [`deploy.sh`](../../scripts/deploy/deploy.sh) - Развертывание и управление платформой
- [`health-check.sh`](../../scripts/deploy/health-check.sh) - Проверка работоспособности

## Быстрый старт

### Полная автоматическая настройка (рекомендуется)

```bash
# Выполнение полной настройки сервера одной командой
curl -fsSL https://raw.githubusercontent.com/AlexMobiCraft/FREESPORT/main/scripts/deploy/server-setup.sh | sudo bash
```

### Пошаговая настройка

```bash
# 1. Установка Docker
curl -fsSL https://raw.githubusercontent.com/AlexMobiCraft/FREESPORT/main/scripts/deploy/install-docker.sh | sudo bash

# 2. Перезаход в систему
exit  # и снова login

# 3. Развертывание
git clone https://github.com/AlexMobiCraft/FREESPORT.git freesport
cd freesport
chmod +x scripts/deploy/*.sh
cp .env.prod.example .env.prod
nano .env.prod  # изменить только пароли!
./scripts/deploy/deploy.sh init

# 4. Настройка SSL
sudo certbot --nginx -d freesport.ru -d www.freesport.ru
```

## Управление платформой

```bash
# Статус сервисов
./scripts/deploy/deploy.sh status

# Обновление
./scripts/deploy/deploy.sh update

# Резервное копирование
./scripts/deploy/deploy.sh backup

# Проверка работоспособности
./scripts/deploy/health-check.sh
```

## Конфигурация

### Основные файлы конфигурации

- [`.env.prod`](../../.env.prod.example) - Переменные окружения для production
- [`docker-compose.prod.yml`](../../docker-compose.prod.yml) - Production конфигурация Docker Compose
- [`docker/nginx/`](../../docker/nginx/) - Конфигурация Nginx

### Переменные окружения

Основные переменные в `.env.prod`:

```bash
# Секретный ключ Django
SECRET_KEY=your-super-secret-key

# Настройки базы данных
DB_NAME=freesport
DB_USER=postgres
DB_PASSWORD=secure-password

# Настройки Redis
REDIS_PASSWORD=redis-password

# Настройки домена
ALLOWED_HOSTS=freesport.ru,www.freesport.ru,5.35.124.149
CORS_ALLOWED_ORIGINS=https://freesport.ru,https://www.freesport.ru
NEXT_PUBLIC_API_URL=https://freesport.ru/api/v1
```

## Безопасность

### Рекомендации по безопасности

1. **Измените все пароли** в файле `.env.prod`
2. **Используйте SSH ключи** для доступа к серверу
3. **Настройте файрвол** для ограничения доступа
4. **Регулярно обновляйте** систему и Docker
5. **Создавайте резервные копии** на регулярной основе
6. **Мониторьте логи** на предмет подозрительной активности

### Настройка SSH

```bash
# Отключение доступа по паролю
echo "PasswordAuthentication no" >> /etc/ssh/sshd_config

# Изменение порта SSH (опционально)
echo "Port 2222" >> /etc/ssh/sshd_config

# Перезапуск SSH
systemctl restart ssh
```

## Мониторинг

### Базовый мониторинг

```bash
# Проверка статуса контейнеров
docker compose -f docker-compose.prod.yml ps

# Проверка использования ресурсов
docker stats

# Проверка дискового пространства
df -h

# Проверка нагрузки
top
```

### Автоматическая проверка

```bash
# Добавление в cron для проверки каждые 5 минут
echo "*/5 * * * * /path/to/freesport/scripts/deploy/health-check.sh" | crontab -
```

## Резервное копирование

### Автоматическое резервное копирование

```bash
# Добавление в cron для ежедневного резервного копирования в 2:00
echo "0 2 * * * /path/to/freesport/scripts/deploy/deploy.sh backup" | crontab -
```

### Восстановление из резервной копии

```bash
# Восстановление из последней резервной копии
./scripts/deploy/deploy.sh restore backups/20231201_120000
```

## Обновление

### Автоматическое обновление

```bash
# Добавление в cron для ежедневного обновления в 3:00
echo "0 3 * * * /path/to/freesport/scripts/deploy/deploy.sh update" | crontab -
```

### Ручное обновление

```bash
# Обновление проекта
./scripts/deploy/deploy.sh update

# Проверка статуса после обновления
./scripts/deploy/deploy.sh status
```

## Поддержка

При возникновении проблем:

1. Проверьте логи контейнеров:
   ```bash
   docker compose -f docker-compose.prod.yml logs -f
   ```

2. Запустите проверку работоспособности:
   ```bash
   ./scripts/deploy/health-check.sh
   ```

3. Обратитесь к документации:
   - [Решение проблем](troubleshooting.md)
   - [Проверка работоспособности](health-check.md)

4. Создайте issue в репозитории проекта

## Дополнительные ресурсы

- [Основная документация проекта](../README.md)
- [API документация](../api-spec.yaml)
- [Скрипты развертывания](../../scripts/deploy/README.md)