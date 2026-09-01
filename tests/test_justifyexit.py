"""Tests of rule P09 justifyexit, from docs/spec/001-overview.md."""

from helpers import run


def test_sys_exit_reports() -> None:
    source = """
    import sys

    def load(path: str) -> bytes:
        if not path:
            sys.exit(1)
        return read(path)
    """
    assert run(source, "justifyexit") == ["6:AS109"]


def test_os_exit_reports() -> None:
    source = """
    import os

    def load(path: str) -> bytes:
        os._exit(1)
    """
    assert run(source, "justifyexit") == ["5:AS109"]


def test_raise_system_exit_reports() -> None:
    source = """
    def load(path: str) -> bytes:
        raise SystemExit(2)
    """
    assert run(source, "justifyexit") == ["3:AS109"]


def test_imported_exit_name_reports() -> None:
    source = """
    from sys import exit

    def load(path: str) -> bytes:
        exit(1)
    """
    assert run(source, "justifyexit") == ["5:AS109"]


def test_local_exit_function_stays_clean() -> None:
    source = """
    def exit(code: int) -> None:
        return None

    def load(path: str) -> bytes:
        exit(1)
    """
    assert run(source, "justifyexit") == []


def test_comment_above_justifies() -> None:
    source = """
    import sys

    def load(path: str) -> bytes:
        # The kernel lost the device. No caller can recover.
        sys.exit(1)
    """
    assert run(source, "justifyexit") == []


def test_main_function_stays_clean() -> None:
    source = """
    import sys

    def main() -> None:
        sys.exit(1)
    """
    assert run(source, "justifyexit") == []


def test_main_block_stays_clean() -> None:
    source = """
    import sys

    if __name__ == "__main__":
        sys.exit(run())
    """
    assert run(source, "justifyexit") == []


def test_else_of_main_block_reports() -> None:
    source = """
    import sys

    if __name__ == "__main__":
        sys.exit(run())
    else:
        sys.exit(2)
    """
    assert run(source, "justifyexit") == ["7:AS109"]


def test_entry_decorator_stays_clean() -> None:
    source = """
    import sys

    import click

    @click.command()
    def build() -> None:
        sys.exit(1)
    """
    assert run(source, "justifyexit") == []


def test_configured_entry_decorator_stays_clean() -> None:
    source = """
    import sys

    @app.entrypoint
    def build() -> None:
        sys.exit(1)
    """
    settings: dict[str, object] = {"entry-decorators": ["app.entrypoint"]}
    assert run(source, "justifyexit", settings=settings) == []


def test_unlisted_decorator_reports() -> None:
    source = """
    import sys

    @app.entrypoint
    def build() -> None:
        sys.exit(1)
    """
    assert run(source, "justifyexit") == ["6:AS109"]


def test_test_file_stays_clean() -> None:
    source = """
    import sys

    def test_build() -> None:
        sys.exit(1)
    """
    assert run(source, "justifyexit", path="tests/test_build.py") == []


def test_ordinary_raise_stays_clean() -> None:
    source = """
    def load(path: str) -> bytes:
        raise ValueError(path)
    """
    assert run(source, "justifyexit") == []


def test_exit_inside_an_except_handler_reports() -> None:
    source = """
    import sys

    def load(path: str) -> bytes:
        try:
            return read(path)
        except ValueError:
            sys.exit(2)
    """
    assert run(source, "justifyexit") == ["8:AS109"]


def test_exit_inside_a_match_case_reports() -> None:
    source = """
    import sys

    def load(command: str) -> None:
        match command:
            case "stop":
                sys.exit(3)
    """
    assert run(source, "justifyexit") == ["7:AS109"]
