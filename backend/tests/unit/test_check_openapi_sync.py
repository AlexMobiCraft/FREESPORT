"""Тесты сверки контракта API с кодом (`manage.py check_openapi_sync`).

Проверяются чистые функции нормализации и сравнения, а также ранние отказы самой команды.
Генерация схемы здесь не запускается намеренно: она стоит секунды и уже покрыта тем, что
команда падает в CI при рассинхроне. Маркер `unit` проставляется автоматически по каталогу.
"""

import pytest
from django.core.management.base import CommandError

from apps.common.management.commands.check_openapi_sync import (
    Command,
    collect_differences,
    default_schema_path,
    normalize,
)


def differences(from_code, from_file):
    """Список расхождений, чтобы не разворачивать генератор в каждом тесте."""
    return list(collect_differences(normalize(from_code), normalize(from_file)))


class TestNormalize:
    """Приведение документа к виду, не зависящему от незначимого порядка."""

    @pytest.mark.parametrize("key", ["tags", "required", "enum"])
    def test_scalar_lists_are_sorted(self, key):
        assert normalize({key: ["b", "a", "c"]}) == {key: ["a", "b", "c"]}

    def test_other_scalar_lists_keep_order(self):
        """Порядок значим не везде: `servers` — упорядоченный список приоритета."""
        document = {"servers": ["https://b", "https://a"]}
        assert normalize(document) == document

    def test_parameters_sorted_by_location_and_name(self):
        document = {
            "parameters": [
                {"in": "query", "name": "page"},
                {"in": "path", "name": "id"},
                {"in": "query", "name": "limit"},
            ]
        }
        assert [p["name"] for p in normalize(document)["parameters"]] == ["id", "limit", "page"]

    def test_parameters_with_ref_do_not_break_sorting(self):
        """В списке параметров бывают `$ref` без `in`/`name` — сортировка обязана их пережить."""
        document = {"parameters": [{"$ref": "#/components/parameters/Page"}, {"in": "path", "name": "id"}]}
        assert len(normalize(document)["parameters"]) == 2

    def test_list_of_mappings_is_normalized_recursively(self):
        document = {"items": [{"tags": ["b", "a"]}]}
        assert normalize(document) == {"items": [{"tags": ["a", "b"]}]}

    def test_mixed_list_under_unordered_key_is_left_alone(self):
        """Сортировать список со словарями нечем — нормализация не должна падать."""
        document = {"tags": [{"name": "b"}, {"name": "a"}]}
        assert normalize(document) == document

    def test_scalars_pass_through(self):
        assert normalize("значение") == "значение"
        assert normalize(3) == 3
        assert normalize(None) is None


class TestCollectDifferences:
    """Поиск и именование расхождений."""

    def test_identical_documents_have_no_differences(self):
        document = {"paths": {"/health/": {"get": {"operationId": "health"}}}}
        assert differences(document, document) == []

    def test_http_method_order_inside_path_is_not_a_difference(self):
        """Ровно тот недетерминизм drf-spectacular, из-за которого нельзя сравнивать текст."""
        from_code = {"paths": {"/x/": {"get": {"id": 1}, "post": {"id": 2}}}}
        from_file = {"paths": {"/x/": {"post": {"id": 2}, "get": {"id": 1}}}}
        assert differences(from_code, from_file) == []

    def test_field_missing_in_file_is_named_by_full_path(self):
        from_code = {"components": {"schemas": {"ProductDetail": {"properties": {"opt4_price": {"type": "string"}}}}}}
        from_file = {"components": {"schemas": {"ProductDetail": {"properties": {}}}}}
        found = differences(from_code, from_file)
        assert len(found) == 1
        location, description = found[0]
        assert location == "components.schemas.ProductDetail.properties.opt4_price"
        assert "отсутствует в openapi.yaml" in description

    def test_field_missing_in_code_is_reported(self):
        found = differences({"paths": {}}, {"paths": {"/legacy/": {}}})
        assert found == [("paths./legacy/", "есть в openapi.yaml, отсутствует в коде")]

    def test_changed_scalar_is_reported_with_both_values(self):
        found = differences({"info": {"version": "2.0.0"}}, {"info": {"version": "1.0.0"}})
        assert len(found) == 1
        location, description = found[0]
        assert location == "info.version"
        assert "2.0.0" in description and "1.0.0" in description

    def test_list_length_mismatch_is_reported_once(self):
        found = differences({"servers": ["a", "b"]}, {"servers": ["a"]})
        assert len(found) == 1
        assert "разная длина списка" in found[0][1]

    def test_list_element_difference_is_indexed(self):
        found = differences({"servers": [{"url": "a"}]}, {"servers": [{"url": "b"}]})
        assert found[0][0] == "servers[0].url"

    def test_type_change_is_a_difference(self):
        found = differences({"x": {"a": 1}}, {"x": [1]})
        assert len(found) == 1

    def test_several_differences_are_all_collected(self):
        from_code = {"a": 1, "b": 2, "c": 3}
        from_file = {"a": 9, "b": 8, "c": 3}
        assert len(differences(from_code, from_file)) == 2


class TestCommandEarlyExits:
    """Отказы до генерации схемы — они должны быть внятными, а не traceback."""

    def test_missing_file_raises_command_error(self, tmp_path):
        missing = tmp_path / "нет-такого.yaml"
        with pytest.raises(CommandError) as exc:
            Command().handle(schema_file=str(missing))
        assert str(missing) in str(exc.value)
        assert "--schema-file" in str(exc.value)

    def test_non_mapping_yaml_raises_command_error(self, tmp_path):
        broken = tmp_path / "openapi.yaml"
        broken.write_text("- просто\n- список\n", encoding="utf-8")
        with pytest.raises(CommandError) as exc:
            Command().handle(schema_file=str(broken))
        assert "не является отображением YAML" in str(exc.value)

    def test_directory_instead_of_file_raises_command_error(self, tmp_path):
        with pytest.raises(CommandError):
            Command().handle(schema_file=str(tmp_path))


class TestDefaultSchemaPath:
    def test_points_at_repository_docs(self):
        path = default_schema_path()
        assert path.parts[-3:] == ("docs", "api", "openapi.yaml")
