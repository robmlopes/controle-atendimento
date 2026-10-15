from typing import Protocol

from domain.models import Booked, Booking, BookingView, NewBooking, SlotTaken


class BookingRead(Protocol):
    def for_day(self, professional_id: int, day: int) -> tuple[Booking, ...]: ...

    def by_token(self, token: str) -> Booking | None: ...

    def view_by_token(self, token: str) -> BookingView | None:
        """The booking with professional, service and business names, whatever its status."""
        ...

    def active_count_for_phone(self, business_id: int, phone: str, from_day: int) -> int:
        """Confirmed bookings of this business for the phone, on or after from_day."""
        ...


class BookingWrite(Protocol):
    def create(self, new: NewBooking) -> Booked | SlotTaken: ...

    def cancel(self, token: str) -> Booking | None: ...
