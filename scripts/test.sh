#!/bin/bash
# Скрипт для запуска тестов FREESPORT Platform в Docker (Linux/macOS)

set -e  # Прекращать выполнение при ошибке

echo "==============================================="
echo "FREESPORT Platform - Запуск тестов в Docker"
echo "==============================================="

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "[ОШИБКА] Docker не найден. Установите Docker."
    exit 1
fi

# Проверка наличия Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "[ОШИБКА] Docker Compose не найден."
    exit 1
fi

# Переход в корневую директорию проекта
cd "$(dirname "$0")/.."

echo "[INFO] Остановка и удаление предыдущих тестовых контейнеров..."
docker-compose -f docker-compose.test.yml down --remove-orphans --volumes

echo "[INFO] Сборка тестовых образов..."
docker-compose -f docker-compose.test.yml build --no-cache

echo "[INFO] Запуск тестовой среды..."
docker-compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from backend

# Сохранение кода выхода
TEST_EXIT_CODE=$?

echo "[INFO] Остановка тестовых контейнеров..."
docker-compose -f docker-compose.test.yml down

# Копирование отчетов о покрытии кода (если существуют)
if [ -d "htmlcov" ]; then
    rm -rf htmlcov
fi

docker run --rm -v freesport_test_coverage:/coverage -v "$(pwd)":/host alpine sh -c "cp -r /coverage/. /host/htmlcov/ 2>/dev/null || true"

echo "==============================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "[УСПЕХ] Все тесты прошли успешно!"
    echo "[INFO] Отчет о покрытии кода: htmlcov/index.html"
else
    echo "[ОШИБКА] Тесты завершились с ошибками (код: $TEST_EXIT_CODE)"
fi
echo "==============================================="

exit $TEST_EXIT_CODE