"""Pure rules of the public booking flow: phone, slug, booking window and per-phone limit."""

from aif import contract


class PublicPolicy:
    SLOT_STEP = 15
    MAX_DAYS_AHEAD = 60
    MAX_ACTIVE_PER_PHONE = 3
    MIN_SLUG = 3
    MAX_SLUG = 40
    PHONE_CHARS = frozenset("0123456789 ()-+.")
    DIGITS = frozenset("0123456789")
    SLUG_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")
    LANDLINE_START = frozenset("2345")
    BR_LENGTHS = (10, 11)
    WITH_COUNTRY_LENGTHS = (12, 13)


def _is_brazilian_number(digits: str) -> bool:
    """DDD (2 digits, none zero) + 8-digit landline (starts 2-5) or 9-digit mobile (starts 9)."""
    if len(digits) not in PublicPolicy.BR_LENGTHS or "0" in digits[:2]:
        return False
    return digits[2] == "9" if len(digits) == 11 else digits[2] in PublicPolicy.LANDLINE_START


@contract(
    ensures=lambda r: r is None or (r.startswith("+55") and r[1:].isdigit() and len(r) in (13, 14)),
    effects=[],
)
def normalize_phone(text: str) -> str | None:
    """Brazilian phone typed in any common format -> '+55DDDNUMBER', or None when it is not valid."""
    cleaned = text.strip()
    if not cleaned or "+" in cleaned[1:] or any(ch not in PublicPolicy.PHONE_CHARS for ch in cleaned):
        return None
    digits = "".join(ch for ch in cleaned if ch in PublicPolicy.DIGITS)
    with_country = len(digits) in PublicPolicy.WITH_COUNTRY_LENGTHS and digits.startswith("55")
    if cleaned.startswith("+") and not with_country:
        return None
    local = digits[2:] if with_country else digits
    return "+55" + local if _is_brazilian_number(local) else None


@contract(
    ensures=lambda r, slug: not r or (slug == slug.lower() and slug.isascii() and " " not in slug),
    effects=[],
)
def is_valid_slug(slug: str) -> bool:
    """Lowercase letters, digits and hyphens; 3 to 40 characters; no hyphen at either end."""
    return (
        PublicPolicy.MIN_SLUG <= len(slug) <= PublicPolicy.MAX_SLUG
        and all(ch in PublicPolicy.SLUG_CHARS for ch in slug)
        and not slug.startswith("-")
        and not slug.endswith("-")
    )


@contract(
    ensures=lambda r, day, today: r == (today <= day <= today + PublicPolicy.MAX_DAYS_AHEAD),
    effects=[],
)
def day_in_window(day: int, today: int) -> bool:
    return today <= day <= today + PublicPolicy.MAX_DAYS_AHEAD


@contract(
    requires=lambda duration_min: duration_min > 0,
    ensures=lambda r, start_min, duration_min: r - start_min == duration_min,
    effects=[],
)
def booking_end(start_min: int, duration_min: int) -> int:
    return start_min + duration_min


@contract(
    ensures=lambda r, active_count: r == (active_count < PublicPolicy.MAX_ACTIVE_PER_PHONE),
    effects=[],
)
def can_book_more(active_count: int) -> bool:
    return active_count < PublicPolicy.MAX_ACTIVE_PER_PHONE
