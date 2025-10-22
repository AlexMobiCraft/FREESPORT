# Часто задаваемые вопросы по развертыванию FREESPORT Platform

## Общие вопросы

### Q: Как проверить выполнился ли полностью скрипт полной настройки сервера одной командой?

**A:** После выполнения автоматической настройки проверьте:

```bash
# Переключитесь на пользователя freesport
sudo su - freesport

# Перейдите в директорию проекта
cd /freesport

# Проверка статуса всех сервисов
./scripts/deploy/deploy.sh status

# Комплексная проверка работоспособности
./scripts/deploy/health-check.sh

# Проверка логов на наличие ошибок
docker compose -f docker/docker-compose.prod.yml logs

# Проверка доступности сайта
curl -I https://freesport.ru
```

**Ожидаемые результаты:**

- Все контейнеры в статусе "Up" или "running"
- Проверка health-check завершается без ошибок
- Сайт отвечает по HTTPS

**Если возникают ошибки при переключении на пользователя freesport:**

1. **Ошибка `sudo: unable to resolve host freesport-server`:**

```bash
# Исправление проблемы с хостом
sudo hostnamectl set-hostname $(hostname)
echo "127.0.0.1 $(hostname)" | sudo tee -a /etc/hosts

# Проверка
hostname
```

2. **Ошибка `su: user freesport does not exist`:**

```bash
# Проверка существования пользователя
id freesport || echo "Пользователь freesport не существует"

# Создание пользователя вручную
sudo adduser --system --group freesport
sudo usermod -aG sudo,docker freesport

# Настройка прав доступа
sudo mkdir -p /opt/freesport
sudo chown freesport:freesport /opt/freesport
```

3. **Альтернативный вариант - работа под текущим пользователем:**

```bash
# Клонирование проекта в домашнюю директорию
git clone https://github.com/AlexMobiCraft/FREESPORT.git ~/freesport
cd ~/freesport

# Настройка прав доступа к Docker
sudo usermod -aG docker $USER
newgrp docker

# Продолжение настройки
chmod +x scripts/deploy/*.sh
cp .env.prod.example .env.prod
nano .env.prod
./scripts/deploy/deploy.sh init
```

### Q: Как при варианте 1 изменить пароли в .env.prod?

**A:** При автоматической настройке пароли генерируются автоматически. Для их изменения:

```bash
# Переключитесь на пользователя freesport
sudo su - freesport

# Перейдите в директорию проекта
cd /opt/freesport

# Отредактируйте файл окружения
nano .env.prod
```

**Обязательно измените в `.env.prod`:**

- `SECRET_KEY` - сгенерируйте новый ключ (подробности ниже)
- `DB_PASSWORD` - установите надежный пароль для PostgreSQL
- `REDIS_PASSWORD` - установите надежный пароль для Redis

### Подробное описание генерации SECRET_KEY

**Что такое SECRET_KEY:**
`SECRET_KEY` - это критически важный параметр безопасности Django, используемый для криптографической подписи сессий, токенов CSRF и других данных безопасности.

**Как сгенерировать новый SECRET_KEY:**

1. **Способ 1: Использование OpenSSL (рекомендуется)**

```bash
# Генерация случайного ключа длиной 50 символов
openssl rand -base64 50

# Или более короткий ключ (минимум 32 символа)
openssl rand -base64 32
```

2. **Способ 2: Использование Python**

```bash
# Генерация с помощью Python
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
```

1. **Способ 3: Онлайн-генератор (для разработки)**

- Перейдите на https://djecrety.ir/
- Сгенерируйте новый ключ

**Процесс замены SECRET_KEY в .env.prod:**

1. **Откройте файл .env.prod:**

```bash
nano /opt/freesport/.env.prod
```

1. **Найдите строку с SECRET_KEY:**

```text
SECRET_KEY=your-super-secret-key-change-this-in-production
```

1. **Замените значение на сгенерированный ключ:**

```bash
# Сначала сгенерируйте ключ
NEW_KEY=$(openssl rand -base64 50)
echo "Новый ключ: $NEW_KEY"

# Затем замените в файле
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$NEW_KEY/" /freesport/.env.prod
```

4. **Или вручную замените в редакторе nano:**

- Нажмите Ctrl+X для выхода
- Нажмите Y для сохранения изменений
- Нажмите Enter для подтверждения имени файла

1. **Проверьте изменения:**

```bash
grep SECRET_KEY /opt/freesport/.env.prod
```

**Важные замечания о SECRET_KEY:**

- Длина ключа должна быть не менее 32 случайных символов
- Используйте только уникальный ключ для каждого проекта
- Никогда не используйте ключ из примеров или документации
- Не храните SECRET_KEY в системах контроля версий
- Регенерируйте ключ при подозрении на компрометацию

**После изменения SECRET_KEY:**

```bash
# Перезапустите сервисы для применения изменений
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.yml up -d

# Проверьте работоспособность
./scripts/deploy/health-check.sh
```

**После изменения паролей:**

```bash
# Перезапустите сервисы
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.yml up -d

# Проверьте работоспособность
./scripts/deploy/health-check.sh
```

## Проблемы и решения

### Q: Скрипт настройки завершился с ошибкой, что делать?

**A:** Проверьте логи выполнения:

```bash
# Проверка логов скрипта
sudo journalctl -u freesport-setup -f

# Проверка логов системных служб
sudo systemctl status docker
sudo journalctl -u docker -f
```

