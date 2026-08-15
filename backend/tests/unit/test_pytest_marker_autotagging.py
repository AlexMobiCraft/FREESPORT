"""
Тесты правила автоматической разметки pytest-маркеров по каталогу.

Проверяется корневой `backend/conftest.py`: чистые функции разметки и сам хук
`pytest_collection_modifyitems`. Хук — обёртка (`wrapper=True`), поэтому в большинстве тестов
он прогоняется хелпером `run_hook` на подставных элементах сбора: без Django и без реального
прогона это отрабатывает за доли секунды.

Исключение — класс `TestRealRun`: факт деселекта, порядок хуков относительно `_pytest.mark`,
код возврата и неглушимость `--disable-warnings` подставным config проверить нельзя в принципе,
поэтому там pytest запускается настоящим подпроцессом.

Сам файл маркера не имеет намеренно: он лежит в `tests/unit/` и получает `unit`
автоматически — ровно тем механизмом, который проверяет.
"""

import configparser
import os
import re
import subprocess
import sys
import types
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


class FakeConfig:
    """Минимальная замена `pytest.Config`: хук читает из него ровно `option.markexpr`."""

    def __init__(self, markexpr=""):
        self.option = types.SimpleNamespace(markexpr=markexpr)


def unmarked_warnings(record):
    """Только `UnmarkedTestWarning` из записи: `pytest.warns` собирает все предупреждения блока."""
    return [w for w in record if issubclass(w.category, root_conftest.UnmarkedTestWarning)]


INNER_RESULT = object()  # то, что pluggy отдаёт обёртке как результат нижележащей цепочки


def run_hook(items, markexpr="", deselect=(), inner_error=None):
    """Прогоняет хук-обёртку целиком, эмулируя отбор pytest между её половинами.

    Хук объявлен как `@pytest.hookimpl(wrapper=True)`, то есть это генератор: часть до `yield`
    размечает, часть после — сверяет, кто уцелел. Здесь мы играем роль pluggy: пускаем первую
    половину, вычёркиваем из `items` то, что «отобрал» pytest, и пускаем вторую.

    `deselect` — элементы, которые отбор отбросил. Пустой по умолчанию: не выпал никто.
    `markexpr` — то, что пришло бы из `-m`; пустая строка означает, что отбора нет.
    `inner_error` — исключение «от нижележащего хука»: pluggy в этом случае бросает его в точку
    `yield`, и вторая половина обёртки не выполняется.

    Возвращает то, что вернул генератор: контракт `wrapper=True` обязывает отдать результат
    нижележащей цепочки, и без этой проверки его потерю не заметил бы ни один тест.
    """
    gen = root_conftest.pytest_collection_modifyitems(FakeConfig(markexpr), items)
    next(gen)
    if deselect:
        dropped = {id(item) for item in deselect}
        items[:] = [item for item in items if id(item) not in dropped]
    if inner_error is not None:
        gen.throw(inner_error)
        return None
    try:
        gen.send(INNER_RESULT)
    except StopIteration as stop:
        return stop.value
    return None


def make_item(rel_path, markers=(), nodeid=None):
    return FakeItem(root_conftest.BACKEND_ROOT / rel_path, markers, nodeid or f"{rel_path}::test_x")


