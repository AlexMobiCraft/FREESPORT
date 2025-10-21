# Скрипты для развертывания и управления FREESPORT Platform

## Описание

В этой директории находятся скрипты для автоматизации установки Docker и развертывания платформы FREESORT.

## Скрипты

### server-setup.sh

Скрипт для полной первоначальной настройки сервера для FREESPORT Platform.

**Использование:**
```bash
# Скачивание и запуск скрипта настройки сервера
curl -fsSL https://raw.githubusercontent.com/AlexMobiCraft/FREESPORT/main/scripts/deploy/server-setup.sh | sudo bash

# Или локально:
sudo chmod +x scripts/deploy/server-setup.sh
sudo ./scripts/deploy/server-setup.sh
```

**Что делает скрипт:**
1. Настраивает имя хоста
2. Обновляет системные пакеты
3. Устанавливает Docker и Docker Compose
4. Создает пользователя freesport
5. Настраивает файрвол
6. Настраивает SSH
7. Клонирует и настраивает проект
8. Настраивает автоматическое обновление
9. Настраивает логирование
10. Выполняет первоначальное развертывание

**Конфигурация:**
- Домен: freesport.ru
- IP: 5.35.124.149
- Репозиторий: https://github.com/AlexMobiCraft/FREESPORT.git
- Директория проекта: /opt/freesport

### install-docker.sh

Скрипт для автоматической установки Docker и Docker Compose на сервер.

**Поддерживаемые ОС:**
- Ubuntu 20.04+
- Debian 11+
- CentOS 8+
- RHEL 8+
- Rocky Linux 8+

**Использование:**
```bash
# Скачивание и запуск скрипта
curl -fsSL https://raw.githubusercontent.com/your-repo/freesport/main/scripts/deploy/install-docker.sh | sudo bash

# Или локально:
sudo chmod +x scripts/deploy/install-docker.sh
sudo ./scripts/deploy/install-docker.sh
```

**Что делает скрипт:**
1. Определяет операционную систему
2. Обновляет системные пакеты
3. Устанавливает Docker Engine
4. Устанавливает Docker Compose
5. Настраивает файрвол
6. Оптимизирует настройки Docker
7. Устанавливает дополнительные утилиты

### deploy.sh

Скрипт для развертывания и управления платформой.

**Использование:**
```bash
chmod +x scripts/deploy/deploy.sh

# Инициализация проекта
./scripts/deploy/deploy.sh init

# Обновление проекта
./scripts/deploy/deploy.sh update

# Создание резервной копии
./scripts/deploy/deploy.sh backup

# Восстановление из резервной копии
./scripts/deploy/deploy.sh restore backups/20231201_120000

# Проверка статуса
./scripts/deploy/deploy.sh status

# Очистка системы
./scripts/deploy/deploy.sh cleanup

# Показать справку
./scripts/deploy/deploy.sh help
```

**Команды:**
- `init` - Первоначальная настройка и развертывание проекта
- `update` - Обновление проекта до последней версии
- `backup` - Создание резервной копии
- `restore` - Восстановление из резервной копии
- `status` - Проверка статуса сервисов
- `cleanup` - Очистка системы Docker
- `help` - Показать справку

### health-check.sh

Скрипт для комплексной проверки работоспособности платформы.

**Использование:**
```bash
chmod +x scripts/deploy/health-check.sh

# Запуск проверки
./scripts/deploy/health-check.sh
```

**Что проверяет:**
- Статус контейнеров
- Работоспособность базы данных
- Работоспособность Redis
- Доступность API
- Работоспособность frontend
- Конфигурацию Nginx

## Подготовка к использованию

1. Убедитесь, что у вас установлен Docker и Docker Compose
2. Клонируйте репозиторий проекта
3. Сделайте скрипты исполняемыми:
   ```bash
   chmod +x scripts/deploy/*.sh
   ```

## Пример развертывания

### Вариант 1: Полная автоматическая настройка сервера (рекомендуется)

```bash
# Выполнение полной настройки сервера
curl -fsSL https://raw.githubusercontent.com/AlexMobiCraft/FREESPORT/main/scripts/deploy/server-setup.sh | sudo bash
```

### Вариант 2: Пошаговая настройка

```bash
# 1. Установка Docker (если еще не установлен)
sudo ./scripts/deploy/install-docker.sh

# 2. Перезаходим в систему для применения изменений группы docker
exit  # и снова login

# 3. Клонирование проекта
git clone https://github.com/AlexMobiCraft/FREESPORT.git freesport
cd freesport

# 4. Настройка переменных окружения
cp .env.prod.example .env.prod
nano .env.prod  # редактирование

# 5. Развертывание проекта
./scripts/deploy/deploy.sh init
```

## Безопасность

- Скрипты запускаются с правами root (для install-docker.sh)
- Все пароли и секретные ключи должны быть изменены перед использованием
- Рекомендуется использовать SSH ключи для доступа к серверу
- Настройте файрвол для ограничения доступа

## Troubleshooting

### Проблема: Permission denied
**Решение:** Убедитесь, что скрипты имеют права на выполнение:
```bash
chmod +x scripts/deploy/*.sh
```

### Проблема: Docker не работает после установки
**Решение:** Перезайдите в систему для применения изменений группы docker или выполните:
```bash
newgrp docker
```

### Проблема: Контейнеры не запускаются
**Решение:** Проверьте логи и статус:
```bash
./scripts/deploy/deploy.sh status
docker compose -f docker-compose.prod.yml logs
```

## Автоматизация

Для автоматического обновления можно добавить в cron:
```bash
# Ежедневное обновление в 3:00
0 3 * * * /path/to/freesport/scripts/deploy/deploy.sh update

# Ежедневное резервное копирование в 2:00
0 2 * * * /path/to/freesport/scripts/deploy/deploy.sh backup
```

## Поддержка

При возникновении проблем:
1. Проверьте логи скриптов
2. Обратитесь к документации проекта
3. Создайте issue в репозитории