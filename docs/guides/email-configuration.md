# Настройка Email для OPTISPORT

> Документация по настройке email сервера для отправки уведомлений.
> Story 29.3: Email Server Configuration

## Обзор

OPTISPORT использует email для:

- Уведомления администраторов о новых B2B заявках
- Отправка верификационных писем пользователям
- Системные уведомления об ошибках

## Конфигурация

### Переменные окружения

| Переменная            | Описание                       | Пример                                        |
| --------------------- | ------------------------------ | --------------------------------------------- |
| `EMAIL_BACKEND`       | Django email backend           | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST`          | SMTP сервер                    | `smtp.yandex.ru`                              |
| `EMAIL_PORT`          | Порт SMTP                      | `465`                                         |
| `EMAIL_USE_TLS`       | STARTTLS (порт 587)            | `False`                                       |
| `EMAIL_USE_SSL`       | Implicit SSL (порт 465)        | `True`                                        |
| `EMAIL_HOST_USER`     | Логин SMTP                     | `noreply@optisport.ru`                        |
| `EMAIL_HOST_PASSWORD` | Пароль SMTP                    | `your-app-password`                           |
| `DEFAULT_FROM_EMAIL`  | Адрес отправителя              | `noreply@optisport.ru`                        |
| `SERVER_EMAIL`        | Email сервера для ошибок       | `noreply@optisport.ru`                        |
| `ADMIN_EMAILS`        | Список админов (через запятую) | `admin1@optisport.ru,admin2@optisport.ru`     |

### Development окружение

В development по умолчанию используется **console backend** — письма выводятся в консоль Docker контейнера:

```bash
# Просмотр логов backend контейнера
docker logs freesport-backend -f
```

Для тестирования с реальной отправкой используйте **Mailhog**:

```bash
# В .env добавьте:
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mailhog
EMAIL_PORT=1025
EMAIL_USE_TLS=False
```

**Mailhog UI:** <http://localhost:8025>

### Production окружение

#### 1. Яндекс 360 для бизнеса — используется на проде

С 24.11.2026 почта домена `optisport.ru` и отправка писем сайта работают через Яндекс 360.
До этого сайт слал через хостинг reg.ru (`mail.hosting.reg.ru`); история — в
[`docs/deploy/domain-migration-optisport.md`](../deploy/domain-migration-optisport.md), п. 1.5 и 4.

**Текущее состояние (проверено 24.11.2026)**

| Что | Значение |
| --- | --- |
| SMTP | `smtp.yandex.ru`, порт `465`, implicit SSL |
| Ящик-отправитель | `noreply@optisport.ru`, вход по паролю приложения |
| MX | `mx.yandex.net` (10) |
| SPF | `v=spf1 redirect=_spf.yandex.net` |
| DKIM | селектор `mail` (`mail._domainkey.optisport.ru`), подпись `d=optisport.ru` |
| DMARC | `p=none`, отчёты на `dmarc@optisport.ru` — **этого ящика в Яндекс 360 пока нет**, отчёты не доходят |
| DNS-зона | по-прежнему у reg.ru (NS `ns1/ns2.hosting.reg.ru`), записи правятся в панели хостинга reg.ru |

Тестовые письма из контейнеров `backend` и `celery` приходят в Gmail с `SPF: PASS` и
`DKIM: PASS` для домена `optisport.ru`.

**Настройка `.env.prod`**

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
EMAIL_HOST_USER=noreply@optisport.ru
EMAIL_HOST_PASSWORD=пароль_приложения_яндекса
DEFAULT_FROM_EMAIL=noreply@optisport.ru
SERVER_EMAIL=noreply@optisport.ru
```

- Порт `465` — implicit SSL: `EMAIL_USE_SSL=True` и обязательно `EMAIL_USE_TLS=False`, обе
  сразу Django не принимает.
- Адрес в `DEFAULT_FROM_EMAIL` должен совпадать с `EMAIL_HOST_USER`: Яндекс не отправляет
  письма с чужим адресом в `From`.
- `EMAIL_HOST_PASSWORD` — пароль приложения, созданный в Яндекс ID под `noreply@optisport.ru`,
  а не пароль ящика.
- Письма о заказах уходят из `celery`, остальные — из `backend`. Обе службы и `celery-beat`
  берут настройки из одного `.env.prod`.

**Смена пароля или почтового сервера на проде**

`.env.prod` не хранится в репозитории и правится на сервере. Переменные окружения читаются
только при создании контейнера, поэтому одного `restart` мало: контейнеры нужно пересоздать.

```bash
ssh root@5.35.124.149
cd /home/freesport/freesport
cp -p .env.prod .env.prod.bak-mail-$(date +%Y%m%d-%H%M%S)
nano .env.prod   # EMAIL_HOST_PASSWORD (и EMAIL_HOST, если меняется сервер)

DC="docker compose --env-file .env.prod -f docker/docker-compose.prod.yml"
$DC up -d --no-deps --force-recreate backend celery celery-beat
$DC ps backend                      # дождаться (healthy)
$DC restart nginx                   # иначе nginx держит старый IP backend и отдаёт 502

$DC exec backend python manage.py test_email --to <адрес> --verbose
```

`.env.prod` на сервере со смешанными концами строк (CRLF/LF). Значения переменных это не
ломает, но при разборе файла скриптом (`grep`, `cut`) символ `\r` нужно срезать.

