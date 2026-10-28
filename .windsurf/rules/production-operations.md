---
trigger: model_decision
description: Продакшен runbook FREESPORT — частые инциденты и восстановление
---

# Продакшен runbook

## Frontend остановился после деплоя / спинер вокруг favicon

**Симптомы:** `https://optisport.ru/` возвращает 502; `docker compose ps -a` показывает `freesport-frontend Exited (0)`; в логах `Failed to find Server Action "x"`.

**Причина:** рассинхрон старого клиентского JS/кэша и новой серверной сборки либо смешанные версии деплоя.

**Восстановление:**

```bash
docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml up -d frontend
docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml restart nginx
```

После этого `/` должен отдавать 307 → `/home`, favicon — 200.

## Next.js Server Action ID mismatch

В логах frontend: `Failed to find Server Action "x". This request might be from an older or newer deployment.`

Это указывает на рассинхрон между старым клиентским JS/кэшем и новой серверной сборкой. Решается полным перезапуском/пересборкой frontend и сбросом кэша (`restart nginx`).

## 502 после перезапуска backend

При `docker compose restart backend celery celery-beat` nginx может потерять upstream.

**Обязательно выполняй:**

```bash
docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml restart nginx
```

## Деплой оборвался на `docker pull` (`Connection reset by peer`, exit 255)

**Симптомы:** шаг «Deploy to production server» падает с `Read from remote host …: Connection reset by peer` и `client_loop: send disconnect: Broken pipe`, код 255; последние строки лога — прогресс `docker pull`, перед обрывом несколько минут тишины (28.10.2026, run 40699691360). Job `rollback` после этого ничего не откатывает — он только печатает инструкцию.

**Причина:** pull тяжёлого образа идёт минутами без вывода, SSH-сессию сбрасывает промежуточный узел, и скрипт на сервере умирает вместе с ней. Шаг «Configure SSH keepalive» в `deploy.yml` (`ServerAliveInterval 30`) закрывает это; сервер при разборе не смотрели, так что если обрыв повторится при включённом keepalive — искать на сервере (`journalctl -u ssh`, `dmesg | grep -i oom`).

**Что с продом:** пока обрыв случился на pull, контейнеры не тронуты — `compose up`, миграции и collectstatic идут после него, и сайт продолжает отдавать прежний релиз. Рабочая копия на сервере при этом уже на новом коммите: `git reset --hard` выполняется до pull. Обрыв позже pull оставляет прод между `compose up` и миграциями — тогда см. комментарий к `timeout-minutes` в `deploy.yml`.

**Повтор:** `gh run rerun <id> --failed` берёт `deploy.yml` из коммита прогона, то есть без исправления. Чтобы выкатить с keepalive, нужен новый push в `main` (синк `develop → main`). Завершённые слои образа сервер уже скачал, повторный pull быстрее.

## Правка nginx не доехала до прода, хотя `nginx -t` и reload прошли

**Симптомы:** после деплоя новой `location` нет (15.10.2026: `/manager/` отвечал 308 от Next вместо 302 от Django), а `nginx -t` и `nginx -s reload` отработали без ошибок.

**Причина:** пофайловый bind-mount (`./nginx/nginx.conf:/etc/nginx/nginx.conf`) держит inode. `git reset --hard` заменяет файл новым inode, а контейнер продолжает видеть старый — reload перечитывает старый конфиг. Каталоги (`conf.d`, `snippets`) этой ловушки не имеют. `deploy.yml` сверяет md5 файлов на диске и в контейнере и при расхождении пересоздаёт nginx сам.

**Проверка:**

```bash
cd /home/freesport/freesport
C="docker compose --env-file .env.prod -f docker/docker-compose.prod.yml"
for f in nginx.conf conf.d/default.conf; do
  echo "$f $(md5sum < docker/nginx/$f | cut -d' ' -f1) $($C exec -T nginx md5sum /etc/nginx/$f < /dev/null | cut -d' ' -f1)"
done
```

**Восстановление** — проверить конфиг с диска, затем пересоздать только nginx (`--no-deps`: иначе compose может пересоздать backend/frontend на образе `:production` из дефолта, если последний деплой был откатом на SHA):

```bash
$C run --rm --no-deps -T --name freesport-nginx-check nginx nginx -t
$C up -d --no-deps --force-recreate nginx
bash scripts/deploy/check-manager-route.sh https://optisport.ru
```
