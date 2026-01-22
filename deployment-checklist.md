# Чек-лист Деплоя (Интеграция 1С)

Похоже, что новая функциональность ещё не попала на сервер (ошибка 404), а миграции не применились (нет права `Can exchange with 1C`).

Выполните эти шаги на сервере по порядку:

## 1. Обновление кода
Убедитесь, что сервер находится на ветке `develop` (или той, куда мы вносили изменения) и скачайте обновления.

```bash
cd /home/freesport/freesport/
git status
# Если ветка не develop - переключитесь: git checkout develop
git pull
```

## 2. Пересборка Backend
Так как мы добавили новые библиотеки и файлы, контейнер нужно пересобрать.

```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml down backend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml build backend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d backend
```

## 3. Применение миграций
Это создаст нужные права в базе данных (`Can exchange with 1C`).

```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate
```

## 4. Перезапуск Nginx
Чтобы Nginx увидел обновленный контейнер (если IP сменился).

```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart nginx
```

## 5. Проверка прав
1. Зайдите в Админку Django -> Пользователи -> `1c_exchange_robot`.
2. В списке прав найдите: `ИНТЕГРАЦИИ | Сессия | Can exchange with 1C`.
3. Добавьте это право пользователю.

## 6. Тест соединения
Теперь откройте в браузере:
`https://freesport.ru/api/integration/1c/exchange/?mode=checkauth`

Должно появиться окно ввода логина/пароля или сообщение `success`.
После этого проверка в 1С тоже заработает.
