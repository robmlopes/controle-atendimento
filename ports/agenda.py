from typing import Protocol

from domain.models import AgendaItem


class AgendaRead(Protocol):
    def agenda(
        self, business_id: int, from_day: int, to_day: int, professional_id: int | None = None
    ) -> tuple[AgendaItem, ...]:
        """Bookings of the business between the two days (inclusive), ordered by day and start."""
        ...


class AgendaAdmin(Protocol):
    def complete_booking(self, business_id: int, booking_id: int, professional_id: int | None = None) -> bool:
        """Mark a confirmed booking as completed. Returns True if updated."""
        ...

    def cancel_for_business(self, business_id: int, booking_id: int, professional_id: int | None = None) -> bool:
        """Cancel a booking of this business. False when the booking is not in the business. Idempotent."""
        ...
