# Скрипты FREESPORT Platform

Этот каталог содержит скрипты для автоматизации различных задач разработки и тестирования.

## Первоначальная настройка

### 1. Настройка среды разработки

Для первоначальной настройки Docker-среды разработки выполните:

```powershell
.\scripts\dev\setup-dev-environment.ps1
```

Этот скрипт выполнит следующие действия:

- Проверит доступность Docker
- Создаст необходимые директории
- Создаст файл `.env` с настройками для разработки
- Соберет и запустит все контейнеры для разработки
- Выполнит миграции базы данных
- Предложит создать суперпользователя Django

После завершения у вас будут доступны следующие сервисы:

- Backend API: <http://localhost:8001/api/v1>
- Frontend: <http://localhost:3000>
- Nginx: <http://localhost>
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 2. Настройка тестовой среды

Для первоначальной настройки Docker-среды для тестирования выполните:

```powershell
.\scripts\dev\setup-test-environment.ps1
```

Этот скрипт выполнит следующие действия:

- Проверит доступность Docker
- Создаст необходимые директории для тестов
- Соберет тестовые Docker-образы
- Запустит тестовые сервисы (база данных и Redis)
- Проверит доступность тестовых сервисов

## Быстрое управление средой разработки

Для быстрого управления средой разработки используйте скрипт `dev-commands.ps1` из этой директории:

```powershell
# Запуск всех сервисов
.\scripts\dev\dev-commands.ps1 start
# или
.\scripts\dev\dev-commands.ps1 -start

# Остановка всех сервисов
.\scripts\dev\dev-commands.ps1 stop
# или
.\scripts\dev\dev-commands.ps1 -stop

# Перезапуск сервисов
.\scripts\dev\dev-commands.ps1 restart

# Просмотр логов
.\scripts\dev\dev-commands.ps1 logs

# Проверка статуса
.\scripts\dev\dev-commands.ps1 status

# Выполнение миграций
.\scripts\dev\dev-commands.ps1 migrate

# Открытие Django shell
.\scripts\dev\dev-commands.ps1 shell

# Запуск тестов
.\scripts\dev\dev-commands.ps1 test

# Очистка Docker ресурсов
.\scripts\dev\dev-commands.ps1 clean
```

## Запуск тестов

### Интерактивный запуск тестов

Для интерактивного запуска тестов с выбором сценариев:

```powershell
.\scripts\..\tests\run-tests-interactive.ps1
```

Этот скрипт предоставит меню для выбора:
- Story 3.1.3 — real catalog (8 тестов)
- Story 3.1.2 — import_catalog_from_1c
- Все backend тесты (pytest tests)
- Произвольный путь/тест

### Прямой запуск тестов

Для прямого запуска тестов с параметрами:

```powershell
.\scripts\..\tests\run-tests-docker-local.ps1 -PytestArgs @("tests/integration/test_real_catalog_import.py", "-v")
```

Доступные параметры:
- `-ComposeFile`: путь к docker-compose файлу (по умолчанию: docker-compose.test.yml)
- `-SkipBuild`: пропустить сборку образов
- `-DockerContext`: Docker контекст (по умолчанию: default)
- `-KeepContainers`: оставить контейнеры после выполнения тестов
- `-ServiceName`: имя сервиса для тестов (по умолчанию: backend)
- `-PytestArgs`: аргументы для pytest

## Полезные команды

### Управление средой разработки

```powershell
# Запуск всех сервисов
docker-compose up -d

# Остановка всех сервисов
docker-compose down

# Просмотр логов
docker-compose logs -f [service]

# Перезапуск сервиса
docker-compose restart [service]

# Выполнение команд в контейнере backend
docker-compose exec backend [command]

# Выполнение миграций
docker-compose exec backend python manage.py migrate

# Создание суперпользователя
docker-compose exec backend python manage.py createsuperuser
```

### Управление тестовой средой

```powershell
# Запуск тестовых сервисов
docker-compose -f docker-compose.test.yml up -d db redis

# Остановка тестовой среды
docker-compose -f docker-compose.test.yml down

# Просмотр логов тестовых сервисов
docker-compose -f docker-compose.test.yml logs -f [service]

# Выполнение команд в тестовом backend
docker-compose -f docker-compose.test.yml exec backend [command]
```

## Структура скриптов

- `setup-dev-environment.ps1` - Первоначальная настройка среды разработки
- `setup-test-environment.ps1` - Первоначальная настройка тестовой среды
- `dev-commands.ps1` - Быстрое управление средой разработки
- `../tests/run-tests-interactive.ps1` - Интерактивный запуск тестов
- `../tests/run-tests-docker-local.ps1` - Основной скрипт для запуска тестов в Docker
- `../server/update_server_code.ps1` - Обновление кода на сервере
- `../inport_from_1C/` - Скрипты для импорта данных из 1С

## Устранение проблем

### Ошибка "Файл compose не найден"

Если вы столкнулись с ошибкой "Файл compose не найден", убедитесь, что:
1. Файл `docker-compose.test.yml` существует в корне проекта
2. Вы запускаете скрипты из корневой директории проекта
3. Пути в скриптах указаны правильно относительно корня проекта

### Проблемы с Docker

Если контейнеры не запускаются:
1. Убедитесь, что Docker запущен и доступен
2. Проверьте, что порты 5432, 6379, 8001, 3000, 80 не заняты другими приложениями
3. Проверьте права доступа к директориям проекта

### Проблемы с тестами

Если тесты не запускаются:
1. Убедитесь, что тестовая среда настроена с помощью `.\scripts\dev\setup-test-environment.ps1`
2. Проверьте, что тестовые сервисы (db, redis) запущены
3. Проверьте логи тестовых контейнеров для диагностики проблем