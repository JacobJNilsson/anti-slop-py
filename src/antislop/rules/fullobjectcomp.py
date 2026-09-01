"""Rule P12 fullobjectcomp (AS112).

A test that asserts attribute after attribute of one object states no
claim about the rest of the value. The test must compare the whole
object against an expected instance. The rule counts the per-attribute
assertions on one subject in one function and reports above a
threshold. Test files only. See docs/spec/001-overview.md, rule P12.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.engine import Context
from antislop.nodes import functions, root_name, statements

MESSAGE = (
    "the test asserts one attribute after another and claims nothing about the "
    "rest of the object. Compare the whole object against an expected value."
)
DEFAULT_THRESHOLD = 3
_EQUAL_ASSERTIONS = {"assertEqual", "assertEquals"}


class FullObjectComp:
    code = "AS112"
    name = "fullobjectcomp"
    default_on = False

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        if not ctx.is_test:
            return
        threshold = _threshold(ctx.settings)
        for function in functions(ctx.tree):
            counted: dict[str, list[ast.stmt]] = {}
            for statement in statements(function.body):
                subject = _subject(statement)
                if subject is not None:
                    counted.setdefault(subject, []).append(statement)
            for group in counted.values():
                if len(group) >= threshold:
                    yield group[0], MESSAGE


# The settings hold raw pyproject data.
def _threshold(settings: dict[str, object]) -> int:
    """Read the count of per-attribute assertions that the rule allows."""
    configured = settings.get("threshold")
    if isinstance(configured, int) and not isinstance(configured, bool):
        return configured
    return DEFAULT_THRESHOLD


def _subject(statement: ast.stmt) -> str | None:
    """Return the name that a per-attribute equality assertion reads."""
    if isinstance(statement, ast.Assert):
        return _compared_attribute(statement.test)
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return _asserted_attribute(statement.value)
    return None


def _compared_attribute(test: ast.expr) -> str | None:
    """Return the root name of an `a.x == value` comparison."""
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return None
    if not isinstance(test.ops[0], ast.Eq):
        return None
    return _attribute_root(test.left)


def _asserted_attribute(call: ast.Call) -> str | None:
    """Return the root name of an assertEqual(a.x, value) call."""
    name = call.func.attr if isinstance(call.func, ast.Attribute) else None
    if isinstance(call.func, ast.Name):
        name = call.func.id
    if name not in _EQUAL_ASSERTIONS or not call.args:
        return None
    return _attribute_root(call.args[0])


def _attribute_root(node: ast.expr) -> str | None:
    """Return the base name of an attribute chain, and None for a plain name."""
    if not isinstance(node, ast.Attribute):
        return None
    return root_name(node)
