"""Session and CSRF guards shared by every owner page."""

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import RedirectResponse, Response

from domain.auth import SessionInfo
from web.auth import csrf_ok, current_session
from web.services import Services, render, services_of


@dataclass(frozen=True)
class Owned:
    services: Services
    info: SessionInfo

    @property
    def business_id(self) -> int:
        return self.info.business_id

    @property
    def is_owner(self) -> bool:
        return self.info.role == "owner"

    @property
    def professional_id(self) -> int | None:
        return self.info.professional_id


def guard(request: Request) -> Owned | Response:
    """The logged-in user (owner or professional), or a redirect to /login."""
    services = services_of(request)
    info = current_session(request, services)
    if info is None:
        return RedirectResponse("/login", status_code=303)
    return Owned(services, info)


def guard_owner(request: Request) -> Owned | Response:
    """Guards owner-only views (e.g. services, team configuration, business settings)."""
    owned = guard(request)
    if isinstance(owned, Response):
        return owned
    if not owned.is_owner:
        return RedirectResponse("/agenda", status_code=303)
    return owned


def guard_post(request: Request, csrf_token: str) -> Owned | Response:
    """Like guard, and the form must carry the session's CSRF token."""
    owned = guard(request)
    if isinstance(owned, Response):
        return owned
    if not csrf_ok(csrf_token, owned.info.csrf_token):
        return render(request, "erro.html", {"message": "Requisição inválida.", "back": "/agenda"}, 403)
    return owned


def guard_owner_post(request: Request, csrf_token: str) -> Owned | Response:
    """Like guard_post, but restricted to owner accounts."""
    owned = guard_post(request, csrf_token)
    if isinstance(owned, Response):
        return owned
    if not owned.is_owner:
        return render(request, "erro.html", {"message": "Acesso não autorizado.", "back": "/agenda"}, 403)
    return owned


def page(request: Request, owned: Owned, name: str, context: dict[str, object], status: int = 200) -> Response:
    ctx = {
        "csrf_token": owned.info.csrf_token,
        "is_owner": owned.is_owner,
        "session_role": owned.info.role,
        "session_pro_id": owned.info.professional_id,
        **context,
    }
    response = render(request, name, ctx, status)
    response.headers["Cache-Control"] = "no-store"
    return response


def not_found(request: Request) -> Response:
    return render(request, "erro.html", {"message": "Não encontrado.", "back": "/agenda"}, 404)
