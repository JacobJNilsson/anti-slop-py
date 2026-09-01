"""Configuration from pyproject.toml.

The [tool.antislop] table holds two lists and per-rule tables:

    [tool.antislop]
    enable = ["noanyparam"]
    disable = ["justifyswallow"]

    [tool.antislop.noreflection]
    boundary-modules = ["myapp.codec.*"]
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    enable: frozenset[str] = frozenset()
    disable: frozenset[str] = frozenset()
    settings: dict[str, dict[str, object]] = field(default_factory=dict)


def find_pyproject(start: Path) -> Path | None:
    for directory in [start, *start.parents]:
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def load_config(start: Path) -> Config:
    pyproject = find_pyproject(start.resolve())
    if pyproject is None:
        return Config()
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    table = data.get("tool", {}).get("antislop", {})
    if not isinstance(table, dict):
        return Config()
    enable = frozenset(_names(table.get("enable")))
    disable = frozenset(_names(table.get("disable")))
    settings = {
        key: value
        for key, value in table.items()
        if isinstance(value, dict)
    }
    return Config(enable=enable, disable=disable, settings=settings)


def _names(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
