# Загрузка данных для импорта 1С на сервер

Инструкция описывает, как перенести локальные данные из каталога `data/import_1c` на прод-сервер `5.35.124.149` перед запуском импорта.

## Предусловия

- Настроен SSH-доступ: `root@5.35.124.149` (или другой пользователь из `scripts/server/update_server_code.ps1`).
- На сервере существует каталог `/home/freesport/freesport/data/import_1c` и поддиректории `goods`, `offers`, `prices`, `rests`, `contragents`, `priceLists`, `storages`, `units`.
- Docker-контейнеры уже запускались, чтобы хостовые директории смонтировались.

## Вариант 1. Простая копия через SCP

```powershell
# из корня репозитория
scp -r .\data\import_1c root@5.35.124.149:/home/freesport/freesport/data/
```

После копирования перезапустите backend, чтобы контейнер увидел новые файлы:

```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart backend
```

## Вариант 2. Синхронизация через rsync (экономит трафик)

```powershell
rsync -avz --delete ./data/import_1c/ root@5.35.124.149:/home/freesport/freesport/data/import_1c/
```

- Флаг `--delete` гарантирует, что на сервере не останутся старые файлы.
- После синхронизации также перезапустите backend.

## Вариант 3. Архив + распаковка

1. На локальной машине:
   ```powershell
   tar -czf import_1c.tar.gz -C ./data import_1c
   scp import_1c.tar.gz root@5.35.124.149:/home/freesport/
   ```
2. На сервере:
   ```bash
   cd /home/freesport
   tar -xzf import_1c.tar.gz -C /home/freesport/freesport/data
   rm import_1c.tar.gz
   docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart backend
   ```

## Проверка на сервере

```bash
ls -la /home/freesport/freesport/data/import_1c

docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend ls -la /app/data/import_1c
```

Если каких-то поддиректорий нет, создайте их на сервере и повторите копирование. После загрузки данных можно запускать импорт через админку или соответствующий management-команду.
