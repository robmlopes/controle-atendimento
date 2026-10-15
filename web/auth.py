"""Owner login, logout and the session guard."""

import hmac
from typing import Annotated

from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import RedirectResponse, Response

from domain.auth import (
    AuthPolicy,
    Owner,
    SessionInfo,
    is_valid_email,
    login_blocked,
    minutes_of,
    normalize_email,
    session_valid,
    window_start,
)
from web.services import Services, render, services_of

router = APIRouter()
SESSION_COOKIE = "session"
LOGIN_CSRF_COOKIE = "login_csrf"
LOGIN_ERROR = "E-mail ou senha inválidos."
BLOCKED_ERROR = "Muitas tentativas. Tente novamente em alguns minutos."


def csrf_ok(given: str, expected: str | None) -> bool:
    return bool(expected) and bool(given) and hmac.compare_digest(given.encode(), (expected or "").encode())


def current_session(request: Request, services: Services) -> SessionInfo | None:
    """The valid session of this request, or None. Expired sessions are deleted."""
    token = request.cookies.get(SESSION_COOKIE)
    info = services.sessions.get(token) if token else None
    if token is None or info is None:
        return None
    if not session_valid(info.created_total, minutes_of(services.clock.now()), AuthPolicy.SESSION_TTL_MIN):
        services.sessions.delete(token)
        return None
    return info


def _login_page(request: Request, services: Services, email: str, error: str | None, status: int) -> Response:
    csrf = services.tokens.new_token()
    response = render(request, "login.html", {"csrf_token": csrf, "error": error, "email": email}, status)
    response.set_cookie(
        LOGIN_CSRF_COOKIE, csrf, httponly=True, samesite="lax", secure=services.cookie_secure, max_age=900
    )
    return response


def _attempt_keys(request: Request, email: str) -> tuple[str, str]:
    host = request.client.host if request.client else "unknown"
    return f"email:{email}", f"ip:{host}"


def _too_many_failures(services: Services, keys: tuple[str, str], now_total: int) -> bool:
    since = window_start(now_total, AuthPolicy.WINDOW_MIN)
    worst = max(services.attempts.failures_since(key, since) for key in keys)
    return login_blocked(worst, AuthPolicy.MAX_FAILURES)


def _authenticate(services: Services, email: str, password: str) -> Owner | None:
    owner = services.owners.owner_by_email(email) if is_valid_email(email) else None
    stored = owner.password_hash if owner is not None else services.dummy_hash
    verified = len(password) <= AuthPolicy.MAX_PASSWORD and services.hasher.verify(stored, password)
    return owner if owner is not None and verified else None


def _start_session(services: Services, owner: Owner, now_total: int) -> Response:
    token, csrf = services.tokens.new_token(), services.tokens.new_token()
    services.sessions.create(owner, token, csrf, now_total)
    response = RedirectResponse("/painel", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=services.cookie_secure,
        max_age=AuthPolicy.SESSION_TTL_MIN * 60,
    )
    response.delete_cookie(LOGIN_CSRF_COOKIE)
    return response


@router.get("/")
def home() -> Response:
    return RedirectResponse("/login", status_code=303)


@router.get("/login")
def login_form(request: Request) -> Response:
    return _login_page(request, services_of(request), "", None, 200)


@router.post("/login")
def login_submit(
    request: Request,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
    login_csrf: Annotated[str | None, Cookie()] = None,
) -> Response:
    services = services_of(request)
    if not csrf_ok(csrf_token, login_csrf):
        return render(request, "erro.html", {"message": "Formulário expirado. Recarregue a página."}, 403)
    email = normalize_email(email)
    now_total = minutes_of(services.clock.now())
    keys = _attempt_keys(request, email)
    if _too_many_failures(services, keys, now_total):
        return _login_page(request, services, email, BLOCKED_ERROR, 429)
    owner = _authenticate(services, email, password)
    if owner is None:
        for key in keys:
            services.attempts.record_failure(key, now_total)
        return _login_page(request, services, email, LOGIN_ERROR, 401)
    services.attempts.clear(keys[0])
    return _start_session(services, owner, now_total)


@router.post("/logout")
def logout(request: Request, csrf_token: Annotated[str, Form()] = "") -> Response:
    services = services_of(request)
    info = current_session(request, services)
    if info is None:
        return RedirectResponse("/login", status_code=303)
    if not csrf_ok(csrf_token, info.csrf_token):
        return render(request, "erro.html", {"message": "Requisição inválida."}, 403)
    services.sessions.delete(request.cookies.get(SESSION_COOKIE, ""))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
