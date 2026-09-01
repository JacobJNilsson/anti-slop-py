"""Rule P06 noadhocisinstance (AS106).

An if/elif chain of isinstance tests re-parses a value away from its
boundary, and every new case grows the burden of the reader. The rule
flags a chain with two or more isinstance tests on one name. A match
statement is the fix, so the rule leaves it alone. The boundary-modules
setting exempts a decode module. See docs/spec/001-overview.md, P06.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.boundary import at_boundary
from antislop.engine import Context

MESSAGE = (
    "the if chain dispatches on isinstance twice for one value. Branch on a "
    "domain value, a match on a sealed union, or functools.singledispatch."
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
            if _dispatches(node):
                yield node, MESSAGE


def _chain_tails(tree: ast.Module) -> set[ast.If]:
    """Collect the if statements that continue another chain."""
    tails: set[ast.If] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            following = _next_branch(node)
            if following is not None:
                tails.add(following)
    return tails


def _dispatches(head: ast.If) -> bool:
    """Report whether one chain tests isinstance twice on one name."""
    counts: dict[str, int] = {}
    for test in _chain_tests(head):
        name = _isinstance_name(test)
        if name is not None:
            counts[name] = counts.get(name, 0) + 1
    return any(count >= 2 for count in counts.values())


def _chain_tests(head: ast.If) -> Iterator[ast.expr]:
    """Yield the test of every branch of one if/elif chain."""
    current: ast.If | None = head
    while current is not None:
        yield current.test
        current = _next_branch(current)


def _next_branch(node: ast.If) -> ast.If | None:
    """Return the next branch of the chain, or None at the end."""
    following = node.orelse
    if len(following) == 1 and isinstance(following[0], ast.If):
        return following[0]
    return None


def _isinstance_name(test: ast.expr) -> str | None:
    """Return the name that one branch tests with isinstance."""
    if not isinstance(test, ast.Call):
        return None
    if not isinstance(test.func, ast.Name) or test.func.id != "isinstance":
        return None
    if not test.args:
        return None
    subject = test.args[0]
    if isinstance(subject, ast.Name):
        return subject.id
    return None
