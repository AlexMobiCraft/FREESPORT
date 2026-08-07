# Переезд на домен optisport.ru

Runbook перевода платформы с `freesport.ru` на `optisport.ru` (регистратор — reg.ru).

Принятые решения:

- `freesport.ru` **выводится из эксплуатации полностью** (не редирект). SEO-вес и старые
  ссылки не переносятся — это осознанный выбор.
- Почтовые адреса переезжают на `@optisport.ru`.
- Бренд «FREESPORT» не меняется: переезжает только домен.

## 0. Состояние на момент подготовки (2026-08-07)

| Что | Значение |
|---|---|
| Сервер | `5.35.124.149`, IPv6 на сервере **отсутствует** |
| `optisport.ru` → | `31.31.197.15` (парковка reg.ru), NS = `ns1/ns2.hosting.reg.ru` |
| `optisport.ru` AAAA → | `2a00:f940:2:2:1:1:0:279` (парковка reg.ru) |
| Сертификат на сервере | `freesport.ru` + `www.freesport.ru`, годен до 2026-10-06 |
| certbot | 1.21.0, webroot `/home/freesport/freesport/data/prod/certbot-webroot` |
| Ветка прода | `main` |

## 1. DNS в панели reg.ru — выполняется вручную

Порядок важен: пока `optisport.ru` не указывает на сервер, сертификат выпустить нельзя.

1. Снизить TTL до 300 с **заранее** (за несколько часов до переключения), чтобы откат был быстрым.
2. Заменить записи зоны `optisport.ru`:
   - `@` → **A** `5.35.124.149` (сейчас указывает на парковку `31.31.197.15`)
   - `www` → **A** `5.35.124.149`
3. **Удалить AAAA-записи** `@` и `www`. У сервера нет глобального IPv6: если оставить AAAA
   на парковку reg.ru, клиенты с IPv6 будут попадать не на сайт (и `certbot` может
   провалить проверку, выбрав IPv6).
4. Дождаться распространения и проверить:

```bash
nslookup -type=A optisport.ru 8.8.8.8      # ожидается 5.35.124.149
nslookup -type=AAAA optisport.ru 8.8.8.8   # ожидается пусто
nslookup -type=A www.optisport.ru 8.8.8.8  # ожидается 5.35.124.149
```

## 2. Доставка кода в `main`

Прод разворачивается из ветки `main` (`git reset --hard origin/main`). Доменные правки
должны попасть в `main` до редеплоя.

Принятый маршрут: правки уходят в `develop`, а на прод — общим релизом `develop → main`.
На момент подготовки `main` отставал от `develop` на 55 коммитов (весь эпик 40), поэтому
релиз выкатит вместе с переездом и его. Перед мержем в `main` учесть открытые риски эпика 40:
патч расширения БУС на проде не установлен, тесты импорта 1С в CI не исполняются.

Если переезд понадобится выкатить раньше релиза — собрать `hotfix/*` от `main` только с
доменными правками.

## 3. Выпуск сертификата Let's Encrypt

Выполняется **до** выката новой конфигурации nginx: новый `default.conf` ссылается на
`/etc/letsencrypt/live/optisport.ru/`, и без сертификата nginx не стартует.

На момент выпуска на сервере ещё работает старая конфигурация — её HTTP-блок отвечает на
любой Host и отдаёт `/.well-known/acme-challenge/` из webroot, поэтому проверка пройдёт.

```bash
ssh root@5.35.124.149
certbot certonly --webroot \
  -w /home/freesport/freesport/data/prod/certbot-webroot \
  -d optisport.ru -d www.optisport.ru \
  --cert-name optisport.ru

# Проверка
certbot certificates | grep -A3 "Certificate Name: optisport.ru"
ls /etc/letsencrypt/live/optisport.ru/fullchain.pem
```

## 4. Правка `.env.prod` на сервере

`.env.prod` не хранится в репозитории — правится на месте. Сделать резервную копию:

```bash
cd /home/freesport/freesport
cp .env.prod .env.prod.bak-$(date +%F)
```

Привести к виду:

```dotenv
ALLOWED_HOSTS=optisport.ru,www.optisport.ru,5.35.124.149,backend,nginx,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://5.35.124.149,http://optisport.ru,https://5.35.124.149,https://optisport.ru,https://www.optisport.ru
CORS_ALLOWED_ORIGINS=https://optisport.ru,https://www.optisport.ru
DEFAULT_FROM_EMAIL=noreply@optisport.ru
SERVER_EMAIL=noreply@optisport.ru
NEXT_PUBLIC_API_URL=https://optisport.ru/api/v1
NEXT_PUBLIC_MEDIA_URL=https://optisport.ru
SITE_URL=https://optisport.ru
```

