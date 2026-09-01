"""Comment facts of one source file.

The justification contract of docs/spec/001-overview.md reads comments.
A comment that owns its line, directly above a flagged statement,
justifies it. A comment beside code justifies the code beside it,
never the line below. This module is the one place that parses
comments. Rules must not re-implement it.

A noqa tag holds for the whole logical line, as flake8 and ruff read
it. A signature over four physical lines is one logical line, so a tag
on the def line suppresses a report on the annotation below. The
module builds the map of physical lines to logical lines from the
NEWLINE tokens, because a NEWLINE ends a logical line.
"""

from __future__ import annotations

import io
import re
import tokenize
from dataclasses import dataclass, field

_IGNORED = frozenset(
    {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
    }
)
_NOQA = re.compile(
    r"#\s*noqa(?::\s*(?P<codes>[A-Z]+[0-9]+(?:[,\s]+[A-Z]+[0-9]+)*))?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CommentIndex:
    """Answers, for one file, where own-line comments and noqa tags sit."""

    own_line: frozenset[int]
    # The noqa field maps a line to the codes it suppresses. An empty
    # set is a blanket suppression and covers every code on that line.
    noqa: dict[int, frozenset[str]] = field(default_factory=dict)
    # The logical field maps a physical line to every physical line of
    # the same logical line.
    logical: dict[int, frozenset[int]] = field(default_factory=dict)

    def justified(self, lines: set[int]) -> bool:
        """Report whether an own-line comment ends directly above one of lines."""
        return any(line - 1 in self.own_line for line in lines)

    def suppressed(self, line: int, code: str) -> bool:
        """Report whether a noqa tag of this logical line covers one code."""
        return any(
            self._tagged(row, code)
            for row in self.logical.get(line, frozenset({line}))
        )

    def _tagged(self, row: int, code: str) -> bool:
        codes = self.noqa.get(row)
        if codes is None:
            return False
        return not codes or code.upper() in codes


def index_comments(source: str) -> CommentIndex:
    """Build the comment facts of one file from its tokens."""
    lines = source.splitlines()
    own_line: set[int] = set()
    noqa: dict[int, frozenset[str]] = {}
    reader = io.StringIO(source).readline
    try:
        tokens = list(tokenize.generate_tokens(reader))
    except tokenize.TokenError:
        # The engine only reaches this point for files that parse, so
        # a tokenize failure is unexpected. Fail open with no comments.
        return CommentIndex(own_line=frozenset())
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        row, col = token.start
        before = lines[row - 1][:col] if row - 1 < len(lines) else ""
        if not before.strip():
            own_line.add(row)
        # A noqa tag sits anywhere in the comment, as flake8 and ruff
        # read it.
        match = _NOQA.search(token.string)
        if match:
            codes = match.group("codes")
            listed = re.split(r"[,\s]+", codes.upper()) if codes else []
            noqa[row] = frozenset(listed)
    return CommentIndex(
        own_line=frozenset(own_line), noqa=noqa, logical=_logical_lines(tokens)
    )


def _logical_lines(tokens: list[tokenize.TokenInfo]) -> dict[int, frozenset[int]]:
    """Map each physical line of code to the lines of its logical line.

    A NEWLINE token ends a logical line. A comment token and an NL
    token carry no code, so neither one opens a logical line. A line
    that holds only a comment therefore stands alone, and a tag there
    suppresses nothing below it.
    """
    found: dict[int, frozenset[int]] = {}
    rows: set[int] = set()
    for token in tokens:
        if token.type in _IGNORED:
            continue
        rows.update(range(token.start[0], token.end[0] + 1))
        if token.type != tokenize.NEWLINE:
            continue
        group = frozenset(rows)
        found.update(dict.fromkeys(group, group))
        rows.clear()
    return found
