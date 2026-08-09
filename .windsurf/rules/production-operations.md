---
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

После этого `/` должен отдавать 307 → `/coming-soon`, favicon — 200.

## Next.js Server Action ID mismatch

В логах frontend: `Failed to find Server Action "x". This request might be from an older or newer deployment.`

Это указывает на рассинхрон между старым клиентским JS/кэшем и новой серверной сборкой. Решается полным перезапуском/пересборкой frontend и сбросом кэша (`restart nginx`).

## 502 после перезапуска backend

При `docker compose restart backend celery celery-beat` nginx может потерять upstream.

**Обязательно выполняй:**

```bash
docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml restart nginx
```
