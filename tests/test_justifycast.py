"""Tests of rule P01 justifycast, from docs/spec/001-overview.md."""

from helpers import run


def test_bare_cast_reports() -> None:
    source = """
    from typing import cast

    def load(raw: object) -> int:
        return cast(int, raw)
    """
    assert run(source, "justifycast") == ["5:AS101"]


def test_comment_above_justifies() -> None:
    source = """
    from typing import cast

    def load(raw: object) -> int:
        # The store only holds int values.
        return cast(int, raw)
    """
    assert run(source, "justifycast") == []


def test_comment_block_above_justifies() -> None:
    source = """
    from typing import cast

    def load(raw: object) -> int:
        # The store only holds int values,
        # and the loader checked the payload.
        return cast(int, raw)
    """
    assert run(source, "justifycast") == []


def test_trailing_comment_justifies_nothing() -> None:
    source = """
    from typing import cast

    def load(raw: object) -> int:
        return cast(int, raw)  # The store only holds int values.
    """
    assert run(source, "justifycast") == ["5:AS101"]


def test_chained_cast_reports_with_comment() -> None:
    source = """
    from typing import cast

    def load(raw: object) -> int:
        # A comment does not justify a chain.
        return cast(int, cast(object, raw))
    """
    assert run(source, "justifycast") == ["6:AS101"]


def test_aliased_import_reports() -> None:
    source = """
    from typing import cast as trustme

    def load(raw: object) -> int:
        return trustme(int, raw)
    """
    assert run(source, "justifycast") == ["5:AS101"]


def test_attribute_call_reports() -> None:
    source = """
    import typing

    def load(raw: object) -> int:
        return typing.cast(int, raw)
    """
    assert run(source, "justifycast") == ["5:AS101"]


def test_other_cast_functions_stay_clean() -> None:
    source = """
    def cast(mold: str) -> str:
        return mold

    def make() -> str:
        return cast("bronze")
    """
    assert run(source, "justifycast") == []


def test_comment_above_multiline_statement_justifies() -> None:
    source = """
    from typing import cast

    def load(raw: object) -> int:
        # The store only holds int values.
        value = cast(
            int,
            raw,
        )
        return value
    """
    assert run(source, "justifycast") == []


def test_cast_in_a_with_header_reports() -> None:
    source = """
    from typing import cast

    def load(raw: object) -> bytes:
        with open(cast(str, raw)) as handle:
            return handle.read()
    """
    assert run(source, "justifycast") == ["5:AS101"]


def test_chained_cast_reports_once() -> None:
    source = """
    from typing import cast

    def load(raw: object) -> int:
        return cast(int, cast(object, raw))
    """
    assert run(source, "justifycast") == ["5:AS101"]