def outside_item(name="test_x.py"):
    """Элемент сбора из чужого дерева — разметить его нечем."""
    return FakeItem(root_conftest.BACKEND_ROOT.parent / "ext" / name)


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
        run_hook([item])
        assert item.added == ["integration"]

    @pytest.mark.parametrize("explicit", ["unit", "integration", "performance"])
    def test_explicit_marker_wins(self, explicit):
        """Главный инвариант: явный маркер хук не переписывает и не дополняет."""
        # Путь говорит `unit`, но в файле стоит другой маркер — победить должен файл.
        item = make_item("apps/products/tests/test_x.py", markers=[explicit])
        run_hook([item])
        assert item.added == []

    def test_orthogonal_marker_does_not_block_autotagging(self):
        """`django_db` / `slow` автоматической разметке не мешают."""
        item = make_item("tests/integration/test_x.py", markers=["django_db", "slow"])
        run_hook([item])
        assert item.added == ["integration"]

    def test_item_outside_backend_is_not_marked_but_reported(self):
        """Чужое дерево размечать нечем, но тихо терять тест нельзя — должно быть слышно."""
        item = FakeItem(root_conftest.BACKEND_ROOT.parent / "frontend" / "test_x.py", nodeid="::test_x")
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            run_hook([item])
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
            run_hook([item])
        assert item.added == []
        message = str(unmarked_warnings(record)[0].message)
        assert "tests/unit/test_x.py::test_generated" in message
        assert "нет пути к файлу" in message

    def test_item_without_path_and_nodeid_is_still_reported(self):
        """Крайний случай: ни файла, ни nodeid — предупреждение всё равно выдаётся."""
        item = PathlessItem()
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            run_hook([item])
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
            run_hook(items)
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
            run_hook(items)
        assert "тестов: 3" in str(unmarked_warnings(record)[0].message)

    def test_normal_item_produces_no_warning(self):
        """Сторож не должен шуметь на обычном прогоне — иначе его перестанут читать."""
        item = make_item("tests/integration/test_x.py")
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            run_hook([item])
        assert unmarked_warnings(record) == []
        assert item.added == ["integration"]

    def test_explicitly_marked_outside_item_produces_no_warning(self):
        """Маркер уже стоит — тест в прогон по `-m` попадёт, предупреждать не о чем."""
        item = FakeItem(root_conftest.BACKEND_ROOT.parent / "test_x.py", markers=["unit"])
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            run_hook([item])
        assert unmarked_warnings(record) == []

    def test_warning_does_not_suppress_usage_error(self):
        """Тест вне дерева и непокрытый путь внутри — сторож обязан сработать всё равно."""
        items = [
            FakeItem(root_conftest.BACKEND_ROOT.parent / "test_out.py"),
            make_item("tests/smoke/test_x.py"),
        ]
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            with pytest.raises(pytest.UsageError) as exc:
                run_hook(items)
        assert "tests/smoke/test_x.py" in str(exc.value)
        assert str(items[0].path) in str(unmarked_warnings(record)[0].message)

    def test_unmapped_item_raises_usage_error(self):
        item = make_item("tests/smoke/test_x.py")
        with pytest.raises(pytest.UsageError) as exc:
            run_hook([item])
        assert "tests/smoke/test_x.py" in str(exc.value)

    def test_usage_error_lists_every_unmapped_file(self):
        items = [make_item("tests/smoke/test_a.py"), make_item("scripts/test_b.py")]
        with pytest.raises(pytest.UsageError) as exc:
            run_hook(items)
        message = str(exc.value)
        assert "tests/smoke/test_a.py" in message
        assert "scripts/test_b.py" in message


