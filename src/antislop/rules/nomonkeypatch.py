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
from antislop.nodes import assigned_targets, direct_expressions, root_name

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
        isinstance(target, ast.Attribute) and root_name(target) in imported
        for target in assigned_targets(statement)
    )


def _setattr_calls(statement: ast.stmt, imported: set[str]) -> Iterator[ast.Call]:
    """Yield the setattr calls of one statement that patch an import."""
    for node in direct_expressions(statement):
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
    return root_name(call.args[0]) in imported
