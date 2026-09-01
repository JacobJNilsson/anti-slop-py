"""The antislop command.

The command reads the files that the caller names and prints what the
enabled rules find. It loads the configuration from the first path
only, so one call covers one project.

The exit code is 0 for a clean run and 1 for a finding. A mistake of
the caller gives 2. A path that does not exist and a file that the
command cannot read are both such mistakes, so CI tells a broken call
from a lint failure.
"""

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
    """Return the Python files below the named paths.

    A glob for `*.py` also matches a directory with that name and a
    broken symbolic link. The is_file test drops both, because neither
    one holds source that the engine can parse.
    """
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(
                found
                for found in sorted(path.rglob("*.py"))
                if found.is_file() and not _SKIP_DIRS.intersection(found.parts)
            )
    return files


def run(paths: list[Path]) -> tuple[list[Diagnostic], list[Path]]:
    """Run the enabled rules over the named paths.

    The second result holds every file that the command could not
    read. The configuration comes from the first path only.
    """
    config = load_config(paths[0] if paths else Path.cwd())
    rules = enabled_rules(config.enable, config.disable)
    found: list[Diagnostic] = []
    unreadable: list[Path] = []
    for file in python_files(paths):
        source = read_source(file)
        if source is None:
            unreadable.append(file)
            continue
        found.extend(check_source(source, file, rules, config.settings))
    return found, unreadable


def read_source(file: Path) -> str | None:
    """Return the text of one file, and None if the read fails."""
    try:
        # An editor may write a byte order mark. The utf-8-sig codec
        # drops it, and the parser then reads a valid file.
        return file.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        # A permission error or a vanished file is a mistake of the
        # caller. The command reports the path and stops with code 2.
        return None


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
    found, unreadable = run(paths)
    for path in unreadable:
        print(f"antislop: {path}: cannot read the file", file=sys.stderr)
    for diagnostic in found:
        print(diagnostic.render())
    if unreadable:
        return 2
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
