"""Pure authentication rules: input validation, login throttling and session expiry."""

from dataclasses import dataclass

from aif import contract

from domain.models import DayLimit, Now


class AuthPolicy:
    MAX_FAILURES = 5
    WINDOW_MIN = 15
    SESSION_TTL_MIN = 480
    MIN_PASSWORD = 8
    MAX_PASSWORD = 128
    MAX_EMAIL = 254


@dataclass(frozen=True)
class Owner:
    id: int
    business_id: int
    email: str
    password_hash: str
    role: str = "owner"
    professional_id: int | None = None


@dataclass(frozen=True)
class SessionInfo:
    owner_id: int
    business_id: int
    csrf_token: str
    created_total: int
    role: str = "owner"
    professional_id: int | None = None


@contract(ensures=lambda r, email: r == r.strip() and r.lower() == r, effects=[])
def normalize_email(email: str) -> str:
    return email.strip().lower()


@contract(
    ensures=lambda r, email: not r or ("@" in email and email == "".join(email.split())),
    effects=[],
)
def is_valid_email(email: str) -> bool:
    local, separator, host = email.partition("@")
    no_spaces = email == "".join(email.split())
    host_ok = "." in host and "@" not in host and not host.startswith(".") and not host.endswith(".")
    return bool(separator) and bool(local) and no_spaces and host_ok and len(email) <= AuthPolicy.MAX_EMAIL


@contract(
    ensures=lambda r, password: not r or AuthPolicy.MIN_PASSWORD <= len(password) <= AuthPolicy.MAX_PASSWORD,
    effects=[],
)
def is_valid_password(password: str) -> bool:
    return AuthPolicy.MIN_PASSWORD <= len(password) <= AuthPolicy.MAX_PASSWORD


@contract(
    ensures=lambda r, now: r >= 0 and r // DayLimit.MINUTES == now.day and r % DayLimit.MINUTES == now.minute,
    effects=[],
)
def minutes_of(now: Now) -> int:
    """Absolute minute counter used to compare instants: day * 1440 + minute of day."""
    return now.day * DayLimit.MINUTES + now.minute


@contract(
    requires=lambda failures, max_failures: failures >= 0 and max_failures > 0,
    ensures=lambda r, failures, max_failures: r == (failures >= max_failures),
    effects=[],
)
def login_blocked(failures: int, max_failures: int) -> bool:
    return failures >= max_failures


@contract(
    requires=lambda window_min: window_min > 0,
    ensures=lambda r, now_total, window_min: now_total - r == window_min,
    effects=[],
)
def window_start(now_total: int, window_min: int) -> int:
    return now_total - window_min


@contract(
    requires=lambda ttl_min: ttl_min > 0,
    ensures=lambda r, created_total, now_total, ttl_min: not r or 0 <= now_total - created_total < ttl_min,
    effects=[],
)
def session_valid(created_total: int, now_total: int, ttl_min: int) -> bool:
    return 0 <= now_total - created_total < ttl_min
