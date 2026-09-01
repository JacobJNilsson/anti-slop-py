"""Tests of rule P04 noanyreturn, from docs/spec/001-overview.md."""

from helpers import run


def test_any_return_reports() -> None:
    source = """
    from typing import Any

    def load() -> Any:
        return 1
    """
    assert run(source, "noanyreturn") == ["4:AS104"]


def test_object_return_reports() -> None:
    source = """
    def load() -> object:
        return 1
    """
    assert run(source, "noanyreturn") == ["2:AS104"]


def test_attribute_form_reports() -> None:
    source = """
    import typing

    async def load() -> typing.Any:
        return 1
    """
    assert run(source, "noanyreturn") == ["4:AS104"]


def test_aliased_import_reports() -> None:
    source = """
    from typing import Any as Whatever

    def load() -> Whatever:
        return 1
    """
    assert run(source, "noanyreturn") == ["4:AS104"]


def test_module_alias_reports() -> None:
    source = """
    from typing import Any

    Result = Any

    def load() -> Result:
        return 1
    """
    assert run(source, "noanyreturn") == ["6:AS104"]


def test_concrete_and_typevar_returns_stay_clean() -> None:
    source = """
    from typing import TypeVar

    T = TypeVar("T")

    def first(values: list[T]) -> T:
        return values[0]

    def count() -> int:
        return 1
    """
    assert run(source, "noanyreturn") == []


def test_missing_annotation_stays_clean() -> None:
    source = """
    def load():
        return 1
    """
    assert run(source, "noanyreturn") == []


def test_comment_above_def_justifies() -> None:
    source = """
    from typing import Any

    # The plugin API fixes this signature.
    def load() -> Any:
        return 1
    """
    assert run(source, "noanyreturn") == []


def test_comment_above_decorator_justifies() -> None:
    source = """
    from typing import Any


    # The plugin API fixes this signature.
    @staticmethod
    def load() -> Any:
        return 1
    """
    assert run(source, "noanyreturn") == []


def test_method_return_reports() -> None:
    source = """
    from typing import Any


    class Store:
        def read(self) -> Any:
            return 1
    """
    assert run(source, "noanyreturn") == ["6:AS104"]
