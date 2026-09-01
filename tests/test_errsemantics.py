"""Tests of rule P13 errsemantics, from docs/spec/001-overview.md."""

from helpers import run

TEST_PATH = "tests/test_loader.py"


def test_raises_with_match_reports() -> None:
    source = """
    def test_load() -> None:
        with pytest.raises(ValueError, match="missing field"):
            load("")
    """
    assert run(source, "errsemantics", path=TEST_PATH) == ["3:AS113"]


def test_raises_without_match_stays_clean() -> None:
    source = """
    def test_load() -> None:
        with pytest.raises(ValueError):
            load("")
    """
    assert run(source, "errsemantics", path=TEST_PATH) == []


def test_string_equality_on_the_error_reports() -> None:
    source = """
    def test_load() -> None:
        try:
            load("")
        except ValueError as error:
            assert str(error) == "missing field"
    """
    assert run(source, "errsemantics", path=TEST_PATH) == ["6:AS113"]


def test_substring_of_the_error_reports() -> None:
    source = """
    def test_load() -> None:
        with pytest.raises(ValueError) as excinfo:
            load("")
        assert "missing" in str(excinfo.value)
    """
    assert run(source, "errsemantics", path=TEST_PATH) == ["5:AS113"]


def test_bound_name_of_the_raises_block_reports() -> None:
    source = """
    def test_load() -> None:
        with pytest.raises(ValueError) as caught:
            load("")
        assert "missing" in str(caught.value)
    """
    assert run(source, "errsemantics", path=TEST_PATH) == ["5:AS113"]


def test_attribute_assertion_stays_clean() -> None:
    source = """
    def test_load() -> None:
        with pytest.raises(MissingField) as excinfo:
            load("")
        assert excinfo.value.field == "name"
    """
    assert run(source, "errsemantics", path=TEST_PATH) == []


def test_comment_above_justifies() -> None:
    source = """
    def test_load() -> None:
        # The message format belongs to this package and the API documents it.
        with pytest.raises(ValueError, match="missing field"):
            load("")
    """
    assert run(source, "errsemantics", path=TEST_PATH) == []


def test_text_of_another_value_stays_clean() -> None:
    source = """
    def test_report() -> None:
        path = build()
        assert str(path) == "/tmp/report.csv"
    """
    assert run(source, "errsemantics", path=TEST_PATH) == []


def test_production_file_stays_clean() -> None:
    source = """
    def load(path: str) -> bytes:
        with pytest.raises(ValueError, match="missing field"):
            read(path)
    """
    assert run(source, "errsemantics", path="src/loader.py") == []
