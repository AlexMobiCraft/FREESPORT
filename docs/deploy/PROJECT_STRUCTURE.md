# Структура проекта FREESPORT Platform после реорганизации

## Обзор

Проект FREESORT Platform был реорганизован для улучшения структуры и удобства развертывания. Все скрипты развертывания, документация и Docker конфигурации теперь находятся в соответствующих поддиректориях.

## Новая структура проекта

```
FREESPORT/
├── docker/                          # Docker конфигурации
│   ├── docker-compose.yml           # Локальная разработка
│   ├── docker-compose.prod.yml      # Production окружение
│   ├── docker-compose.test.yml      # Тестовое окружение
│   ├── docker-compose-temp.yml      # Временная конфигурация
│   ├── init-db.sql/                 # Скрипты инициализации БД
│   │   └── 01-init.sql
│   ├── nginx/                       # Конфигурации Nginx
│   │   ├── nginx.conf
│   │   └── conf.d/
│   │       └── default.conf
│   └── ssl/                         # SSL сертификаты
├── scripts/deploy/                  # Скрипты развертывания
│   ├── README.md                    # Документация скриптов
│   ├── server-setup.sh              # Полная настройка сервера
│   ├── install-docker.sh            # Установка Docker
│   ├── deploy.sh                    # Управление платформой
│   └── health-check.sh              # Проверка работоспособности
├── docs/deploy/                     # Документация по развертыванию
│   ├── README.md                    # Основная документация
│   ├── DOCKER_SETUP.md              # Краткая инструкция
│   ├── docker-server-setup.md       # Подробная инструкция
│   ├── quick-deployment.md          # Быстрое развертывание
│   ├── health-check.md              # Проверка работоспособности
│   └── PROJECT_STRUCTURE.md         # Этот файл
├── backend/                         # Django backend
├── frontend/                        # Next.js frontend
├── data/                            # Данные приложения
├── logs/                            # Логи
├── tests/                           # Тесты
└── .env.prod.example                # Шаблон переменных окружения
```

## Изменения в структуре

### 1. Скрипты развертывания
- **Раньше**: `scripts/`, `scripts/install-docker.sh`, `scripts/deploy.sh`, `scripts/server-setup.sh`
- **Теперь**: `scripts/deploy/`, `scripts/deploy/install-docker.sh`, `scripts/deploy/deploy.sh`, `scripts/deploy/server-setup.sh`

### 2. Docker конфигурации
- **Раньше**: `docker-compose.yml`, `docker-compose.prod.yml`, `docker-compose.test.yml` в корне
- **Теперь**: `docker/docker-compose.yml`, `docker/docker-compose.prod.yml`, `docker/docker-compose.test.yml`

### 3. Документация по развертыванию
- **Раньше**: `docs/docker-server-setup.md`, `docs/quick-deployment.md`, `docs/health-check.md` в корне docs
- **Теперь**: `docs/deploy/docker-server-setup.md`, `docs/deploy/quick-deployment.md`, `docs/deploy/health-check.md`

### 4. Краткая инструкция по Docker
- **Раньше**: `DOCKER_SETUP.md` в корне
- **Теперь**: `docs/deploy/DOCKER_SETUP.md`

## Обновленные пути в скриптах

Все скрипты были обновлены для использования новых путей:

### deploy.sh
- `docker compose -f docker-compose.prod.yml` → `docker compose -f docker/docker-compose.prod.yml`

### health-check.sh
- `docker compose -f docker-compose.prod.yml` → `docker compose -f docker/docker-compose.prod.yml`
- Проверка наличия файла: `docker-compose.prod.yml` → `docker/docker-compose.prod.yml`

### server-setup.sh
- `./scripts/deploy.sh` → `./scripts/deploy/deploy.sh`
- `docker compose -f docker-compose.prod.yml` → `docker compose -f docker/docker-compose.prod.yml`

## Преимущества новой структуры

1. **Лучшая организация**: Все связанные файлы находятся в соответствующих директориях
2. **Четкое разделение**: Скрипты, документация и конфигурации разделены
3. **Удобство навигации**: Легко найти нужные файлы по назначению
4. **Масштабируемость**: Простое добавление новых скриптов и конфигураций
5. **Соответствие лучшим практикам**: Структура соответствует современным стандартам организации проектов

## Использование скриптов

### Быстрое развертывание
```bash
# Полная автоматическая настройка сервера
curl -fsSL https://raw.githubusercontent.com/AlexMobiCraft/FREESPORT/main/scripts/deploy/server-setup.sh | sudo bash
```

### Пошаговое развертывание
```bash
# 1. Установка Docker
curl -fsSL https://raw.githubusercontent.com/AlexMobiCraft/FREESPORT/main/scripts/deploy/install-docker.sh | sudo bash

# 2. Развертывание платформы
git clone https://github.com/AlexMobiCraft/FREESPORT.git freesport
cd freesport
chmod +x scripts/deploy/*.sh
cp .env.prod.example .env.prod
nano .env.prod  # Изменить пароли!
./scripts/deploy/deploy.sh init
```

### Управление платформой
```bash
# Статус
./scripts/deploy/deploy.sh status

# Обновление
./scripts/deploy/deploy.sh update

# Резервное копирование
./scripts/deploy/deploy.sh backup

# Проверка работоспособности
./scripts/deploy/health-check.sh
```

## Совместимость

Новая структура полностью обратимо совместима с предыдущей версией:
- Все скрипты обновлены для работы с новыми путями
- Документация обновлена с учетом новой структуры
- Docker конфигурации работают с новыми относительными путями

## Миграция со старой структуры

Если у вас есть существующая установка со старой структурой:

1. **Обновите скрипты**: Скачайте новые версии скриптов из `scripts/deploy/`
2. **Переместите docker-compose файлы**: Переместите их в директорию `docker/`
3. **Обновите команды**: Используйте новые пути в командах Docker Compose

## Заключение

Новая структура проекта делает FREESPORT Platform более организованной и удобной для развертывания и поддержки. Все компоненты логически сгруппированы, что упрощает навигацию и управление проектом.