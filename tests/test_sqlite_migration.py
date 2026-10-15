import sqlite3
from pathlib import Path

from adapters.sqlite_booking import SqliteBookings
from adapters.sqlite_db import Database

LEGACY = """
CREATE TABLE businesses (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL);
CREATE TABLE professionals (id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL, name TEXT NOT NULL);
CREATE TABLE services (id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL, name TEXT NOT NULL,
    duration_min INTEGER NOT NULL);
CREATE TABLE bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, professional_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL, day INTEGER NOT NULL, start_min INTEGER NOT NULL, end_min INTEGER NOT NULL,
    customer_name TEXT NOT NULL, customer_phone TEXT NOT NULL);
INSERT INTO businesses(slug, name) VALUES ('old', 'Old Shop');
INSERT INTO professionals(business_id, name) VALUES (1, 'Maria');
INSERT INTO services(business_id, name, duration_min) VALUES (1, 'Corte', 30);
INSERT INTO bookings(professional_id, service_id, day, start_min, end_min, customer_name, customer_phone)
    VALUES (1, 1, 7, 600, 630, 'Legacy', '+5511911111111'), (1, 1, 7, 700, 730, 'Legacy2', '+5511922222222');
"""


def _legacy(tmp_path: Path) -> str:
    path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(path)
    conn.executescript(LEGACY)
    conn.commit()
    conn.close()
    return path


def _columns(path: str, table: str) -> set[str]:
    conn = sqlite3.connect(path)
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    conn.close()
    return cols


def test_migration_upgrades_legacy_database_without_losing_rows(tmp_path: Path) -> None:
    path = _legacy(tmp_path)
    Database(path).migrate()
    assert {"status", "cancel_token"} <= _columns(path, "bookings")
    assert {"active"} <= _columns(path, "professionals")
    assert {"price_cents", "active"} <= _columns(path, "services")
    assert {"whatsapp"} <= _columns(path, "businesses")
    rows = SqliteBookings(Database(path)).for_day(1, 7)
    assert [r.customer_name for r in rows] == ["Legacy", "Legacy2"]
    assert all(r.status == "confirmed" for r in rows)
    assert len({r.cancel_token for r in rows}) == 2 and all(r.cancel_token for r in rows)


def test_legacy_services_stay_visible_after_migration(tmp_path: Path) -> None:
    path = _legacy(tmp_path)
    Database(path).migrate()
    from adapters.sqlite_admin import SqliteAdmin

    assert [s.name for s in SqliteAdmin(Database(path)).business_services(1)] == ["Corte"]


def test_migration_is_idempotent(tmp_path: Path) -> None:
    path = _legacy(tmp_path)
    db = Database(path)
    db.migrate()
    tokens = [r.cancel_token for r in SqliteBookings(db).for_day(1, 7)]
    db.migrate()
    db.migrate()
    assert [r.cancel_token for r in SqliteBookings(db).for_day(1, 7)] == tokens
