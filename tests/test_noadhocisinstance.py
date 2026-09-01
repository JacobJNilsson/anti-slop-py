"""Tests of rule P06 noadhocisinstance, from docs/spec/001-overview.md."""

from helpers import run


def test_isinstance_chain_reports() -> None:
    source = """
    def render(node: object) -> str:
        if isinstance(node, Heading):
            return heading(node)
        elif isinstance(node, Paragraph):
            return paragraph(node)
        return ""
    """
    assert run(source, "noadhocisinstance") == ["3:AS106"]


def test_long_chain_reports_once() -> None:
    source = """
    def render(node: object) -> str:
        if isinstance(node, Heading):
            return heading(node)
        elif isinstance(node, Paragraph):
            return paragraph(node)
        elif isinstance(node, Code):
            return code(node)
        else:
            return ""
    """
    assert run(source, "noadhocisinstance") == ["3:AS106"]


def test_chain_in_else_branch_reports_once() -> None:
    source = """
    def render(node: object) -> str:
        if isinstance(node, Heading):
            return heading(node)
        else:
            if isinstance(node, Paragraph):
                return paragraph(node)
        return ""
    """
    assert run(source, "noadhocisinstance") == ["3:AS106"]


def test_single_isinstance_stays_clean() -> None:
    source = """
    def render(node: object) -> str:
        if isinstance(node, Heading):
            return heading(node)
        return ""
    """
    assert run(source, "noadhocisinstance") == []


def test_match_statement_stays_clean() -> None:
    source = """
    def render(node: object) -> str:
        match node:
            case Heading():
                return heading(node)
            case Paragraph():
                return paragraph(node)
        return ""
    """
    assert run(source, "noadhocisinstance") == []


def test_different_names_stay_clean() -> None:
    source = """
    def combine(left: object, right: object) -> str:
        if isinstance(left, str):
            return left
        elif isinstance(right, str):
            return right
        return ""
    """
    assert run(source, "noadhocisinstance") == []


def test_boundary_module_setting_exempts_the_file() -> None:
    source = """
    def decode(node: object) -> str:
        if isinstance(node, Heading):
            return heading(node)
        elif isinstance(node, Paragraph):
            return paragraph(node)
        elif isinstance(node, Code):
            return code(node)
        return ""
    """
    settings: dict[str, object] = {"boundary-modules": ["*/codec.py"]}
    assert run(source, "noadhocisinstance", "src/app/codec.py", settings) == []


def test_two_branch_union_check_at_a_boundary_stays_clean() -> None:
    source = """
    def decode(value: int | str) -> str:
        if isinstance(value, int):
            return str(value)
        elif isinstance(value, str):
            return value
        return ""
    """
    settings: dict[str, object] = {"boundary-modules": ["src/codec/*"]}
    assert run(source, "noadhocisinstance", "src/codec/json.py", settings) == []
    assert run(source, "noadhocisinstance", "src/app/render.py") == ["3:AS106"]
