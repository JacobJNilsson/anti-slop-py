"""Rule P11 noredundantguard (AS111).

A guard that repeats the annotation of a parameter is defensiveness
without evidence. It tells the reader that the author did not trust the
annotation, and it keeps a dead branch alive. Phase 1 catches the part
the AST shows: a guard on a parameter tested against its own
annotation in the same function. No comment clears a report. The
author deletes the guard, or fixes the annotation.
See docs/spec/001-overview.md, P11.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.annotations import dotted_name
from antislop.engine import Context
from antislop.nodes import direct_expressions, functions, statements

ISINSTANCE_MESSAGE = (
    "the isinstance() check repeats the annotation of the parameter. Trust the "
    "annotation and delete the guard, or annotate the wider type you accept."
)
HASATTR_MESSAGE = (
    "the hasattr() check doubts the annotation of the parameter. Trust the "
    "annotation and delete the guard, or accept a Protocol that holds the attribute."
)
_EMPTY_TYPES = {"Any", "object", "typing.Any"}


class NoRedundantGuard:
    code = "AS111"
    name = "noredundantguard"
    default_on = False

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        typevars = _typevars(ctx.tree)
        for function in functions(ctx.tree):
            annotated = _annotated_parameters(function, typevars)
            if not annotated:
                continue
            for statement in statements(function.body):
                for node in direct_expressions(statement):
                    if not isinstance(node, ast.Call):
                        continue
                    message = _redundant(node, annotated)
                    if message is None:
                        continue
                    yield node, message


def _typevars(tree: ast.Module) -> set[str]:
    """Collect the names that a TypeVar call binds in this file."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if dotted_name(node.value.func) not in {"TypeVar", "typing.TypeVar"}:
            continue
        names.update(
            target.id for target in node.targets if isinstance(target, ast.Name)
        )
    return names


def _annotated_parameters(
    function: ast.FunctionDef | ast.AsyncFunctionDef, typevars: set[str]
) -> dict[str, str]:
    """Map each parameter with a plain concrete annotation to that annotation."""
    arguments = function.args
    found: dict[str, str] = {}
    for argument in [
        *arguments.posonlyargs,
        *arguments.args,
        *arguments.kwonlyargs,
    ]:
        annotation = argument.annotation
        if annotation is None:
            continue
        name = dotted_name(annotation)
        if name is None or name in _EMPTY_TYPES or name in typevars:
            continue
        found[argument.arg] = name
    return found


def _redundant(call: ast.Call, annotated: dict[str, str]) -> str | None:
    """Return the message for a guard that the annotation already answers."""
    if not isinstance(call.func, ast.Name) or len(call.args) != 2:
        return None
    subject, second = call.args
    if not isinstance(subject, ast.Name):
        return None
    annotation = annotated.get(subject.id)
    if annotation is None:
        return None
    if call.func.id == "isinstance" and dotted_name(second) == annotation:
        return ISINSTANCE_MESSAGE
    names_attribute = isinstance(second, ast.Constant) and isinstance(second.value, str)
    if call.func.id == "hasattr" and names_attribute:
        return HASATTR_MESSAGE
    return None
