#!/usr/bin/env bash
# Есть ли раздел менеджера /manager/ (стори 42.4) в коде разворачиваемого релиза.
# deploy.yml проверяет /manager/ на проде только у такого релиза: откат (image_tag)
# на релиз до 42.4 разворачивает исправный образ без раздела (R42.4-35).
# Решает код коммита релиза, а не ответ сервера: иначе сломанный маршрут нового
# релиза сам стал бы поводом пропустить проверку.
#
# Использование: bash scripts/deploy/release-has-manager-route.sh <коммит релиза>
#   Запускать в git-клоне с историей, где этот коммит есть (checkout fetch-depth: 0).
#   Коммит — полный или короткий SHA: теги образов в ghcr — короткий SHA (type=sha).
#
# Код завершения: 0 — маршрут есть, 1 — релиз раньше раздела,
# 2 — коммит не найден (решать вызывающему; deploy.yml тогда проверяет /manager/).
# Тест — backend/tests/unit/test_release_has_manager_route_script.py.

set -u

RELEASE="${1:-}"
URLS_FILE=backend/freesport/urls.py
# Подключение сайта раздела в URLconf — backend/freesport/urls.py.
MARKER='path("manager/", manager_site.urls)'

if [ -z "$RELEASE" ] || ! git rev-parse --verify --quiet "$RELEASE^{commit}" > /dev/null; then
  echo "Коммит релиза «$RELEASE» не найден в репозитории"
  exit 2
fi

if git show "$RELEASE:$URLS_FILE" 2> /dev/null | grep -qF "$MARKER"; then
  echo "Релиз $RELEASE: раздел /manager/ есть"
  exit 0
fi
echo "Релиз $RELEASE: раздела /manager/ нет (релиз раньше стори 42.4)"
exit 1
