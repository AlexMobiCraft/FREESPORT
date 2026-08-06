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
import re
import warnings
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
    """Минимальная замена элемента сбора: хук трогает только эти четыре вещи."""

    def __init__(self, path, markers=(), nodeid="fake::test_x"):
        self.path = path
        if nodeid is not None:
            self.nodeid = nodeid
        self._explicit = set(markers)
        self.added = []

    def get_closest_marker(self, name):
        return name if name in self._explicit else None

    def add_marker(self, mark):
        self.added.append(mark.name)


class PathlessItem(FakeItem):
    """Элемент сбора без файла и без `nodeid` — проверяет запасную ветку `_identify`."""

    def __init__(self):
        super().__init__(None, nodeid=None)


def unmarked_warnings(record):
    """Только `UnmarkedTestWarning` из записи: `pytest.warns` собирает все предупреждения блока."""
    return [w for w in record if issubclass(w.category, root_conftest.UnmarkedTestWarning)]


def make_item(rel_path, markers=(), nodeid=None):
    return FakeItem(root_conftest.BACKEND_ROOT / rel_path, markers, nodeid or f"{rel_path}::test_x")


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

    def test_item_outside_backend_is_not_marked_but_reported(self):
        """Чужое дерево размечать нечем, но тихо терять тест нельзя — должно быть слышно."""
        item = FakeItem(root_conftest.BACKEND_ROOT.parent / "frontend" / "test_x.py", nodeid="::test_x")
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            root_conftest.pytest_collection_modifyitems(None, [item])
        assert item.added == []
        message = str(unmarked_warnings(record)[0].message)
        assert "путь вне backend/" in message
        # Именно путь, а не nodeid: у файла снаружи rootdir pytest вырождает nodeid в `::test_x`,
        # и предупреждение без имени файла не даёт понять, какой тест выпал.
        assert str(item.path) in message

    def test_pathless_item_is_reported_by_nodeid(self):
        """Файла нет — назвать тест можно только по nodeid."""
        item = FakeItem(None, nodeid="tests/unit/test_x.py::test_generated")
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            root_conftest.pytest_collection_modifyitems(None, [item])
        assert item.added == []
        message = str(unmarked_warnings(record)[0].message)
        assert "tests/unit/test_x.py::test_generated" in message
        assert "нет пути к файлу" in message

    def test_item_without_path_and_nodeid_is_still_reported(self):
        """Крайний случай: ни файла, ни nodeid — предупреждение всё равно выдаётся."""
        item = PathlessItem()
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            root_conftest.pytest_collection_modifyitems(None, [item])
        assert item.added == []
        assert "<элемент сбора без пути>" in str(unmarked_warnings(record)[0].message)

    def test_every_unmarkable_item_lands_in_one_warning(self):
        """Одно предупреждение на весь сбор, но со всеми виновниками поимённо."""
        outside = root_conftest.BACKEND_ROOT.parent
        items = [
            FakeItem(outside / "a" / "test_a.py"),
            FakeItem(outside / "b" / "test_b.py"),
            PathlessItem(),
        ]
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            root_conftest.pytest_collection_modifyitems(None, items)
        warned = unmarked_warnings(record)
        assert len(warned) == 1
        message = str(warned[0].message)
        assert str(items[0].path) in message
        assert str(items[1].path) in message
        assert "<элемент сбора без пути>" in message

    def test_warning_counts_tests_per_file(self):
        """Несколько тестов одного файла схлопываются в строку — счётчик не даёт потерять их число."""
        outside_file = root_conftest.BACKEND_ROOT.parent / "ext" / "test_many.py"
        items = [FakeItem(outside_file), FakeItem(outside_file), FakeItem(outside_file)]
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            root_conftest.pytest_collection_modifyitems(None, items)
        assert "тестов: 3" in str(unmarked_warnings(record)[0].message)

    def test_normal_item_produces_no_warning(self):
        """Сторож не должен шуметь на обычном прогоне — иначе его перестанут читать."""
        item = make_item("tests/integration/test_x.py")
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            root_conftest.pytest_collection_modifyitems(None, [item])
        assert unmarked_warnings(record) == []
        assert item.added == ["integration"]

    def test_explicitly_marked_outside_item_produces_no_warning(self):
        """Маркер уже стоит — тест в прогон по `-m` попадёт, предупреждать не о чем."""
        item = FakeItem(root_conftest.BACKEND_ROOT.parent / "test_x.py", markers=["unit"])
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            root_conftest.pytest_collection_modifyitems(None, [item])
        assert unmarked_warnings(record) == []

    def test_warning_does_not_suppress_usage_error(self):
        """Тест вне дерева и непокрытый путь внутри — сторож обязан сработать всё равно."""
        items = [
            FakeItem(root_conftest.BACKEND_ROOT.parent / "test_out.py"),
            make_item("tests/smoke/test_x.py"),
        ]
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            with pytest.raises(pytest.UsageError) as exc:
                root_conftest.pytest_collection_modifyitems(None, items)
        assert "tests/smoke/test_x.py" in str(exc.value)
        assert str(items[0].path) in str(unmarked_warnings(record)[0].message)

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

    @pytest.mark.parametrize("ini_relative", INI_FILES)
    def test_orthogonal_markers_are_declared(self, ini_relative):
        """`slow` и `data_dependent` объявлены: на них завязаны фильтры CI, а не только хук.

        Фильтрация по незаявленному маркеру работает и без объявления — но даёт
        `PytestUnknownMarkWarning`, а под `--strict-markers` роняет сбор. Держим объявленными,
        потому что `slow` теперь определяет состав трёх PR-гейтов и nightly.
        """
        declared = self._markers(ini_relative)
        missing = set(root_conftest.ORTHOGONAL_MARKERS) - declared
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


