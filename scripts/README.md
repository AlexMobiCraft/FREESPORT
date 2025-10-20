# Скрипты FREESPORT Platform

Этот каталог содержит скрипты для автоматизации различных задач разработки и тестирования.

## Структура директорий

- [`dev/`](dev/) - Скрипты для настройки и управления средой разработки
- [`tests/`](tests/) - Скрипты для запуска тестов
- [`server/`](server/) - Скрипты для работы с сервером
- [`inport_from_1C/`](inport_from_1C/) - Скрипты для импорта данных из 1С

## Быстрый старт

### Первоначальная настройка

1. **Настройка среды разработки:**

   ```powershell
   .\scripts\dev\setup-dev-environment.ps1
   ```

2. **Настройка тестовой среды:**

   ```powershell
   .\scripts\dev\setup-test-environment.ps1
   ```

### Управление средой разработки

Для быстрого управления средой разработки используйте:

```powershell
# Запуск всех сервисов
.\scripts\dev\dev-commands.ps1 start
# или
.\scripts\dev\dev-commands.ps1 -start

# Остановка всех сервисов
.\scripts\dev\dev-commands.ps1 stop
# или
.\scripts\dev\dev-commands.ps1 -stop

# Другие команды
.\scripts\dev\dev-commands.ps1 logs
.\scripts\dev\dev-commands.ps1 status
.\scripts\dev\dev-commands.ps1 migrate
.\scripts\dev\dev-commands.ps1 shell
.\scripts\dev\dev-commands.ps1 test
```

### Запуск тестов

Для запуска тестов используйте:

```powershell
# Интерактивный запуск
.\scripts\tests\run-tests-interactive.ps1

# Прямой запуск с параметрами
.\scripts\tests\run-tests-docker-local.ps1 -PytestArgs @("tests/integration/test_real_catalog_import.py", "-v")
```

## Подробная документация

- [Настройка и управление средой разработки](dev/README.md)
- [Запуск тестов](tests/README.md) (если существует)
- [Работа с сервером](server/README.md) (если существует)
- [Импорт данных из 1С](inport_from_1C/README.md) (если существует)

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
