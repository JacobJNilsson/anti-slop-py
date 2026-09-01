"""Comment facts of one source file.

The justification contract of docs/spec/001-overview.md reads comments.
A comment that owns its line, directly above a flagged statement,
justifies it. A comment beside code justifies the code beside it,
never the line below. This module is the one place that parses
comments. Rules must not re-implement it.
"""

from __future__ import annotations

import io
import re
import tokenize
from dataclasses import dataclass, field

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

    def justified(self, lines: set[int]) -> bool:
        """Report whether an own-line comment ends directly above one of lines."""
        return any(line - 1 in self.own_line for line in lines)

    def suppressed(self, line: int, code: str) -> bool:
        codes = self.noqa.get(line)
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
        match = _NOQA.match(token.string)
        if match:
            codes = match.group("codes")
            listed = re.split(r"[,\s]+", codes.upper()) if codes else []
            noqa[row] = frozenset(listed)
    return CommentIndex(own_line=frozenset(own_line), noqa=noqa)
