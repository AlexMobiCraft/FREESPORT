---
description: Докуменция по CI/CD образов
---
# Сборка и публикация Docker-образов FREESPORT

Этот документ описывает процесс подготовки и доставки Docker-образов backend и frontend проекта FREESPORT в GitHub Container Registry, а также применение этих образов на продакшн-сервере.

## 1. Подготовка тегов релиза

1. На машине разработчика или CI определить тег релиза. Рекомендуемый формат: `vYYYYMMDD-HHMM` или семантическая версия (`v1.0.0`).
2. Зафиксировать тег для backend и frontend. 
   Пример:
   - `BACKEND_TAG=v20251102-01`
   - `FRONTEND_TAG=v20251102-01`

### 1.1 Автоматическая генерация тегов

Для удобства используйте скрипт [`scripts/dev/generate-image-tags.ps1`](../../scripts/dev/generate-image-tags.ps1):

```powershell
# Генерация тега в формате vYYYYMMDD-HHmm и сохранение в scripts/dev/last-release-tags.json
pwsh scripts/dev/generate-image-tags.ps1

# Использовать кастомное значение
pwsh scripts/dev/generate-image-tags.ps1 -CustomTag "v1.0.0"

# Перезаписать файл без предупреждений
pwsh scripts/dev/generate-image-tags.ps1 -Overwrite
```

Скрипт автоматически:

- устанавливает переменные окружения `BACKEND_TAG`, `FRONTEND_TAG`, `BACKEND_IMAGE` и `FRONTEND_IMAGE` в текущей PowerShell-сессии;
- обновляет файл `.env.prod`, проставляя свежие значения `BACKEND_IMAGE` и `FRONTEND_IMAGE`;
- сохраняет историю последнего релиза в `scripts/dev/last-release-tags.json`;
- добавляет запись в журнал `docs/ci-cd/change-log.md`.

## 2. Сборка и публикация образов (локально или через CI)

### 2.0 Скрипт автоматизации

Для типовой сборки и публикации используйте [`scripts/dev/build-and-push-images.ps1`](../../scripts/dev/build-and-push-images.ps1)
(скрипт сам вызовет генерацию тегов):

```powershell
# Сборка обоих сервисов (по умолчанию)
pwsh scripts/dev/build-and-push-images.ps1

# Только backend
pwsh scripts/dev/build-and-push-images.ps1 -Target backend

# Только frontend
pwsh scripts/dev/build-and-push-images.ps1 -Target frontend

# Использовать уже подготовленные переменные/tags
pwsh scripts/dev/build-and-push-images.ps1 -SkipTagGeneration
```

### 2.1 Backend

```powershell
# В корне репозитория
$backendTag = "ghcr.io/alexmobicraft/freesport/backend:$env:BACKEND_TAG"
docker build --platform linux/amd64 -t $backendTag -f backend/Dockerfile backend

docker push $backendTag
```

### 2.2 Frontend

```powershell
$frontendTag = "ghcr.io/alexmobicraft/freesport/frontend:$env:FRONTEND_TAG"
docker build --platform linux/amd64 -t $frontendTag -f frontend/Dockerfile frontend

docker push $frontendTag
```

> **Важно**: перед сборкой установить переменные окружения `BACKEND_TAG` и `FRONTEND_TAG`, а также выполнить `docker login ghcr.io` с токеном GitHub.

## 3. Обновление переменных окружения

1. В файле `.env.prod` на продакшн-сервере указать новые теги образов:

   ```dotenv
   BACKEND_IMAGE=ghcr.io/alexmobicraft/freesport/backend:v20251102-01
   FRONTEND_IMAGE=ghcr.io/alexmobicraft/freesport/frontend:v20251102-01
   ```

2. Зафиксировать изменение в системном журнале (см. `docs/ci-cd/README.md`).

## 4. Применение на сервере

1. Подключиться к серверу `5.35.124.149` (см. [docs/deploy/README.md](README.md)).
2. В каталоге `/home/freesport/freesport` выполнить перезапуск сервисов:

   ```bash
   docker compose --env-file .env.prod -f docker/docker-compose.prod.yml pull backend frontend celery celery-beat
   docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --force-recreate backend frontend celery celery-beat
   ```

3. Проверить логи `docker compose -f docker/docker-compose.prod.yml logs -f backend`.

## 5. Восстановление из резервной копии

Для отката на предыдущий релиз:

1. В `.env.prod` вернуть значения `BACKEND_IMAGE` и `FRONTEND_IMAGE` на предыдущие теги.
2. Выполнить `docker compose ... up -d --force-recreate` как в шаге 4.

## 6. Автоматизация в GitHub Actions

### 6.1 Backend (`.github/workflows/backend-ci.yml`)

- Проверить, что job `build` завершает `docker/build-push-action` с нужными тегами (branch, release, latest).
- Добавить тег релиза:

  ```yaml
  tags: |
    type=ref,event=branch
    type=ref,event=pr
    type=sha,prefix=commit-
    type=raw,value=${{ env.BACKEND_TAG }},enable=${{ inputs.release }}
  ```

### 6.2 Frontend (`.github/workflows/frontend-ci.yml`)

- Аналогично backend добавить поддержку `FRONTEND_TAG` и флагов релиза.

## 7. Документирование

- Каждое обновление фиксировать в `docs/ci-cd/change-log.md`.
- Обновлять `docs/deploy/README.md` при изменениях процесса.

## 8. Чек-лист релиза

- [ ] Тесты backend и frontend пройдены.
- [ ] Образы собраны и опубликованы с уникальными тегами.
- [ ] `.env.prod` обновлен на новые теги.
- [ ] Сервисы перезапущены и прошли smoke-тест.
- [ ] Логи проверены, критических ошибок нет.
- [ ] Документация и change-log обновлены.

---

**Последнее обновление:** 2025-11-02
