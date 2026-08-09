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

## 1. DNS в reg.ru — выполняется вручную

Пока `optisport.ru` не указывает на сервер, сертификат выпустить нельзя: Let's Encrypt
проверяет владение доменом, обращаясь к нему по HTTP.

### 1.1. Где редактируется зона

Для `optisport.ru` прописаны NS `ns1.hosting.reg.ru` / `ns2.hosting.reg.ru`. У reg.ru от
пары NS зависит **место** редактирования записей:

| NS домена | Где менять записи |
|---|---|
| `ns1.reg.ru` / `ns2.reg.ru` | Личный кабинет reg.ru → «Домены» → «DNS-серверы и зона» |
| `ns1.hosting.reg.ru` / `ns2.hosting.reg.ru` | Панель управления **хостингом** (ISPmanager / cPanel / Plesk) |

То есть сейчас зона живёт в панели хостинга, а не в личном кабинете. Отсюда два маршрута.

**Маршрут A — перевести домен на обычные DNS reg.ru (рекомендуется).**
Сайт уезжает на собственный сервер `5.35.124.149`. Если оставить хостинговые NS, зона
перестанет обслуживаться, когда услуга хостинга закончится, — и сайт ляжет без видимой
причины.

1. Личный кабинет reg.ru → «Домены» → `optisport.ru` → «DNS-серверы и зона».
2. Сменить NS на `ns1.reg.ru` и `ns2.reg.ru`.
3. Прописать записи из п. 1.3 уже в личном кабинете.
4. Заложить **до 24 часов** на смену NS.

> [!WARNING]
> Смена NS **не отвязывает домен от услуги хостинга** — она переносит только обслуживание
> зоны. Почта `@optisport.ru` живёт на хостинге reg.ru: `MX` смотрят на
> `mx1/mx2.hosting.reg.ru`, а ящик `noreply@optisport.ru` — тот самый, через который
> бэкенд шлёт транзакционные письма. Пока почту не увезли к другому провайдеру, услуга
> хостинга нужна, и отказ от неё положит и почту сайта.
>
> Смена NS переносит обслуживание зоны, но **не копирует записи** — в новой зоне их надо
> создать заново. Перед сменой снять полный список текущих записей (в том числе `MX`,
> `TXT`-SPF, `dkim._domainkey`, `_dmarc`, `A` для `mail`), иначе почта отвалится молча.

**Маршрут B — ничего не переносить, править на месте.**
Открыть панель управления хостингом → «Управление DNS» → `optisport.ru` → «DNS-записи»
и внести правки из п. 1.3 там. Быстрее (15 минут – 1 час), но зона остаётся привязанной
к услуге хостинга.

### 1.2. Сначала снизить TTL

TTL — время, которое ответ DNS хранится в кэше провайдеров. Сейчас у записей
`optisport.ru` TTL = 3600 (1 час): после переключения часть пользователей будет ещё до
часа видеть старый адрес, и откат займёт столько же.

1. Не меняя адреса, выставить у записей `@` и `www` TTL = **300** (5 минут).
2. **Подождать час** — ровно столько живёт старый TTL в чужих кэшах. Только после этого
   новые значения начнут разлетаться за 5 минут.

Шаг необязательный, но он превращает потенциальный часовой откат в пятиминутный.

### 1.3. Целевые записи

Привести зону `optisport.ru` к такому виду:

| Действие | Тип | Имя | Значение | TTL |
|---|---|---|---|---|
| Изменить | A | `@` | `5.35.124.149` | 300 |
| Изменить | A | `www` | `5.35.124.149` | 300 |
| **Удалить** | AAAA | `@` | — | — |
| **Удалить** | AAAA | `www` | — | — |

Сейчас A-записи указывают на `31.31.197.15` — это парковка reg.ru, а не ваш сервер.

Про `@`: так обозначается сам домен без поддомена, то есть `optisport.ru`. В некоторых
панелях вместо `@` нужно вписать домен целиком и **с точкой на конце** — `optisport.ru.`

**AAAA-записи обязательно удалить.** AAAA — это адрес по IPv6. У сервера `5.35.124.149`
глобального IPv6 нет, а сейчас AAAA указывает на парковку reg.ru
(`2a00:f940:2:2:1:1:0:279`). Браузеры и системные резолверы предпочитают IPv6, когда он
доступен: если запись останется, часть посетителей и, что хуже, проверяющий сервер
Let's Encrypt пойдут на парковку вместо сайта — выпуск сертификата провалится, а причина
будет неочевидной.

### 1.4. Проверка

