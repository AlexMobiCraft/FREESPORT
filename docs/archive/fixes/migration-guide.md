# Руководство по миграции на унифицированное виртуальное окружение

## Обзор

Данное руководство описывает процесс миграции с некорректно настроенного виртуального окружения на унифицированную систему разработки, объединяющую Docker и локальные утилиты.

## Проблема

### Исходное состояние
- Нестандартная структура виртуального окружения (`backend/venv/Script/` вместо `Scripts/`)
- Дублирование зависимостей между локальным venv и Docker
- Ошибки при запуске утилит кодирования
- Отсутствие единой стратегии разработки

### Симптомы
```
Fatal error in launcher: Unable to create process using 
"C:\Users\tkachenko\DEV\FREESPORT\backend\venv\Scripts\python.exe"  
"C:\Users\tkachenko\DEV\FREESPORT\backend\venv\Script\black.exe" .': 
The system cannot find the file specified.
```

## Решение

### Архитектура после миграции

```
FREESPORT/
├── backend/
│   ├── venv/                    # Стандартное виртуальное окружение
│   │   ├── Scripts/             # Стандартная структура Windows
│   │   │   ├── black.exe
│   │   │   ├── isort.exe
│   │   │   ├── flake8.exe
│   │   │   ├── mypy.exe
│   │   │   └── pytest.exe
│   │   └── ENV_INFO.txt         # Информация об окружении
│   └── requirements.txt
├── docker/
│   └── Dockerfile.dev-tools     # Lightweight образ для утилит
├── scripts/migration/            # Скрипты миграции
│   ├── backup-current-env.ps1
│   ├── create-new-venv.ps1
│   ├── migrate-to-unified-env.ps1
│   └── check-env-consistency.ps1
└── Makefile                     # Обновленные команды
```

### Стратегия "Docker-First с локальными утилитами"

1. **Docker** - основная среда разработки
   - Полная изоляция
   - Соответствие production
   - Интеграция с базой данных и Redis

2. **Локальное venv** - быстрые утилиты
   - Code formatting (black, isort)
   - Линтинг (flake8, mypy)
   - Быстрое тестирование (pytest)

## Процесс миграции

### Автоматическая миграция

```bash
# Полная миграция с резервным копированием
powershell -ExecutionPolicy Bypass -File scripts/migration/migrate-to-unified-env.ps1

# Миграция без Docker (если Docker не используется)
powershell -ExecutionPolicy Bypass -File scripts/migration/migrate-to-unified-env.ps1 -SkipDocker

# Принудительная миграция (игнорирование ошибок)
powershell -ExecutionPolicy Bypass -File scripts/migration/migrate-to-unified-env.ps1 -Force
```

### Ручная миграция

#### Шаг 1: Резервное копирование
```bash
powershell -ExecutionPolicy Bypass -File scripts/migration/backup-current-env.ps1
```

#### Шаг 2: Создание нового окружения
```bash
powershell -ExecutionPolicy Bypass -File scripts/migration/create-new-venv.ps1
```

#### Шаг 3: Сборка Docker образа
```bash
docker build -f docker/Dockerfile.dev-tools -t freesport-dev-tools ./backend
```

#### Шаг 4: Валидация
```bash
powershell -ExecutionPolicy Bypass -File scripts/migration/check-env-consistency.ps1
```

## Использование после миграции

### Вариант 1: Docker (рекомендуется)

```bash
# Запуск полной среды разработки
make up

# Форматирование через Docker
make format

# Линтинг через Docker
make lint

# Тестирование через Docker
make test
```

### Вариант 2: Быстрые Docker утилиты

```bash
# Быстрое форматирование (без запуска полной среды)
make format-fast

# Быстрый линтинг
make lint-fast

# Быстрое тестирование
make test-fast-tools
```

### Вариант 3: Локальные утилиты

```bash
# Активация виртуального окружения
cd backend
venv\Scripts\activate

# Использование утилит
black .                    # Форматирование
isort .                   # Сортировка импортов
flake8 .                   # Линтинг
mypy .                    # Type checking
pytest -v                  # Тестирование

# Или прямой вызов без активации
backend/venv/Scripts/black.exe .
backend/venv/Scripts/isort.exe .
backend/venv/Scripts/flake8.exe .
backend/venv/Scripts/mypy.exe .
backend/venv/Scripts/pytest.exe -v
```

## Мониторинг и поддержка

### Проверка согласованности окружений

```bash
# Полная проверка всех окружений
make check-env-consistency

# Или напрямую
powershell -ExecutionPolicy Bypass -File scripts/migration/check-env-consistency.ps1
```

### Устранение неполадок

#### Проблема: "black не найден"
```bash
# Решение 1: Через python -m
backend/venv/Scripts/python.exe -m black .

# Решение 2: Прямой вызов
backend/venv/Scripts/black.exe .

# Решение 3: Активация окружения
cd backend
venv\Scripts\activate
black .
```

#### Проблема: Docker утилиты не работают
```bash
# Пересборка образа
docker build -f docker/Dockerfile.dev-tools -t freesport-dev-tools ./backend

# Проверка образа
docker run --rm freesport-dev-tools black --version
```

#### Проблема: Версии пакетов не совпадают
```bash
# Обновление локального окружения
cd backend
venv\Scripts\activate
pip install black==23.11.0 isort==5.12.0 flake8==6.1.0 mypy==1.7.1 pytest==7.4.3

# Пересборка Docker образа
docker build -f docker/Dockerfile.dev-tools -t freesport-dev-tools ./backend
```

## Восстановление

Если миграция вызвала проблемы, можно восстановить предыдущее состояние:

```bash
# Найти резервную копию
ls backend/venv.backup.*

# Восстановить
Move-Item 'backend/venv.backup.20251027-101500' 'backend/venv' -Force
```

## Преимущества новой архитектуры

### Для разработчиков
- ✅ Быстрый доступ к утилитам локально
- ✅ Стандартная структура виртуального окружения
- ✅ Сохранение преимуществ Docker
- ✅ Минимальные изменения в рабочих процессах

### Для проекта
- ✅ Унификация зависимостей
- ✅ Автоматическая проверка согласованности
- ✅ Улучшенная документация
- ✅ Снижение риска ошибок окружения

### Для CI/CD
- ✅ Предсказуемые окружения
- ✅ Быстрые проверки кода
- ✅ Унифицированные версии пакетов
- ✅ Автоматическая валидация

## Следующие шаги

1. **Выполнить миграцию** с помощью автоматического скрипта
2. **Проверить функциональность** всех утилит
3. **Обновить рабочие процессы** команды разработки
4. **Настроить CI/CD** для проверки согласованности
5. **Обучить команду** новым командам и процессам

## Поддержка

При возникновении проблем:
1. Проверьте логи миграции в `scripts/migration/`
2. Запустите `make check-env-consistency` для диагностики
3. Обратитесь к документации в `docs/development-environment.md`
4. Используйте резервное копирование для отката

---

**Версия документа**: 1.0  
**Дата обновления**: 2025-10-27  
**Автор**: DevOps Infrastructure Specialist