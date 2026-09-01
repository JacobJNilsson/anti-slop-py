"""Tree walks that more than one rule needs.

Several rules ask the same questions of one tree. Which functions does
this file define? Which statements does one function body hold, without
the bodies of a nested scope? Which expressions belong to one
statement, and not to a statement inside it? What does an assignment
write to, and which name sits at the root of an attribute path? This
module answers each question once.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator


def functions(tree: ast.Module) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Yield every function of one file, the nested ones included."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node


def statements(body: list[ast.stmt]) -> Iterator[ast.stmt]:
    """Yield the statements of one function body, without nested scopes."""
    for statement in body:
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        yield statement
        for child in ast.iter_child_nodes(statement):
            if isinstance(child, ast.stmt):
                yield from statements([child])


def direct_expressions(statement: ast.stmt) -> Iterator[ast.expr]:
    """Yield the expressions of one statement, not those of a nested one."""
    for child in ast.iter_child_nodes(statement):
        if not isinstance(child, ast.expr):
            continue
        for node in ast.walk(child):
            if isinstance(node, ast.expr):
                yield node


def assigned_targets(node: ast.AST) -> list[ast.expr]:
    """Return what one assignment statement writes to."""
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, ast.AnnAssign | ast.AugAssign):
        return [node.target]
    return []


def root_name(node: ast.expr) -> str | None:
    """Return the name at the root of an attribute path."""
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None
