# Исправление ошибки 405 (Method POST not allowed)

1С (в вашей конфигурации) отправляет запрос `checkauth` методом **POST**, а мы ожидали только GET. Я добавил поддержку POST.

Выполните эти действия для обновления сервера:

## 1. Зафиксировать изменения (Локально)
Если вы еще не делали commit/push, нужно отправить исправление в репозиторий.
(Я уже подготовил код, вам нужно только отправить его).

```bash
# В терминале на ВАШЕМ компьютере (где мы сейчас общаемся):
git add backend/apps/integrations/onec_exchange/views.py
git commit -m "fix(1c): allow POST method for checkauth (1C requirement)"
git push origin develop
```

## 2. Обновить сервер (На сервере)
Зайдите по SSH и обновите код:

```bash
cd /home/freesport/freesport/
git pull
```

## 3. Перезапустить Backend
Чтобы новый код view вступил в силу.

```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart backend
```

## 4. Проверка
Теперь в 1С нажмите "Проверить соединение". Ошибка "Method POST not allowed" должна исчезнуть.
