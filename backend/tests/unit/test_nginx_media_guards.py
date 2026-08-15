"""Story 36.1: nginx обязан закрывать legacy-каталоги обмена 1С под /media/.

Каталоги `1c_import`/`1c_temp` перенесены в приватный `ONEC_PRIVATE_DIR`, но на
production media-volume сохраняется между деплоями: файлы незавершённых обменов,
записанные до переезда, физически остаются под `MEDIA_ROOT` и без 404-guard
продолжают отдаваться по прямой ссылке. Тест фиксирует наличие guard'ов в
конфигурации nginx как defense-in-depth (очистка самих файлов — команда
`purge_legacy_1c_media`).
"""

import re
from pathlib import Path

import pytest

# В тестовом контейнере смонтирован только backend/ (как /app), а docker/nginx
# подключается отдельным volume в /app/docker/nginx. В CI и локальном venv
# pytest стартует из backend/ полного checkout — там конфиги лежат на уровень выше.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_NGINX_CONF_CANDIDATES = (
    _BACKEND_ROOT / "docker" / "nginx" / "conf.d",
    _BACKEND_ROOT.parent / "docker" / "nginx" / "conf.d",
)


def _nginx_conf_dir() -> Path | None:
    for candidate in _NGINX_CONF_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return None


def _guard_pattern(subdir: str) -> re.Pattern[str]:
    """location /media/<subdir>/ { ... return 404; ... }"""
    return re.compile(
        r"location\s+/media/" + re.escape(subdir) + r"/\s*\{[^}]*return\s+404\s*;",
        re.DOTALL,
    )


conf_dir = _nginx_conf_dir()

pytestmark = pytest.mark.skipif(
    conf_dir is None,
    reason=(
        "docker/nginx/conf.d недоступен из этого окружения " f"(искали в {[str(p) for p in _NGINX_CONF_CANDIDATES]})"
    ),
)


class TestLegacyOneCMediaGuards:
    """Оба legacy-каталога обмена должны отдавать 404 во всех конфигах nginx."""

    @pytest.mark.parametrize("conf_name", ["default.conf", "local.conf"])
    @pytest.mark.parametrize("subdir", ["1c_import", "1c_temp"])
    def test_legacy_exchange_dir_returns_404(self, conf_name: str, subdir: str) -> None:
        assert conf_dir is not None  # для mypy: skipif уже отсеял None
        conf_path = conf_dir / conf_name
        assert conf_path.is_file(), f"Конфиг {conf_name} не найден в {conf_dir}"

        content = conf_path.read_text(encoding="utf-8")

        assert _guard_pattern(subdir).search(content), (
            f"{conf_name}: нет 404-guard для /media/{subdir}/. "
            "Legacy-файлы обмена 1С на сохранившемся media-volume останутся "
            "доступны анонимно по прямой ссылке."
        )
