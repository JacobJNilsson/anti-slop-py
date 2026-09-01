"""Tests of the engine, the comment index, and suppression."""

import textwrap
from pathlib import Path

from antislop.comments import index_comments
from antislop.engine import check_source, is_test_path
from antislop.rules import ALL_RULES


def test_syntax_error_gives_no_diagnostics() -> None:
    found = check_source("def broken(:", Path("app.py"), list(ALL_RULES), {})
    assert found == []


def test_own_line_comment_index() -> None:
    source = textwrap.dedent("""
    # own line
    x = 1  # trailing
    """)
    comments = index_comments(source)
    assert comments.justified({3}) is True
    assert comments.justified({4}) is False


def test_is_test_path() -> None:
    assert is_test_path(Path("tests/test_app.py")) is True
    assert is_test_path(Path("pkg/app_test.py")) is True
    assert is_test_path(Path("src/app.py")) is False


def test_rule_codes_are_unique() -> None:
    codes = [rule.code for rule in ALL_RULES]
    assert len(codes) == len(set(codes))


def test_is_test_path_covers_a_root_conftest() -> None:
    assert is_test_path(Path("conftest.py")) is True



