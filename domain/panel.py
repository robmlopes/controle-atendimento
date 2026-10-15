"""Pure validation and parsing rules for the owner panel forms."""

from aif import contract

from domain.models import DayLimit


class PanelLimits:
    MAX_NAME = 80
    MIN_DURATION = 5
    MAX_DURATION = 480
    MAX_PRICE_CENTS = 1_000_000
    MAX_PRICE_DIGITS = 7
    LAST_WEEKDAY = 6


@contract(ensures=lambda r, name: r == " ".join(name.split()), effects=[])
def clean_name(name: str) -> str:
    return " ".join(name.split())


@contract(ensures=lambda r, name: not r or 1 <= len(name) <= PanelLimits.MAX_NAME, effects=[])
def is_valid_name(name: str) -> bool:
    return name == clean_name(name) and name.isprintable() and 1 <= len(name) <= PanelLimits.MAX_NAME


@contract(
    ensures=lambda r, duration_min: r == (PanelLimits.MIN_DURATION <= duration_min <= PanelLimits.MAX_DURATION),
    effects=[],
)
def is_valid_duration(duration_min: int) -> bool:
    return PanelLimits.MIN_DURATION <= duration_min <= PanelLimits.MAX_DURATION


@contract(
    ensures=lambda r, price_cents: r == (price_cents is None or 0 <= price_cents <= PanelLimits.MAX_PRICE_CENTS),
    effects=[],
)
def is_valid_price(price_cents: int | None) -> bool:
    return price_cents is None or 0 <= price_cents <= PanelLimits.MAX_PRICE_CENTS


@contract(
    ensures=lambda r, weekday: r == (0 <= weekday <= PanelLimits.LAST_WEEKDAY),
    effects=[],
)
def is_valid_weekday(weekday: int) -> bool:
    return 0 <= weekday <= PanelLimits.LAST_WEEKDAY


@contract(
    ensures=lambda r, start_min, end_min: r == (0 <= start_min < end_min <= DayLimit.MINUTES),
    effects=[],
)
def is_valid_range(start_min: int, end_min: int) -> bool:
    return 0 <= start_min < end_min <= DayLimit.MINUTES


@contract(ensures=lambda r: r is None or 0 <= r < DayLimit.MINUTES, effects=[])
def parse_time(text: str) -> int | None:
    """Parse 'H:MM' or 'HH:MM' (ASCII digits only) into minutes since midnight."""
    hours, separator, minutes = text.strip().partition(":")
    digits = hours + minutes
    if not separator or len(hours) not in (1, 2) or len(minutes) != 2:
        return None
    if not (digits.isascii() and digits.isdigit()):
        return None
    return int(hours) * 60 + int(minutes) if int(hours) < 24 and int(minutes) < 60 else None


@contract(
    requires=lambda minute: 0 <= minute <= DayLimit.MINUTES,
    ensures=lambda r: len(r) == 5 and r[2] == ":",
    effects=[],
)
def format_time(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


@contract(ensures=lambda r: r is None or 0 <= r <= PanelLimits.MAX_PRICE_CENTS, effects=[])
def parse_price(text: str) -> int | None:
    """Parse '12', '12,5' or '12.50' (at most 2 decimals) into cents."""
    whole, _, fraction = text.strip().replace(",", ".").partition(".")
    digits = whole + fraction
    if not whole or len(whole) > PanelLimits.MAX_PRICE_DIGITS or len(fraction) > 2:
        return None
    if not (digits.isascii() and digits.isdigit()):
        return None
    cents = int(whole) * 100 + int(fraction.ljust(2, "0"))
    return cents if cents <= PanelLimits.MAX_PRICE_CENTS else None


@contract(
    requires=lambda cents: cents >= 0,
    ensures=lambda r, cents: parse_price(r) == (cents if cents <= PanelLimits.MAX_PRICE_CENTS else None),
    effects=[],
)
def format_price(cents: int) -> str:
    return f"{cents // 100},{cents % 100:02d}"


@contract(ensures=lambda r, pct: r == (0 <= pct <= 100), effects=[])
def is_valid_commission(pct: int) -> bool:
    return 0 <= pct <= 100


@contract(
    requires=lambda price_cents, commission_pct: (
        0 <= commission_pct <= 100 and (price_cents is None or price_cents >= 0)
    ),
    ensures=lambda r, price_cents, commission_pct: r >= 0 and (price_cents is None or r <= price_cents),
    effects=[],
)
def compute_commission(price_cents: int | None, commission_pct: int) -> int:
    if price_cents is None or price_cents <= 0 or commission_pct <= 0:
        return 0
    return (price_cents * commission_pct + 50) // 100
