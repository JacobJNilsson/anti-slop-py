"""Rule P06 noadhocisinstance (AS106).

An if/elif chain of isinstance tests re-parses a value away from its
boundary, and every new case grows the burden of the reader. The rule
flags a chain with two or more isinstance tests on one value. The value
is a name or an attribute path, because dispatch on node.value is a
common shape. The report sits on the first branch that tests
isinstance. A match statement is the fix, so the rule leaves it alone.
See docs/spec/001-overview.md, P06.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.annotations import dotted_name
from antislop.boundary import at_boundary
from antislop.engine import Context

MESSAGE = (
    "the if chain dispatches on isinstance twice for one value. Branch on a "
    "domain value, match a sealed union, or use functools.singledispatch."
)


class NoAdHocIsinstance:
    code = "AS106"
    name = "noadhocisinstance"
    default_on = True

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        if at_boundary(ctx):
            return
        tails = _chain_tails(ctx.tree)
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.If):
                continue
            if node in tails:
                # The head of the chain already carries the report.
                continue
            anchor = _anchor(node)
            if anchor is not None:
                yield anchor, MESSAGE


def _chain_tails(tree: ast.Module) -> set[ast.If]:
    """Collect the if statements that continue another chain."""
    tails: set[ast.If] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            following = _next_branch(node)
            if following is not None:
                tails.add(following)
    return tails


def _anchor(head: ast.If) -> ast.If | None:
    """Return the branch that carries the report of one chain.

    The chain dispatches when it tests isinstance twice on one value.
    The report sits on the first branch that tests isinstance, because
    the head of the chain may test something else.
    """
    counts: dict[str, int] = {}
    first: ast.If | None = None
    for branch in _chain_branches(head):
        names = set(_tested_names(branch.test))
        if names and first is None:
            first = branch
        for name in names:
            counts[name] = counts.get(name, 0) + 1
    if any(count >= 2 for count in counts.values()):
        return first
    return None


def _tested_names(test: ast.expr) -> Iterator[str]:
    """Yield the values that one branch tests with isinstance.

    A branch holds the call inside an and, an or, or a not, so the walk
    reads through those operators.
    """
    if isinstance(test, ast.BoolOp):
        for value in test.values:
            yield from _tested_names(value)
        return
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        yield from _tested_names(test.operand)
        return
    name = _isinstance_name(test)
    if name is not None:
        yield name


def _chain_branches(head: ast.If) -> Iterator[ast.If]:
    """Yield every branch of one if/elif chain."""
    current: ast.If | None = head
    while current is not None:
        yield current
        current = _next_branch(current)


def _next_branch(node: ast.If) -> ast.If | None:
    """Return the next branch of the chain, or None at the end."""
    following = node.orelse
    if len(following) == 1 and isinstance(following[0], ast.If):
        return following[0]
    return None


def _isinstance_name(test: ast.expr) -> str | None:
    """Return the value that one branch tests with isinstance.

    The value is the dotted path of a name or of an attribute chain.
    Two different paths of one object are two different values.
    """
    if not isinstance(test, ast.Call):
        return None
    if not isinstance(test.func, ast.Name) or test.func.id != "isinstance":
        return None
    if not test.args:
        return None
    return dotted_name(test.args[0])
