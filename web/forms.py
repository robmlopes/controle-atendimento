"""Parsing and formatting helpers for web forms (date handling lives here: the domain has no datetime)."""

import re
from datetime import date

from domain.models import DayLimit

WEEKDAYS = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")
ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
MAX_DIGITS = 9


def to_int(text: str) -> int | None:
    value = text.strip()
    if value.isascii() and value.isdigit() and len(value) <= MAX_DIGITS:
        return int(value)
    return None


def parse_day(text: str) -> int | None:
    """'YYYY-MM-DD' -> domain day (0 = Monday 0001-01-01)."""
    value = text.strip()
    if not ISO_DATE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value).toordinal() - 1
    except ValueError:
        return None


def iso_day(day: int) -> str:
    return date.fromordinal(day + 1).isoformat()


def br_day(day: int) -> str:
    moment = date.fromordinal(day + 1)
    return f"{moment.day:02d}/{moment.month:02d}/{moment.year}"


def weekday_name(day: int) -> str:
    return WEEKDAYS[day % 7]


def whole_day(start_min: int, end_min: int) -> bool:
    return start_min == 0 and end_min == DayLimit.MINUTES


def digits_only(text: str) -> str:
    return "".join(ch for ch in text if ch.isascii() and ch.isdigit())
