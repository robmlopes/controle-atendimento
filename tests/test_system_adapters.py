from datetime import date

from adapters.system_clock import SecureTokens, SystemClock


def test_clock_matches_domain_day_model() -> None:
    now = SystemClock().now()
    assert 0 <= now.minute < 1440
    assert date.fromordinal(now.day + 1).weekday() == now.day % 7


def test_tokens_are_long_and_unique() -> None:
    tokens = SecureTokens()
    first, second = tokens.new_token(), tokens.new_token()
    assert first != second and len(first) >= 40
