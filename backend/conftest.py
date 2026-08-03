"""
Корневой conftest бэкенда FREESPORT.

Единственная задача файла — автоматически проставлять маркер `unit` / `integration` /
`performance` по каталогу, в котором лежит тест. Маркер руками ставить не нужно:
правило определяется путём файла. Явный маркер в тесте всегда побеждает автоматический.

Зачем: до появления этого хука 852 из 2699 тестов (31 %) не имели ни одного маркера и
молча выпадали из `make test-unit` / `make test-integration`. Правило «маркер обязателен»
было записано в документации, но ничем не обеспечено, и каждый новый файл без маркера
расширял слепую зону. Теперь разметка не может разойтись с реальностью: путь, не покрытый
правилами, обрывает сбор с ошибкой.

ВАЖНО: pytest загружает этот файл раньше, чем `backend/tests/unit/conftest.py`, который сам
вызывает `settings.configure()`. Поэтому здесь запрещены импорты Django и любое обращение
к настройкам — только pytest и стандартная библиотека.

Подробности и таблица соответствия — `backend/docs/testing-standards.md`, раздел
«Маркеры pytest».
"""

from pathlib import Path

import pytest

# Каталог `backend/`. Считаем от самого файла, а не от `config.rootpath`: в репозитории есть
# второй, корневой `pytest.ini`, и при запуске с корня rootdir оказывается другим — привязка
# к `__file__` делает разметку независимой от того, откуда запущен pytest.
BACKEND_ROOT = Path(__file__).resolve().parent

# Маркеры, которыми управляет этот хук. Если любой из них уже проставлен в тесте явно
# (`@pytest.mark.*` или `pytestmark`), хук такой тест не трогает.
AUTO_MARKERS = ("unit", "integration", "performance")

# Каталоги-категории. Ищутся среди сегментов пути и работают на любой глубине, поэтому
# и `tests/integration/`, и `apps/products/tests/integration/`, и гипотетический
# `apps/products/api/tests/integration/` размечаются одинаково.
CATEGORY_DIRS = {
    "unit": "unit",
    "integration": "integration",
    "functional": "integration",
    "regression": "integration",
    "performance": "performance",
}

# Значение по умолчанию для деревьев без каталога-категории: тесты приложения рядом с кодом
# считаются модульными. Асимметрия с `tests/` осознанная — см. testing-standards.md.
DEFAULT_PREFIX_RULES = ((("apps",), "unit"),)


def marker_for_path(rel_parts):
    """Возвращает имя маркера для пути теста относительно `backend/`.

    `rel_parts` — кортеж сегментов пути (`Path.parts`), например
    `("tests", "unit", "test_models", "test_product_models.py")`.

    Сначала ищется каталог-категория; берётся самый глубокий, потому что он говорит о тесте
    точнее вышестоящих. Если категории нет — применяются префиксные правила по умолчанию.
    Возвращает `None`, если путь не покрыт ничем.
    """
    for segment in reversed(rel_parts[:-1]):
        marker = CATEGORY_DIRS.get(segment)
        if marker is not None:
            return marker

    for prefix, marker in DEFAULT_PREFIX_RULES:
        if rel_parts[: len(prefix)] == prefix:
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


# tryfirst обязателен: деселект по `-m` делает встроенный плагин `_pytest.mark` в собственном
# `pytest_collection_modifyitems`. Разметить надо до отбора, иначе `-m unit` снова начнёт
# молча терять тесты — ровно та дыра, ради которой хук и написан.
@pytest.hookimpl(tryfirst=True)
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
            "Положите тест в каталог-категорию (unit/integration/functional/regression/performance), "
            "поставьте маркер в файле явно или добавьте правило в backend/conftest.py. "
            "Если это временный или служебный файл — его каталог должен быть в norecursedirs (pytest.ini). "
            "См. backend/docs/testing-standards.md, раздел «Маркеры pytest»."
        )
