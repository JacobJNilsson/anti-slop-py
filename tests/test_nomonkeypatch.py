"""Tests of rule P08 nomonkeypatch, from docs/spec/001-overview.md."""

from helpers import run


def test_patched_module_attribute_reports() -> None:
    source = """
    import config

    def boot() -> None:
        config.DEBUG = True
    """
    assert run(source, "nomonkeypatch") == ["5:AS108"]


def test_patched_imported_class_reports() -> None:
    source = """
    from stripe import Client

    def boot() -> None:
        Client.timeout = 30
    """
    assert run(source, "nomonkeypatch") == ["5:AS108"]


def test_patched_submodule_attribute_reports() -> None:
    source = """
    import os.path

    def boot() -> None:
        os.path.sep = "|"
    """
    assert run(source, "nomonkeypatch") == ["5:AS108"]


def test_setattr_on_imported_module_reports() -> None:
    source = """
    import config

    def boot() -> None:
        setattr(config, "DEBUG", True)
    """
    assert run(source, "nomonkeypatch") == ["5:AS108"]


def test_local_instance_stays_clean() -> None:
    source = """
    from stripe import Client

    def boot() -> Client:
        client = Client()
        client.timeout = 30
        return client
    """
    assert run(source, "nomonkeypatch") == []


def test_own_attribute_stays_clean() -> None:
    source = """
    import config

    class Boot:
        def __init__(self) -> None:
            self.debug = config.DEBUG
    """
    assert run(source, "nomonkeypatch") == []


def test_computed_setattr_name_stays_clean() -> None:
    source = """
    import config

    def boot(field: str) -> None:
        setattr(config, field, True)
    """
    assert run(source, "nomonkeypatch") == []


def test_justification_comment_clears_the_report() -> None:
    source = """
    import upstream

    def boot() -> None:
        # Upstream 2.4 parses a naive date. Remove this after upstream 2.5.
        upstream.parse = parse_aware
    """
    assert run(source, "nomonkeypatch") == []


def test_test_file_stays_clean() -> None:
    source = """
    import config

    def test_boot() -> None:
        config.DEBUG = True
    """
    assert run(source, "nomonkeypatch", "tests/test_boot.py") == []


def test_tuple_unpacking_target_reports() -> None:
    source = """
    import sys

    def boot() -> None:
        sys.path, other = build()
    """
    assert run(source, "nomonkeypatch") == ["5:AS108"]


def test_list_unpacking_target_reports() -> None:
    source = """
    import sys

    def boot() -> None:
        [sys.argv] = build()
    """
    assert run(source, "nomonkeypatch") == ["5:AS108"]
