"""The rule registry.

Every rule module registers its class here. The engine and the CLI
read this list and nothing else.
"""

from __future__ import annotations

from antislop.engine import Rule
from antislop.rules.justifycast import JustifyCast
from antislop.rules.justifyswallow import JustifySwallow
from antislop.rules.noanydecl import NoAnyDecl
from antislop.rules.noanyparam import NoAnyParam
from antislop.rules.noanyreturn import NoAnyReturn
from antislop.rules.nountypeddict import NoUntypedDict

ALL_RULES: list[Rule] = [
    JustifyCast(),
    JustifySwallow(),
    NoAnyDecl(),
    NoAnyParam(),
    NoAnyReturn(),
    NoUntypedDict(),
]
