"""Rule P02 nountypeddict (AS102).

An untyped dict describes no data. The rule flags parameters, returns,
class attributes, and dataclass fields that name a bare dict, a dict
with Any or object values, or a Mapping with such values. A module
level alias of such a type is the same absence of information, so the
rule resolves aliases of the same file. A cross module alias is out of
scope for phase 1. The boundary-modules setting exempts whole files
that decode raw data. A comment above the definition justifies one
signature. See docs/spec/001-overview.md, rule P02.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from fnmatch import fnmatch

from antislop.annotations import Annotations, definition_lines
from antislop.engine import Context

MESSAGE = (
    "the annotation names an untyped dict, so the reader learns no keys. "
    "Declare a dataclass, a TypedDict, or a validated model."
)


class NoUntypedDict:
    code = "AS102"
    name = "nountypeddict"
    default_on = True

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        if _is_boundary(ctx):
            return
        annotations = Annotations(ctx.tree)
        for node in ast.walk(ctx.tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                yield from _signature(node, annotations, ctx)
            elif isinstance(node, ast.ClassDef):
                yield from _fields(node, annotations, ctx)


def _signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    annotations: Annotations,
    ctx: Context,
) -> Iterator[tuple[ast.AST, str]]:
    """Yield the untyped dicts of one signature."""
    if ctx.justified(definition_lines(node)):
        return
    for annotation in [*_parameters(node.args), node.returns]:
        if annotation is not None and annotations.is_untyped_dict(annotation):
            yield annotation, MESSAGE


def _fields(
    node: ast.ClassDef, annotations: Annotations, ctx: Context
) -> Iterator[tuple[ast.AST, str]]:
    """Yield the untyped dicts of the attributes of one class."""
    for statement in node.body:
        if not isinstance(statement, ast.AnnAssign):
            continue
        if ctx.justified({statement.lineno}):
            continue
        if annotations.is_untyped_dict(statement.annotation):
            yield statement.annotation, MESSAGE


def _parameters(args: ast.arguments) -> list[ast.expr | None]:
    """Return the annotation of every parameter of one signature."""
    named = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    starred = [args.vararg, args.kwarg]
    return [argument.annotation for argument in named] + [
        argument.annotation for argument in starred if argument is not None
    ]


def _is_boundary(ctx: Context) -> bool:
    """Report whether the settings exempt this file as a decode boundary."""
    patterns = ctx.settings.get("boundary-modules")
    if not isinstance(patterns, list):
        return False
    return any(
        isinstance(pattern, str) and fnmatch(ctx.path, pattern) for pattern in patterns
    )
