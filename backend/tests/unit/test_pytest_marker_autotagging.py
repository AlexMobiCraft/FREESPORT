"""
Тесты правила автоматической разметки pytest-маркеров по каталогу.

Проверяется корневой `backend/conftest.py`: чистая функция `marker_for_path` и сам хук
`pytest_collection_modifyitems`. Хук вызывается напрямую на подставных элементах сбора —
без Django и без реального прогона, поэтому весь файл отрабатывает за доли секунды.

Сам файл маркера не имеет намеренно: он лежит в `tests/unit/` и получает `unit`
автоматически — ровно тем механизмом, который проверяет.
"""

import configparser
import os
from pathlib import Path

import pytest

import conftest as root_conftest

marker_for_path = root_conftest.marker_for_path

# Каталоги, которые pytest не обходит (norecursedirs) — обход дерева их пропускает.
SKIPPED_DIRS = {
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "build",
    "dist",
    "env",
    "htmlcov",
    "media",
    "node_modules",
    "staticfiles",
    "temp",
}


def _is_test_file(name):
    """Совпадает ли имя файла с `python_files` из pytest.ini."""
    return name == "tests.py" or name.startswith("test_") and name.endswith(".py") or name.endswith("_tests.py")


class FakeItem:
    """Минимальная замена элемента сбора: хук трогает только эти три вещи."""

    def __init__(self, path, markers=()):
        self.path = path
        self._explicit = set(markers)
        self.added = []

    def get_closest_marker(self, name):
        return name if name in self._explicit else None

    def add_marker(self, mark):
        self.added.append(mark.name)


def make_item(rel_path, markers=()):
    return FakeItem(root_conftest.BACKEND_ROOT / rel_path, markers)


class TestMarkerForPath:
    """Каждое правило соответствия."""

    @pytest.mark.parametrize(
        "rel_path,expected",
        [
            ("tests/unit/test_models/test_product_models.py", "unit"),
            ("tests/integration/test_product_detail_api.py", "integration"),
            ("tests/functional/test_checkout_flow.py", "integration"),
            ("tests/regression/test_epic_28_intact.py", "integration"),
            ("tests/performance/test_search_performance.py", "performance"),
            ("apps/products/tests/test_models.py", "unit"),
            ("apps/banners/tests/test_views.py", "unit"),
            # Django-style: собирается по шаблону `tests.py`, лежит не в `apps/*/tests/`
            ("apps/pages/tests.py", "unit"),
            # Каталог-категория внутри приложения
            ("apps/products/tests/integration/test_import_orchestration.py", "integration"),
            ("apps/products/tests/unit/test_pricing_policy.py", "unit"),
        ],
    )
    def test_known_paths_get_expected_marker(self, rel_path, expected):
        assert marker_for_path(Path(rel_path).parts) == expected

    @pytest.mark.parametrize(
        "rel_path,expected",
        [
            # Каталог-категория внутри apps/ должен побеждать умолчание `apps/` → unit
            ("apps/products/tests/performance/test_checkout_load.py", "performance"),
            ("apps/orders/tests/functional/test_flow.py", "integration"),
            ("apps/orders/tests/regression/test_epic.py", "integration"),
            # Категория работает на любой глубине, а не только на втором сегменте после apps/
            ("apps/products/api/tests/integration/test_x.py", "integration"),
            ("apps/a/b/c/d/tests/performance/test_x.py", "performance"),
        ],
    )
    def test_category_dir_wins_over_apps_default(self, rel_path, expected):
        assert marker_for_path(Path(rel_path).parts) == expected

    def test_deepest_category_wins(self):
        """Самый глубокий каталог-категория точнее вышестоящего."""
        assert marker_for_path(Path("tests/unit/integration/test_x.py").parts) == "integration"
        assert marker_for_path(Path("tests/integration/unit/test_x.py").parts) == "unit"

    def test_filename_is_not_treated_as_category(self):
        """Категорию задаёт каталог, а не имя файла."""
        assert marker_for_path(Path("tests/performance.py").parts) is None

    @pytest.mark.parametrize(
        "rel_path",
        [
            "tests/smoke/test_x.py",  # новый каталог без категории
            "tests/test_orphan.py",  # тест прямо в корне tests/
            "scripts/test_helper.py",  # вне apps/ и tests/
            "test_toplevel.py",  # в корне backend/
        ],
    )
    def test_unmapped_paths_return_none(self, rel_path):
        assert marker_for_path(Path(rel_path).parts) is None

    def test_empty_path_returns_none(self):
        assert marker_for_path(()) is None

    def test_bare_directory_returns_none(self):
        """Последний сегмент считается именем файла и категорией не является."""
        assert marker_for_path(("tests",)) is None


