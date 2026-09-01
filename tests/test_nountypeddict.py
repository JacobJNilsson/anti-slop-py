"""Tests of rule P02 nountypeddict, from docs/spec/001-overview.md."""

from helpers import run


def test_any_valued_dict_parameter_reports() -> None:
    source = """
    from typing import Any

    def load(payload: dict[str, Any]) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["4:AS102"]


def test_object_valued_dict_return_reports() -> None:
    source = """
    def load() -> dict[str, object]:
        return {}
    """
    assert run(source, "nountypeddict") == ["2:AS102"]


def test_bare_dict_annotation_reports() -> None:
    source = """
    def load(payload: dict) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["2:AS102"]


def test_typing_dict_alias_import_reports() -> None:
    source = """
    from typing import Any, Dict

    def load(payload: Dict[str, Any]) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["4:AS102"]


def test_mapping_with_any_values_reports() -> None:
    source = """
    from collections.abc import Mapping
    from typing import Any

    def load(payload: Mapping[str, Any]) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["5:AS102"]


def test_class_attribute_and_dataclass_field_report() -> None:
    source = """
    from dataclasses import dataclass, field
    from typing import Any


    class Store:
        cache: dict[str, Any]


    @dataclass
    class Record:
        extra: dict[str, Any] = field(default_factory=dict)
    """
    assert run(source, "nountypeddict") == ["7:AS102", "12:AS102"]


def test_named_types_stay_clean() -> None:
    source = """
    from dataclasses import dataclass


    @dataclass
    class Payload:
        name: str


    def load(payload: Payload, counts: dict[str, int]) -> Payload:
        return payload
    """
    assert run(source, "nountypeddict") == []


def test_comment_above_def_justifies() -> None:
    source = """
    from typing import Any

    # The wire format has no fixed keys.
    def load(payload: dict[str, Any]) -> None:
        return None
    """
    assert run(source, "nountypeddict") == []


def test_comment_above_decorator_justifies() -> None:
    source = """
    from typing import Any


    # The wire format has no fixed keys.
    @staticmethod
    def load(payload: dict[str, Any]) -> None:
        return None
    """
    assert run(source, "nountypeddict") == []


def test_module_alias_reports() -> None:
    source = """
    from typing import Any

    Payload = dict[str, Any]

    def load(payload: Payload) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["6:AS102"]


def test_type_alias_annotation_reports() -> None:
    source = """
    from typing import Any, TypeAlias

    Payload: TypeAlias = dict[str, Any]

    def load(payload: Payload) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["6:AS102"]


def test_type_alias_statement_reports() -> None:
    source = """
    from typing import Any

    type Payload = dict[str, Any]

    def load(payload: Payload) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["6:AS102"]


def test_optional_untyped_dict_reports() -> None:
    source = """
    from typing import Any

    def load(payload: dict[str, Any] | None) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["4:AS102"]


def test_boundary_module_setting_exempts_the_file() -> None:
    source = """
    from typing import Any

    def decode(payload: dict[str, Any]) -> None:
        return None
    """
    settings: dict[str, object] = {"boundary-modules": ["*/codec.py"]}
    assert run(source, "nountypeddict", "app/codec.py", settings) == []
    assert run(source, "nountypeddict", "app/service.py", settings) == ["4:AS102"]


def test_string_annotation_reports() -> None:
    source = """
    from typing import Any

    def load(payload: "dict[str, Any]") -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["4:AS102"]


def test_dict_inside_a_generic_reports() -> None:
    source = """
    from typing import Any

    def load() -> list[dict[str, Any]]:
        return []
    """
    assert run(source, "nountypeddict") == ["4:AS102"]


def test_dict_of_dicts_reports() -> None:
    source = """
    from typing import Any

    def load(payload: dict[str, dict[str, Any]]) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["4:AS102"]


def test_mutable_mapping_with_any_values_reports() -> None:
    source = """
    from collections.abc import MutableMapping
    from typing import Any

    def load(payload: MutableMapping[str, Any]) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["5:AS102"]


def test_recursive_string_alias_stays_clean() -> None:
    source = """
    from typing import TypeAlias

    Json: TypeAlias = "dict[str, Json]"

    def load(payload: Json) -> None:
        return None
    """
    assert run(source, "nountypeddict") == []


def test_recursive_assigned_string_alias_stays_clean() -> None:
    source = """
    Json = "dict[str, Json]"

    def load(payload: Json) -> None:
        return None
    """
    assert run(source, "nountypeddict") == []


def test_recursive_alias_with_a_quoted_member_stays_clean() -> None:
    source = """
    Json = dict[str, "Json"]

    def load(payload: Json) -> None:
        return None
    """
    assert run(source, "nountypeddict") == []


def test_recursive_type_statement_stays_clean() -> None:
    source = """
    type Json = dict[str, Json]

    def load(payload: Json) -> None:
        return None
    """
    assert run(source, "nountypeddict") == []


def test_two_aliases_that_name_each_other_stay_clean() -> None:
    source = """
    A = "B"
    B = "A"

    def load(payload: A) -> None:
        return None
    """
    assert run(source, "nountypeddict") == []


def test_recursive_alias_still_resolves_its_untyped_member() -> None:
    source = """
    from typing import Any, TypeAlias

    Json: TypeAlias = "dict[str, Json] | dict[str, Any]"

    def load(payload: Json) -> None:
        return None
    """
    assert run(source, "nountypeddict") == ["6:AS102"]