`SITE_URL` теперь пробрасывается во фронт как `NEXT_PUBLIC_APP_URL` (build arg и env) —
от него зависит `metadataBase`, то есть canonical- и OG-ссылки. Раньше он во фронт не
передавался вовсе, и в проде `metadataBase` падал на `http://localhost:3000`.

`EMAIL_HOST_USER` не трогаем: отправка идёт через SMTP Gmail, `DEFAULT_FROM_EMAIL` — только
адрес в поле From.

## 5. Редеплой

Фронт требует **пересборки**, а не перезапуска: `NEXT_PUBLIC_*` вшиваются в бандл на этапе
сборки.

```bash
cd /home/freesport/freesport
git fetch origin main && git reset --hard origin/main

docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build backend frontend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart nginx

# Конфигурация nginx валидна?
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec nginx nginx -t
```

## 6. Проверки после выката

```bash
curl -I https://optisport.ru/                     # 200
curl -I https://www.optisport.ru/                 # 200
curl -s https://optisport.ru/api/v1/products/ | head -c 200
curl -I https://optisport.ru/admin/               # без ошибки CSRF/DisallowedHost
curl -I http://freesport.ru/                      # 410 Gone
echo | openssl s_client -connect optisport.ru:443 -servername optisport.ru 2>/dev/null \
  | openssl x509 -noout -subject -dates
```

Дополнительно вручную:

- В HTML главной проверить `<link rel="canonical">` и `og:url` — должны указывать на
  `https://optisport.ru`, а не на `localhost:3000`.
- Картинки товаров грузятся (в `next.config.ts` разрешены `optisport.ru`, `cdn.optisport.ru`,
  `**.optisport.ru`).
- Письмо-уведомление: `docker compose ... exec backend python manage.py test_email --to <адрес>`.

## 7. Обмен с 1С — требует отдельной проверки

1. **Реквизит «Сайт» в выгрузке заказа** (`apps/orders/services/order_export.py`) изменён с
   `freesport.ru` на `optisport.ru`. Blast radius по GitNexus — CRITICAL: символ участвует в
   7 процессах обмена. Структура XML не менялась, но после выката **обязательно провести
   контрольный заказ** и убедиться, что УТ 11 принимает документ и корректно заполняет реквизит.
2. **Учётная запись робота обмена** `1c_exchange_robot@freesport.ru` намеренно **не переименована**.
   Это логин пользователя Django, а не почтовый ящик; он же прописан в настройках узла обмена
   на стороне 1С. Переименование требует одновременной правки с обеих сторон и согласования с
   администратором 1С. Пока логин остаётся прежним — обмен не ломается.
   Значение по умолчанию в `docker/verify_1c_session.sh` оставлено соответствующим.

## 8. Вывод freesport.ru из эксплуатации

Только после того, как `optisport.ru` подтверждённо работает.

Конфигурация nginx уже содержит блок, отдающий `410 Gone` на `freesport.ru` и `www.freesport.ru`
по HTTP. Это защита от того, чтобы старый домен молча обслуживался через `default_server`
копией сайта. По HTTPS старый домен перестанет отвечать корректно, как только будет удалён
его сертификат.

```bash
# Убедиться, что новый домен работает, и только потом:
certbot delete --cert-name freesport.ru
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart nginx
```

DNS-записи `freesport.ru` можно снять в панели регистратора после этого.

## 9. Откат

Пока сертификат `freesport.ru` не удалён, откат быстрый:

```bash
cd /home/freesport/freesport
cp .env.prod.bak-<дата> .env.prod
git reset --hard <коммит-до-переезда>
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build backend frontend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart nginx
```

DNS `optisport.ru` при этом можно оставить как есть — старый домен продолжит работать.

## 10. Что осталось за рамками переезда

- Бренд-строка `© 2025-2026 FREESPORT.RU` в `frontend/src/app/ComingSoonClient.tsx` — по
  решению «бренд не трогаем». Формально она называет выведенный из эксплуатации домен.
- Django-пакет `backend/freesport/`, имена контейнеров `freesport-*`, `DB_NAME=freesport`,
  путь `/home/freesport/freesport` — переименование инфраструктуры под новый бренд не входит
  в переезд домена.
- Историю в `docs/archive/` и `_bmad-output/` не переписывали: это артефакты закрытых стори.
