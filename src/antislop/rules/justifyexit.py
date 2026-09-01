"""Rule P09 justifyexit (AS109).

sys.exit(), os._exit(), and a raised SystemExit outside an entry point
stop the process of another program. The author states why the process
cannot continue, in a comment directly above the statement, or raises
an ordinary exception. See docs/spec/001-overview.md, rule P09.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from fnmatch import fnmatchcase

from antislop.engine import Context

MESSAGE = (
    "this exit stops the process of the caller. State why the process cannot "
    "continue in a comment directly above it, or raise an ordinary exception."
)
DEFAULT_ENTRY_DECORATORS = ("click.*", "typer.*", "*.command", "*.group")
_EXIT_FUNCTIONS = {("sys", "exit"), ("os", "_exit")}


class JustifyExit:
    code = "AS109"
    name = "justifyexit"
    default_on = False

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        if ctx.is_test:
            return
        patterns = _entry_decorators(ctx.settings)
        modules, exits = _exit_names(ctx.tree)
        for statement, exempt in _scan(ctx.tree.body, False, patterns):
            if exempt:
                continue
            for node in _exit_nodes(statement, modules, exits):
                if ctx.justified({node.lineno, statement.lineno}):
                    continue
                yield node, MESSAGE


# The settings hold raw pyproject data.
def _entry_decorators(settings: dict[str, object]) -> tuple[str, ...]:
    """Read the decorator patterns that mark an entry point."""
    configured = settings.get("entry-decorators")
    if not isinstance(configured, list):
        return DEFAULT_ENTRY_DECORATORS
    return tuple(item for item in configured if isinstance(item, str))


def _exit_names(tree: ast.Module) -> tuple[dict[str, str], set[str]]:
    """Collect the local names that mean an exit call.

    The first result maps a local module name to sys or os. The second
    holds the local names bound by a from-import of an exit function.
    """
    modules: dict[str, str] = {}
    exits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"sys", "os"}:
                    modules[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if (node.module, alias.name) in _EXIT_FUNCTIONS:
                    exits.add(alias.asname or alias.name)
    return modules, exits


def _scan(
    body: list[ast.stmt], exempt: bool, patterns: tuple[str, ...]
) -> Iterator[tuple[ast.stmt, bool]]:
    """Yield every statement of a body with the exempt state around it."""
    for statement in body:
        yield statement, exempt
        inner = exempt
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
            inner = exempt or _is_entry_point(statement, patterns)
        main_block = isinstance(statement, ast.If) and _is_main_test(statement.test)
        for field, value in ast.iter_fields(statement):
            if not isinstance(value, list):
                continue
            nested = [item for item in value if isinstance(item, ast.stmt)]
            if not nested:
                continue
            entry = inner or (main_block and field == "body")
            yield from _scan(nested, entry, patterns)


def _is_entry_point(
    function: ast.FunctionDef | ast.AsyncFunctionDef, patterns: tuple[str, ...]
) -> bool:
    """Report whether a function is an entry point by name or decorator."""
    if function.name == "main":
        return True
    return any(
        any(fnmatchcase(name, pattern) for pattern in patterns)
        for name in map(_decorator_name, function.decorator_list)
        if name
    )


def _decorator_name(decorator: ast.expr) -> str | None:
    """Return the dotted name of a decorator, with any call stripped."""
    node = decorator.func if isinstance(decorator, ast.Call) else decorator
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _is_main_test(test: ast.expr) -> bool:
    """Report whether a test reads as __name__ == "__main__"."""
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    left, right = test.left, test.comparators[0]
    pair = {_literal(left), _literal(right)}
    return pair == {"__name__", "__main__"}


def _literal(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _exit_nodes(
    statement: ast.stmt, modules: dict[str, str], exits: set[str]
) -> Iterator[ast.stmt | ast.Call]:
    """Yield the exits of one statement, not those of nested statements."""
    if isinstance(statement, ast.Raise) and _raises_system_exit(statement):
        yield statement
        return
    for child in ast.iter_child_nodes(statement):
        if not isinstance(child, ast.expr):
            continue
        for node in ast.walk(child):
            if isinstance(node, ast.Call) and _is_exit_call(node, modules, exits):
                yield node


def _raises_system_exit(statement: ast.Raise) -> bool:
    node = statement.exc
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        return node.attr == "SystemExit"
    return isinstance(node, ast.Name) and node.id == "SystemExit"


def _is_exit_call(call: ast.Call, modules: dict[str, str], exits: set[str]) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id in exits
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and (modules.get(func.value.id), func.attr) in _EXIT_FUNCTIONS
    )
