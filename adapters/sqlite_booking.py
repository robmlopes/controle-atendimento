"""SQLite implementation of the BookingRead and BookingWrite ports. Booking is atomic."""

from typing import Any

from adapters.sqlite_db import Database
from domain.models import Booked, Booking, BookingStatus, BookingView, NewBooking, SlotTaken

COLUMNS = (
    "id, professional_id, service_id, day, start_min, end_min, customer_name, customer_phone, status, cancel_token"
)


def _booking(r: tuple[Any, ...]) -> Booking:
    return Booking(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9])


class SqliteBookings:
    def __init__(self, db: Database) -> None:
        self.db = db

    def for_day(self, professional_id: int, day: int) -> tuple[Booking, ...]:
        with self.db.connection() as conn:
            rows = conn.execute(
                f"SELECT {COLUMNS} FROM bookings WHERE professional_id = ? AND day = ? ORDER BY start_min",
                (professional_id, day),
            ).fetchall()
        return tuple(_booking(r) for r in rows)

    def by_token(self, token: str) -> Booking | None:
        with self.db.connection() as conn:
            row = conn.execute(f"SELECT {COLUMNS} FROM bookings WHERE cancel_token = ?", (token,)).fetchone()
        return None if row is None else _booking(row)

    def create(self, new: NewBooking) -> Booked | SlotTaken:
        """Check overlap and insert inside one write transaction (BEGIN IMMEDIATE serialises writers)."""
        with self.db.connection(write=True) as conn:
            clash = conn.execute(
                "SELECT 1 FROM bookings WHERE professional_id = ? AND day = ? AND status = ?"
                " AND start_min < ? AND ? < end_min LIMIT 1",
                (new.professional_id, new.day, BookingStatus.CONFIRMED, new.end_min, new.start_min),
            ).fetchone()
            if clash is not None:
                return SlotTaken(new.professional_id)
            cur = conn.execute(
                "INSERT INTO bookings(professional_id, service_id, day, start_min, end_min, customer_name,"
                " customer_phone, status, cancel_token) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    new.professional_id,
                    new.service_id,
                    new.day,
                    new.start_min,
                    new.end_min,
                    new.customer_name,
                    new.customer_phone,
                    BookingStatus.CONFIRMED,
                    new.cancel_token,
                ),
            )
        booking = Booking(
            int(cur.lastrowid or 0),
            new.professional_id,
            new.service_id,
            new.day,
            new.start_min,
            new.end_min,
            new.customer_name,
            new.customer_phone,
            BookingStatus.CONFIRMED,
            new.cancel_token,
        )
        return Booked(booking)

    def view_by_token(self, token: str) -> BookingView | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT b.id, b.professional_id, b.service_id, b.day, b.start_min, b.end_min, b.customer_name,"
                " b.customer_phone, b.status, b.cancel_token, p.name, s.name, bus.name, bus.slug, bus.whatsapp"
                " FROM bookings b JOIN professionals p ON p.id = b.professional_id"
                " JOIN services s ON s.id = b.service_id JOIN businesses bus ON bus.id = p.business_id"
                " WHERE b.cancel_token = ?",
                (token,),
            ).fetchone()
        if row is None:
            return None
        return BookingView(_booking(row[:10]), row[10], row[11], row[12], row[13], row[14])

    def active_count_for_phone(self, business_id: int, phone: str, from_day: int) -> int:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM bookings b JOIN professionals p ON p.id = b.professional_id"
                " WHERE p.business_id = ? AND b.customer_phone = ? AND b.status = ? AND b.day >= ?",
                (business_id, phone, BookingStatus.CONFIRMED, from_day),
            ).fetchone()
        return int(row[0])

    def cancel(self, token: str) -> Booking | None:
        """Idempotent: cancelling an already cancelled booking returns its current state."""
        with self.db.connection(write=True) as conn:
            conn.execute("UPDATE bookings SET status = ? WHERE cancel_token = ?", (BookingStatus.CANCELLED, token))
        return self.by_token(token)
