"""
Своя БД Redis на воркер pytest-xdist (`freesport/settings/test.py`, R42.4-18).

Autouse-фикстура `clear_db_before_test` перед каждым тестом зовёт
`cache.clear()`, то есть FLUSHDB. Если два воркера параллельного прогона
окажутся в одной БД Redis, очистка одного посреди теста другого удалит ему
кэш и локи импорта 1С. Обязательный CI-прогон последовательный и такую
поломку настроек не увидит, поэтому тест поднимает настройки воркеров
`gw0` и `gw1` в двух отдельных процессах — так же, как их получает xdist.

База — номер 12 в `REDIS_URL` дочерних процессов, а не номер текущего
прогона: очистка `gw0` с настоящей базой стёрла бы данные живого воркера
`gw0` параллельного прогона. 12 и 13 свободны, пока воркеров меньше 12
(локальный прогон — `-n 4`).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings

BASE_DB = 12
KEY = "xdist-isolation-probe"

# Дочерний процесс: настройки freesport.settings.test, шаги из argv —
# `set=<значение>`, `get`, `clear`. Печатает LOCATION кэша и прочитанное.
CHILD = """
import json, sys
import django

django.setup()
from django.conf import settings
from django.core.cache import cache

key, steps = sys.argv[1], sys.argv[2:]
result = {"location": settings.CACHES["default"]["LOCATION"], "got": []}
for step in steps:
    if step.startswith("set="):
        cache.set(key, step[len("set="):], timeout=300)
    elif step == "get":
        result["got"].append(cache.get(key))
    elif step == "clear":
        cache.clear()
print(json.dumps(result))
"""


def run_worker(worker: str, *steps: str) -> dict[str, Any]:
    """Шаги с кэшем в отдельном процессе с настройками воркера `worker`."""
    redis_url = urlsplit(os.environ.get("REDIS_URL") or settings.CACHES["default"]["LOCATION"])
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "freesport.settings.test",
        "PYTEST_XDIST_WORKER": worker,
        "REDIS_URL": urlunsplit(redis_url._replace(path=f"/{BASE_DB}")),
    }
    completed = subprocess.run(
        [sys.executable, "-c", CHILD, KEY, *steps],
        cwd=Path(settings.BASE_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, f"воркер {worker} упал:\n{completed.stderr}"
    return json.loads(completed.stdout.strip().splitlines()[-1])


def redis_db(location: str) -> int:
    return int(urlsplit(location).path.lstrip("/"))


def test_workers_do_not_clear_each_other() -> None:
    """Очистка кэша воркером gw0 не трогает значение воркера gw1."""
    try:
        second = run_worker("gw1", "set=gw1", "get")
        first = run_worker("gw0", "set=gw0", "get", "clear", "get")

        assert redis_db(first["location"]) == BASE_DB
        assert redis_db(second["location"]) == BASE_DB + 1
        # Контрольные значения: каждый воркер прочитал своё.
        assert second["got"] == ["gw1"]
        assert first["got"] == ["gw0", None]

        after = run_worker("gw1", "get")
        assert after["got"] == ["gw1"], "cache.clear() воркера gw0 удалил значение воркера gw1"
    finally:
        # Ключи с таймаутом и так истекут, но базы 12 и 13 оставляем пустыми.
        run_worker("gw1", "clear")
