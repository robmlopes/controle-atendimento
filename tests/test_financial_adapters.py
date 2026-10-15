from pathlib import Path

from adapters.sqlite_agenda import SqliteAgenda
from adapters.sqlite_booking import SqliteBookings
from adapters.sqlite_catalog import SqliteCatalog
from adapters.sqlite_db import Database
from adapters.sqlite_financial import SqliteFinancial
from domain.models import BookingStatus, NewBooking


def test_financial_summary_and_statement(tmp_path: Path) -> None:
    db = Database(str(tmp_path / "fin.db"))
    db.migrate()

    catalog = SqliteCatalog(db)
    b = catalog.add_business("barbearia", "Barbearia")
    p1 = catalog.add_professional(b.id, "Carlos", commission_pct=60)
    p2 = catalog.add_professional(b.id, "Marcos", commission_pct=50)

    s1 = catalog.add_service(b.id, "Corte", 30, 5000)  # R$ 50
    s2 = catalog.add_service(b.id, "Barba", 30, 3000)  # R$ 30

    bookings = SqliteBookings(db)
    agenda = SqliteAgenda(db)
    financial = SqliteFinancial(db)

    # p1 bookings
    b1 = bookings.create(NewBooking(p1.id, s1.id, 10, 600, 630, "Cli 1", "1191", "t1"))
    b2 = bookings.create(NewBooking(p1.id, s2.id, 10, 660, 690, "Cli 2", "1192", "t2"))
    # p2 booking
    b3 = bookings.create(NewBooking(p2.id, s1.id, 10, 600, 630, "Cli 3", "1193", "t3"))

    assert hasattr(b1, "booking") and hasattr(b2, "booking") and hasattr(b3, "booking")

    # Complete b1 (Carlos, Corte 5000 * 60% = 3000)
    assert agenda.complete_booking(b.id, b1.booking.id) is True
    # Cancel b2 (Carlos, Barba 3000)
    assert agenda.cancel_for_business(b.id, b2.booking.id) is True
    # b3 remains CONFIRMED (Marcos, Corte 5000 * 50% = 2500)

    # Carlos summary: realized = 3000, projected = 0 (b2 is cancelled), gross = 5000
    sum_p1 = financial.summary(b.id, 10, 10, p1.id)
    assert sum_p1.realized_cents == 3000
    assert sum_p1.projected_cents == 0
    assert sum_p1.gross_realized_cents == 5000
    assert sum_p1.completed_count == 1
    assert sum_p1.projected_count == 0

    # Business overall summary (both pros)
    sum_all = financial.summary(b.id, 10, 10)
    assert sum_all.realized_cents == 3000
    assert sum_all.projected_cents == 2500
    assert sum_all.gross_realized_cents == 5000
    assert sum_all.completed_count == 1
    assert sum_all.projected_count == 1

    # Statement checks
    stmt = financial.statement(b.id, 10, 10, p1.id)
    assert len(stmt) == 2
    assert stmt[0].status in (BookingStatus.COMPLETED, BookingStatus.CANCELLED)
