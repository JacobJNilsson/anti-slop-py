"""Rule P13 errsemantics (AS113).

A test that matches the message of an error decides from prose that no
API promises. A reword breaks the test. The test must assert the type
of the exception and its attributes. A match on a stable owned message
format stays possible through a justification comment. The rule reads
the error names from the bindings of the file, because both shapes of
the spec bind the error to a name. Test files only.
See docs/spec/001-overview.md, rule P13.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from antislop.engine import Context
from antislop.nodes import root_name

MATCH_MESSAGE = (
    "the match argument tests the wording of the error, and a reword breaks it. "
    "Assert the type of the exception and its attributes."
)
TEXT_MESSAGE = (
    "the assertion reads the text of the error, and a reword breaks it. "
    "Assert the type of the exception and its attributes."
)


class ErrSemantics:
    code = "AS113"
    name = "errsemantics"
    default_on = False

    def check(self, ctx: Context) -> Iterator[tuple[ast.AST, str]]:
        if not ctx.is_test:
            return
        errors = _bound_error_names(ctx.tree)
        for statement in _statements(ctx.tree):
            for node, message in _matches(statement, errors):
                if ctx.justified({node.lineno, statement.lineno}):
                    continue
                yield node, message


def _statements(node: ast.AST) -> Iterator[ast.stmt]:
    """Yield every statement under a node, nested statements included."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.stmt):
            yield child
            yield from _statements(child)
        elif not isinstance(child, ast.expr):
            # An except clause and a match case hold statements, but
            # neither one is a statement.
            yield from _statements(child)


def _bound_error_names(tree: ast.Module) -> set[str]:
    """Collect the names that an except clause or a raises block binds."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.With | ast.AsyncWith):
            for item in node.items:
                bound = item.optional_vars
                if _is_raises_call(item.context_expr) and isinstance(bound, ast.Name):
                    names.add(bound.id)
    return names


def _matches(
    statement: ast.stmt, errors: set[str]
) -> Iterator[tuple[ast.expr, str]]:
    """Yield the message assertions of one statement, with their message."""
    for child in ast.iter_child_nodes(statement):
        if isinstance(child, ast.withitem):
            child = child.context_expr
        if not isinstance(child, ast.expr):
            continue
        for node in ast.walk(child):
            if isinstance(node, ast.Call) and _matches_wording(node):
                yield node, MATCH_MESSAGE
            elif isinstance(node, ast.Compare) and _reads_message(node, errors):
                yield node, TEXT_MESSAGE


def _is_raises_call(node: ast.expr) -> bool:
    """Report whether an expression calls pytest.raises."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr == "raises"
    return isinstance(func, ast.Name) and func.id == "raises"


def _matches_wording(call: ast.Call) -> bool:
    """Report whether a raises call carries a match argument."""
    if not _is_raises_call(call):
        return False
    return any(keyword.arg == "match" for keyword in call.keywords)


def _reads_message(node: ast.Compare, errors: set[str]) -> bool:
    """Report whether a comparison reads the text of an error."""
    if len(node.ops) != 1:
        return False
    operator = node.ops[0]
    left, right = node.left, node.comparators[0]
    if isinstance(operator, ast.Eq):
        pair = [left, right]
        return any(_is_error_text(item, errors) for item in pair) and any(
            _is_string(item) for item in pair
        )
    if isinstance(operator, ast.In):
        return _is_string(left) and _is_error_text(right, errors)
    return False


def _is_string(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_error_text(node: ast.expr, errors: set[str]) -> bool:
    """Report whether an expression renders an error as text."""
    if not isinstance(node, ast.Call) or len(node.args) != 1:
        return False
    if not isinstance(node.func, ast.Name) or node.func.id != "str":
        return False
    return root_name(node.args[0]) in errors
