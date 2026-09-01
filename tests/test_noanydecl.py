"""Tests of rule P14 noanydecl, from docs/spec/001-overview.md."""

from helpers import run


def test_constructor_initializer_reports() -> None:
    source = """
    from typing import Any

    from myapp.config import Config

    settings: Any = Config()
    """
    assert run(source, "noanydecl") == ["6:AS114"]


def test_literal_initializer_reports() -> None:
    source = """
    limit: object = 5
    """
    assert run(source, "noanydecl") == ["2:AS114"]


def test_display_and_fstring_initializers_report() -> None:
    source = """
    from typing import Any

    names: Any = ["ada"]
    counts: Any = {"ada": 1}
    label: Any = f"{names}"
    """
    assert run(source, "noanydecl") == ["4:AS114", "5:AS114", "6:AS114"]


def test_class_and_function_scopes_report() -> None:
    source = """
    from typing import Any


    class Store:
        limit: Any = 5

        def load(self) -> int:
            value: Any = 5
            return value
    """
    assert run(source, "noanydecl") == ["6:AS114", "9:AS114"]


def test_module_alias_reports() -> None:
    source = """
    from typing import Any

    Wide = Any

    limit: Wide = 5
    """
    assert run(source, "noanydecl") == ["6:AS114"]


def test_opaque_call_stays_clean() -> None:
    source = """
    from typing import Any

    from myapp.plugins import load

    handler: Any = load()
    """
    assert run(source, "noanydecl") == []


def test_named_annotation_stays_clean() -> None:
    source = """
    limit: int = 5
    """
    assert run(source, "noanydecl") == []


def test_declaration_without_initializer_stays_clean() -> None:
    source = """
    from typing import Any

    limit: Any
    """
    assert run(source, "noanydecl") == []


def test_none_and_ellipsis_initializers_stay_clean() -> None:
    source = """
    from typing import Any

    cursor: Any = None
    marker: Any = ...
    """
    assert run(source, "noanydecl") == []


def test_comment_above_statement_justifies() -> None:
    source = """
    from typing import Any

    from myapp.config import Config

    # The plugin registry stores values of every plugin type.
    settings: Any = Config()
    """
    assert run(source, "noanydecl") == []
