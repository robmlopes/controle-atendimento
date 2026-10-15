"""SQLite connection handling and idempotent, backward-compatible schema migration."""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

TABLES = (
    "CREATE TABLE IF NOT EXISTS businesses (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT NOT NULL UNIQUE,"
    " name TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS professionals (id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL"
    " REFERENCES businesses(id), name TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,"
    " commission_pct INTEGER NOT NULL DEFAULT 100)",
    "CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL"
    " REFERENCES businesses(id), name TEXT NOT NULL, duration_min INTEGER NOT NULL, price_cents INTEGER)",
    "CREATE TABLE IF NOT EXISTS professional_services (professional_id INTEGER NOT NULL REFERENCES professionals(id),"
    " service_id INTEGER NOT NULL REFERENCES services(id), PRIMARY KEY (professional_id, service_id))",
    "CREATE TABLE IF NOT EXISTS weekly_rules (id INTEGER PRIMARY KEY AUTOINCREMENT, professional_id INTEGER NOT NULL"
    " REFERENCES professionals(id), weekday INTEGER NOT NULL, start_min INTEGER NOT NULL, end_min INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS blocks (id INTEGER PRIMARY KEY AUTOINCREMENT, professional_id INTEGER NOT NULL"
    " REFERENCES professionals(id), day INTEGER NOT NULL, start_min INTEGER NOT NULL, end_min INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, professional_id INTEGER NOT NULL"
    " REFERENCES professionals(id), service_id INTEGER NOT NULL REFERENCES services(id), day INTEGER NOT NULL,"
    " start_min INTEGER NOT NULL, end_min INTEGER NOT NULL, customer_name TEXT NOT NULL,"
    " customer_phone TEXT NOT NULL, completed_at INTEGER)",
    "CREATE TABLE IF NOT EXISTS owners (id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL"
    " REFERENCES businesses(id), email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,"
    " role TEXT NOT NULL DEFAULT 'owner', professional_id INTEGER REFERENCES professionals(id))",
    "CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES owners(id),"
    " business_id INTEGER NOT NULL, csrf_token TEXT NOT NULL, created_total INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS login_failures (key TEXT NOT NULL, at_total INTEGER NOT NULL)",
)

# Columns added after the first schema version: (table, column, definition). Applied only when missing.
LATER_COLUMNS = (
    ("professionals", "active", "INTEGER NOT NULL DEFAULT 1"),
    ("professionals", "commission_pct", "INTEGER NOT NULL DEFAULT 100"),
    ("services", "price_cents", "INTEGER"),
    ("services", "active", "INTEGER NOT NULL DEFAULT 1"),
    ("businesses", "whatsapp", "TEXT"),
    ("bookings", "status", "TEXT NOT NULL DEFAULT 'confirmed'"),
    ("bookings", "cancel_token", "TEXT NOT NULL DEFAULT ''"),
    ("bookings", "completed_at", "INTEGER"),
    ("owners", "role", "TEXT NOT NULL DEFAULT 'owner'"),
    ("owners", "professional_id", "INTEGER REFERENCES professionals(id)"),
)

INDEXES = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_bookings_token ON bookings(cancel_token)",
    "CREATE INDEX IF NOT EXISTS ix_login_failures_key ON login_failures(key, at_total)",
    "CREATE INDEX IF NOT EXISTS ix_bookings_day ON bookings(professional_id, day, status)",
)


class Database:
    def __init__(self, path: str) -> None:
        if path == ":memory:" or path == "":
            raise ValueError("an on-disk database path is required; ':memory:' is not allowed")
        self.path = path

    @contextmanager
    def connection(self, write: bool = False) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield conn
            conn.execute("COMMIT")
        except sqlite3.Error:
            logger.error("database operation failed on %s", self.path, exc_info=True)
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def migrate(self) -> None:
        """Create missing tables, add missing columns, backfill tokens. Safe to run on every start."""
        with self.connection(write=True) as conn:
            for ddl in TABLES:
                conn.execute(ddl)
            for table, column, definition in LATER_COLUMNS:
                existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            conn.execute("UPDATE bookings SET cancel_token = lower(hex(randomblob(16))) WHERE cancel_token = ''")
            for ddl in INDEXES:
                conn.execute(ddl)
