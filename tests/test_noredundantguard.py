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


def test_hasattr_on_an_opaque_annotation_stays_clean() -> None:
    source = """
    def save(order: Order) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_hasattr_on_a_class_of_the_same_file_reports() -> None:
    source = """
    class Order:
        total: int

    def save(order: Order) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == ["6:AS111"]


def test_hasattr_on_a_method_of_the_same_file_reports() -> None:
    source = """
    class Order:
        def total(self) -> int:
            return 1

    def save(order: Order) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == ["7:AS111"]


def test_hasattr_on_an_init_parameter_of_the_same_file_reports() -> None:
    source = """
    class Order:
        def __init__(self, total: int) -> None:
            self.total = total

    def save(order: Order) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == ["7:AS111"]


def test_hasattr_that_the_local_class_does_not_declare_stays_clean() -> None:
    source = """
    class Order:
        total: int

    def save(order: Order) -> None:
        if hasattr(order, "discount"):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_hasattr_on_an_imported_annotation_stays_clean() -> None:
    source = """
    from models import Order

    def save(order: Order) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_hasattr_on_a_node_of_another_library_stays_clean() -> None:
    source = """
    import ast

    def line(node: ast.AST) -> int:
        if hasattr(node, "lineno"):
            return node.lineno
        return 0
    """
    assert run(source, "noredundantguard") == []


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


def test_comprehension_that_rebinds_the_name_stays_clean() -> None:
    source = """
    def save(value: int) -> None:
        store([value for value in values if isinstance(value, int)])
    """
    assert run(source, "noredundantguard") == []


def test_lambda_that_rebinds_the_name_stays_clean() -> None:
    source = """
    def save(value: int) -> None:
        store(lambda value: isinstance(value, int))
    """
    assert run(source, "noredundantguard") == []


def test_assignment_that_rebinds_the_name_stays_clean() -> None:
    source = """
    def save(value: int) -> None:
        value = parse(value)
        if isinstance(value, int):
            store(value)
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


def test_class_nested_in_a_function_does_not_answer_for_the_module_class() -> None:
    source = """
    class Order:
        pass

    def build() -> object:
        class Order:
            total: int
        return Order()

    def save(order: Order) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == []


def test_module_class_still_answers_beside_a_nested_class_of_that_name() -> None:
    source = """
    class Order:
        def __init__(self) -> None:
            self.total = 0

    def build() -> object:
        class Order:
            pass
        return Order()

    def save(order: Order) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == ["12:AS111"]


def test_hasattr_on_an_init_constant_of_the_same_file_reports() -> None:
    source = """
    class Order:
        def __init__(self) -> None:
            self.total = 0

    def save(order: Order) -> None:
        if hasattr(order, "total"):
            store(order)
    """
    assert run(source, "noredundantguard") == ["7:AS111"]
