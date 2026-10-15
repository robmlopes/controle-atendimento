from hypothesis import given
from hypothesis import strategies as st

from domain.panel import (
    PanelLimits,
    clean_name,
    format_price,
    format_time,
    is_valid_duration,
    is_valid_name,
    is_valid_price,
    is_valid_range,
    is_valid_weekday,
    parse_price,
    parse_time,
)


def test_parse_time_examples() -> None:
    assert parse_time("09:00") == 540 and parse_time("9:05") == 545 and parse_time(" 23:59 ") == 1439
    for bad in ("", "24:00", "9:5", "09:60", "ab:cd", "09-00", "090:00", "٠٩:٠٠", "-1:00", "9:0a"):
        assert parse_time(bad) is None, bad


def test_parse_price_examples() -> None:
    assert parse_price("35") == 3500 and parse_price("35,5") == 3550 and parse_price("35.50") == 3550
    assert parse_price("0") == 0 and parse_price("0,05") == 5
    for bad in ("", "abc", "-1", "1,234", "10000000", "10000,01", "1,2,3", ",5", "٣٥"):
        assert parse_price(bad) is None, bad


def test_name_rules() -> None:
    assert clean_name("  Ana   Maria ") == "Ana Maria"
    assert is_valid_name("Ana") and not is_valid_name("") and not is_valid_name(" Ana")
    assert not is_valid_name("a" * (PanelLimits.MAX_NAME + 1)) and is_valid_name("a" * PanelLimits.MAX_NAME)
    assert not is_valid_name("tab\there")


def test_bounds() -> None:
    assert not is_valid_duration(4) and is_valid_duration(5) and is_valid_duration(480) and not is_valid_duration(481)
    assert is_valid_price(None) and is_valid_price(0) and not is_valid_price(-1)
    assert is_valid_weekday(0) and is_valid_weekday(6) and not is_valid_weekday(7) and not is_valid_weekday(-1)
    assert is_valid_range(0, 1440) and not is_valid_range(5, 5) and not is_valid_range(-1, 10)
    assert not is_valid_range(10, 1441)


@given(st.integers(min_value=0, max_value=1439))
def test_time_round_trip(minute: int) -> None:
    assert parse_time(format_time(minute)) == minute


@given(st.integers(min_value=0, max_value=PanelLimits.MAX_PRICE_CENTS))
def test_price_round_trip(cents: int) -> None:
    assert parse_price(format_price(cents)) == cents


@given(st.text())
def test_clean_name_is_idempotent(name: str) -> None:
    assert clean_name(clean_name(name)) == clean_name(name)
