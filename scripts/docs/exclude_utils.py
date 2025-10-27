"""Утилиты для работы с исключениями в скриптах документации."""
from pathlib import Path
from typing import Iterable, List

EXCLUDES_FILENAME = "docs_exclude_patterns.txt"


def _normalize(pattern: str) -> str:
    """Привести шаблон к POSIX-виду для унификации сравнения."""
    return pattern.replace("\\", "/").strip()


def load_exclude_patterns(
    project_root: Path, extra_patterns: Iterable[str] | None = None
) -> List[str]:
    """Прочитать базовый список исключений и объединить его с дополнительными шаблонами."""
    patterns: List[str] = []
    config_path = project_root / "scripts" / EXCLUDES_FILENAME

    if config_path.exists():
        for raw_line in config_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(_normalize(line))

    if extra_patterns:
        patterns.extend(
            _normalize(pattern) for pattern in extra_patterns if pattern.strip()
        )

    return patterns
