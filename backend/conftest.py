"""
Корневой conftest бэкенда FREESPORT.

Единственная задача файла — автоматически проставлять маркер `unit` / `integration` /
`performance` по каталогу, в котором лежит тест. Маркер руками ставить не нужно:
правило определяется путём файла. Явный маркер в тесте всегда побеждает автоматический.

Зачем: до появления этого хука 852 из 2699 тестов (31 %) не имели ни одного маркера и
молча выпадали из `make test-unit` / `make test-integration`. Правило «маркер обязателен»
было записано в документации, но ничем не обеспечено, и каждый новый файл без маркера
расширял слепую зону. Теперь разметка не может разойтись с реальностью: путь, не покрытый
правилами, обрывает сбор с ошибкой. Тест вне дерева `backend/` разметить нечем — он проходит
без маркера, но не молча: хук выдаёт `UnmarkedTestWarning` с перечнем таких файлов.

ГРАНИЦА ВОЗМОЖНОСТЕЙ: предупреждение появляется только там, где этот conftest вообще загружен,
то есть когда rootdir — `backend/` или в аргументах есть хотя бы один путь внутри него. Вызов
вида `pytest /tmp/ext/test_x.py` без единого внутреннего пути даёт другой rootdir, файл не
подхватывается, и ни одна строка отсюда не исполняется. Закрыть этот случай из conftest нельзя
в принципе — он требует плагина, установленного в окружение (`-p`/entry point).

ВАЖНО: pytest загружает этот файл раньше, чем `backend/tests/unit/conftest.py`, который сам
вызывает `settings.configure()`. Поэтому здесь запрещены импорты Django и любое обращение
к настройкам — только pytest и стандартная библиотека.

Подробности и таблица соответствия — `backend/docs/testing-standards.md`, раздел
«Маркеры pytest».
"""

import warnings
from collections import Counter
from pathlib import Path

import pytest

# Каталог `backend/`. Считаем от самого файла, а не от `config.rootpath`: в репозитории есть
# второй, корневой `pytest.ini`, и при запуске с корня rootdir оказывается другим — привязка
# к `__file__` делает разметку независимой от того, откуда запущен pytest.
BACKEND_ROOT = Path(__file__).resolve().parent

# Маркеры, которыми управляет этот хук. Если любой из них уже проставлен в тесте явно
# (`@pytest.mark.*` или `pytestmark`), хук такой тест не трогает.
AUTO_MARKERS = ("unit", "integration", "performance")

# Маркеры, ортогональные автоматическим: ставятся вручную и хуком не управляются. Перечислены
# здесь, потому что от них зависят фильтры CI (`and not slow` в PR-гейтах, `performance or slow`
# в nightly) — список должен быть в одном месте, а не продублирован в тестах.
ORTHOGONAL_MARKERS = ("data_dependent", "slow")

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

# Путь есть, но ведёт за пределы `backend/`. Отдельное значение, а не второй `None`: «чужое
# дерево» и «у элемента сбора вообще нет файла» — разные ситуации, и в предупреждении каждая
# должна быть названа своим именем.
OUTSIDE_BACKEND = object()


class UnmarkedTestWarning(UserWarning):
    """Тест собран, но авторазметка к нему неприменима — в прогоны по `-m` он не попадёт."""


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


def _item_path(item):
    """Путь к файлу элемента сбора или `None`. Единственное место, где он извлекается."""
    return getattr(item, "path", None) or getattr(item, "fspath", None)


def _relative_parts(item):
    """Сегменты пути теста относительно `backend/`.

    Возвращает кортеж сегментов — для теста внутри `backend/`; `OUTSIDE_BACKEND` — если путь
    ведёт наружу (симлинк, `--pyargs`, файл, переданный явным путём) либо не поддаётся
    разрешению; `None` — если у элемента сбора файла нет вовсе. Две последние ситуации
    разметить нечем, но молчать о них нельзя: такой тест не попадёт ни в один прогон по `-m`,
    а это ровно то тихое выпадение, ради которого хук и написан.

    `resolve()` может бросить не только `ValueError` (путь вне дерева), но и `OSError` или
    `RuntimeError` — петля симлинков, превышение MAX_PATH, недопустимые символы. Ловим все
    три: необработанное исключение здесь обрывает весь сбор трейсбеком.
    """
    path = _item_path(item)
    if path is None:
        return None
    try:
        return Path(str(path)).resolve().relative_to(BACKEND_ROOT).parts
    except (ValueError, OSError, RuntimeError):
        return OUTSIDE_BACKEND


def _identify(item):
    """Как назвать тест в предупреждении: путь к файлу, а если файла нет — `nodeid`.

    Полагаться на один `nodeid` нельзя: pytest строит его относительно rootdir, и у файла
    снаружи дерева он вырождается в `::test_x` — предупреждение без имени файла бесполезно.
    Проверено вручную на `/tmp/exttests/test_outside.py`, переданном вместе с внутренним путём.
    """
    path = _item_path(item)
    if path is not None:
        return str(path)
    return str(getattr(item, "nodeid", None) or "<элемент сбора без пути>")


# tryfirst обязателен: деселект по `-m` делает встроенный плагин `_pytest.mark` в собственном
# `pytest_collection_modifyitems`. Разметить надо до отбора, иначе `-m unit` снова начнёт
# молча терять тесты — ровно та дыра, ради которой хук и написан.
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """Проставляет маркер по каталогу теста, уважая явно заданные маркеры."""
    unmapped = set()
    unmarkable_reasons = {}
    unmarkable_counts = Counter()

    for item in items:
        if any(item.get_closest_marker(name) for name in AUTO_MARKERS):
            continue

        rel_parts = _relative_parts(item)
        if rel_parts is OUTSIDE_BACKEND or rel_parts is None:
            # Считаем тесты поимённо: несколько тестов одного файла схлопываются в одну строку
            # перечня, и без счётчика не видно, сколько именно их выпало.
            name = _identify(item)
            unmarkable_reasons[name] = (
                "путь вне backend/" if rel_parts is OUTSIDE_BACKEND else "у элемента сбора нет пути к файлу"
            )
            unmarkable_counts[name] += 1
            continue

        marker = marker_for_path(rel_parts)
        if marker is None:
            unmapped.add("/".join(rel_parts))
            continue

        item.add_marker(getattr(pytest.mark, marker))

    # Предупреждение выдаётся раньше UsageError: сторож обрывает сбор, и информация о тестах
    # вне дерева иначе потерялась бы вместе с прогоном.
    if unmarkable_reasons:
        listing = "\n".join(
            f"  - {name} ({reason}, тестов: {unmarkable_counts[name]})"
            for name, reason in sorted(unmarkable_reasons.items())
        )
        warnings.warn(
            "Собраны тесты, которым авторазметка не может проставить маркер "
            "unit/integration/performance, — ни в один прогон по `-m` они не попадут:\n"
            f"{listing}\n\n"
            "Для чужого дерева это ожидаемо (--pyargs, файл снаружи backend/, переданный явным путём) "
            "и обрывать чужой сбор своим правилом мы не будем. Если файл должен размечаться — "
            "перенесите его под backend/ или поставьте маркер в файле явно. "
            "См. backend/docs/testing-standards.md, раздел «Маркеры pytest».",
            UnmarkedTestWarning,
            stacklevel=1,
        )

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