Через 5–15 минут после правок (или до суток, если меняли NS):

```bash
nslookup -type=A    optisport.ru     8.8.8.8   # ожидается 5.35.124.149
nslookup -type=A    www.optisport.ru 8.8.8.8   # ожидается 5.35.124.149
nslookup -type=AAAA optisport.ru     8.8.8.8   # ожидается пусто
nslookup -type=NS   optisport.ru     8.8.8.8   # маршрут A: ns1.reg.ru / ns2.reg.ru
```

Спрашиваем именно у `8.8.8.8`, а не у своего провайдера: так виден настоящий результат,
а не запись из локального кэша. Переходить к п. 3 (выпуск сертификата) можно только после
того, как обе A-записи отдают `5.35.124.149`, а AAAA не отдаёт ничего.

### 1.5. Почтовые записи — не трогать заодно с сайтом

A-запись `@` переехала на свой сервер, но вся почтовая часть зоны осталась на reg.ru и
должна такой остаться, пока почта живёт там:

| Тип | Имя | Значение | Зачем |
|---|---|---|---|
| MX | `@` | `mx1.hosting.reg.ru` (10), `mx2.hosting.reg.ru` (20) | приём почты |
| A | `mail` | `31.31.197.15` | почтовый узел домена |
| TXT | `@` | `v=spf1 ip4:31.31.197.15 a mx include:_spf.hosting.reg.ru ~all` | авторизация отправителей |
| TXT | `dkim._domainkey` | `v=DKIM1; k=rsa; s=email; p=…` | подпись писем как `d=optisport.ru` |
| TXT | `_dmarc` | см. ниже | политика и отчёты |

> [!CAUTION]
> `ip4:31.31.197.15` из SPF **удалять нельзя.** Адрес совпадает с бывшей парковочной
> страницей, из-за чего выглядит мусором, но это действующий исходящий узел почты домена,
> и в `include:_spf.hosting.reg.ru` его нет — сняв запись, вы уроните SPF всей исходящей
> почты, включая регистрации и уведомления о заказах.

Проверено 2026-08-09 по заголовкам письма, отправленного командой `test_email` (п. 6):

```
Received: from server279.hosting.reg.ru ([31.31.197.15]) by mx.google.com
Received-SPF: pass (google.com: domain of noreply@optisport.ru
              designates 31.31.197.15 as permitted sender) client-ip=31.31.197.15
```

Фактическая цепочка отправки — три разных узла, наружу письмо отдаёт последний:

```
Django → mail.hosting.reg.ru  (31.31.194.65, submission :465)
       → mail3.hosting.reg.ru (31.31.194.18, внутренний релей)
       → server279.hosting.reg.ru (31.31.197.15) → получатель
```

`server279` — сервер, на котором физически размещён хостинг-аккаунт; он же
`mail.optisport.ru`. Ни его адрес, ни адреса промежуточных узлов в `_spf.hosting.reg.ru`
не входят: тот include перечисляет другую группу релеев reg.ru.

Значение `_dmarc` (применено 2026-08-09):

```
v=DMARC1; p=none; sp=none; adkim=r; aspf=r; rua=mailto:dmarc@optisport.ru; fo=1
```

Ящик `dmarc@optisport.ru` должен существовать: отчёты приходят ежедневно XML-вложениями.
Адрес в **чужом** домене (например, на `gmail.com`) не годится — приём отчётов за другой
домен требует разрешающей записи вида `optisport.ru._report._dmarc.<домен-получателя>`,
которой у публичных почтовиков нет, и отчёты будут молча отбрасываться.

Ужесточать политику (`p=quarantine`, затем `p=reject`) имеет смысл не раньше, чем
отчёты за 1–2 недели подтвердят, что легитимные отправители домена выровнены.

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

Почта переведена на ящик домена у reg.ru — на проде стоит:

```dotenv
EMAIL_HOST=mail.hosting.reg.ru
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
EMAIL_HOST_USER=noreply@optisport.ru
```

Это не косметика, а условие прохождения DMARC. SPF домена авторизует релей reg.ru
(`include:_spf.hosting.reg.ru`), а DKIM-селектор `dkim._domainkey.optisport.ru` подписывает
письма с `d=optisport.ru` — оба механизма выровнены с `From: noreply@optisport.ru`.
Если вернуть отправку на сторонний SMTP (Gmail и т.п.), сохранив тот же `From`, alignment
провалится по обоим механизмам: конверт и подпись будут в домене отправителя, а не в
`optisport.ru`. При текущем `p=none` письма ещё доставляются, но осядут в спаме.

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
