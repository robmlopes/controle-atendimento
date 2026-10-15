"""Pure scheduling entities.

Time model (no `datetime` in the domain):
- a day is an integer day number where day 0 is a Monday, so ``weekday = day % 7`` (0 = Monday).
  Adapters convert with ``date.toordinal() - 1`` (0001-01-01 is a Monday);
- a time of day is an integer number of minutes since midnight, in ``[0, DayLimit.MINUTES]``.
"""

from dataclasses import dataclass
from enum import StrEnum


class BookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class UserRole(StrEnum):
    OWNER = "owner"
    PROFESSIONAL = "professional"


class DayLimit:
    MINUTES = 1440


@dataclass(frozen=True)
class Business:
    id: int
    slug: str
    name: str
    whatsapp: str | None = None


@dataclass(frozen=True)
class Professional:
    id: int
    business_id: int
    name: str
    active: bool
    commission_pct: int = 100


@dataclass(frozen=True)
class Service:
    id: int
    business_id: int
    name: str
    duration_min: int
    price_cents: int | None


@dataclass(frozen=True)
class ProfessionalService:
    professional_id: int
    service_id: int


@dataclass(frozen=True)
class WeeklyRule:
    """Recurring availability range: weekday 0-6 (0 = Monday), minutes since midnight."""

    professional_id: int
    weekday: int
    start_min: int
    end_min: int


@dataclass(frozen=True)
class Block:
    """Unavailable range on one day. A whole-day block spans 0 to DayLimit.MINUTES."""

    professional_id: int
    day: int
    start_min: int
    end_min: int


@dataclass(frozen=True)
class Booking:
    id: int
    professional_id: int
    service_id: int
    day: int
    start_min: int
    end_min: int
    customer_name: str
    customer_phone: str
    status: str
    cancel_token: str


@dataclass(frozen=True)
class Now:
    """Current instant as supplied by the Clock port (same day/minute model as the rest of the domain)."""

    day: int
    minute: int


@dataclass(frozen=True)
class NewBooking:
    professional_id: int
    service_id: int
    day: int
    start_min: int
    end_min: int
    customer_name: str
    customer_phone: str
    cancel_token: str


@dataclass(frozen=True)
class Booked:
    booking: Booking


@dataclass(frozen=True)
class SlotTaken:
    """The requested range overlaps a confirmed booking of the same professional."""

    professional_id: int


@dataclass(frozen=True)
class AgendaItem:
    """A booking together with the names the owner needs to read the agenda."""

    booking: Booking
    professional_name: str
    service_name: str


@dataclass(frozen=True)
class BookingView:
    """What the customer sees on the confirmation page: the booking plus the names around it."""

    booking: Booking
    professional_name: str
    service_name: str
    business_name: str
    business_slug: str
    business_whatsapp: str | None


@dataclass(frozen=True)
class MovementItem:
    booking_id: int
    day: int
    start_min: int
    end_min: int
    customer_name: str
    customer_phone: str
    professional_id: int
    professional_name: str
    service_name: str
    price_cents: int | None
    commission_pct: int
    commission_cents: int
    status: str


@dataclass(frozen=True)
class FinancialSummary:
    realized_cents: int
    projected_cents: int
    gross_realized_cents: int
    completed_count: int
    projected_count: int
