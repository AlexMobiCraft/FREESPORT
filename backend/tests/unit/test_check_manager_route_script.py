"""
Скрипт HTTP-проверки маршрута `/manager/` (`scripts/deploy/check-manager-route.sh`).

По коду завершения скрипта решается, прошли ли шаг `main.yml` и проверка
production после деплоя (`deploy.yml`). Тест запускает скрипт против
локального HTTP-сервера с заданными ответами: успех — только 302 ровно на
страницу входа и полностью полученная страница входа с кодом 200 (R42.4-15).
"""

from __future__ import annotations

import shutil
import subprocess
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator, NamedTuple

import pytest

# В тестовом контейнере scripts/ смонтирован в /app/scripts, в CI и venv
# pytest стартует из backend/ полного checkout — скрипт на уровень выше.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_CANDIDATES = (
    _BACKEND_ROOT / "scripts" / "deploy" / "check-manager-route.sh",
    _BACKEND_ROOT.parent / "scripts" / "deploy" / "check-manager-route.sh",
)
SCRIPT = next((path for path in _SCRIPT_CANDIDATES if path.is_file()), None)

pytestmark = pytest.mark.skipif(
    SCRIPT is None or shutil.which("bash") is None or shutil.which("curl") is None,
    reason=f"нужны bash, curl и скрипт (искали в {[str(p) for p in _SCRIPT_CANDIDATES]})",
)


class Reply(NamedTuple):
    status: int
    headers: dict[str, str]
    body: bytes = b""
    # Объявленная длина тела; None — настоящая. Больше настоящей — ответ
    # обрывается: сервер закрывает соединение, не дослав тело.
    content_length: int | None = None


LOGIN_PAGE = b'<html><body><form id="login-form" method="post" action="/manager/login/"></form></body></html>'
TO_LOGIN = Reply(302, {"Location": "/manager/login/?next=/manager/"})
LOGIN_OK = Reply(200, {"Content-Type": "text/html"}, LOGIN_PAGE)


@contextmanager
def serve(routes: dict[str, Reply]) -> Iterator[str]:
    """HTTP-сервер на свободном порту; неизвестный путь — 404."""

    class Handler(BaseHTTPRequestHandler):
        # HTTP/1.0: соединение закрывается после ответа, оборванное тело curl замечает.
        def do_GET(self) -> None:
            reply = routes.get(self.path, Reply(404, {}))
            self.send_response(reply.status)
            for name, value in reply.headers.items():
                self.send_header(name, value)
            length = len(reply.body) if reply.content_length is None else reply.content_length
            self.send_header("Content-Length", str(length))
            self.end_headers()
            self.wfile.write(reply.body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


def run_script(routes: dict[str, Reply]) -> subprocess.CompletedProcess[str]:
    with serve(routes) as base_url:
        return subprocess.run(
            ["bash", str(SCRIPT), base_url], capture_output=True, text=True, encoding="utf-8", timeout=120
        )


def test_section_routed_to_django_passes():
    result = run_script({"/manager/": TO_LOGIN, "/manager/login/": LOGIN_OK})

    assert result.returncode == 0, result.stdout + result.stderr
    assert "✅" in result.stdout


@pytest.mark.parametrize(
    "routes",
    [
        # Страница входа оборвана: curl завершается с ошибкой 18, хотя форма уже пришла.
        pytest.param(
            {"/manager/": TO_LOGIN, "/manager/login/": LOGIN_OK._replace(content_length=9999)},
            id="login-body-truncated",
        ),
        # Форма входа в теле, но код не 200.
        pytest.param(
            {"/manager/": TO_LOGIN, "/manager/login/": Reply(302, {"Location": "/manager/login/"}, LOGIN_PAGE)},
            id="login-302-with-form",
        ),
        pytest.param(
            {"/manager/": TO_LOGIN, "/manager/login/": Reply(200, {}, b"<html>Next.js</html>")},
            id="login-without-form",
        ),
        pytest.param(
            {"/manager/": TO_LOGIN._replace(content_length=9999, body=b"x"), "/manager/login/": LOGIN_OK},
            id="redirect-truncated",
        ),
        pytest.param(
            {"/manager/": Reply(302, {"Location": "/admin/login/?next=/admin/"}), "/manager/login/": LOGIN_OK},
            id="redirect-elsewhere",
        ),
        pytest.param({"/manager/login/": LOGIN_OK}, id="section-404"),
    ],
)
def test_broken_route_fails(routes):
    result = run_script(routes)

    assert result.returncode != 0, result.stdout
    assert "❌" in result.stdout
    assert "✅" not in result.stdout