class TestHook:
    """Поведение самого `pytest_collection_modifyitems`."""

    def test_marks_unmarked_item(self):
        item = make_item("tests/integration/test_x.py")
        root_conftest.pytest_collection_modifyitems(None, [item])
        assert item.added == ["integration"]

    @pytest.mark.parametrize("explicit", ["unit", "integration", "performance"])
    def test_explicit_marker_wins(self, explicit):
        """Главный инвариант: явный маркер хук не переписывает и не дополняет."""
        # Путь говорит `unit`, но в файле стоит другой маркер — победить должен файл.
        item = make_item("apps/products/tests/test_x.py", markers=[explicit])
        root_conftest.pytest_collection_modifyitems(None, [item])
        assert item.added == []

    def test_orthogonal_marker_does_not_block_autotagging(self):
        """`django_db` / `slow` автоматической разметке не мешают."""
        item = make_item("tests/integration/test_x.py", markers=["django_db", "slow"])
        root_conftest.pytest_collection_modifyitems(None, [item])
        assert item.added == ["integration"]

    def test_item_outside_backend_is_skipped(self):
        item = FakeItem(root_conftest.BACKEND_ROOT.parent / "frontend" / "test_x.py")
        root_conftest.pytest_collection_modifyitems(None, [item])
        assert item.added == []

    def test_item_without_path_is_skipped(self):
        item = FakeItem(None)
        root_conftest.pytest_collection_modifyitems(None, [item])
        assert item.added == []

    def test_unmapped_item_raises_usage_error(self):
        item = make_item("tests/smoke/test_x.py")
        with pytest.raises(pytest.UsageError) as exc:
            root_conftest.pytest_collection_modifyitems(None, [item])
        assert "tests/smoke/test_x.py" in str(exc.value)

    def test_usage_error_lists_every_unmapped_file(self):
        items = [make_item("tests/smoke/test_a.py"), make_item("scripts/test_b.py")]
        with pytest.raises(pytest.UsageError) as exc:
            root_conftest.pytest_collection_modifyitems(None, items)
        message = str(exc.value)
        assert "tests/smoke/test_a.py" in message
        assert "scripts/test_b.py" in message


class TestRealTree:
    """Правила проверяются против фактического содержимого репозитория."""

    def _walk_test_files(self):
        for dirpath, dirnames, filenames in os.walk(root_conftest.BACKEND_ROOT):
            dirnames[:] = [
                d for d in dirnames if d not in SKIPPED_DIRS and not d.startswith(".") and not d.startswith("venv")
            ]
            for name in filenames:
                if _is_test_file(name):
                    yield Path(dirpath, name).relative_to(root_conftest.BACKEND_ROOT).parts

    def test_every_real_test_file_is_covered(self):
        """Самая вероятная регрессия — новый тестовый каталог без правила.

        Полный сбор pytest занимает ~6 минут; этот обход стоит миллисекунды и ловит ту же
        ситуацию до того, как она обрушит прогон в CI.
        """
        uncovered = sorted("/".join(parts) for parts in self._walk_test_files() if marker_for_path(parts) is None)
        assert not uncovered, "нет правила разметки для файлов: " + ", ".join(uncovered)

    def test_walk_finds_a_meaningful_number_of_files(self):
        """Сторож самого обхода: если фильтр сломается и найдёт ноль файлов, тест выше станет пустым."""
        assert len(list(self._walk_test_files())) > 100


class TestConfigConsistency:
    """Инварианты конфигурации, которые легко нарушить при правке."""

    INI_FILES = ("pytest.ini", "../pytest.ini")

    def _markers(self, ini_relative):
        """Маркеры, объявленные в pytest.ini.

        Корневой `../pytest.ini` лежит вне `backend/`, а тест-контейнер монтирует только
        `backend/` — там файла нет, и проверка пропускается вместо ложного падения.
        """
        path = root_conftest.BACKEND_ROOT / ini_relative
        parser = configparser.ConfigParser()
        if not parser.read(path, encoding="utf-8"):
            pytest.skip(f"{ini_relative} недоступен в этом окружении (вне смонтированного backend/)")
        raw = parser.get("pytest", "markers")
        return {line.split(":", 1)[0].strip() for line in raw.splitlines() if line.strip()}

    @pytest.mark.parametrize("ini_relative", INI_FILES)
    def test_all_auto_markers_are_declared(self, ini_relative):
        """Оба pytest.ini объявляют все автоматические маркеры.

        Корневой конфиг репозитория действует, когда pytest запускают не из `backend/`;
        незаявленный маркер там даёт PytestUnknownMarkWarning, а при --strict-markers — падение.
        """
        declared = self._markers(ini_relative)
        missing = set(root_conftest.AUTO_MARKERS) - declared
        assert not missing, f"{ini_relative}: не объявлены маркеры {sorted(missing)}"

    def test_both_ini_files_declare_the_same_markers(self):
        assert self._markers("pytest.ini") == self._markers("../pytest.ini")

    def test_rules_produce_only_known_markers(self):
        produced = set(root_conftest.CATEGORY_DIRS.values())
        produced |= {marker for _, marker in root_conftest.DEFAULT_PREFIX_RULES}
        assert produced <= set(root_conftest.AUTO_MARKERS)

    def test_category_dirs_cover_every_default_prefix_tree(self):
        """Умолчание — только запасной вариант; каталоги-категории должны иметь приоритет."""
        for prefix, _ in root_conftest.DEFAULT_PREFIX_RULES:
            probe = prefix + ("app", "tests", "integration", "test_x.py")
            assert marker_for_path(probe) == "integration"
