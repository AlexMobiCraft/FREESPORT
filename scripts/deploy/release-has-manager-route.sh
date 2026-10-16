#!/usr/bin/env bash
# Есть ли раздел сотрудников — /manager/ (стори 42.4) или /marketing/ (стори 42.6) —
# в коде разворачиваемого релиза. deploy.yml проверяет раздел на проде только у
# такого релиза: откат (image_tag) на релиз до стори раздела разворачивает
# исправный образ без него (R42.4-35).
# Решает код коммита релиза, а не ответ сервера: иначе сломанный маршрут нового
# релиза сам стал бы поводом пропустить проверку.
#
# Использование: bash scripts/deploy/release-has-manager-route.sh <коммит релиза> [раздел]
#   раздел — manager (по умолчанию) или marketing; только строчные латинские буквы.
#   Запускать в git-клоне с историей, где этот коммит есть (checkout fetch-depth: 0).
#   Коммит — полный или короткий SHA: теги образов в ghcr — короткий SHA (type=sha).
#
# Код завершения: 0 — маршрут есть, 1 — релиз раньше раздела,
# 2 — коммит не найден или недопустимое имя раздела (решать вызывающему;
# deploy.yml тогда проверяет раздел).
# Тест — backend/tests/unit/test_release_has_manager_route_script.py.

set -u

RELEASE="${1:-}"
SECTION="${2:-manager}"
if ! [[ "$SECTION" =~ ^[a-z]+$ ]]; then
  echo "Недопустимое имя раздела «$SECTION»: только строчные латинские буквы"
  exit 2
fi
URLS_FILE=backend/freesport/urls.py
# Подключение сайта раздела в URLconf — backend/freesport/urls.py.
MARKER="path(\"$SECTION/\", ${SECTION}_site.urls)"

if [ -z "$RELEASE" ] || ! git rev-parse --verify --quiet "$RELEASE^{commit}" > /dev/null; then
  echo "Коммит релиза «$RELEASE» не найден в репозитории"
  exit 2
fi

if git show "$RELEASE:$URLS_FILE" 2> /dev/null | grep -qF "$MARKER"; then
  echo "Релиз $RELEASE: раздел /$SECTION/ есть"
  exit 0
fi
echo "Релиз $RELEASE: раздела /$SECTION/ нет (релиз раньше стори раздела)"
exit 1
