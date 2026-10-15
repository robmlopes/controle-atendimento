"""Wiring shared by all web routes: the ports a request may use, plus template rendering."""

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

from ports.admin import CatalogAdmin
from ports.agenda import AgendaAdmin, AgendaRead
from ports.auth import LoginAttempts, OwnerRead, OwnerWrite, PasswordHasher, SessionStore
from ports.booking import BookingRead, BookingWrite
from ports.catalog import CatalogRead, CatalogWrite
from ports.clock import Clock
from ports.financial import FinancialRead
from ports.tokens import TokenSource


@dataclass(frozen=True)
class Services:
    owners: OwnerRead
    owner_write: OwnerWrite
    hasher: PasswordHasher
    sessions: SessionStore
    attempts: LoginAttempts
    clock: Clock
    tokens: TokenSource
    catalog: CatalogRead
    catalog_write: CatalogWrite
    admin: CatalogAdmin
    agenda: AgendaRead
    agenda_admin: AgendaAdmin
    financial: FinancialRead
    bookings: BookingRead
    booking_write: BookingWrite
    dummy_hash: str
    cookie_secure: bool


def services_of(request: Request) -> Services:
    found = request.app.state.services
    if not isinstance(found, Services):
        raise RuntimeError("web services are not configured")
    return found


def render(request: Request, name: str, context: dict[str, object], status_code: int = 200) -> Response:
    templates = request.app.state.templates
    if not isinstance(templates, Jinja2Templates):
        raise RuntimeError("templates are not configured")
    return templates.TemplateResponse(request, name, context, status_code=status_code)
