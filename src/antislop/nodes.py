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
        yield from _nested_statements(statement)


def _nested_statements(node: ast.AST) -> Iterator[ast.stmt]:
    """Yield the statements under one node, without nested scopes."""
    for child in ast.iter_child_nodes(node):
        match child:
            case ast.stmt():
                yield from statements([child])
            case ast.expr():
                continue
            case _:
                # An except handler and a match case hold statements,
                # but neither one is a statement.
                yield from _nested_statements(child)


def direct_expressions(statement: ast.stmt) -> Iterator[ast.expr]:
    """Yield the expressions of one statement, not those of a nested one."""
    for child in ast.iter_child_nodes(statement):
        if isinstance(child, ast.stmt):
            continue
        if isinstance(child, ast.expr):
            yield from _expressions(child)
            continue
        # A with item, an except handler, and a match case hold the
        # expressions of the header of the statement.
        for inner in ast.iter_child_nodes(child):
            if isinstance(inner, ast.expr):
                yield from _expressions(inner)


def _expressions(node: ast.expr) -> Iterator[ast.expr]:
    """Yield one expression and every expression under it."""
    for found in ast.walk(node):
        if isinstance(found, ast.expr):
            yield found


def assigned_targets(node: ast.AST) -> list[ast.expr]:
    """Return what one assignment statement writes to.

    An unpacking target holds the names it writes to, so the result
    flattens a tuple, a list, and a starred target.
    """
    if isinstance(node, ast.Assign):
        return _flatten(node.targets)
    if isinstance(node, ast.AnnAssign | ast.AugAssign):
        return _flatten([node.target])
    return []


def _flatten(targets: list[ast.expr]) -> list[ast.expr]:
    """Return the targets of an assignment, unpacked ones included."""
    found: list[ast.expr] = []
    for target in targets:
        match target:
            case ast.Tuple() | ast.List():
                found.extend(_flatten(list(target.elts)))
            case ast.Starred():
                found.extend(_flatten([target.value]))
            case _:
                found.append(target)
    return found


def root_name(node: ast.expr) -> str | None:
    """Return the name at the root of an attribute path."""
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None
