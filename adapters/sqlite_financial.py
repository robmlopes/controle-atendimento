"""SQLite implementation of the FinancialRead port."""

from typing import Any

from adapters.sqlite_db import Database
from domain.models import BookingStatus, FinancialSummary, MovementItem
from domain.panel import compute_commission


def _to_movement(r: tuple[Any, ...]) -> MovementItem:
    price = None if r[9] is None else int(r[9])
    pct = int(r[10])
    status = str(r[11])
    comm = compute_commission(price, pct) if status != BookingStatus.CANCELLED else 0
    return MovementItem(
        booking_id=int(r[0]),
        day=int(r[1]),
        start_min=int(r[2]),
        end_min=int(r[3]),
        customer_name=str(r[4]),
        customer_phone=str(r[5]),
        professional_id=int(r[6]),
        professional_name=str(r[7]),
        service_name=str(r[8]),
        price_cents=price,
        commission_pct=pct,
        commission_cents=comm,
        status=status,
    )


class SqliteFinancial:
    def __init__(self, db: Database) -> None:
        self.db = db

    def statement(
        self, business_id: int, from_day: int, to_day: int, professional_id: int | None = None
    ) -> tuple[MovementItem, ...]:
        q = (
            "SELECT b.id, b.day, b.start_min, b.end_min, b.customer_name, b.customer_phone,"
            " p.id, p.name, s.name, s.price_cents, p.commission_pct, b.status"
            " FROM bookings b"
            " JOIN professionals p ON p.id = b.professional_id"
            " JOIN services s ON s.id = b.service_id"
            " WHERE p.business_id = ? AND b.day BETWEEN ? AND ?"
        )
        params: list[object] = [business_id, from_day, to_day]
        if professional_id is not None:
            q += " AND b.professional_id = ?"
            params.append(professional_id)
        q += " ORDER BY b.day DESC, b.start_min DESC, b.id DESC"

        with self.db.connection() as conn:
            rows = conn.execute(q, params).fetchall()
        return tuple(_to_movement(r) for r in rows)

    def summary(
        self, business_id: int, from_day: int, to_day: int, professional_id: int | None = None
    ) -> FinancialSummary:
        items = self.statement(business_id, from_day, to_day, professional_id)
        realized = 0
        projected = 0
        gross_realized = 0
        completed_count = 0
        projected_count = 0

        for item in items:
            if item.status == BookingStatus.COMPLETED:
                realized += item.commission_cents
                gross_realized += item.price_cents or 0
                completed_count += 1
            elif item.status == BookingStatus.CONFIRMED:
                projected += item.commission_cents
                projected_count += 1

        return FinancialSummary(
            realized_cents=realized,
            projected_cents=projected,
            gross_realized_cents=gross_realized,
            completed_count=completed_count,
            projected_count=projected_count,
        )
