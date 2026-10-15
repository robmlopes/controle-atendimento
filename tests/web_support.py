"""Shared fixtures for web tests: a real app over a temporary SQLite file and a controllable clock."""

import re
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from adapters.argon_hasher import ArgonHasher
from adapters.sqlite_admin import SqliteAdmin
from adapters.sqlite_agenda import SqliteAgenda
from adapters.sqlite_auth import SqliteLoginAttempts, SqliteOwners, SqliteSessions
from adapters.sqlite_booking import SqliteBookings
from adapters.sqlite_catalog import SqliteCatalog
from adapters.sqlite_db import Database
from adapters.sqlite_financial import SqliteFinancial
from adapters.system_clock import SecureTokens
from domain.models import Now
from web.app import create_app
from web.services import Services

PASSWORD = "senha-segura-1"


class FakeClock:
    def __init__(self) -> None:
        self.current = Now(100, 600)

    def now(self) -> Now:
        return self.current


@dataclass
class Env:
    client: TestClient
    clock: FakeClock
    db: Database
    catalog: SqliteCatalog
    hasher: ArgonHasher
    services: Services


def make_env(tmp_path: Path) -> Env:
    db = Database(str(tmp_path / "web.db"))
    db.migrate()
    hasher = ArgonHasher()
    catalog = SqliteCatalog(db)
    agenda = SqliteAgenda(db)
    bookings = SqliteBookings(db)
    owners = SqliteOwners(db)
    clock = FakeClock()
    services = Services(
        owners=owners,
        owner_write=owners,
        hasher=hasher,
        sessions=SqliteSessions(db),
        attempts=SqliteLoginAttempts(db),
        clock=clock,
        tokens=SecureTokens(),
        catalog=catalog,
        catalog_write=catalog,
        admin=SqliteAdmin(db),
        agenda=agenda,
        agenda_admin=agenda,
        financial=SqliteFinancial(db),
        bookings=bookings,
        booking_write=bookings,
        dummy_hash=hasher.hash("dummy"),
        cookie_secure=False,
    )
    client = TestClient(create_app(services), follow_redirects=False)
    return Env(client, clock, db, catalog, hasher, services)


def add_owner(env: Env, slug: str, email: str) -> int:
    business = env.catalog.add_business(slug, slug.title())
    SqliteOwners(env.db).add_owner(business.id, email, env.hasher.hash(PASSWORD))
    return business.id


def csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match
    return match.group(1)


def login(client: TestClient, email: str, password: str = PASSWORD) -> int:
    token = csrf(client.get("/login").text)
    response = client.post("/login", data={"email": email, "password": password, "csrf_token": token})
    return int(response.status_code)


def post(client: TestClient, url: str, data: dict[str, object], page_url: str = "/painel") -> int:
    """POST with the CSRF token taken from an already-rendered page of the logged-in session."""
    token = csrf(client.get(page_url).text)
    return int(client.post(url, data={**data, "csrf_token": token}).status_code)
