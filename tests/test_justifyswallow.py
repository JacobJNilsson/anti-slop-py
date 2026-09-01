"""Tests of rule P10 justifyswallow, from docs/spec/001-overview.md."""

from helpers import run


def test_pass_handler_reports() -> None:
    source = """
    def warm(cache: object) -> None:
        try:
            cache.warm()
        except Exception:
            pass
    """
    assert run(source, "justifyswallow") == ["5:AS110"]


def test_return_constant_reports() -> None:
    source = """
    def price(sku: str) -> float:
        try:
            return fetch(sku)
        except Exception:
            return 0.0
    """
    assert run(source, "justifyswallow") == ["5:AS110"]


def test_return_empty_dict_reports() -> None:
    source = """
    def price(sku: str) -> dict:
        try:
            return fetch(sku)
        except Exception:
            return {}
    """
    assert run(source, "justifyswallow") == ["5:AS110"]


def test_continue_reports() -> None:
    source = """
    def drain(items: list) -> None:
        for item in items:
            try:
                push(item)
            except Exception:
                continue
    """
    assert run(source, "justifyswallow") == ["6:AS110"]


def test_narrow_exception_still_reports() -> None:
    source = """
    def warm(cache: object) -> None:
        try:
            cache.warm()
        except TimeoutError:
            pass
    """
    assert run(source, "justifyswallow") == ["5:AS110"]


def test_comment_above_handler_justifies() -> None:
    source = """
    def warm(cache: object) -> None:
        try:
            cache.warm()
        # The cache is optional. A cold start only costs latency.
        except TimeoutError:
            pass
    """
    assert run(source, "justifyswallow") == []


def test_comment_first_in_body_justifies() -> None:
    source = """
    def warm(cache: object) -> None:
        try:
            cache.warm()
        except TimeoutError:
            # The cache is optional. A cold start only costs latency.
            pass
    """
    assert run(source, "justifyswallow") == []


def test_handler_that_raises_stays_clean() -> None:
    source = """
    def load(path: str) -> bytes:
        try:
            return read(path)
        except OSError as error:
            raise LoadError(path) from error
    """
    assert run(source, "justifyswallow") == []


def test_handler_that_logs_stays_clean() -> None:
    source = """
    def warm(cache: object) -> None:
        try:
            cache.warm()
        except TimeoutError:
            log.warning("cache warmup timed out")
    """
    assert run(source, "justifyswallow") == []


def test_return_computed_value_stays_clean() -> None:
    source = """
    def price(sku: str, fallback: float) -> float:
        try:
            return fetch(sku)
        except LookupError:
            return fallback
    """
    assert run(source, "justifyswallow") == []
