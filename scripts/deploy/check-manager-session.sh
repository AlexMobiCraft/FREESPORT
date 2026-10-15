#!/usr/bin/env bash
# Вход менеджера в раздел /manager/ (стори 42.4) через nginx и список его клиентов.
# Анонимная проверка check-manager-route.sh не заметит location, которая теряет
# Cookie или Set-Cookie: редирект и страница входа анонима от них не зависят,
# а Django-тесты ходят мимо nginx. Здесь — настоящий вход формой и список.
#
# Использование:
#   bash scripts/deploy/check-manager-session.sh <базовый URL> <email менеджера> \
#     <пароль> <email своего клиента> <email чужого клиента>
#   main.yml — nginx в Docker дважды: с local.conf и с production default.conf
#   (самоподписанный сертификат, CURL_CA_BUNDLE); учётные записи создаёт сам шаг.
#   На production не запускается: тестовой учётной записи менеджера там нет.
#
# Ожидается: вход формой → 302 на /manager/, затем /manager/users/user/ → 200,
# свой клиент в списке есть, чужого нет.

set -u

BASE_URL="${1:?Укажите базовый URL, например http://localhost:8080}"
# Слэш в конце убирается: иначе запросы уйдут на «//manager/» (R42.4-33).
BASE_URL="${BASE_URL%/}"
EMAIL="${2:?Укажите email менеджера}"
PASSWORD="${3:?Укажите пароль менеджера}"
OWN_EMAIL="${4:?Укажите email клиента менеджера}"
FOREIGN_EMAIL="${5:?Укажите email клиента другого менеджера}"
CURL_OPTS=(-sS --connect-timeout 10 --max-time 30)
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT
JAR="$WORK_DIR/cookies"
BODY="$WORK_DIR/body"

# Запрос с общей cookie-сессией; печатает «<код> <адрес редиректа>».
# Код curl проверяется вызывающим: оборванный ответ — провал.
fetch() {
  curl "${CURL_OPTS[@]}" -c "$JAR" -b "$JAR" -o "$BODY" -w '%{http_code} %{redirect_url}' "$@"
}

if ! RESULT=$(fetch "$BASE_URL/manager/login/"); then
  echo "❌ /manager/login/: запрос не выполнен целиком (ошибка curl)"
  exit 1
fi
TOKEN=$(sed -n 's/.*name="csrfmiddlewaretoken" value="\([^"]*\)".*/\1/p' "$BODY" | head -n 1)
if [ "${RESULT%% *}" != "200" ] || [ -z "$TOKEN" ]; then
  echo "❌ /manager/login/: ожидался 200 с CSRF-токеном формы, получено $RESULT"
  exit 1
fi

if ! RESULT=$(fetch \
  --data-urlencode "csrfmiddlewaretoken=$TOKEN" \
  --data-urlencode "username=$EMAIL" \
  --data-urlencode "password=$PASSWORD" \
  --data-urlencode "next=/manager/" \
  "$BASE_URL/manager/login/"); then
  echo "❌ Вход в /manager/: запрос не выполнен целиком (ошибка curl)"
  exit 1
fi
if [ "$RESULT" != "302 $BASE_URL/manager/" ]; then
  echo "❌ Вход в /manager/: ожидался 302 на /manager/, получено $RESULT"
  exit 1
fi

if ! RESULT=$(fetch "$BASE_URL/manager/users/user/"); then
  echo "❌ /manager/users/user/: запрос не выполнен целиком (ошибка curl)"
  exit 1
fi
if [ "${RESULT%% *}" != "200" ]; then
  echo "❌ /manager/users/user/: ожидался 200 для вошедшего менеджера, получено $RESULT"
  exit 1
fi
if ! grep -qF "$OWN_EMAIL" "$BODY"; then
  echo "❌ /manager/users/user/: в списке нет клиента менеджера $OWN_EMAIL"
  exit 1
fi
if grep -qF "$FOREIGN_EMAIL" "$BODY"; then
  echo "❌ /manager/users/user/: в списке клиент другого менеджера $FOREIGN_EMAIL"
  exit 1
fi

echo "✅ Менеджер входит в раздел через nginx и видит только своих клиентов"
