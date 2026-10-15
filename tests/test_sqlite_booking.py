import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from adapters.sqlite_booking import SqliteBookings
from adapters.sqlite_catalog import SqliteCatalog
from adapters.sqlite_db import Database
from domain.models import Block, Booked, NewBooking, SlotTaken, WeeklyRule


def _db(tmp_path: Path) -> Database:
    db = Database(str(tmp_path / "app.db"))
    db.migrate()
    return db


def _new(token: str, start: int = 600, end: int = 630) -> NewBooking:
    return NewBooking(1, 1, 5, start, end, "Ana", "+5511999999999", token)


def _seed(db: Database) -> None:
    catalog = SqliteCatalog(db)
    business = catalog.add_business("barbearia", "Barbearia")
    pro = catalog.add_professional(business.id, "Zé")
    service = catalog.add_service(business.id, "Corte", 30, None)
    catalog.link_service(pro.id, service.id)


def test_catalog_round_trip(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed(db)
    catalog = SqliteCatalog(db)
    business = catalog.business_by_slug("barbearia")
    assert business is not None and catalog.business_by_slug("nope") is None
    pros = catalog.professionals(business.id)
    assert [p.name for p in pros] == ["Zé"]
    assert [s.name for s in catalog.services_of(pros[0].id)] == ["Corte"]
    catalog.add_rule(WeeklyRule(pros[0].id, 0, 540, 720))
    catalog.add_block(Block(pros[0].id, 5, 0, 1440))
    assert len(catalog.rules(pros[0].id)) == 1 and len(catalog.blocks(pros[0].id, 5)) == 1
    assert catalog.blocks(pros[0].id, 6) == ()
    assert catalog.service(999) is None


def test_overlap_is_rejected_and_adjacent_is_allowed(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed(db)
    bookings = SqliteBookings(db)
    assert isinstance(bookings.create(_new("t1")), Booked)
    assert isinstance(bookings.create(_new("t2", 615, 645)), SlotTaken)
    assert isinstance(bookings.create(_new("t3", 630, 660)), Booked)


def test_cancel_frees_slot_and_is_idempotent(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed(db)
    bookings = SqliteBookings(db)
    bookings.create(_new("t1"))
    first = bookings.cancel("t1")
    second = bookings.cancel("t1")
    assert first is not None and second is not None and second.status == "cancelled"
    assert bookings.cancel("unknown") is None
    assert isinstance(bookings.create(_new("t2")), Booked)
    assert len(bookings.for_day(1, 5)) == 2


def test_concurrent_bookings_of_same_slot_produce_one_winner(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed(db)
    bookings = SqliteBookings(db)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda i: bookings.create(_new(f"tok{i}")), range(8)))
    assert sum(isinstance(r, Booked) for r in results) == 1
    assert sum(isinstance(r, SlotTaken) for r in results) == 7


def test_memory_database_is_rejected() -> None:
    with pytest.raises(ValueError):
        Database(":memory:")


def test_database_errors_are_logged_and_raised(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    db = Database(str(tmp_path / "missing.db"))
    with caplog.at_level(logging.ERROR), pytest.raises(sqlite3.Error), db.connection() as conn:
        conn.execute("SELECT * FROM table_that_does_not_exist")
    assert "database operation failed" in caplog.text
