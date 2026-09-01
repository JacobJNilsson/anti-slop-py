"""Rule P04 noanyreturn (AS104).

A declared Any or object return forces every caller to guess. The
author returns the concrete type, a Protocol that the caller consumes,
or a TypeVar. A module level alias of Any hides the same absence, so
the rule resolves aliases of the same file. A cross module alias is out
of scope for phase 1. A comment above the definition justifies one
return. See docs/spec/001-overview.md, rule P04.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.annotations import Annotations, definition_lines
from antislop.engine import Context

MESSAGE = (
    "the declared return is Any or object, so every caller must guess. "
    "Return the concrete type, a Protocol, or a TypeVar."
)


class NoAnyReturn:
    code = "AS104"
    name = "noanyreturn"
    default_on = True

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        annotations = Annotations(ctx.tree)
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if node.returns is None or not annotations.is_wide(node.returns):
                continue
            if ctx.justified(definition_lines(node)):
                continue
            yield node.returns, MESSAGE
