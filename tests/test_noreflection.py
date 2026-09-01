"""Tests of rule P07 noreflection, from docs/spec/001-overview.md."""

from pathlib import Path

from helpers import run


def test_computed_getattr_reports() -> None:
    source = """
    def read(record: object, field: str) -> object:
        return getattr(record, field)
    """
    assert run(source, "noreflection") == ["3:AS107"]


def test_computed_setattr_reports() -> None:
    source = """
    def write(record: object, field: str, value: object) -> None:
        setattr(record, field, value)
    """
    assert run(source, "noreflection") == ["3:AS107"]


def test_computed_delattr_reports() -> None:
    source = """
    def drop(record: object, field: str) -> None:
        delattr(record, field)
    """
    assert run(source, "noreflection") == ["3:AS107"]


def test_vars_reports() -> None:
    source = """
    def dump(record: object) -> dict:
        return vars(record)
    """
    assert run(source, "noreflection") == ["3:AS107"]


def test_globals_subscript_reports() -> None:
    source = """
    def lookup(name: str) -> object:
        return globals()[name]
    """
    assert run(source, "noreflection") == ["3:AS107"]


def test_dict_write_reports() -> None:
    source = """
    def load(record: object, data: dict) -> None:
        record.__dict__["total"] = data["total"]
    """
    assert run(source, "noreflection") == ["3:AS107"]


def test_dict_update_reports() -> None:
    source = """
    def load(record: object, data: dict) -> None:
        record.__dict__.update(data)
    """
    assert run(source, "noreflection") == ["3:AS107"]


def test_constant_getattr_stays_clean() -> None:
    source = """
    def read(record: object) -> object:
        return getattr(record, "total", 0)
    """
    assert run(source, "noreflection") == []


def test_constant_setattr_stays_clean() -> None:
    source = """
    def write(record: object, value: object) -> None:
        setattr(record, "total", value)
    """
    assert run(source, "noreflection") == []


def test_attribute_access_stays_clean() -> None:
    source = """
    def read(record: Order) -> float:
        return record.total
    """
    assert run(source, "noreflection") == []


def test_eval_and_exec_stay_clean() -> None:
    source = """
    def run(text: str) -> object:
        exec(text)
        return eval(text)
    """
    assert run(source, "noreflection") == []


def test_boundary_module_setting_exempts_the_file() -> None:
    source = """
    def encode(record: object, field: str) -> object:
        return getattr(record, field)
    """
    settings: dict[str, object] = {"boundary-modules": ["*/codec.py", "*/plugins.py"]}
    assert run(source, "noreflection", "src/app/codec.py", settings) == []
    assert run(source, "noreflection", "src/app/plugins.py", settings) == []
    assert run(source, "noreflection", "src/app/order.py", settings) == ["3:AS107"]


def test_boundary_pattern_holds_for_an_absolute_path() -> None:
    source = """
    def encode(record: object, field: str) -> object:
        return getattr(record, field)
    """
    settings: dict[str, object] = {"boundary-modules": ["src/app/codec.py"]}
    absolute = str(Path.cwd() / "src" / "app" / "codec.py")
    assert run(source, "noreflection", absolute, settings) == []
    assert run(source, "noreflection", "src/app/codec.py", settings) == []
    assert run(source, "noreflection", "src/app/order.py", settings) == ["3:AS107"]
