#!/usr/bin/env bash
# Разделы сотрудников — /manager/ (стори 42.4) и /marketing/ (стори 42.6) —
# nginx проксирует в Django. Без location запрос уходит в Next и получает 404.
#
# Использование: bash scripts/deploy/check-manager-route.sh <базовый URL> [раздел]
#   раздел — manager (по умолчанию) или marketing; только строчные латинские буквы.
#   deploy.yml — production после деплоя (docker/nginx/conf.d/default.conf);
#   main.yml   — nginx в Docker с docker/nginx/conf.d/local.conf и с default.conf.
#
# Ожидается: /<раздел>/ → 302 ровно на /<раздел>/login/?next=/<раздел>/,
# затем /<раздел>/login/ → 200 со страницей входа Django (id="login-form").
# Ответ, оборванный на середине (curl завершается с ошибкой), — провал,
# даже если нужная часть уже пришла. Тест скрипта —
# backend/tests/unit/test_check_manager_route_script.py.

set -u

BASE_URL="${1:?Укажите базовый URL, например https://optisport.ru}"
# Слэш в конце убирается: иначе запросы уйдут на «//manager/» (R42.4-33).
BASE_URL="${BASE_URL%/}"
SECTION="${2:-manager}"
if ! [[ "$SECTION" =~ ^[a-z]+$ ]]; then
  echo "❌ Недопустимое имя раздела «$SECTION»: только строчные латинские буквы"
  exit 1
fi
CURL_OPTS=(-sS --connect-timeout 10 --max-time 30)
BODY_FILE=$(mktemp)
trap 'rm -f "$BODY_FILE"' EXIT

# Код curl проверяется отдельно: в конвейере он теряется.
if ! HEADERS=$(curl "${CURL_OPTS[@]}" -o /dev/null -D - "$BASE_URL/$SECTION/"); then
  echo "❌ /$SECTION/: запрос не выполнен целиком (ошибка curl)"
  exit 1
fi
HEADERS=$(printf '%s\n' "$HEADERS" | tr -d '\r')
STATUS=$(printf '%s\n' "$HEADERS" | awk 'NR == 1 {print $2}')
LOCATION=$(printf '%s\n' "$HEADERS" | awk 'tolower($1) == "location:" {print $2}')
if [ "$STATUS" != "302" ] || [ "$LOCATION" != "/$SECTION/login/?next=/$SECTION/" ]; then
  echo "❌ /$SECTION/: ожидался 302 на /$SECTION/login/?next=/$SECTION/, получено ${STATUS:-нет ответа} ${LOCATION:-без Location}"
  exit 1
fi

if ! LOGIN_STATUS=$(curl "${CURL_OPTS[@]}" -o "$BODY_FILE" -w '%{http_code}' "$BASE_URL/$SECTION/login/"); then
  echo "❌ /$SECTION/login/: запрос не выполнен целиком (ошибка curl)"
  exit 1
fi
if [ "$LOGIN_STATUS" != "200" ]; then
  echo "❌ /$SECTION/login/: ожидался 200, получено $LOGIN_STATUS"
  exit 1
fi
if ! grep -q 'id="login-form"' "$BODY_FILE"; then
  echo "❌ /$SECTION/login/ не отдаёт страницу входа Django"
  exit 1
fi

echo "✅ Раздел /$SECTION/ проксируется в Django"
