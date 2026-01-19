# Локальная разработка FREESPORT Platform

Эта инструкция описывает первоначальную настройку среды разработки на локальной машине разработчика.

## Предварительные требования

- **Docker Desktop** (Windows/Mac) или Docker + Docker Compose (Linux)
  - Минимум: Docker 20.10+, Docker Compose 2.0+
- **Git** для клонирования репозитория
- **Терминал/PowerShell** (Windows) или bash (Mac/Linux)
- **Минимум 8GB RAM** (рекомендуется 16GB для комфортной работы)
- **20GB свободного места** на диске для контейнеров и данных

## Шаг 1: Проверка предварительных требований

```bash
# Проверка Docker
docker --version
# Ожидаемый результат: Docker version 20.10+

# Проверка Docker Compose
docker compose version
# Ожидаемый результат: Docker Compose version 2.0+

# Проверка Git
git --version

Шаг 4: Сборка Docker образов
Сборка всех необходимых Docker образов для разработки:

Что собирается:

freesport-db - PostgreSQL база данных
freesport-redis - Redis для кеширования
freesport-backend - Django приложение
freesport-frontend - Next.js приложение
freesport-nginx - Nginx reverse proxy
freesport-celery-worker - Celery воркер для фоновых задач
freesport-celery-beat - Celery Beat для расписания
Шаг 5: Запуск контейнеров
Ожидаемое время первого запуска: 2-5 минут (зависит от скорости интернета для скачивания образов)

Проверка статуса контейнеров:

Вы должны увидеть все контейнеры в статусе Up:

Шаг 6: Инициализация базы данных
Шаг 7: Проверка работоспособности
Структура томов Docker
При первом запуске создаются следующие Docker томы для хранения данных:

Для просмотра томов:

Для очистки томов (⚠️ будут удалены все данные):

Основные команды для разработки
Решение распространенных проблем
Проблема: Ошибка "Cannot bind to port 8001"
Причина: Портбраузер или другое приложение уже использует этот порт.

Решение:

Или измените порт в docker/docker-compose.dev.yml, строка 61:

Проблема: Ошибка "Cannot connect to database"
Проблема: Frontend выдает "Cannot reach API"
Убедитесь, что переменная окружения установлена правильно в .env:

Перестартуйте frontend:

Проблема: Диск заполнен Docker образами
Проблема: Медленная работа на Windows/Mac
Docker Desktop на Windows и Mac может быть медленнее. Рекомендации:

Выделить больше ресурсов:

Docker Desktop Settings → Resources → CPU: 4+, Memory: 8GB+
Использовать WSL2 на Windows:

Docker Desktop → Settings → General → WSL 2 engine
Оптимизировать bind-mounts:

