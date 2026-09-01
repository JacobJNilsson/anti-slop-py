"""Rule P10 justifyswallow (AS110).

An except handler that swallows hides a failure and returns a guess.
The author states why ignoring the error is correct, in a comment
directly above the handler or first in its body. The rule fires on any
exception type. See docs/spec/001-overview.md, rule P10.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.engine import Context

MESSAGE = (
    "the except handler discards the error. State why that is correct in a "
    "comment above the handler or first in its body, or handle the error."
)


class JustifySwallow:
    code = "AS110"
    name = "justifyswallow"
    default_on = True

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if not _swallows(node.body):
                continue
            if ctx.justified({node.lineno}):
                continue
            first = node.body[0]
            comment_inside = first.lineno - 1 > node.lineno and ctx.justified(
                {first.lineno}
            )
            if comment_inside:
                continue
            yield node, MESSAGE


def _swallows(body: list[ast.stmt]) -> bool:
    """Report whether a handler body discards the error."""
    return all(_discards(statement) for statement in body)


def _discards(statement: ast.stmt) -> bool:
    if isinstance(statement, ast.Pass | ast.Continue | ast.Break):
        return True
    if isinstance(statement, ast.Expr):
        return isinstance(statement.value, ast.Constant)
    if isinstance(statement, ast.Return):
        return statement.value is None or _is_constant(statement.value)
    return False


def _is_constant(value: ast.expr) -> bool:
    """Report whether an expression is a literal guess, not computed data."""
    if isinstance(value, ast.Constant):
        return True
    if isinstance(value, ast.UnaryOp):
        return _is_constant(value.operand)
    if isinstance(value, ast.Dict):
        return not value.keys
    if isinstance(value, ast.List | ast.Tuple | ast.Set):
        return not value.elts
    if isinstance(value, ast.Call):
        # dict(), list(), set(), and tuple() with no arguments are the
        # spelled forms of the empty literals.
        return (
            isinstance(value.func, ast.Name)
            and value.func.id in {"dict", "list", "set", "tuple"}
            and not value.args
            and not value.keywords
        )
    return False
