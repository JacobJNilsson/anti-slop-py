"""The rule engine.

The engine parses one file once, builds the comment index once, and
hands both to every enabled rule through a Context. A rule yields
diagnostics and touches no file itself.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from antislop.comments import CommentIndex, index_comments


@dataclass(frozen=True, order=True)
class Diagnostic:
    path: str
    line: int
    col: int
    code: str
    rule: str
    message: str

    def render(self) -> str:
        place = f"{self.path}:{self.line}:{self.col}"
        return f"{place}: {self.code} {self.rule}: {self.message}"


class Context:
    """What one rule may read about one file."""

    def __init__(
        self,
        path: str,
        tree: ast.Module,
        comments: CommentIndex,
        is_test: bool,
        settings: dict[str, object],
    ) -> None:
        self.path = path
        self.tree = tree
        self.comments = comments
        self.is_test = is_test
        self.settings = settings

    def justified(self, lines: set[int]) -> bool:
        """Report whether a justification comment sits directly above one of lines."""
        return self.comments.justified(lines)


class Rule(Protocol):
    code: str
    name: str
    default_on: bool

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        """Yield a flagged node and the message for it."""
        ...


def is_test_path(path: Path) -> bool:
    """Report whether a path is test code by pytest conventions."""
    name = path.name
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    if name == "conftest.py":
        # A conftest holds the sanctioned patching of a test suite.
        return True
    return any(part == "tests" for part in path.parts)


def check_source(
    source: str,
    path: Path,
    rules: Sequence[Rule],
    settings: dict[str, dict[str, object]],
) -> list[Diagnostic]:
    """Run every rule over one file and return the kept diagnostics."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # A file that does not parse is the interpreter's report to
        # make, not this linter's.
        return []
    comments = index_comments(source)
    is_test = is_test_path(path)
    found: list[Diagnostic] = []
    for rule in rules:
        ctx = Context(str(path), tree, comments, is_test, settings.get(rule.name, {}))
        for node, message in rule.check(ctx):
            line = getattr(node, "lineno", 1)
            col = getattr(node, "col_offset", 0)
            if comments.suppressed(line, rule.code):
                continue
            found.append(
                Diagnostic(str(path), line, col, rule.code, rule.name, message)
            )
    return sorted(found)
