# План выката стори 41.5 — единый источник заголовков безопасности

**Ветка:** `feature/story-41-5-security-headers` → `develop` → `main`
**Дата подготовки:** 2026-08-25
**Срочности нет.** Выкат — отдельным заходом в удобное окно (решение владельца 2026-08-25).
Стори переводится в `done` **после прод-замера** (шаги 8–10), а не по мержу.

> 🔴 **Две ловушки этого выката, обе про то, что падение будет невидимым.**
>
> 1. **`up -d --build frontend` пересоздаёт контейнер** — фронт получает новый IP,
>    nginx держит старый и начинает отдавать 502. Дальше срабатывает
>    `default.conf`: `proxy_intercept_errors on;` + `error_page 502 503 504 =200
>    /coming-soon/index.html;`. nginx перехватывает 502 и отдаёт заглушку
>    «Скоро открытие» **со статусом 200**. Сайт молча превращается в заглушку,
>    любая проверка по коду ответа этого не увидит. Отсюда шаг 9 — глазами.
> 2. **Сниппеты требуют `up -d nginx`, а не `nginx -s reload`.** Каталог
>    `docker/nginx/snippets/` — новый bind-mount, а bind-mount добавляется только
>    пересозданием контейнера. После `reload` nginx упадёт с
>    `open() "/etc/nginx/snippets/security-headers.conf" failed`.
>
> **Порядок «сначала фронт, потом nginx» обязателен.** В обратном порядке nginx
> поднимется, запомнит текущий IP фронта, и фронт уедет из-под него.

---

## Что выкатывается

| Что | Файлы | Почему требует чего-то особого |
|---|---|---|
| Новый каталог сниппетов nginx | `docker/nginx/snippets/*.conf` | новый bind-mount → пересоздание контейнера nginx |
| Подключение сниппетов | `docker/nginx/conf.d/default.conf`, `local.conf` | — |
| Монтирование каталога | `docker/docker-compose.yml`, `docker-compose.prod.yml` | — |
| Заголовки HTML | `frontend/next.config.ts` | правка конфига → полная пересборка образа фронта |
| Срок жизни HTML | `frontend/src/app/layout.tsx` | входит в ту же пересборку |
| HSTS снят с Django | `backend/freesport/settings/{base,production}.py` | рестарт backend + celery, затем **обязательно** рестарт nginx |

---

## Порядок команд на проде

Все команды — из корня репозитория на сервере, по SSH.

```bash
# 1. Забрать код. Именно fetch+reset, НЕ git pull:
#    на проде не должно возникать мержей и локальных коммитов.
git fetch origin main
git reset --hard origin/main

# 2. Убедиться, что новый каталог приехал. Если его нет — дальше идти нельзя:
#    nginx на шаге 4 упадёт на старте.
ls -1 docker/nginx/snippets/

# 3. Фронт — ПЕРВЫМ. Полная пересборка: правка next.config.ts
#    в существующий образ не подхватывается, `restart frontend` её не увидит.
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build frontend

# 4. nginx — ВТОРЫМ, и именно `up -d`, а не `reload`:
#    новый bind-mount ./nginx/snippets появляется только при пересоздании контейнера.
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d nginx

# 5. Django: HSTS снят в settings — нужен рестарт всех процессов, читающих настройки.
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart backend celery celery-beat

# 6. ОБЯЗАТЕЛЬНЫЙ рестарт nginx после шага 5: после пересоздания/рестарта
#    апстрима nginx держит старый IP и отдаёт 502 (см. врезку выше).
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart nginx

# 7. Синтаксис конфигурации внутри живого контейнера.
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec nginx nginx -t
```

**Чего в этом плане нет и не должно появиться:**
`docker compose down -v` — снесёт volume с `media/` и `static/`, то есть все
пользовательские загрузки и изображения из обмена 1С. Миграций стори не несёт,
`manage.py migrate` не нужен. `collectstatic` тоже: статика не менялась.

---

## Проверка после выката

### 8. Глазами, ДО любых замеров

```
Открыть в браузере https://optisport.ru
```

Это не формальность: при рассинхроне IP апстрима сайт отдаёт заглушку
«Скоро открытие» **со статусом 200**, и ни один `curl` по коду ответа этого не
покажет. Если видна заглушка — вернуться к шагу 6 (`restart nginx`).

