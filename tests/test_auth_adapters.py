import sqlite3
from pathlib import Path

from adapters.argon_hasher import ArgonHasher
from adapters.sqlite_auth import SqliteLoginAttempts, SqliteOwners, SqliteSessions
from adapters.sqlite_catalog import SqliteCatalog
from adapters.sqlite_db import Database


def _db(tmp_path: Path) -> Database:
    db = Database(str(tmp_path / "auth.db"))
    db.migrate()
    return db


def test_hasher_verifies_only_the_right_password() -> None:
    hasher = ArgonHasher()
    stored = hasher.hash("correct horse")
    assert stored.startswith("$argon2") and "correct horse" not in stored
    assert hasher.verify(stored, "correct horse")
    assert not hasher.verify(stored, "wrong")
    assert not hasher.verify("not-a-hash", "correct horse")


def test_owner_round_trip_and_unique_email(tmp_path: Path) -> None:
    db = _db(tmp_path)
    business = SqliteCatalog(db).add_business("loja", "Loja")
    owners = SqliteOwners(db)
    created = owners.add_owner(business.id, "a@b.com", "hash")
    assert owners.owner_by_email("a@b.com") == created and owners.owner_by_email("x@y.com") is None
    try:
        owners.add_owner(business.id, "a@b.com", "other")
    except sqlite3.IntegrityError:
        return
    raise AssertionError("duplicate e-mail accepted")


def test_session_stores_only_a_digest_and_can_be_deleted(tmp_path: Path) -> None:
    db = _db(tmp_path)
    business = SqliteCatalog(db).add_business("loja", "Loja")
    owner = SqliteOwners(db).add_owner(business.id, "a@b.com", "hash")
    sessions = SqliteSessions(db)
    sessions.create(owner, "raw-token", "csrf", 1000)
    info = sessions.get("raw-token")
    assert info is not None and info.business_id == business.id and info.csrf_token == "csrf"
    assert sessions.get("other") is None
    with db.connection() as conn:
        stored = [row[0] for row in conn.execute("SELECT token_hash FROM sessions")]
    assert stored and "raw-token" not in stored[0]
    sessions.delete("raw-token")
    assert sessions.get("raw-token") is None


def test_login_attempts_count_within_window_and_clear(tmp_path: Path) -> None:
    attempts = SqliteLoginAttempts(_db(tmp_path))
    for at in (100, 101, 102):
        attempts.record_failure("k", at)
    attempts.record_failure("other", 102)
    assert attempts.failures_since("k", 0) == 3
    assert attempts.failures_since("k", 100) == 2
    attempts.clear("k")
    assert attempts.failures_since("k", 0) == 0 and attempts.failures_since("other", 0) == 1
