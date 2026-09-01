"""Tests of the antislop command.

The command reads the files that the caller names and reports what the
enabled rules find. See docs/spec/001-overview.md, the decision
paragraph that names the command and its config.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from antislop import cli

SWALLOW = """try:
    load()
except OSError:
    pass
"""


def test_a_byte_order_mark_does_not_hide_a_file(tmp_path: Path) -> None:
    file = tmp_path / "app.py"
    file.write_text(SWALLOW, encoding="utf-8-sig")
    found, unreadable = cli.run([file])
    assert [diagnostic.code for diagnostic in found] == ["AS110"]
    assert unreadable == []


def test_a_plain_file_reports_the_same(tmp_path: Path) -> None:
    file = tmp_path / "app.py"
    file.write_text(SWALLOW, encoding="utf-8")
    found, unreadable = cli.run([file])
    assert [diagnostic.code for diagnostic in found] == ["AS110"]
    assert unreadable == []


def test_a_missing_path_ends_with_code_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "gone.py"
    assert cli.main([str(missing)]) == 2
    assert "gone.py" in capsys.readouterr().err


def test_a_clean_file_ends_with_code_zero(tmp_path: Path) -> None:
    file = tmp_path / "app.py"
    file.write_text("def load() -> int:\n    return 1\n", encoding="utf-8")
    assert cli.main([str(file)]) == 0


def test_a_file_with_a_finding_ends_with_code_one(tmp_path: Path) -> None:
    file = tmp_path / "app.py"
    file.write_text(SWALLOW, encoding="utf-8")
    assert cli.main([str(file)]) == 1


def test_a_directory_named_like_a_module_ends_with_code_zero(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "x.py").mkdir()
    (package / "app.py").write_text("def load() -> int:\n    return 1\n")
    assert cli.main([str(package)]) == 0


def test_an_unreadable_file_ends_with_code_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    file = package / "app.py"
    file.write_text(SWALLOW, encoding="utf-8")
    file.chmod(0o000)
    if os.access(file, os.R_OK):
        pytest.skip("the file stays readable, so the run cannot fail")
    try:
        assert cli.main([str(package)]) == 2
    finally:
        file.chmod(0o600)
    assert "app.py" in capsys.readouterr().err
