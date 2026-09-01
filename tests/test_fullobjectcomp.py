"""Tests of rule P12 fullobjectcomp, from docs/spec/001-overview.md."""

from helpers import run

TEST_PATH = "tests/test_order.py"


def test_three_attribute_asserts_report() -> None:
    source = """
    def test_order() -> None:
        order = build()
        assert order.total == 10
        assert order.currency == "SEK"
        assert order.lines == 2
    """
    assert run(source, "fullobjectcomp", path=TEST_PATH) == ["4:AS112"]


def test_assert_equal_calls_report() -> None:
    source = """
    class OrderTest(TestCase):
        def test_order(self) -> None:
            order = build()
            self.assertEqual(order.total, 10)
            self.assertEqual(order.currency, "SEK")
            self.assertEqual(order.lines, 2)
    """
    assert run(source, "fullobjectcomp", path=TEST_PATH) == ["5:AS112"]


def test_attribute_on_the_right_of_the_comparison_reports() -> None:
    source = """
    def test_order() -> None:
        order = build()
        assert 10 == order.total
        assert "SEK" == order.currency
        assert 2 == order.lines
    """
    assert run(source, "fullobjectcomp", path=TEST_PATH) == ["4:AS112"]


def test_one_assert_of_joined_comparisons_reports() -> None:
    source = """
    def test_order() -> None:
        order = build()
        assert order.total == 10 and order.currency == "SEK" and order.lines == 2
    """
    assert run(source, "fullobjectcomp", path=TEST_PATH) == ["4:AS112"]


def test_nested_attribute_counts_on_its_root() -> None:
    source = """
    def test_order() -> None:
        order = build()
        assert order.buyer.name == "Ada"
        assert order.buyer.city == "Gothenburg"
        assert order.total == 10
    """
    assert run(source, "fullobjectcomp", path=TEST_PATH) == ["4:AS112"]


def test_whole_object_comparison_stays_clean() -> None:
    source = """
    def test_order() -> None:
        order = build()
        assert order == Order(total=10, currency="SEK", lines=2)
    """
    assert run(source, "fullobjectcomp", path=TEST_PATH) == []


def test_two_attribute_asserts_stay_clean() -> None:
    source = """
    def test_order() -> None:
        order = build()
        assert order.total == 10
        assert order.currency == "SEK"
    """
    assert run(source, "fullobjectcomp", path=TEST_PATH) == []


def test_threshold_setting_lowers_the_count() -> None:
    source = """
    def test_order() -> None:
        order = build()
        assert order.total == 10
        assert order.currency == "SEK"
    """
    settings: dict[str, object] = {"threshold": 2}
    found = run(source, "fullobjectcomp", path=TEST_PATH, settings=settings)
    assert found == ["4:AS112"]


def test_two_subjects_below_the_threshold_stay_clean() -> None:
    source = """
    def test_order() -> None:
        order = build()
        receipt = render(order)
        assert order.total == 10
        assert order.currency == "SEK"
        assert receipt.total == 10
        assert receipt.currency == "SEK"
    """
    assert run(source, "fullobjectcomp", path=TEST_PATH) == []


def test_separate_functions_count_apart() -> None:
    source = """
    def test_total() -> None:
        order = build()
        assert order.total == 10
        assert order.currency == "SEK"

    def test_lines() -> None:
        order = build()
        assert order.lines == 2
        assert order.buyer == "Ada"
    """
    assert run(source, "fullobjectcomp", path=TEST_PATH) == []


def test_production_file_stays_clean() -> None:
    source = """
    def check(order: Order) -> None:
        assert order.total == 10
        assert order.currency == "SEK"
        assert order.lines == 2
    """
    assert run(source, "fullobjectcomp", path="src/order.py") == []


def test_asserts_inside_an_except_handler_report() -> None:
    source = """
    def test_order() -> None:
        order = build()
        try:
            check(order)
        except AssertionError:
            assert order.total == 10
            assert order.currency == "SEK"
            assert order.lines == 2
    """
    assert run(source, "fullobjectcomp", path=TEST_PATH) == ["7:AS112"]