class TestDeselectGate:
    """Гейт срабатывает по факту выпадения теста из отбора, а не по виду выражения `-m`.

    Предупреждение не влияет на код возврата и глушится `--disable-warnings`; когда тест
    действительно выпал, этого мало. Но и рвать сбор всегда при `-m` нельзя: неразмеченный
    тест проходит любое отрицательное выражение (`-m "not slow"`), а такие выражения — это
    три из четырёх прогонов CI.
    """

    def test_dropped_item_under_markexpr_raises(self):
        item = outside_item()
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            with pytest.raises(pytest.UsageError) as exc:
                run_hook([item], markexpr="unit", deselect=[item])
        message = str(exc.value)
        assert str(item.path) in message
        assert "отбором текущего прогона отброшены" in message
        # Ошибка говорит то же самое — дублировать её предупреждением незачем.
        assert unmarked_warnings(record) == []

    def test_gate_message_does_not_blame_markexpr(self):
        """Причину выпадения не называем: при `-m unit --lf` отбросить мог и не маркер.

        Узнать, кто именно выбросил элемент, из хука нельзя — `-k`, `--deselect` и `--lf`
        мутируют `items` в той же фазе. Утверждать «виноват `-m`» значит врать в единственном
        сообщении, которое увидит человек.
        """
        item = outside_item()
        with pytest.raises(pytest.UsageError) as exc:
            run_hook([item], markexpr="unit", deselect=[item])
        message = str(exc.value)
        assert "отбором по `-m`" not in message
        # И не обещаем, что тест не исполнится нигде: `make test` идёт без `-m`.
        assert "ни в каком другом прогоне" not in message

    def test_gate_message_scopes_filter_removal_to_local_runs(self):
        """Снятие отбора — выход только локальный, и текст обязан это различать.

        Состав фильтров всех четырёх прогонов CI задан явно и застережён тестом
        `test_pr_gates_exclude_performance_and_slow` в этом же файле. Безусловное «уберите отбор»
        отправляло читателя лога CI за выходом, которого там нет, — совет, запрещённый
        собственными тестами проекта. Без этого теста формулировка ничем не держится и вернётся
        при первой же правке текста.
        """
        item = outside_item()
        with pytest.raises(pytest.UsageError) as exc:
            run_hook([item], markexpr="unit", deselect=[item])
        message = str(exc.value)
        assert "Локально помогает и снятие отбора" in message
        assert "В CI такого выхода нет" in message
        # Прежняя безусловная формулировка не должна вернуться ни целиком, ни обрывком.
        assert "Либо уберите отбор" not in message

    def test_hook_returns_inner_result(self):
        """Контракт `wrapper=True`: обёртка обязана вернуть результат нижележащей цепочки."""
        assert run_hook([make_item("tests/unit/test_x.py")]) is INNER_RESULT

    def test_surviving_item_under_markexpr_only_warns(self):
        """Ключевой случай: отрицательное выражение неразмеченный тест пропускает.

        `-m "not performance and not slow"` — фильтр `backend-ci`, `main` и `deploy`. Тест
        без маркеров ему удовлетворяет и исполняется, поэтому рвать сбор не за что.
        """
        item = outside_item()
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            run_hook([item], markexpr="not performance and not slow")
        assert "Сейчас они исполняются" in str(unmarked_warnings(record)[0].message)

    def test_dropped_without_markexpr_only_warns(self):
        """Деселекта мало: без `-m` тест могли отбросить по `-k` — это выбор запускающего."""
        item = outside_item()
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            run_hook([item], markexpr="", deselect=[item])
        message = str(unmarked_warnings(record)[0].message)
        # Текст обязан признать факт: тест отброшен, и говорить «сейчас они исполняются» — ложь.
        assert "отбор текущего прогона отбросил" in message
        assert "Сейчас они исполняются" not in message

    @pytest.mark.parametrize("markexpr", ["", "   "], ids=["пустое", "пробелы"])
    def test_blank_markexpr_is_no_selection(self, markexpr):
        """`-m ""` и `-m "   "` не отбирают ничего — включаться гейту не на что."""
        item = outside_item()
        with pytest.warns(root_conftest.UnmarkedTestWarning):
            run_hook([item], markexpr=markexpr, deselect=[item])

    @pytest.mark.parametrize(
        "config",
        [
            None,
            object(),
            types.SimpleNamespace(option=types.SimpleNamespace(markexpr=["unit"])),
            types.SimpleNamespace(option=types.SimpleNamespace(markexpr=None)),
        ],
        ids=["none", "без option", "markexpr не строка", "markexpr None"],
    )
    def test_unusable_config_degrades_to_warning(self, config):
        """Компромисс защитного чтения: гейт молчит, но сбор остаётся жив, а не падает.

        Проверяется поведение хука целиком, а не только `_markexpr`: обрыв сбора `AttributeError`
        из второй половины обёртки — ровно то, от чего защита и ставилась. Элемент при этом
        ещё и «выпадает» из отбора, то есть попадает в самую опасную ветку.
        """
        assert root_conftest._markexpr(config) == ""

        item = outside_item()
        items = [item]
        gen = root_conftest.pytest_collection_modifyitems(config, items)
        next(gen)
        items[:] = []  # отбор отбросил всё — при рабочем config тут сработал бы гейт
        with pytest.warns(root_conftest.UnmarkedTestWarning):
            with pytest.raises(StopIteration):
                gen.send(INNER_RESULT)

    def test_survivors_are_named_alongside_the_dropped(self):
        """Обрыв сбора не должен уносить с собой тех, кто просто остался без маркера."""
        dropped = outside_item("test_dropped.py")
        survived = outside_item("test_survived.py")
        with pytest.raises(pytest.UsageError) as exc:
            run_hook([dropped, survived], markexpr="unit", deselect=[dropped])
        message = str(exc.value)
        assert "test_dropped.py" in message
        # Уцелевший назван, но отдельной секцией — путать его с выпавшим нельзя.
        assert "test_survived.py" in message
        assert message.index("test_dropped.py") < message.index("Заодно")

    def test_mixed_reasons_produce_both_advices(self):
        """Причины разные — советов два, и склейка не даёт лишних пробелов."""
        outside = outside_item()
        pathless = PathlessItem()
        with pytest.raises(pytest.UsageError) as exc:
            run_hook([outside, pathless], markexpr="unit", deselect=[outside, pathless])
        message = str(exc.value)
        assert "перенесите его под backend/" in message
        assert "перенос не поможет" in message
        # Пустой совет склеился бы в двойной пробел — проверяем построчно, чтобы переводы
        # строк между абзацами не считались за него.
        for line in message.splitlines():
            assert "  " not in line.strip(), f"двойной пробел в строке: {line!r}"

    def test_pathless_item_gets_applicable_advice(self):
        """«Перенесите файл» бесполезно там, где файла нет вовсе."""
        item = PathlessItem()
        with pytest.raises(pytest.UsageError) as exc:
            run_hook([item], markexpr="unit", deselect=[item])
        message = str(exc.value)
        assert "перенос не поможет" in message
        assert "перенесите его под backend/" not in message

    def test_gate_does_not_touch_markable_items(self):
        """Размеченный тест выпадает из отбора штатно — это не повод рвать сбор."""
        item = make_item("tests/integration/test_x.py")
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            run_hook([item], markexpr="unit", deselect=[item])
        assert item.added == ["integration"]
        assert unmarked_warnings(record) == []

    def test_unmapped_error_fires_before_selection(self):
        """Сторож для путей внутри `backend/` срабатывает до отбора и не зависит от `-m`."""
        inside = make_item("tests/smoke/test_x.py")
        with pytest.raises(pytest.UsageError) as exc:
            run_hook([inside], markexpr="unit")
        assert "tests/smoke/test_x.py" in str(exc.value)

    def test_unmapped_guard_still_reports_unmarkable_items(self):
        """Обрыв сбора не должен унести с собой перечень неразмечаемых тестов."""
        outside = outside_item("test_out.py")
        inside = make_item("tests/smoke/test_x.py")
        with pytest.warns(root_conftest.UnmarkedTestWarning) as record:
            with pytest.raises(pytest.UsageError) as exc:
                run_hook([outside, inside], markexpr="unit")
        assert "tests/smoke/test_x.py" in str(exc.value)
        assert str(outside.path) in str(unmarked_warnings(record)[0].message)

    def test_unmapped_guard_survives_a_failing_inner_hook(self):
        """Сторож обязан сработать раньше, чем упадёт что-то ниже по цепочке.

        Регрессионный сторож: пока проверка `unmapped` стояла после `yield`, исключение из
        нижележащего хука (битое выражение `-m "unit and"`, падение чужого плагина) отменяло её
        целиком — про непокрытый каталог разработчик не узнавал вовсе. Документация при этом
        обещает, что этот сторож срабатывает всегда.
        """
        inside = make_item("tests/smoke/test_x.py")
        with pytest.raises(pytest.UsageError) as exc:
            run_hook([inside], markexpr="unit", inner_error=RuntimeError("чужой плагин упал"))
        assert "tests/smoke/test_x.py" in str(exc.value)


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

    @pytest.mark.parametrize("ini_relative", INI_FILES)
    def test_no_addopts_in_ini(self, ini_relative):
        """`addopts` не должен появиться ни в одном из двух конфигов.

        Гейт включается только там, где идёт отбор по маркеру. Строка вида
        `addopts = -m "not slow"` подмешала бы отбор в каждый прогон — включая `make test`
        и `make test-fast`, которые идут без `-m` намеренно, — и мягкий режим исчез бы
        бесшумно, без единого падения, которое на это указало бы.
        """
        path = root_conftest.BACKEND_ROOT / ini_relative
        parser = configparser.ConfigParser()
        if not parser.read(path, encoding="utf-8"):
            pytest.skip(f"{ini_relative} недоступен в этом окружении (вне смонтированного backend/)")
        assert not parser.has_option(
            "pytest", "addopts"
        ), f"{ini_relative}: появился addopts — убедитесь, что он не подмешивает -m"

    def test_no_pytest_addopts_in_pyproject(self):
        """`pyproject.toml` — второй легальный дом для `addopts`, и он тоже должен быть пуст.

        Сторож по `pytest.ini` его не видит: секции `[tool.pytest.ini_options]` там сейчас нет,
        но появиться она может в любой момент, и `-m` из неё подмешался бы в каждый прогон.
        """
        text = (root_conftest.BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        if "[tool.pytest.ini_options]" not in text:
            return
        section = text.split("[tool.pytest.ini_options]", 1)[1].split("\n[", 1)[0]
        assert "addopts" not in section, "в pyproject.toml появился addopts — проверьте, нет ли в нём -m"

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


class TestRealRun:
    """Настоящий прогон pytest подпроцессом — то, что подставным config проверить нельзя.

    Здесь и только здесь проверяются: реальный порядок обёртки относительно деселекта в
    `_pytest.mark`, ненулевой код возврата и то, что ошибку не глушат флаги подавления
    предупреждений. Всё это — утверждения о поведении самого pytest, а не о нашей логике,
    и на подставных объектах они держались бы на честном слове.

    Прогоны стоят несколько секунд каждый. Маркер `slow` намеренно не ставится: тесты
    детерминированы и ничего не меряют по времени, а `slow` вывел бы их из PR-гейтов.
    """

    # Быстрый узел внутри `backend/`. Он обязателен: без единого внутреннего пути rootdir
    # оказывается другим, корневой conftest не подхватывается, и проверять было бы нечего.
    INSIDE_NODE = "tests/unit/test_pytest_marker_autotagging.py::TestMarkerForPath::test_empty_path_returns_none"

    def _run(self, tmp_path, *args):
        """Прогон pytest на внешнем файле вместе с внутренним узлом. `tmp_path` вне `backend/`.

        Окружение чистится намеренно: `PYTEST_ADDOPTS` подмешал бы `-m` во вложенный прогон и
        покрасил бы тест от конфигурации, а не от дефекта; `COV_*` заставили бы вложенный pytest
        писать свои `.coverage.*` в смонтированный `backend/`, и они попали бы в `combine`
        внешнего прогона, который считает порог покрытия.
        """
        external = tmp_path / "test_outside_tree.py"
        external.write_text("def test_outside():\n    pass\n", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTEST_", "COV_"))}
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args, str(external), self.INSIDE_NODE],
            cwd=root_conftest.BACKEND_ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )

    def test_inside_node_exists(self):
        """Сторож связки: `INSIDE_NODE` — жёстко зашитый nodeid, и его переименование должно
        падать понятной ошибкой здесь, а не тремя «no tests ran» ниже."""
        class_name, method = self.INSIDE_NODE.rsplit("::", 2)[-2:]
        assert hasattr(globals()[class_name], method), f"узел {self.INSIDE_NODE} больше не существует"

    def test_gate_fails_the_run_despite_warning_suppression(self, tmp_path):
        """Положительное выражение: тест выпал → прогон обязан покраснеть, что бы ни глушили."""
        result = self._run(tmp_path, "-m", "unit", "--disable-warnings", "-p", "no:warnings")
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "отбором текущего прогона отброшены" in output, output

    def test_negative_expression_keeps_the_run_green(self, tmp_path):
        """Отрицательное выражение: тест исполняется → прогон зелёный.

        Регрессионный сторож против первой реализации гейта, которая рвала сбор на любом
        непустом `-m` и тем самым ломала три из четырёх прогонов CI.
        """
        result = self._run(tmp_path, "-m", "not performance and not slow")
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        # Ноль сам по себе получился бы и если бы внешний тест перестал собираться,
        # поэтому проверяем, что исполнились оба.
        assert "2 passed" in output, output

    def test_no_markexpr_keeps_the_run_green(self, tmp_path):
        """Без `-m` поведение прежнее: предупреждение, сбор продолжается."""
        result = self._run(tmp_path)
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "2 passed" in output, output
        assert "UnmarkedTestWarning" in output, output