**Распространенные проблемы:**

1. **Недостаточно прав** - выполняйте скрипт с `sudo`
2. **Проблемы с сетью** - проверьте доступ к репозиторию Docker и GitHub
3. **Недостаточно места на диске** - очистите временные файлы

### Q: Контейнеры не запускаются после настройки

**A:** Проверьте состояние контейнеров:

```bash
# Проверка статуса
docker compose -f docker/docker-compose.prod.yml ps

# Проверка логов конкретного контейнера
docker compose -f docker/docker-compose.prod.yml logs [имя_контейнера]

# Проверка конфигурации
docker compose -f docker/docker-compose.prod.yml config
```

### Q: Сайт недоступен после настройки

**A:** Проверьте несколько моментов:

```bash
# Проверка работы Nginx
docker compose -f docker/docker-compose.prod.yml exec nginx nginx -t

# Проверка файрвола
sudo ufw status

# Проверка DNS
nslookup freesport.ru

# Проверка SSL сертификата
sudo certbot certificates
```

## Управление платформой

### Q: Как обновить платформу до новой версии?

**A:** Используйте скрипт обновления:

```bash
# Переключитесь на пользователя freesport
sudo su - freesport

# Перейдите в директорию проекта
cd /opt/freesport

# Обновление
./scripts/deploy/deploy.sh update

# Проверка после обновления
./scripts/deploy/health-check.sh
```

### Q: Как создать резервную копию?

**A:** Используйте скрипт резервного копирования:

```bash
# Создание резервной копии
./scripts/deploy/deploy.sh backup

# Просмотр доступных бэкапов
ls -la backups/

# Восстановление из бэкапа
./scripts/deploy/deploy.sh restore backups/20231201_120000
```

### Q: Как перезапустить отдельный сервис?

**A:** Используйте Docker Compose:

```bash
# Перезапуск всех сервисов
docker compose -f docker/docker-compose.prod.yml restart

# Перезапуск конкретного сервиса
docker compose -f docker/docker-compose.prod.yml restart [имя_сервиса]

# Примеры:
docker compose -f docker/docker-compose.prod.yml restart backend
docker compose -f docker/docker-compose.prod.yml restart nginx
```

## Мониторинг и отладка

### Q: Как проверить загрузку системы?

**A:** Используйте следующие команды:

```bash
# Статистика Docker контейнеров
docker stats

# Использование ресурсов системы
htop
df -h
free -h

# Нагрузка на процессор
uptime
```

### Q: Как посмотреть логи приложения?

**A:** Используйте команды Docker:

```bash
# Все логи
docker compose -f docker/docker-compose.prod.yml logs -f

# Логи конкретного сервиса
docker compose -f docker/docker-compose.prod.yml logs -f backend
docker compose -f docker/docker-compose.prod.yml logs -f frontend
docker compose -f docker/docker-compose.prod.yml logs -f nginx

# Логи за последний час
docker compose -f docker/docker-compose.prod.yml logs --since="1h" backend
```

### Q: Как подключиться к базе данных?

**A:** Используйте команду exec:

```bash
# Подключение к PostgreSQL
docker compose -f docker/docker-compose.prod.yml exec db psql -U postgres -d freesport

# Подключение к Redis
docker compose -f docker/docker-compose.prod.yml exec redis redis-cli -a [REDIS_PASSWORD]
```

## Безопасность

### Q: Как настроить SSL сертификат?

**A:** Используйте Certbot:

```bash
# Установка Certbot (если не установлен)
sudo apt install -y certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d freesport.ru -d www.freesport.ru

# Автоматическое обновление
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### Q: Как изменить SSH порт?

**A:** Отредактируйте конфигурацию SSH:

```bash
# Редактирование конфигурации
sudo nano /etc/ssh/sshd_config

# Измените порт:
# Port 22 → Port 2222

# Перезапуск SSH
sudo systemctl restart ssh

# Обновите правила файрвола
sudo ufw delete allow 22/tcp
sudo ufw allow 2222/tcp
```

## Производительность

### Q: Как оптимизировать работу платформы?

**A:** Выполните следующие действия:

```bash
# Очистка Docker
docker system prune -a

# Оптимизация базы данных
docker compose -f docker/docker-compose.prod.yml exec db psql -U postgres -d freesport -c "VACUUM ANALYZE;"

# Перезапуск сервисов для освобождения памяти
docker compose -f docker/docker-compose.prod.yml restart
```

### Q: Как увеличить лимиты системы?

**A:** Отредактируйте системные ограничения:

```bash
# Редактирование лимитов
sudo nano /etc/security/limits.conf

# Добавьте строки:
freesport soft nofile 65536
freesport hard nofile 65536

# Перезагрузите систему для применения изменений
sudo reboot
```

## Дополнительная информация

### Q: Где найти дополнительную документацию?

**A:** Обратитесь к следующим ресурсам:

- [Основная документация по развертыванию](README.md)
- [Подробная инструкция по установке](docker-server-setup.md)
- [Проверка работоспособности](health-check.md)
- [Структура проекта](PROJECT_STRUCTURE.md)

### Q: Как сообщить о проблеме?

**A:** Создайте issue в репозитории проекта со следующей информацией:

- Версия ОС
- Версия Docker
- Логи ошибок
- Шаги воспроизведения проблемы
