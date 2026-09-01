"""The boundary-modules setting.

Rules P02, P06, and P07 permit a wide type or dynamic code in the
modules that decode raw input or load plugins. The setting holds glob
patterns.

The caller decides how the command line names a file, so a pattern
matches one file in three forms. The forms are the path as the command
line gives it, the resolved absolute path, and the resolved path below
the current directory. A match of one form exempts the file, so one
pattern holds for a relative call and for an absolute call.
"""

from __future__ import annotations

from contextlib import suppress
from fnmatch import fnmatch
from pathlib import Path

from antislop.engine import Context

SETTING = "boundary-modules"


def at_boundary(ctx: Context) -> bool:
    """Report whether the boundary-modules setting exempts this file."""
    patterns = ctx.settings.get(SETTING)
    if not isinstance(patterns, list):
        return False
    candidates = _candidates(ctx.path)
    return any(
        isinstance(pattern, str)
        and any(fnmatch(candidate, pattern) for candidate in candidates)
        for pattern in patterns
    )


def _candidates(path: str) -> list[str]:
    """Return the forms of one path that a pattern may match."""
    absolute = Path(path).resolve()
    found = [path, absolute.as_posix()]
    # A file outside the current directory has no form below it.
    with suppress(ValueError):
        found.append(absolute.relative_to(Path.cwd()).as_posix())
    return found
