# План реализации навыка `backend-local-update`

## Цель
Создать специализированный навык для быстрого и надежного обновления локального бекенд-окружения в Docker. Это позволит избежать ручного ввода длинных команд и минимизировать ошибки при обновлении зависимостей или структуры БД.

## Структура
1. `.agent/skills/backend-local-update/SKILL.md` — основные инструкции и команды.
2. `.agent/skills/backend-local-update/examples/usage.md` — примеры использования для ИИ.

## Основные сценарии
- **Простой перезапуск**: `docker compose ... restart backend` (когда изменился только код, а горячая перезагрузка не сработала).
- **Пересборка (Build)**: `docker compose ... up -d --build backend` (когда изменились `requirements.txt` или `Dockerfile`).
- **Полное обновление**: Пересборка + `migrate` + `collectstatic`.

## Команды
- Базовая команда Docker Compose: `docker compose --env-file .env -f docker/docker-compose.yml`
- Миграции: `exec backend python manage.py migrate`
- Статика: `exec backend python manage.py collectstatic --no-input`

## Этапы
1. Создать `SKILL.md` с YAML заголовком и структурированными инструкциями.
2. Добавить примеры в `examples/usage.md`.
3. Подтвердить готовность пользователю.