class TestCIFilters:
    """Состав каждого прогона CI держится на именах маркеров — сторож против опечатки в YAML.

    Хук защищает от «разметка разошлась с реальностью» внутри Python, но после подключения
    `slow` к гейтам тот же класс ошибки переехал на уровень YAML: `-m "not slo"` отфильтрует
    ровно ничего и молча вернёт флак в PR-прогон, а `-m "performance or slwo"` так же молча
    отберёт ноль тестов в nightly. Ни pytest, ни GitHub Actions такую опечатку не заметят.

    Файлы лежат вне `backend/`, а тест-контейнер монтирует только его — там проверки
    пропускаются вместо ложного падения.
    """

    PR_GATES = ("backend-ci.yml", "deploy.yml", "main.yml")
    ALL_WORKFLOWS = PR_GATES + ("performance-tests.yml",)

    def _repo_file(self, *parts):
        path = root_conftest.BACKEND_ROOT.parent.joinpath(*parts)
        if not path.exists():
            pytest.skip(f"{'/'.join(parts)} недоступен в этом окружении (вне смонтированного backend/)")
        return path

    def _pytest_filters(self, workflow):
        """Все выражения из `-m "..."` в workflow. `python -m venv` под шаблон не подпадает."""
        text = self._repo_file(".github", "workflows", workflow).read_text(encoding="utf-8")
        return re.findall(r'-m\s+"([^"]+)"', text)

    @pytest.mark.parametrize("workflow", PR_GATES)
    def test_pr_gates_exclude_performance_and_slow(self, workflow):
        """Ни один PR-гейт не должен гонять тесты, меряющие время."""
        filters = self._pytest_filters(workflow)
        assert filters, f"{workflow}: не найдено ни одного фильтра -m — гейт гоняет весь набор"
        for expression in filters:
            assert "not performance" in expression, f"{workflow}: перф-тесты не исключены ({expression})"
            assert "not slow" in expression, f"{workflow}: медленные тесты не исключены ({expression})"

    def test_nightly_runs_what_pr_gates_dropped(self):
        """Выведенное из гейтов обязано исполняться в nightly, иначе оно не исполняется нигде.

        Сравниваем множество: выражение встречается и в вызове pytest, и в комментарии-шапке,
        и они обязаны совпадать — разошедшийся комментарий вводит в заблуждение не меньше,
        чем неверный фильтр.
        """
        assert set(self._pytest_filters("performance-tests.yml")) == {"performance or slow"}

    @pytest.mark.parametrize("workflow", ALL_WORKFLOWS)
    def test_ci_filters_mention_only_declared_markers(self, workflow):
        """Опечатка в имени маркера превращает фильтр в тихий no-op — ловим её здесь."""
        known = set(root_conftest.AUTO_MARKERS) | set(root_conftest.ORTHOGONAL_MARKERS)
        for expression in self._pytest_filters(workflow):
            names = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", expression)) - {"not", "and", "or"}
            unknown = names - known
            assert not unknown, f"{workflow}: неизвестные маркеры в `-m {expression}`: {sorted(unknown)}"

    def test_coverage_is_measured_only_on_the_full_run(self):
        """Покрытие меряет тот прогон, который исполняет покрывающие тесты, — и только он.

        Замер 2026-08-06: на быстром гейте то же продакшен-покрытие даёт 62,5 %, на полном
        наборе — 76,4 %. Пока порог стоял в `backend-ci.yml`, каждая стори, покрывшая новый
        код интеграционными тестами, опускала метрику, и гейт краснел без регрессии. Тест
        не даёт вернуть подсчёт в узкий прогон.
        """
        for workflow in self.PR_GATES:
            text = self._repo_file(".github", "workflows", workflow).read_text(encoding="utf-8")
            if workflow == "main.yml":
                assert "--cov-fail-under" in text, "main.yml обязан считать покрытие с порогом"
                continue
            assert "--cov-fail-under" not in text, (
                f"{workflow} снова считает покрытие: его набор уже интеграционных тестов, "
                "метрика будет систематически занижена"
            )

    def test_coverage_denominator_excludes_tests(self):
        """Тесты и миграции — вне знаменателя, иначе метрика меряет сама себя.

        При `--cov=.` две трети объёма приходилось на код самих тестов, и исключение любого
        теста из прогона механически понижало покрытие, не меняя покрытия продукта.
        """
        text = self._repo_file("backend", "pyproject.toml").read_text(encoding="utf-8")
        assert "[tool.coverage.run]" in text, "конфиг покрытия пропал из backend/pyproject.toml"
        for pattern in ('"*/tests/*"', '"*/test_*.py"', '"*/migrations/*"'):
            assert pattern in text, f"из omit пропал {pattern}"

    def test_test_compose_has_no_variable_substitution(self):
        """Makefile зовёт `docker-compose.test.yml` без `--env-file` — это верно, пока нет `${}`.

        Появится первая подстановка — она молча резолвится в пустую строку. Правило записано
        комментарием в Makefile; здесь оно обеспечено.
        """
        text = self._repo_file("docker", "docker-compose.test.yml").read_text(encoding="utf-8")
        assert "${" not in text, "в docker-compose.test.yml появилась подстановка — верните --env-file в Makefile"
