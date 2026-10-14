#!/usr/bin/env bash
# Раздел менеджера /manager/ (стори 42.4) nginx проксирует в Django.
# Без этой location запрос уходит в Next и получает 404.
#
# Использование: bash scripts/deploy/check-manager-route.sh <базовый URL>
#   deploy.yml — production после деплоя (docker/nginx/conf.d/default.conf);
#   main.yml   — nginx в Docker с docker/nginx/conf.d/local.conf и с default.conf.
#
# Ожидается: /manager/ → 302 ровно на /manager/login/?next=/manager/,
# затем /manager/login/ → 200 со страницей входа Django (id="login-form").
# Ответ, оборванный на середине (curl завершается с ошибкой), — провал,
# даже если нужная часть уже пришла. Тест скрипта —
# backend/tests/unit/test_check_manager_route_script.py.

set -u

BASE_URL="${1:?Укажите базовый URL, например https://optisport.ru}"
CURL_OPTS=(-sS --connect-timeout 10 --max-time 30)
BODY_FILE=$(mktemp)
trap 'rm -f "$BODY_FILE"' EXIT

# Код curl проверяется отдельно: в конвейере он теряется.
if ! HEADERS=$(curl "${CURL_OPTS[@]}" -o /dev/null -D - "$BASE_URL/manager/"); then
  echo "❌ /manager/: запрос не выполнен целиком (ошибка curl)"
  exit 1
fi
HEADERS=$(printf '%s\n' "$HEADERS" | tr -d '\r')
STATUS=$(printf '%s\n' "$HEADERS" | awk 'NR == 1 {print $2}')
LOCATION=$(printf '%s\n' "$HEADERS" | awk 'tolower($1) == "location:" {print $2}')
if [ "$STATUS" != "302" ] || [ "$LOCATION" != "/manager/login/?next=/manager/" ]; then
  echo "❌ /manager/: ожидался 302 на /manager/login/?next=/manager/, получено ${STATUS:-нет ответа} ${LOCATION:-без Location}"
  exit 1
fi

if ! LOGIN_STATUS=$(curl "${CURL_OPTS[@]}" -o "$BODY_FILE" -w '%{http_code}' "$BASE_URL/manager/login/"); then
  echo "❌ /manager/login/: запрос не выполнен целиком (ошибка curl)"
  exit 1
fi
if [ "$LOGIN_STATUS" != "200" ]; then
  echo "❌ /manager/login/: ожидался 200, получено $LOGIN_STATUS"
  exit 1
fi
if ! grep -q 'id="login-form"' "$BODY_FILE"; then
  echo "❌ /manager/login/ не отдаёт страницу входа Django"
  exit 1
fi

echo "✅ Раздел менеджера проксируется в Django"
