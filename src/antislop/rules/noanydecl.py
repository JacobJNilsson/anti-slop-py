"""Rule P14 noanydecl (AS114).

A declaration that annotates a known value Any or object throws the
evidence away at the declaration. The author deletes the annotation and
keeps the inferred type, or names the concrete type.

Phase 1 reads the initializers whose type is evident from the syntax.
These are a literal, a display of a list, dict, set, or tuple, and an
f-string. A call of a name with a capital first letter is also evident,
because that is the constructor convention. A None or an Ellipsis
initializer states no value, so the rule skips it. A lower case call is
opaque until the type bridge of phase 2 arrives. A module level alias
of Any is no loophole, but a cross module alias is out of scope for
phase 1. A comment above the statement justifies one declaration.
See docs/spec/001-overview.md, rule P14.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.annotations import Annotations, dotted_name
from antislop.engine import Context

MESSAGE = (
    "the declaration widens a known value to Any or object. "
    "Delete the annotation, or name the concrete type."
)


class NoAnyDecl:
    code = "AS114"
    name = "noanydecl"
    default_on = True

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        annotations = Annotations(ctx.tree)
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.AnnAssign) or node.value is None:
                continue
            if not annotations.is_wide(node.annotation):
                continue
            if not _is_evident(node.value):
                continue
            if ctx.justified({node.lineno}):
                continue
            yield node, MESSAGE


def _is_evident(value: ast.expr) -> bool:
    """Report whether the syntax of an initializer states its type."""
    if isinstance(value, ast.Constant):
        return value.value is not None and value.value is not Ellipsis
    if isinstance(value, ast.List | ast.Dict | ast.Set | ast.Tuple | ast.JoinedStr):
        return True
    if isinstance(value, ast.Call):
        name = dotted_name(value.func)
        return name is not None and name.rsplit(".", 1)[-1][:1].isupper()
    return False
