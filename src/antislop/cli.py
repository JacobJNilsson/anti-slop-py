"""The antislop command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from antislop.config import load_config
from antislop.engine import Diagnostic, Rule, check_source
from antislop.rules import ALL_RULES

_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}


def enabled_rules(enable: frozenset[str], disable: frozenset[str]) -> list[Rule]:
    return [
        rule
        for rule in ALL_RULES
        if (rule.default_on or rule.name in enable) and rule.name not in disable
    ]


def python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(
                found
                for found in sorted(path.rglob("*.py"))
                if not _SKIP_DIRS.intersection(found.parts)
            )
    return files


def run(paths: list[Path]) -> list[Diagnostic]:
    config = load_config(paths[0] if paths else Path.cwd())
    rules = enabled_rules(config.enable, config.disable)
    found: list[Diagnostic] = []
    for file in python_files(paths):
        # An editor may write a byte order mark. The utf-8-sig codec
        # drops it, and the parser then reads a valid file.
        source = file.read_text(encoding="utf-8-sig", errors="replace")
        found.extend(check_source(source, file, rules, config.settings))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="antislop", description="Evidence rules for Python."
    )
    parser.add_argument("paths", nargs="*", type=Path, default=[Path.cwd()])
    arguments = parser.parse_args(argv)
    paths = arguments.paths or [Path.cwd()]
    missing = [path for path in paths if not path.exists()]
    if missing:
        # A path that does not exist is a mistake of the caller. A
        # silent pass would hide it from a hook and from CI.
        for path in missing:
            print(f"antislop: {path}: no such file or directory", file=sys.stderr)
        return 2
    found = run(paths)
    for diagnostic in found:
        print(diagnostic.render())
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
