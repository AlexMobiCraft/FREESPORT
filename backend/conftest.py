"""
Корневой conftest бэкенда FREESPORT.

Единственная задача файла — автоматически проставлять маркер `unit` / `integration` /
`performance` по каталогу, в котором лежит тест. Маркер руками ставить не нужно:
правило определяется путём файла. Явный маркер в тесте всегда побеждает автоматический.

Зачем: до появления этого хука 852 из 2699 тестов (31 %) не имели ни одного маркера и
молча выпадали из `make test-unit` / `make test-integration`. Правило «маркер обязателен»
было записано в документации, но ничем не обеспечено, и каждый новый файл без маркера
расширял слепую зону. Теперь разметка не может разойтись с реальностью: путь, не покрытый
`PATH_RULES`, обрывает сбор с ошибкой.

ВАЖНО: pytest загружает этот файл раньше, чем `backend/tests/unit/conftest.py`, который сам
вызывает `settings.configure()`. Поэтому здесь запрещены импорты Django и любое обращение
к настройкам — только pytest и стандартная библиотека.

Подробности и таблица соответствия — `backend/docs/testing-standards.md`, раздел
«Маркеры pytest».
"""

from pathlib import Path

import pytest

# Каталог `backend/`. Считаем от самого файла, а не от `config.rootpath`: так разметка
# не зависит от того, откуда запущен pytest.
BACKEND_ROOT = Path(__file__).resolve().parent

# Маркеры, которыми управляет этот хук. Если любой из них уже проставлен в тесте явно
# (`@pytest.mark.*` или `pytestmark`), хук такой тест не трогает.
AUTO_MARKERS = ("unit", "integration", "performance")

# Соответствие «каталог → маркер». Порядок значим: первое совпадение выигрывает, поэтому
# специфичные правила стоят раньше общих (`apps/*/tests/integration/` раньше, чем `apps/`).
# Сегмент "*" в шаблоне совпадает с любым одним сегментом пути.
PATH_RULES = (
    (("tests", "performance"), "performance"),
    (("tests", "integration"), "integration"),
    (("tests", "functional"), "integration"),
    (("tests", "regression"), "integration"),
    (("tests", "unit"), "unit"),
    (("apps", "*", "tests", "integration"), "integration"),
    (("apps",), "unit"),
)


def _pattern_matches(pattern, parts):
    """Совпадает ли шаблон каталога с началом пути теста."""
    if len(pattern) > len(parts):
        return False
    return all(expected in ("*", actual) for expected, actual in zip(pattern, parts))


def marker_for_path(rel_parts):
    """Возвращает имя маркера для пути теста относительно `backend/`.

    `rel_parts` — кортеж сегментов пути (`Path.parts`), например
    `("tests", "unit", "test_models", "test_product_models.py")`.
    Возвращает `None`, если путь не покрыт ни одним правилом из `PATH_RULES`.
    """
    for pattern, marker in PATH_RULES:
        if _pattern_matches(pattern, rel_parts):
            return marker
    return None


def _relative_parts(item):
    """Сегменты пути теста относительно `backend/` или `None`, если тест вне этого дерева."""
    path = getattr(item, "path", None) or getattr(item, "fspath", None)
    if path is None:
        return None
    try:
        return Path(str(path)).resolve().relative_to(BACKEND_ROOT).parts
    except ValueError:
        return None


def pytest_collection_modifyitems(config, items):
    """Проставляет маркер по каталогу теста, уважая явно заданные маркеры."""
    unmapped = set()

    for item in items:
        if any(item.get_closest_marker(name) for name in AUTO_MARKERS):
            continue

        rel_parts = _relative_parts(item)
        if rel_parts is None:
            # Тест вне `backend/` — не наше дерево, размечать нечем.
            continue

        marker = marker_for_path(rel_parts)
        if marker is None:
            unmapped.add("/".join(rel_parts))
            continue

        item.add_marker(getattr(pytest.mark, marker))

    if unmapped:
        listing = "\n".join(f"  - {path}" for path in sorted(unmapped))
        raise pytest.UsageError(
            "Не удалось определить pytest-маркер по каталогу для файлов:\n"
            f"{listing}\n\n"
            "Маркер unit/integration/performance проставляется автоматически по каталогу теста. "
            "Добавьте правило для нового каталога в PATH_RULES (backend/conftest.py) "
            "или поставьте маркер в файле явно. "
            "См. backend/docs/testing-standards.md, раздел «Маркеры pytest»."
        )
