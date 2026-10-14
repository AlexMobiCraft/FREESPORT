#!/usr/bin/env bash
# Раздел менеджера /manager/ (стори 42.4) nginx проксирует в Django.
# Без этой location запрос уходит в Next и получает 404.
#
# Использование: bash scripts/deploy/check-manager-route.sh <базовый URL>
#   deploy.yml — production после деплоя (docker/nginx/conf.d/default.conf);
#   main.yml   — локальный nginx в Docker с docker/nginx/conf.d/local.conf.
#
# Ожидается: /manager/ → 302 ровно на /manager/login/?next=/manager/,
# затем /manager/login/ → 200 со страницей входа Django (id="login-form").

set -u

BASE_URL="${1:?Укажите базовый URL, например https://optisport.ru}"
CURL_OPTS=(-sS --connect-timeout 10 --max-time 30)

HEADERS=$(curl "${CURL_OPTS[@]}" -o /dev/null -D - "$BASE_URL/manager/" | tr -d '\r')
STATUS=$(printf '%s\n' "$HEADERS" | awk 'NR == 1 {print $2}')
LOCATION=$(printf '%s\n' "$HEADERS" | awk 'tolower($1) == "location:" {print $2}')
if [ "$STATUS" != "302" ] || [ "$LOCATION" != "/manager/login/?next=/manager/" ]; then
  echo "❌ /manager/: ожидался 302 на /manager/login/?next=/manager/, получено ${STATUS:-нет ответа} ${LOCATION:-без Location}"
  exit 1
fi

if ! curl "${CURL_OPTS[@]}" -f "$BASE_URL/manager/login/" | grep -q 'id="login-form"'; then
  echo "❌ /manager/login/ не отдаёт страницу входа Django"
  exit 1
fi

echo "✅ Раздел менеджера проксируется в Django"
