# Полный справочник Docker-команд для тестирования

## Тестовая среда (docker-compose.test.yml)

### Полный цикл (рекомендуется для CI)
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down --remove-orphans --volumes
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from backend
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down
```

### Unit-тесты
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down --remove-orphans
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml run --rm backend pytest -v -m unit --cov=apps --cov-report=term-missing
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down
```

### Интеграционные тесты
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down --remove-orphans
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml run --rm backend pytest -v -m integration --cov=apps --cov-report=term-missing
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down
```

### Быстрый запуск (без пересборки)
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml run --rm backend pytest -v --tb=short
```

### Конкретный файл/тест
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml run --rm backend pytest apps/orders/tests/test_views.py::TestOrderCreation -v --tb=short
```

### Очистка тестовой среды
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml down --remove-orphans --volumes
```

## Dev-среда (docker-compose.yml)

### Запуск тестов в уже поднятом контейнере
```powershell
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest apps/orders/tests/ -v
```

### Shell в backend-контейнере
```powershell
cd docker
docker compose --env-file .env -f docker-compose.yml exec backend bash
```

### Логи тестового окружения
```powershell
cd docker
docker compose -p freesport-test --env-file .env -f docker-compose.test.yml logs -f
```

## Переменные окружения

Тестовый docker-compose использует:
- `.env` — для конфигурации Docker (порты, volumes)
- `../backend/.env.test` — для Django settings (БД, Redis, SECRET_KEY)

Убедись, что `backend/.env.test` существует перед запуском.
