"""SQLite implementations of OwnerRead/Write, SessionStore and LoginAttempts."""

import hashlib

from adapters.sqlite_db import Database
from domain.auth import AuthPolicy, Owner, SessionInfo
from domain.models import DayLimit


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class SqliteOwners:
    def __init__(self, db: Database) -> None:
        self.db = db

    def owner_by_email(self, email: str) -> Owner | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT id, business_id, email, password_hash, role, professional_id FROM owners WHERE email = ?",
                (email,),
            ).fetchone()
        return None if row is None else Owner(row[0], row[1], row[2], row[3], str(row[4] or "owner"), row[5])

    def owner_by_professional(self, business_id: int, professional_id: int) -> Owner | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT id, business_id, email, password_hash, role, professional_id FROM owners"
                " WHERE business_id = ? AND professional_id = ?",
                (business_id, professional_id),
            ).fetchone()
        return None if row is None else Owner(row[0], row[1], row[2], row[3], str(row[4] or "owner"), row[5])

    def add_owner(
        self,
        business_id: int,
        email: str,
        password_hash: str,
        role: str = "owner",
        professional_id: int | None = None,
    ) -> Owner:
        with self.db.connection(write=True) as conn:
            cur = conn.execute(
                "INSERT INTO owners(business_id, email, password_hash, role, professional_id) VALUES (?, ?, ?, ?, ?)",
                (business_id, email, password_hash, role, professional_id),
            )
        return Owner(int(cur.lastrowid or 0), business_id, email, password_hash, role, professional_id)


class SqliteSessions:
    """Only a SHA-256 digest of the session token is stored."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, owner: Owner, token: str, csrf_token: str, created_total: int) -> None:
        with self.db.connection(write=True) as conn:
            conn.execute("DELETE FROM sessions WHERE created_total < ?", (created_total - AuthPolicy.SESSION_TTL_MIN,))
            conn.execute(
                "INSERT INTO sessions(token_hash, owner_id, business_id, csrf_token, created_total)"
                " VALUES (?, ?, ?, ?, ?)",
                (_digest(token), owner.id, owner.business_id, csrf_token, created_total),
            )

    def get(self, token: str) -> SessionInfo | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT s.owner_id, s.business_id, s.csrf_token, s.created_total, o.role, o.professional_id"
                " FROM sessions s JOIN owners o ON o.id = s.owner_id WHERE s.token_hash = ?",
                (_digest(token),),
            ).fetchone()
        return None if row is None else SessionInfo(row[0], row[1], row[2], row[3], str(row[4] or "owner"), row[5])

    def delete(self, token: str) -> None:
        with self.db.connection(write=True) as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_digest(token),))


class SqliteLoginAttempts:
    def __init__(self, db: Database) -> None:
        self.db = db

    def record_failure(self, key: str, at_total: int) -> None:
        with self.db.connection(write=True) as conn:
            conn.execute("DELETE FROM login_failures WHERE at_total < ?", (at_total - DayLimit.MINUTES,))
            conn.execute("INSERT INTO login_failures(key, at_total) VALUES (?, ?)", (key, at_total))

    def failures_since(self, key: str, since_total: int) -> int:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM login_failures WHERE key = ? AND at_total > ?", (key, since_total)
            ).fetchone()
        return int(row[0])

    def clear(self, key: str) -> None:
        with self.db.connection(write=True) as conn:
            conn.execute("DELETE FROM login_failures WHERE key = ?", (key,))
