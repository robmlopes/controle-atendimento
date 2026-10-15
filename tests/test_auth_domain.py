from hypothesis import given
from hypothesis import strategies as st

from domain.auth import (
    AuthPolicy,
    is_valid_email,
    is_valid_password,
    login_blocked,
    minutes_of,
    normalize_email,
    session_valid,
    window_start,
)
from domain.models import Now


def test_email_validation_examples() -> None:
    assert is_valid_email("dono@loja.com.br")
    for bad in ("", "x", "a@b", "@b.com", "a@.com", "a@b.", "a b@c.com", "a@@b.com", "a@b@c.com"):
        assert not is_valid_email(bad), bad
    assert not is_valid_email("a" * 250 + "@b.com")


def test_normalize_email_trims_and_lowercases() -> None:
    assert normalize_email("  Dono@Loja.COM ") == "dono@loja.com"


def test_password_length_bounds() -> None:
    assert not is_valid_password("a" * (AuthPolicy.MIN_PASSWORD - 1))
    assert is_valid_password("a" * AuthPolicy.MIN_PASSWORD)
    assert is_valid_password("a" * AuthPolicy.MAX_PASSWORD)
    assert not is_valid_password("a" * (AuthPolicy.MAX_PASSWORD + 1))


def test_login_blocked_threshold() -> None:
    assert not login_blocked(4, 5) and login_blocked(5, 5) and login_blocked(9, 5)


def test_session_expiry_boundaries() -> None:
    assert session_valid(100, 100, 480)
    assert session_valid(100, 579, 480)
    assert not session_valid(100, 580, 480)
    assert not session_valid(100, 99, 480)


@given(st.text())
def test_normalized_email_is_idempotent(email: str) -> None:
    assert normalize_email(normalize_email(email)) == normalize_email(email)


@given(st.integers(min_value=0, max_value=10**6), st.integers(min_value=1, max_value=10**4))
def test_window_start_is_before_now(now_total: int, window: int) -> None:
    assert window_start(now_total, window) == now_total - window


@given(st.integers(min_value=0, max_value=10**5), st.integers(min_value=0, max_value=1439))
def test_minutes_of_is_monotonic(day: int, minute: int) -> None:
    assert minutes_of(Now(day, minute)) < minutes_of(Now(day + 1, minute))
