"""Annotation facts of one source file.

Rules P02, P03, P04, and P14 read annotations and ask the same
questions. Which local name means typing.Any? Which annotation names a
dict that carries no value type? Which module level alias stands for
such a type? This module answers them from one pass over the file.

Alias resolution covers module level aliases of the same file, in the
three forms of the spec: a plain assignment, a TypeAlias annotation,
and the type statement of Python 3.12. A cross module alias is out of
scope for phase 1. See docs/spec/001-overview.md, rules P02 to P04 and
P14.
"""

from __future__ import annotations

import ast
import sys

TYPING_MODULES = frozenset({"typing", "typing_extensions"})
_MAPPING_MODULES = TYPING_MODULES | {"collections.abc"}
_ALIAS_DEPTH = 8


def dotted_name(node: ast.expr) -> str | None:
    """Return the dotted name of a Name or an Attribute chain."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    return None


def parameters(args: ast.arguments) -> list[ast.arg]:
    """Return every parameter of one signature, starred ones included."""
    starred = [args.vararg, args.kwarg]
    return [
        *args.posonlyargs,
        *args.args,
        *args.kwonlyargs,
        *[argument for argument in starred if argument is not None],
    ]


def definition_lines(node: ast.AST) -> set[int]:
    """Return the lines that a justification comment may sit above."""
    lines = {getattr(node, "lineno", 1)}
    decorators = getattr(node, "decorator_list", [])
    if decorators:
        lines.add(decorators[0].lineno)
    return lines


class Annotations:
    """The imported names and the type aliases of one file."""

    def __init__(self, tree: ast.Module) -> None:
        self.any_names = _imported(tree, "Any", TYPING_MODULES)
        self.dict_names = _imported(tree, "Dict", TYPING_MODULES) | {"dict"}
        self.mapping_names = _imported(tree, "Mapping", _MAPPING_MODULES)
        self.aliases = _aliases(tree)

    def resolve(self, node: ast.expr) -> ast.expr:
        """Return the type that an annotation names, through its aliases."""
        seen: set[str] = set()
        for _ in range(_ALIAS_DEPTH):
            name = dotted_name(node)
            if name is None or name in seen or name not in self.aliases:
                return node
            seen.add(name)
            node = self.aliases[name]
        return node

    def is_any(self, node: ast.expr) -> bool:
        """Report whether an annotation means typing.Any."""
        name = dotted_name(self.resolve(node))
        if name is None:
            return False
        return name in self.any_names or name in {
            f"{module}.Any" for module in TYPING_MODULES
        }

    def is_object(self, node: ast.expr) -> bool:
        """Report whether an annotation means the builtin object."""
        return dotted_name(self.resolve(node)) == "object"

    def is_wide(self, node: ast.expr) -> bool:
        """Report whether an annotation is Any or object."""
        return self.is_any(node) or self.is_object(node)

    def is_untyped_dict(self, node: ast.expr) -> bool:
        """Report whether an annotation names a dict without a value type."""
        return any(self._is_untyped_dict(member) for member in self._members(node))

    def _is_untyped_dict(self, node: ast.expr) -> bool:
        resolved = self.resolve(node)
        name = dotted_name(resolved)
        if name is not None:
            return self._is_dict_name(name)
        if not isinstance(resolved, ast.Subscript):
            return False
        base = dotted_name(resolved.value)
        if base is None:
            return False
        arguments = _subscript_arguments(resolved)
        if len(arguments) != 2:
            return False
        if not self._is_dict_name(base) and not self._is_mapping_name(base):
            return False
        return self.is_wide(arguments[1])

    def _members(self, node: ast.expr) -> list[ast.expr]:
        """Return the members of a union, or the annotation itself."""
        resolved = self.resolve(node)
        if isinstance(resolved, ast.BinOp) and isinstance(resolved.op, ast.BitOr):
            return self._members(resolved.left) + self._members(resolved.right)
        if isinstance(resolved, ast.Subscript):
            base = dotted_name(resolved.value)
            plain = base.rsplit(".", 1)[-1] if base else ""
            if plain in {"Optional", "Union"}:
                members: list[ast.expr] = []
                for argument in _subscript_arguments(resolved):
                    members.extend(self._members(argument))
                return members
        return [resolved]

    def _is_dict_name(self, name: str) -> bool:
        return name in self.dict_names or name in {
            f"{module}.Dict" for module in TYPING_MODULES
        }

    def _is_mapping_name(self, name: str) -> bool:
        return name in self.mapping_names or name in {
            f"{module}.Mapping" for module in _MAPPING_MODULES
        }


def _subscript_arguments(node: ast.Subscript) -> list[ast.expr]:
    """Return the arguments of a subscript, one or many."""
    if isinstance(node.slice, ast.Tuple):
        return list(node.slice.elts)
    return [node.slice]


def _imported(tree: ast.Module, name: str, modules: frozenset[str]) -> frozenset[str]:
    """Collect the local names that one import of one module gives."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in modules:
            found.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == name
            )
    return frozenset(found)


def _aliases(tree: ast.Module) -> dict[str, ast.expr]:
    """Collect the module level type aliases of one file."""
    found: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.value is not None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
            and _is_type_alias_annotation(node.annotation)
        ):
            found[node.target.id] = node.value
        elif sys.version_info >= (3, 12) and isinstance(node, ast.TypeAlias):
            found[node.name.id] = node.value
    return found


def _is_type_alias_annotation(node: ast.expr) -> bool:
    name = dotted_name(node)
    if name is None:
        return False
    return name.rsplit(".", 1)[-1] == "TypeAlias"
