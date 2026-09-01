"""Shared test helpers.

run() executes one rule over one source text and returns compact
"line:code" strings, so a test reads as the spec does.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from antislop.engine import check_source
from antislop.rules import ALL_RULES


def run(
    source: str,
    rule_name: str,
    path: str = "app.py",
    settings: dict[str, object] | None = None,
) -> list[str]:
    rules = [rule for rule in ALL_RULES if rule.name == rule_name]
    assert rules, f"no rule named {rule_name}"
    found = check_source(
        textwrap.dedent(source),
        Path(path),
        rules,
        {rule_name: settings or {}},
    )
    return [f"{diagnostic.line}:{diagnostic.code}" for diagnostic in found]
