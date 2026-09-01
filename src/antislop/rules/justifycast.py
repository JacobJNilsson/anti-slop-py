"""Rule P01 justifycast (AS101).

cast() is a no-op at runtime. It tells the checker to believe the
author without evidence. The author states the invariant in a comment
directly above the statement, or narrows with a checked construct.
A chained cast fabricates evidence twice and no comment justifies it.
See docs/spec/001-overview.md, rule P01.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.annotations import TYPING_MODULES, dotted_name, typing_aliases
from antislop.engine import Context
from antislop.nodes import direct_expressions

MESSAGE = (
    "cast() has no justification comment. State the invariant in a comment "
    "directly above it, or narrow with a checked construct such as isinstance."
)
CHAIN_MESSAGE = (
    "chained cast() fabricates evidence twice. Remove the inner cast and "
    "narrow with a checked construct."
)


class JustifyCast:
    code = "AS101"
    name = "justifycast"
    default_on = True

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        names = _cast_aliases(ctx.tree)
        modules = typing_aliases(ctx.tree)
        for statement in ast.walk(ctx.tree):
            if not isinstance(statement, ast.stmt):
                continue
            calls = [
                node
                for node in direct_expressions(statement)
                if isinstance(node, ast.Call) and _is_cast(node, names, modules)
            ]
            inner = [
                call.args[1] for call in calls if _is_chained(call, names, modules)
            ]
            for node in calls:
                if any(node is item for item in inner):
                    # The report of the outer cast covers the chain, so
                    # one chain gets one report.
                    continue
                if _is_chained(node, names, modules):
                    yield node, CHAIN_MESSAGE
                    continue
                if ctx.justified({node.lineno, statement.lineno}):
                    continue
                yield node, MESSAGE


def _cast_aliases(tree: ast.Module) -> set[str]:
    """Collect the local names that a from import binds to typing.cast."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in TYPING_MODULES:
            names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "cast"
            )
    return names


def _is_cast(node: ast.AST, names: set[str], modules: frozenset[str]) -> bool:
    """Report whether a node calls typing.cast, under any name it has here."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in names
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "cast"
        and dotted_name(func.value) in modules
    )


def _is_chained(call: ast.Call, names: set[str], modules: frozenset[str]) -> bool:
    """Report whether the value argument of a cast is itself a cast."""
    if len(call.args) < 2:
        return False
    return _is_cast(call.args[1], names, modules)
