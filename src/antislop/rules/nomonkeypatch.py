"""Rule P08 nomonkeypatch (AS108).

Production code must not assign attributes onto an imported module,
class, or object. The mutation is invisible at the call site and it
depends on the import order. The rule reads the imports of the file to
know the names. A test file is exempt, because mock.patch and pytest
monkeypatch restore the state. A compatibility shim for a known
upstream bug earns a justification comment directly above the
statement. See docs/spec/001-overview.md, rule P08.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.engine import Context

MESSAGE = (
    "the assignment patches an attribute of an imported module or class. "
    "Inject the dependency instead, or name the upstream bug in a comment above."
)
SETATTR_MESSAGE = (
    "setattr() patches an attribute of an imported module or class. "
    "Inject the dependency instead, or name the upstream bug in a comment above."
)


class NoMonkeyPatch:
    code = "AS108"
    name = "nomonkeypatch"
    default_on = True

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        if ctx.is_test:
            return
        imported = _imported_names(ctx.tree)
        if not imported:
            return
        for statement in ast.walk(ctx.tree):
            if not isinstance(statement, ast.stmt):
                continue
            if ctx.justified({statement.lineno}):
                continue
            if _patches_an_import(statement, imported):
                yield statement, MESSAGE
                continue
            for call in _setattr_calls(statement, imported):
                yield call, SETATTR_MESSAGE


def _imported_names(tree: ast.Module) -> set[str]:
    """Collect the local names that the imports of the file bind."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _patches_an_import(statement: ast.stmt, imported: set[str]) -> bool:
    """Report whether one statement writes to an attribute of an import."""
    return any(
        isinstance(target, ast.Attribute) and _root_name(target) in imported
        for target in _assigned_targets(statement)
    )


def _assigned_targets(statement: ast.stmt) -> list[ast.expr]:
    """Return what one assignment statement writes to."""
    if isinstance(statement, ast.Assign):
        return list(statement.targets)
    if isinstance(statement, ast.AnnAssign | ast.AugAssign):
        return [statement.target]
    return []


def _setattr_calls(statement: ast.stmt, imported: set[str]) -> Iterator[ast.Call]:
    """Yield the setattr calls of one statement that patch an import."""
    for child in ast.iter_child_nodes(statement):
        if not isinstance(child, ast.expr):
            continue
        for node in ast.walk(child):
            if isinstance(node, ast.Call) and _patches_by_setattr(node, imported):
                yield node


def _patches_by_setattr(call: ast.Call, imported: set[str]) -> bool:
    """Report whether one setattr call names an attribute of an import."""
    if not isinstance(call.func, ast.Name) or call.func.id != "setattr":
        return False
    if len(call.args) < 2:
        return False
    name = call.args[1]
    if not isinstance(name, ast.Constant) or not isinstance(name.value, str):
        # A computed name is reflection. Rule P07 owns it.
        return False
    return _root_name(call.args[0]) in imported


def _root_name(node: ast.expr) -> str | None:
    """Return the name at the root of an attribute path."""
    if isinstance(node, ast.Attribute):
        return _root_name(node.value)
    if isinstance(node, ast.Name):
        return node.id
    return None
