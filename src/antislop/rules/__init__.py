"""The rule registry.

Every rule module registers its class here. The engine and the CLI
read this list and nothing else.
"""

from __future__ import annotations

from antislop.engine import Rule
from antislop.rules.justifycast import JustifyCast
from antislop.rules.justifyexit import JustifyExit
from antislop.rules.justifyswallow import JustifySwallow
from antislop.rules.noadhocisinstance import NoAdHocIsinstance
from antislop.rules.noanydecl import NoAnyDecl
from antislop.rules.noanyparam import NoAnyParam
from antislop.rules.noanyreturn import NoAnyReturn
from antislop.rules.nomonkeypatch import NoMonkeyPatch
from antislop.rules.noreflection import NoReflection
from antislop.rules.nountypeddict import NoUntypedDict

ALL_RULES: list[Rule] = [
    JustifyCast(),
    JustifyExit(),
    JustifySwallow(),
    NoAdHocIsinstance(),
    NoAnyDecl(),
    NoAnyParam(),
    NoAnyReturn(),
    NoMonkeyPatch(),
    NoReflection(),
    NoUntypedDict(),
]