Отдельно — что за заглушкой живёт настоящий Django, а не тот же перехват:

```bash
curl -sSI https://optisport.ru/api/v1/pages/ | head -1   # ожидается 200 от Django
```

### 9. HSTS: `includeSubDomains` обязан уйти

```bash
curl -sSI https://optisport.ru | grep -i strict-transport
# ожидается ровно: strict-transport-security: max-age=31536000
# НЕ должно быть: includeSubDomains, preload
```

Это снимает действующую поломку `http://mail.optisport.ru` у браузеров, успевших
закэшировать старое значение от Django: новый заголовок перезапишет запись при
первом же визите по HTTPS.

### 10. Таблица замеров (AC13 стори)

```bash
for p in / /static/admin/css/base.css /media/ /health /api/v1/pages/ /admin/login/ /swagger/ /redoc/; do
  echo "=== $p"
  curl -sS -o /dev/null -D - "https://optisport.ru$p" \
    | grep -iE '^(x-frame-options|x-content-type-options|referrer-policy|content-security-policy|permissions-policy|x-xss-protection|strict-transport-security|cache-control):'
done
```

Проверяется два условия:

- **ни один заголовок из набора не встречается дважды** — счётчик, а не глаза:
  ```bash
  curl -sS -o /dev/null -D - https://optisport.ru/ | grep -icE '^x-frame-options:'   # обязано быть 1
  ```
- **ни одна локация не осталась без `nosniff`**, включая ответы, отличные от 200:
  ```bash
  curl -sS -o /dev/null -D - https://optisport.ru/media/1c_temp/x.xml | grep -i x-content-type
  ```

### 11. Регрессии интеграций (AC6)

- `/delivery` — карта Яндекса отображается, в консоли браузера нет ошибок CSP.
  Если карта не открылась — снять `geolocation=()` из `Permissions-Policy` во
  **всех трёх** сниппетах и в `next.config.ts` (страж согласованности иначе
  упадёт) и зафиксировать причину.
- Страница товара с изображениями — картинки грузятся.
- Оформление заказа проходит.
- Обмен с 1С: следующий плановый обмен завершается без ошибок
  (`/api/v1/integrations/1c/exchange/`).

### 12. Запас на встраивание (AC13)

В консоли браузера на любой странице сайта:

```js
document.body.insertAdjacentHTML('beforeend',
  '<iframe id="t" src="/delivery" style="width:300px;height:200px"></iframe>');
```

`/delivery` **обязан отрисоваться** (`SAMEORIGIN` + `frame-ancestors 'self'`).
Тот же фрейм с `src="/admin/login/"` — **не должен** (`DENY` +
`frame-ancestors 'none'`), в консоли появится сообщение о запрете. Обратный
результат означает, что значения разошлись между слоями.

---

## Откат

Правка целиком в конфигурации, миграций нет — откат симметричен выкату:

```bash
git reset --hard <предыдущий коммит main>
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build frontend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d nginx
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart backend celery celery-beat
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart nginx
```

Единственное, что откат **не** отменяет, — HSTS-записи в браузерах. Они и не
требуют отмены: новое значение (`max-age=31536000` без `includeSubDomains`)
строго слабее прежнего, поэтому откат к прежнему заголовку просто вернул бы
`includeSubDomains`. Это довод в пользу того, чтобы откатывать конфигурацию
целиком, а не «вернуть как было» точечно по HSTS.

---

## Отдельно: этот выкат — первая проверка гипотезы про заглушку

`error_page 502 503 504 =200 /coming-soon/index.html` превращает падение фронта
в успешный ответ. Гипотеза: именно поэтому падения фронта на проде до сих пор
не ловились мониторингом.

**Что сделать по итогу шага 8.** Если между шагом 3 и шагом 6 сайт хотя бы
однажды отдал заглушку со статусом 200 — гипотеза подтверждена, и в
`_bmad-output/planning-artifacts/tech-debt.md` заводится отдельный пункт:
«`error_page 502 503 504 =200` скрывает падение фронта от мониторинга; проверка
доступности по коду ответа неинформативна». Правка самого поведения в объём
стори 41.5 **не входит** — это осознанное решение, а не забытая задача.
