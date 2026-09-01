"""Tests of rule P11 noredundantguard, from docs/spec/001-overview.md."""

from helpers import run


def test_isinstance_on_own_annotation_reports() -> None:
    source = """
    def save(order: Order) -> None:
        if isinstance(order, Order):
            store(order)
    """
    assert run(source, "noredundantguard") == ["3:AS111"]


def test_dotted_annotation_reports() -> None:
    source = """
    def save(order: models.Order) -> None:
        if isinstance(order, models.Order):
            store(order)
    """
    assert run(source, "noredundantguard") == ["3:AS111"]


def test_hasattr_on_annotated_parameter_reports() -> None:
    source = """
    def save(order: Order) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == ["3:AS111"]


def test_method_parameter_reports() -> None:
    source = """
    class Store:
        def save(self, order: Order) -> None:
            if isinstance(order, Order):
                self.write(order)
    """
    assert run(source, "noredundantguard") == ["4:AS111"]


def test_test_file_reports() -> None:
    source = """
    def test_save(order: Order) -> None:
        assert isinstance(order, Order)
    """
    assert run(source, "noredundantguard", path="tests/test_store.py") == ["3:AS111"]


def test_narrowing_to_a_subclass_stays_clean() -> None:
    source = """
    def save(animal: Animal) -> None:
        if isinstance(animal, Dog):
            walk(animal)
    """
    assert run(source, "noredundantguard") == []


def test_comment_above_does_not_clear_the_report() -> None:
    source = """
    def save(order: Order) -> None:
        # The queue holds records of an old release without the annotation.
        if isinstance(order, Order):
            store(order)
    """
    assert run(source, "noredundantguard") == ["4:AS111"]


def test_guard_inside_an_except_handler_reports() -> None:
    source = """
    def save(order: Order) -> None:
        try:
            store(order)
        except OSError:
            if isinstance(order, Order):
                retry(order)
    """
    assert run(source, "noredundantguard") == ["6:AS111"]


def test_guard_inside_a_match_case_reports() -> None:
    source = """
    def save(order: Order, command: str) -> None:
        match command:
            case "store":
                if isinstance(order, Order):
                    store(order)
    """
    assert run(source, "noredundantguard") == ["5:AS111"]


def test_optional_annotation_stays_clean() -> None:
    source = """
    def save(order: Optional[Order]) -> None:
        if isinstance(order, Order):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_union_annotation_stays_clean() -> None:
    source = """
    def save(order: Order | None) -> None:
        if isinstance(order, Order):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_any_annotation_stays_clean() -> None:
    source = """
    def save(order: Any) -> None:
        if isinstance(order, Order):
            store(order)
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_object_annotation_stays_clean() -> None:
    source = """
    def save(order: object) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_typevar_annotation_stays_clean() -> None:
    source = """
    from typing import TypeVar

    T = TypeVar("T")

    def save(order: T) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_local_variable_stays_clean() -> None:
    source = """
    def save(raw: bytes) -> None:
        order = decode(raw)
        if isinstance(order, Order):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_isinstance_tuple_stays_clean() -> None:
    source = """
    def save(order: Order) -> None:
        if isinstance(order, (Order, Draft)):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_parameter_of_another_function_stays_clean() -> None:
    source = """
    def save(order: Order) -> None:
        store(order)

    def check(value: object) -> None:
        if isinstance(order, Order):
            store(order)
    """
    assert run(source, "noredundantguard") == []
