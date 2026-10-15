from hypothesis import given
from hypothesis import strategies as st

from domain.public import (
    PublicPolicy,
    booking_end,
    can_book_more,
    day_in_window,
    is_valid_slug,
    normalize_phone,
)


def test_normalize_phone_brazilian_examples() -> None:
    assert normalize_phone("(11) 98765-4321") == "+5511987654321"
    assert normalize_phone("11987654321") == "+5511987654321"
    assert normalize_phone("+55 11 98765-4321") == "+5511987654321"
    assert normalize_phone("5511987654321") == "+5511987654321"
    assert normalize_phone("(11) 3456-7890") == "+551134567890"


def test_normalize_phone_rejects_invalid() -> None:
    for bad in ("", "123", "1198765432", "011987654321", "10987654321", "11887654321", "+1 555 1234", "11987654321x"):
        assert normalize_phone(bad) is None, bad


def test_slug_rules() -> None:
    assert is_valid_slug("barbearia") and is_valid_slug("salao-da-ana") and is_valid_slug("ze1")
    for bad in (
        "",
        "ab",
        "a" * (PublicPolicy.MAX_SLUG + 1),
        "-barbearia",
        "barbearia-",
        "Barbearia",
        "barb earia",
        "barb_earia",
    ):
        assert not is_valid_slug(bad), bad


def test_window_and_limits() -> None:
    assert (
        day_in_window(100, 100)
        and day_in_window(160, 100)
        and not day_in_window(99, 100)
        and not day_in_window(161, 100)
    )
    assert can_book_more(0) and can_book_more(2) and not can_book_more(3) and not can_book_more(4)


@given(st.integers(min_value=0, max_value=1440), st.integers(min_value=1, max_value=480))
def test_booking_end_always_advances(start: int, duration: int) -> None:
    assert booking_end(start, duration) == start + duration
