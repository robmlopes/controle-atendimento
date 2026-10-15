"""SQLite implementation of AgendaRead and AgendaAdmin, scoped to one business."""

from adapters.sqlite_db import Database
from domain.models import AgendaItem, Booking, BookingStatus


class SqliteAgenda:
    def __init__(self, db: Database) -> None:
        self.db = db

    def agenda(
        self, business_id: int, from_day: int, to_day: int, professional_id: int | None = None
    ) -> tuple[AgendaItem, ...]:
        query = (
            "SELECT b.id, b.professional_id, b.service_id, b.day, b.start_min, b.end_min, b.customer_name,"
            " b.customer_phone, b.status, b.cancel_token, p.name, s.name FROM bookings b"
            " JOIN professionals p ON p.id = b.professional_id JOIN services s ON s.id = b.service_id"
            " WHERE p.business_id = ? AND b.status IN (?, ?) AND b.day BETWEEN ? AND ?"
        )
        params: list[object] = [business_id, BookingStatus.CONFIRMED, BookingStatus.COMPLETED, from_day, to_day]
        if professional_id is not None:
            query += " AND b.professional_id = ?"
            params.append(professional_id)
        query += " ORDER BY b.day, b.start_min, b.id"

        with self.db.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return tuple(AgendaItem(Booking(*r[:10]), r[10], r[11]) for r in rows)

    def complete_booking(self, business_id: int, booking_id: int, professional_id: int | None = None) -> bool:
        cond = "b.id = ? AND p.business_id = ? AND b.status = ?"
        params: list[object] = [booking_id, business_id, BookingStatus.CONFIRMED]
        if professional_id is not None:
            cond += " AND b.professional_id = ?"
            params.append(professional_id)

        with self.db.connection(write=True) as conn:
            row = conn.execute(
                f"SELECT 1 FROM bookings b JOIN professionals p ON p.id = b.professional_id WHERE {cond}",
                params,
            ).fetchone()
            if row is None:
                return False
            conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (BookingStatus.COMPLETED, booking_id))
        return True

    def cancel_for_business(self, business_id: int, booking_id: int, professional_id: int | None = None) -> bool:
        cond = "b.id = ? AND p.business_id = ?"
        params: list[object] = [booking_id, business_id]
        if professional_id is not None:
            cond += " AND b.professional_id = ?"
            params.append(professional_id)

        with self.db.connection(write=True) as conn:
            row = conn.execute(
                f"SELECT 1 FROM bookings b JOIN professionals p ON p.id = b.professional_id WHERE {cond}",
                params,
            ).fetchone()
            if row is None:
                return False
            conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (BookingStatus.CANCELLED, booking_id))
        return True
