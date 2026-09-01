"""Rule P07 noreflection (AS107).

Dynamic reflection erases every static guarantee. The rule flags
getattr, setattr, and delattr with a computed name, vars() calls,
globals() subscripts, and writes to __dict__.
See docs/spec/001-overview.md, rule P07.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.boundary import at_boundary
from antislop.engine import Context
from antislop.nodes import assigned_targets

_ATTRIBUTE_BUILTINS = frozenset({"getattr", "setattr", "delattr"})

DYNAMIC_MESSAGE = (
    "{name}() computes the attribute name and erases the static guarantees. "
    "Name the attribute directly, or decode the value into a named type."
)
VARS_MESSAGE = (
    "vars() opens the attribute dictionary and erases the static guarantees. "
    "Read the named attributes, or use dataclasses.asdict at the boundary."
)
GLOBALS_MESSAGE = (
    "the subscript reaches into the module namespace through globals(). "
    "Import the name, or hold the values in a dictionary that you own."
)
DICT_MESSAGE = (
    "the write to __dict__ bypasses the declared attributes. Assign the "
    "attribute directly, or decode the data into a named type."
)


class NoReflection:
    code = "AS107"
    name = "noreflection"
    default_on = True

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        if at_boundary(ctx):
            return
        for node in ast.walk(ctx.tree):
            message = _report(node)
            if message is not None:
                yield node, message


def _report(node: ast.AST) -> str | None:
    """Return the message for one node, or None when the node is clean."""
    if isinstance(node, ast.Call):
        return _call_report(node)
    if isinstance(node, ast.Subscript):
        return _subscript_report(node)
    return _write_report(node)


def _call_report(call: ast.Call) -> str | None:
    function = call.func
    if isinstance(function, ast.Attribute):
        if function.attr == "update" and _is_instance_dict(function.value):
            return DICT_MESSAGE
        return None
    if not isinstance(function, ast.Name):
        return None
    if function.id in _ATTRIBUTE_BUILTINS and _computes_the_name(call):
        return DYNAMIC_MESSAGE.format(name=function.id)
    if function.id == "vars":
        return VARS_MESSAGE
    return None


def _computes_the_name(call: ast.Call) -> bool:
    """Report whether the name argument is something other than a string."""
    if len(call.args) < 2:
        return False
    name = call.args[1]
    return not (isinstance(name, ast.Constant) and isinstance(name.value, str))


def _subscript_report(node: ast.Subscript) -> str | None:
    value = node.value
    if not isinstance(value, ast.Call):
        return None
    if isinstance(value.func, ast.Name) and value.func.id == "globals":
        return GLOBALS_MESSAGE
    return None


def _write_report(node: ast.AST) -> str | None:
    for target in assigned_targets(node):
        if _touches_instance_dict(target):
            return DICT_MESSAGE
    return None


def _touches_instance_dict(target: ast.expr) -> bool:
    return any(_is_instance_dict(inner) for inner in ast.walk(target))


def _is_instance_dict(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "__dict__"
