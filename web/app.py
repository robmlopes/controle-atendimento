"""FastAPI application factory."""

import logging
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

from adapters.argon_hasher import ArgonHasher
from adapters.sqlite_admin import SqliteAdmin
from adapters.sqlite_agenda import SqliteAgenda
from adapters.sqlite_auth import SqliteLoginAttempts, SqliteOwners, SqliteSessions
from adapters.sqlite_booking import SqliteBookings
from adapters.sqlite_catalog import SqliteCatalog
from adapters.sqlite_db import Database
from adapters.sqlite_financial import SqliteFinancial
from adapters.system_clock import SecureTokens, SystemClock
from web import (
    auth,
    panel,
    panel_agenda,
    panel_booking_manual,
    panel_business,
    panel_financial,
    panel_people,
    panel_schedule,
    public_book,
    public_pages,
    public_view,
)
from web.services import Services, render

logger = logging.getLogger(__name__)
TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def database_error(request: Request, exc: Exception) -> Response:
    logger.error("request failed because the database is unavailable: %s", request.url.path, exc_info=exc)
    return render(request, "erro.html", {"message": "Serviço temporariamente indisponível. Tente novamente."}, 503)


def create_app(services: Services) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.services = services
    app.state.templates = TEMPLATES
    app.add_exception_handler(sqlite3.Error, database_error)
    for module in (
        auth,
        panel,
        panel_agenda,
        panel_booking_manual,
        panel_financial,
        panel_business,
        panel_people,
        panel_schedule,
        public_pages,
        public_book,
        public_view,
    ):
        app.include_router(module.router)
    return app


def default_app() -> FastAPI:
    """Production entry point: `uvicorn --factory web.app:default_app`. Set CONTROLE_DB (and CONTROLE_HTTPS=1)."""
    db = Database(os.environ["CONTROLE_DB"])
    db.migrate()
    hasher = ArgonHasher()
    catalog = SqliteCatalog(db)
    agenda = SqliteAgenda(db)
    bookings = SqliteBookings(db)
    owners = SqliteOwners(db)
    services = Services(
        owners=owners,
        owner_write=owners,
        hasher=hasher,
        sessions=SqliteSessions(db),
        attempts=SqliteLoginAttempts(db),
        clock=SystemClock(),
        tokens=SecureTokens(),
        catalog=catalog,
        catalog_write=catalog,
        admin=SqliteAdmin(db),
        agenda=agenda,
        agenda_admin=agenda,
        financial=SqliteFinancial(db),
        bookings=bookings,
        booking_write=bookings,
        dummy_hash=hasher.hash("dummy-password-for-timing"),
        cookie_secure=os.environ.get("CONTROLE_HTTPS") == "1",
    )
    return create_app(services)
