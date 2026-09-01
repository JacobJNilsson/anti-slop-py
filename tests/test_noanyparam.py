"""Tests of rule P03 noanyparam, from docs/spec/001-overview.md."""

from helpers import run

from antislop.rules import ALL_RULES


def test_the_rule_ships_off() -> None:
    rules = [rule for rule in ALL_RULES if rule.name == "noanyparam"]
    assert [rule.default_on for rule in rules] == [False]


def test_any_parameter_reports() -> None:
    source = """
    from typing import Any

    def load(payload: Any) -> int:
        return 1
    """
    assert run(source, "noanyparam") == ["4:AS103"]


def test_object_parameter_reports() -> None:
    source = """
    def load(payload: object) -> int:
        return 1
    """
    assert run(source, "noanyparam") == ["2:AS103"]


def test_module_alias_reports() -> None:
    source = """
    from typing import Any

    Payload = Any

    def load(payload: Payload) -> int:
        return 1
    """
    assert run(source, "noanyparam") == ["6:AS103"]


def test_domain_types_stay_clean() -> None:
    source = """
    from typing import Protocol, TypeVar

    T = TypeVar("T")


    class Reader(Protocol):
        def read(self) -> str: ...


    class Store:
        def load(self, source: Reader, value: T) -> T:
            return value
    """
    assert run(source, "noanyparam") == []


def test_lambda_stays_clean() -> None:
    source = """
    identity = lambda value: value
    """
    assert run(source, "noanyparam") == []


def test_comment_above_def_justifies() -> None:
    source = """
    from typing import Any

    # The plugin API hands the payload over untyped.
    def load(payload: Any) -> int:
        return 1
    """
    assert run(source, "noanyparam") == []


def test_forwarded_kwargs_stay_clean() -> None:
    source = """
    from collections.abc import Callable
    from typing import Any

    def wrap(func: Callable[..., int], **kwargs: Any) -> int:
        return func(**kwargs)
    """
    assert run(source, "noanyparam") == []


def test_kwargs_forwarded_twice_report() -> None:
    source = """
    from collections.abc import Callable
    from typing import Any

    def wrap(
        first: Callable[..., int],
        second: Callable[..., int],
        **kwargs: Any,
    ) -> int:
        first(**kwargs)
        return second(**kwargs)
    """
    assert run(source, "noanyparam") == ["8:AS103"]


def test_kwargs_read_but_not_forwarded_report() -> None:
    source = """
    from typing import Any

    def wrap(**kwargs: Any) -> int:
        return len(kwargs)
    """
    assert run(source, "noanyparam") == ["4:AS103"]


def test_star_args_of_a_forwarding_wrapper_reports() -> None:
    source = """
    from collections.abc import Callable
    from typing import Any

    def wrap(
        func: Callable[..., int],
        *args: Any,
        **kwargs: Any,
    ) -> int:
        return func(*args, **kwargs)
    """
    assert run(source, "noanyparam") == ["7:AS103"]
