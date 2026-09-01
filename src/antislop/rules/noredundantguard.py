"""Rule P11 noredundantguard (AS111).

A guard that repeats the annotation of a parameter is defensiveness
without evidence. It tells the reader that the author did not trust the
annotation, and it keeps a dead branch alive. Phase 1 catches the part
the AST shows: a guard on a parameter tested against its own
annotation in the same function.

The hasattr half reads only an annotation that names a class of the
same file. It reports when that class declares the attribute. Every
other annotation waits for the checker bridge of phase 2. A function
that binds the name of a parameter again hides which value a guard
reads, so the rule skips that parameter. No comment clears a report.
The author deletes the guard, or fixes the annotation.
See docs/spec/001-overview.md, P11.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.annotations import dotted_name, parameters
from antislop.engine import Context
from antislop.nodes import (
    assigned_targets,
    direct_expressions,
    functions,
    root_name,
    statements,
)

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
        attributes = _class_attributes(ctx.tree)
        for function in functions(ctx.tree):
            annotated = _annotated_parameters(function, typevars)
            if not annotated:
                continue
            for statement in statements(function.body):
                for node in direct_expressions(statement):
                    if not isinstance(node, ast.Call):
                        continue
                    message = _redundant(node, annotated, attributes)
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


def _class_attributes(tree: ast.Module) -> dict[str, set[str]]:
    """Map each class of this file to the attributes that it declares."""
    return {
        node.name: _declared(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


def _declared(node: ast.ClassDef) -> set[str]:
    """Return the attributes that one class body declares."""
    names: set[str] = set()
    for statement in node.body:
        match statement:
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                names.add(statement.name)
                if statement.name == "__init__":
                    names.update(_self_attributes(statement))
            case ast.Assign() | ast.AnnAssign():
                names.update(_bound_names(assigned_targets(statement)))
    return names


def _self_attributes(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Return the attributes that __init__ writes from its own parameters."""
    accepted = {argument.arg for argument in parameters(function.args)}
    names: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Name):
            continue
        if node.value.id not in accepted:
            continue
        names.update(
            target.attr
            for target in assigned_targets(node)
            if isinstance(target, ast.Attribute) and root_name(target) == "self"
        )
    return names


def _annotated_parameters(
    function: ast.FunctionDef | ast.AsyncFunctionDef, typevars: set[str]
) -> dict[str, str]:
    """Map each parameter with a plain concrete annotation to that annotation."""
    arguments = function.args
    rebound = _rebound_names(function)
    found: dict[str, str] = {}
    for argument in [
        *arguments.posonlyargs,
        *arguments.args,
        *arguments.kwonlyargs,
    ]:
        annotation = argument.annotation
        if annotation is None or argument.arg in rebound:
            continue
        name = dotted_name(annotation)
        if name is None or name in _EMPTY_TYPES or name in typevars:
            continue
        found[argument.arg] = name
    return found


def _rebound_names(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Collect the names that the body of one function binds again."""
    names: set[str] = set()
    for statement in function.body:
        for node in ast.walk(statement):
            names.update(_binds(node))
    return names


def _binds(node: ast.AST) -> set[str]:
    """Return the names that one node binds."""
    match node:
        case ast.Lambda() | ast.FunctionDef() | ast.AsyncFunctionDef():
            return {argument.arg for argument in parameters(node.args)}
        case ast.NamedExpr() | ast.comprehension():
            return _bound_names([node.target])
        case ast.ExceptHandler():
            return {node.name} if node.name else set()
        case _:
            return _bound_names(assigned_targets(node))


def _bound_names(targets: list[ast.expr]) -> set[str]:
    """Return the plain names among the targets of one binding."""
    return {target.id for target in targets if isinstance(target, ast.Name)}


def _redundant(
    call: ast.Call, annotated: dict[str, str], attributes: dict[str, set[str]]
) -> str | None:
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
    if call.func.id == "hasattr" and _declares(attributes, annotation, second):
        return HASATTR_MESSAGE
    return None


def _declares(
    attributes: dict[str, set[str]], annotation: str, name: ast.expr
) -> bool:
    """Report whether a class of this file declares the named attribute."""
    if not isinstance(name, ast.Constant) or not isinstance(name.value, str):
        return False
    return name.value in attributes.get(annotation, set())
