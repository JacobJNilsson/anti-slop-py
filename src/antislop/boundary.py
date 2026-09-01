"""The boundary-modules setting.

Rules P02, P06, and P07 permit a wide type or dynamic code in the
modules that decode raw input or load plugins. The setting holds glob
patterns. The rule matches every pattern against the path of the file.
"""

from __future__ import annotations

from fnmatch import fnmatch

from antislop.engine import Context

SETTING = "boundary-modules"


def at_boundary(ctx: Context) -> bool:
    """Report whether the boundary-modules setting exempts this file."""
    patterns = ctx.settings.get(SETTING)
    if not isinstance(patterns, list):
        return False
    return any(
        isinstance(pattern, str) and fnmatch(ctx.path, pattern) for pattern in patterns
    )
