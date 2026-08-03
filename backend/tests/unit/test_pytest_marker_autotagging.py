"""
Тесты правила автоматической разметки pytest-маркеров по каталогу.

Проверяется чистая функция `marker_for_path` из корневого `backend/conftest.py` —
без сбора тестов и без Django. Полный сбор пакета занимает ~7,5 минут, поэтому
регрессию правила ловим здесь, а не прогоном.

Сам файл маркера не имеет намеренно: он лежит в `tests/unit/` и получает `unit`
автоматически — ровно тем механизмом, который проверяет.
"""

from pathlib import Path

import pytest

import conftest as root_conftest

marker_for_path = root_conftest.marker_for_path


class TestMarkerForPath:
    """Каждое правило таблицы PATH_RULES."""

    @pytest.mark.parametrize(
        "rel_path,expected",
        [
            # tests/* — по одному представителю на каталог
            ("tests/unit/test_models/test_product_models.py", "unit"),
            ("tests/integration/test_product_detail_api.py", "integration"),
            ("tests/functional/test_checkout_flow.py", "integration"),
            ("tests/regression/test_epic_28_intact.py", "integration"),
            ("tests/performance/test_search_performance.py", "performance"),
            # apps/* — общее правило
            ("apps/products/tests/test_models.py", "unit"),
            ("apps/banners/tests/test_views.py", "unit"),
            # Django-style: собирается по шаблону `tests.py`, лежит не в `apps/*/tests/`
            ("apps/pages/tests.py", "unit"),
            # Специфичное правило: вложенный integration внутри apps
            ("apps/products/tests/integration/test_import_orchestration.py", "integration"),
        ],
    )
    def test_known_paths_get_expected_marker(self, rel_path, expected):
        assert marker_for_path(Path(rel_path).parts) == expected

    def test_specific_apps_rule_wins_over_generic(self):
        """`apps/*/tests/integration/` не должен схлопываться в `unit` по общему правилу `apps/`."""
        nested = marker_for_path(Path("apps/products/tests/integration/test_x.py").parts)
        flat = marker_for_path(Path("apps/products/tests/test_x.py").parts)
        assert nested == "integration"
        assert flat == "unit"

    def test_wildcard_matches_any_single_segment(self):
        """Сегмент `*` в шаблоне совпадает с именем любого приложения."""
        for app in ("products", "orders", "какое-угодно-новое"):
            parts = Path(f"apps/{app}/tests/integration/test_x.py").parts
            assert marker_for_path(parts) == "integration"

    @pytest.mark.parametrize(
        "rel_path",
        [
            "tests/smoke/test_x.py",  # новый каталог, правила ещё нет
            "tests/test_orphan.py",  # тест прямо в корне tests/
            "scripts/test_helper.py",  # вне apps/ и tests/
            "test_toplevel.py",  # в корне backend/
        ],
    )
    def test_unmapped_paths_return_none(self, rel_path):
        assert marker_for_path(Path(rel_path).parts) is None

    def test_empty_path_returns_none(self):
        assert marker_for_path(()) is None

    def test_bare_directory_does_not_match_deeper_rule(self):
        """`tests` без второго сегмента не должен совпасть с `("tests", "unit")`."""
        assert marker_for_path(("tests",)) is None


class TestRulesTable:
    """Инварианты самой таблицы, которые легко нарушить при правке."""

    def test_all_markers_are_declared_in_pytest_ini(self):
        """Каждый автоматический маркер объявлен в pytest.ini — иначе PytestUnknownMarkWarning."""
        pytest_ini = (root_conftest.BACKEND_ROOT / "pytest.ini").read_text(encoding="utf-8")
        for marker in root_conftest.AUTO_MARKERS:
            assert f"{marker}:" in pytest_ini, f"маркер {marker} не объявлен в pytest.ini"

    def test_rules_produce_only_known_markers(self):
        produced = {marker for _, marker in root_conftest.PATH_RULES}
        assert produced <= set(root_conftest.AUTO_MARKERS)

    def test_generic_apps_rule_is_last(self):
        """Общее правило `apps/` должно стоять после всех специфичных, иначе они мертвы."""
        patterns = [pattern for pattern, _ in root_conftest.PATH_RULES]
        assert patterns.index(("apps",)) == len(patterns) - 1
