"""Tests of the config reader and of the rule selection.

The config shapes come from docs/spec/001-overview.md, the decision
paragraph that puts the settings in [tool.antislop] of pyproject.toml.
"""

from __future__ import annotations

from pathlib import Path

from antislop.cli import enabled_rules
from antislop.config import Config, find_pyproject, load_config
from antislop.engine import Rule

FULL = """
[tool.antislop]
enable = ["noanyparam"]
disable = ["justifyswallow"]

[tool.antislop.noreflection]
boundary-modules = ["myapp/codec/*"]
"""


def _write(directory: Path, text: str) -> None:
    (directory / "pyproject.toml").write_text(text, encoding="utf-8")


def test_load_config_reads_enable_disable_and_a_rule_table(tmp_path: Path) -> None:
    _write(tmp_path, FULL)
    config = load_config(tmp_path)
    assert config == Config(
        enable=frozenset({"noanyparam"}),
        disable=frozenset({"justifyswallow"}),
        settings={"noreflection": {"boundary-modules": ["myapp/codec/*"]}},
    )


def test_find_pyproject_walks_upward(tmp_path: Path) -> None:
    _write(tmp_path, "[tool.antislop]\n")
    nested = tmp_path / "src" / "antislop"
    nested.mkdir(parents=True)
    assert find_pyproject(nested) == tmp_path / "pyproject.toml"


def test_find_pyproject_stops_at_the_nearest_file(tmp_path: Path) -> None:
    _write(tmp_path, "[tool.antislop]\n")
    nested = tmp_path / "package"
    nested.mkdir()
    _write(nested, "[tool.antislop]\n")
    assert find_pyproject(nested) == nested / "pyproject.toml"


def test_load_config_reads_the_file_above_the_start(tmp_path: Path) -> None:
    _write(tmp_path, FULL)
    nested = tmp_path / "src"
    nested.mkdir()
    assert load_config(nested).enable == frozenset({"noanyparam"})


def test_a_missing_table_gives_the_empty_config(tmp_path: Path) -> None:
    _write(tmp_path, '[project]\nname = "app"\n')
    assert load_config(tmp_path) == Config()


def test_a_malformed_table_gives_the_empty_config(tmp_path: Path) -> None:
    _write(tmp_path, '[tool]\nantislop = "on"\n')
    assert load_config(tmp_path) == Config()


def test_a_malformed_enable_list_gives_no_names(tmp_path: Path) -> None:
    _write(tmp_path, '[tool.antislop]\nenable = "noanyparam"\n')
    assert load_config(tmp_path) == Config()


def test_the_default_selection_holds_the_error_rules_only() -> None:
    names = _names(enabled_rules(frozenset(), frozenset()))
    assert "justifyswallow" in names
    assert "noanyparam" not in names


def test_enable_turns_an_opt_in_rule_on() -> None:
    names = _names(enabled_rules(frozenset({"noanyparam"}), frozenset()))
    assert "noanyparam" in names


def test_disable_turns_an_error_rule_off() -> None:
    names = _names(enabled_rules(frozenset(), frozenset({"justifyswallow"})))
    assert "justifyswallow" not in names


def test_disable_beats_enable_for_one_name() -> None:
    selected = enabled_rules(frozenset({"noanyparam"}), frozenset({"noanyparam"}))
    assert "noanyparam" not in _names(selected)


def _names(rules: list[Rule]) -> set[str]:
    return {rule.name for rule in rules}
