"""Rule P03 noanyparam (AS103).

An Any parameter moves the parse from the boundary into the callee. An
object parameter forces an isinstance in the callee for the same
reason, so the rule treats both as one absence of a contract. TypeVars
and Protocols carry evidence and never match. A lambda takes no
annotation, so the rule reads functions and methods only.

The one exemption is the decorator idiom. A **kwargs parameter that the
function forwards verbatim in exactly one call is a pass through, not a
contract. The same call often forwards *args with it, and the exemption
then covers both parameters. A module level alias of Any is no
loophole, but a cross
module alias is out of scope for phase 1. A comment above the
definition names the API that fixes the signature. The rule ships off.
See docs/spec/001-overview.md, rule P03.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.annotations import Annotations, definition_lines, parameters
from antislop.engine import Context

MESSAGE = (
    "the parameter is Any or object, so the callee must parse the value. "
    "Accept a named domain type, a Protocol, or a TypeVar."
)


class NoAnyParam:
    code = "AS103"
    name = "noanyparam"
    default_on = False

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        annotations = Annotations(ctx.tree)
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if ctx.justified(definition_lines(node)):
                continue
            forwarded = _forwarded(node)
            for argument in parameters(node.args):
                annotation = argument.annotation
                if annotation is None or argument.arg in forwarded:
                    continue
                if annotations.is_wide(annotation):
                    yield annotation, MESSAGE


def _forwarded(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Return the pass through parameters of a wrapper function.

    The decorator idiom hands **kwargs, and often *args with it, to one
    callee. A second forwarding call is no pass through.
    """
    kwarg = node.args.kwarg
    if kwarg is None:
        return set()
    calls = [
        child
        for statement in node.body
        for child in ast.walk(statement)
        if isinstance(child, ast.Call) and _forwards_keywords(child, kwarg.arg)
    ]
    if len(calls) != 1:
        return set()
    found = {kwarg.arg}
    vararg = node.args.vararg
    if vararg is not None and _forwards_positionals(calls[0], vararg.arg):
        found.add(vararg.arg)
    return found


def _forwards_keywords(call: ast.Call, name: str) -> bool:
    """Report whether a call passes one name on as **name."""
    return any(
        keyword.arg is None
        and isinstance(keyword.value, ast.Name)
        and keyword.value.id == name
        for keyword in call.keywords
    )


def _forwards_positionals(call: ast.Call, name: str) -> bool:
    """Report whether a call passes one name on as *name."""
    return any(
        isinstance(argument, ast.Starred)
        and isinstance(argument.value, ast.Name)
        and argument.value.id == name
        for argument in call.args
    )