**Подключение домена (выполнено, для справки)**

1. В Яндекс 360 для бизнеса добавить домен и подтвердить его TXT-записью `yandex-verification`.
2. Заменить MX на `mx.yandex.net` (приоритет 10).
3. SPF: `v=spf1 redirect=_spf.yandex.net`.
4. DKIM: включить подпись в админке Яндекс 360 и опубликовать выданный ключ TXT-записью `mail._domainkey`.
5. Создать ящик `noreply` и под ним пароль приложения для почты.

#### 2. Google Workspace (Свой домен) или Gmail

**Альтернативный вариант**

**Вариант А: Google Workspace (Свой домен)**

1. Зарегистрируйтесь в [Google Workspace](https://workspace.google.com/).
2. Подтвердите домен и настройте MX-записи Google (`ASPMX.L.GOOGLE.COM` и др.).
3. Настройте SPF (`v=spf1 include:_spf.google.com ~all`) и DKIM в Google Admin.

**Вариант Б: Обычный Gmail (Для тестов/разработки)**

1. Используйте обычный аккаунт `@gmail.com`.
2. Включите **2-Step Verification** в [настройках безопасности](https://myaccount.google.com/security).

**Общий шаг: Создание App Password**

1. Перейдите в [Google Account Security](https://myaccount.google.com/security).
2. Найдите "App passwords" (Пароли приложений).
   - _Если нет в меню, воспользуйтесь поиском по настройкам._
3. Создайте пароль "Django Backend".
4. Скопируйте 16-значный код.

**Конфигурация `.env`**

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=xxxx-xxxx-xxxx-xxxx
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

## Rate Limits провайдеров

> ⚠️ **Важно:** Учитывайте лимиты при высокой нагрузке

| Provider      | Лимит           | Рекомендация                      |
| ------------- | --------------- | --------------------------------- |
| Gmail         | 500 emails/день | Только для development/testing    |
| Yandex Mail   | 100-500/день    | Подходит для небольшого объема    |
| SendGrid Free | 100/день        | Альтернатива для production       |
| SendGrid Paid | 40,000+/месяц   | Рекомендуется для масштабирования |

## Тестирование

### Management command

```bash
# В Docker контейнере
docker exec -it freesport-backend python manage.py test_email --to admin@optisport.ru

# Локально (с активированным venv)
cd backend
python manage.py test_email --to admin@optisport.ru
```

### Django Shell

```python
docker exec -it freesport-backend python manage.py shell

>>> from django.core.mail import send_mail
>>> send_mail(
...     'Test Email',
...     'Тестовое сообщение от OPTISPORT',
...     None,  # Использует DEFAULT_FROM_EMAIL
...     ['admin@optisport.ru'],
...     fail_silently=False,
... )
1  # Возвращает 1 при успехе
```

### Проверка конфигурации

```python
>>> from django.conf import settings
>>> print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
>>> print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
>>> print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
>>> print(f"ADMINS: {settings.ADMINS}")
```

## Troubleshooting

### Ошибка аутентификации (535)

- Проверьте правильность `EMAIL_HOST_USER` и `EMAIL_HOST_PASSWORD`
- Для Gmail: убедитесь, что используете App Password, а не обычный пароль
- Для Яндекса (`535 5.7.8 Error: authentication failed: Invalid user or password!`):
  - ящик существует и активен;
  - в `EMAIL_HOST_PASSWORD` пароль приложения, а не пароль ящика;
  - для ящика разрешён доступ почтовым программам (настройки Почты, раздел «Почтовые программы»)
- Пароль можно проверить до правки `.env.prod`, не трогая работающие контейнеры:

  ```bash
  docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python -c \
    "import smtplib,getpass; s=smtplib.SMTP_SSL('smtp.yandex.ru',465,timeout=20); s.login('noreply@optisport.ru', getpass.getpass()); print('OK')"
  ```

### Ошибка подключения (Connection refused)

- Проверьте `EMAIL_HOST` и `EMAIL_PORT`
- В Docker: убедитесь, что mailhog сервис запущен
- Проверьте firewall настройки

### Письма не доставляются

- Проверьте spam/junk папку получателя
- Убедитесь, что `DEFAULT_FROM_EMAIL` совпадает с `EMAIL_HOST_USER`
- Проверьте SPF/DKIM записи домена: откройте письмо в Gmail через «Показать оригинал»,
  там должны быть `SPF: PASS` и `DKIM: PASS` для `optisport.ru`. `FAIL` при отправке через
  `smtp.yandex.ru` означает, что в DNS сменились записи из таблицы «Текущее состояние»

### 502 на сайте после пересоздания backend

nginx запоминает IP контейнера `backend` при старте. После `up -d --force-recreate backend`
выполните `docker compose ... restart nginx`.

## См. также

- [Story 29.4: Email Notification System](../archive/v4/stories/epic-29/29.4.email-notification-system.md)
- [Доступы и оплата услуг](../deploy/accounts-and-billing.md) — где живут домен, DNS и почта
- [Переезд на optisport.ru](../deploy/domain-migration-optisport.md) — история DNS и почты на reg.ru
- [Django Email Documentation](https://docs.djangoproject.com/en/4.2/topics/email/)
