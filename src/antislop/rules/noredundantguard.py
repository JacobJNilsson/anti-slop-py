"""Rule P11 noredundantguard (AS111).

A guard that repeats the annotation of a parameter is defensiveness
without evidence. It tells the reader that the author did not trust the
annotation, and it keeps a dead branch alive. Phase 1 catches the part
the AST shows: a guard on a parameter tested against its own
annotation in the same function. See docs/spec/001-overview.md, P11.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.engine import Context

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
        for function in _functions(ctx.tree):
            annotations = _annotated_parameters(function, typevars)
            if not annotations:
                continue
            for statement in _statements(function.body):
                for call in _direct_calls(statement):
                    message = _redundant(call, annotations)
                    if message is None:
                        continue
                    if ctx.justified({call.lineno, statement.lineno}):
                        continue
                    yield call, message


def _typevars(tree: ast.Module) -> set[str]:
    """Collect the names that a TypeVar call binds in this file."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if _dotted_name(node.value.func) not in {"TypeVar", "typing.TypeVar"}:
            continue
        names.update(
            target.id for target in node.targets if isinstance(target, ast.Name)
        )
    return names


def _functions(tree: ast.Module) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node


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
        name = _dotted_name(annotation)
        if name is None or name in _EMPTY_TYPES or name in typevars:
            continue
        found[argument.arg] = name
    return found


def _statements(body: list[ast.stmt]) -> Iterator[ast.stmt]:
    """Yield the statements of one function body, without nested scopes."""
    for statement in body:
        if isinstance(
            statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            continue
        yield statement
        for value in ast.iter_child_nodes(statement):
            if isinstance(value, ast.stmt):
                yield from _statements([value])


def _direct_calls(statement: ast.stmt) -> Iterator[ast.Call]:
    """Yield the calls of a statement, not those of nested statements."""
    for child in ast.iter_child_nodes(statement):
        if not isinstance(child, ast.expr):
            continue
        for node in ast.walk(child):
            if isinstance(node, ast.Call):
                yield node


def _redundant(call: ast.Call, annotations: dict[str, str]) -> str | None:
    """Return the message for a guard that the annotation already answers."""
    if not isinstance(call.func, ast.Name) or len(call.args) != 2:
        return None
    subject, second = call.args
    if not isinstance(subject, ast.Name):
        return None
    annotation = annotations.get(subject.id)
    if annotation is None:
        return None
    if call.func.id == "isinstance" and _dotted_name(second) == annotation:
        return ISINSTANCE_MESSAGE
    names_attribute = isinstance(second, ast.Constant) and isinstance(second.value, str)
    if call.func.id == "hasattr" and names_attribute:
        return HASATTR_MESSAGE
    return None


def _dotted_name(node: ast.expr) -> str | None:
    """Return the dotted name of a plain Name or Attribute expression."""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))
