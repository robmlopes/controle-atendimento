import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adapters.sqlite_auth import SqliteOwners
from domain.auth import AuthPolicy
from domain.models import Now
from tests.web_support import PASSWORD, FakeClock, add_owner, login, make_env
from tests.web_support import csrf as _csrf


def _setup(tmp_path: Path) -> tuple[TestClient, FakeClock, object]:
    env = make_env(tmp_path)
    add_owner(env, "loja", "dono@loja.com")
    return env.client, env.clock, env.db


def _login(client: TestClient, email: str = "dono@loja.com", password: str = PASSWORD) -> int:
    return login(client, email, password)


def test_valid_login_reaches_painel_and_logout_ends_session(tmp_path: Path) -> None:
    client, _, _ = _setup(tmp_path)
    assert _login(client) == 303
    painel = client.get("/painel")
    assert painel.status_code == 200 and "<h1>Agenda</h1>" in painel.text
    assert painel.headers["cache-control"] == "no-store"
    cookie = client.cookies.get("session")
    assert client.post("/logout", data={"csrf_token": "wrong"}).status_code == 403
    assert client.get("/painel").status_code == 200
    assert client.post("/logout", data={"csrf_token": _csrf(painel.text)}).status_code == 303
    client.cookies.set("session", cookie or "")
    assert client.get("/painel").status_code == 303


def test_wrong_password_and_unknown_email_give_the_same_error(tmp_path: Path) -> None:
    client, _, _ = _setup(tmp_path)
    assert _login(client, password="errada-errada") == 401
    wrong = client.get("/login")
    assert _login(client, email="ninguem@loja.com") == 401
    assert client.get("/painel").status_code == 303
    assert wrong.status_code == 200


def test_error_message_is_identical(tmp_path: Path) -> None:
    client, _, _ = _setup(tmp_path)
    token = _csrf(client.get("/login").text)
    one = client.post("/login", data={"email": "dono@loja.com", "password": "x" * 9, "csrf_token": token})
    token = _csrf(client.get("/login").text)
    two = client.post("/login", data={"email": "no@loja.com", "password": "x" * 9, "csrf_token": token})
    assert "E-mail ou senha inválidos." in one.text and "E-mail ou senha inválidos." in two.text


def test_login_without_csrf_is_rejected(tmp_path: Path) -> None:
    client, _, _ = _setup(tmp_path)
    client.get("/login")
    response = client.post("/login", data={"email": "dono@loja.com", "password": PASSWORD, "csrf_token": "forged"})
    assert response.status_code == 403
    assert TestClient(client.app).post("/login", data={"email": "a", "password": "b"}).status_code == 403


def test_login_is_blocked_after_too_many_failures_even_with_right_password(tmp_path: Path) -> None:
    client, clock, _ = _setup(tmp_path)
    for _ in range(AuthPolicy.MAX_FAILURES):
        assert _login(client, password="errada-errada") == 401
    assert _login(client) == 429
    clock.current = Now(100, 600 + AuthPolicy.WINDOW_MIN + 1)
    assert _login(client) == 303


def test_session_expires(tmp_path: Path) -> None:
    client, clock, _ = _setup(tmp_path)
    assert _login(client) == 303
    assert client.get("/painel").status_code == 200
    clock.current = Now(101, 600 + AuthPolicy.SESSION_TTL_MIN)
    assert client.get("/painel").status_code == 303


def test_painel_requires_login_and_cookie_flags(tmp_path: Path) -> None:
    client, _, _ = _setup(tmp_path)
    assert client.get("/painel").status_code == 303
    assert client.get("/").headers["location"] == "/login"
    _login(client)
    header = client.get("/login").headers.get("set-cookie", "")
    assert "HttpOnly" in header and "SameSite=lax" in header


def test_database_failure_shows_503_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, _ = _setup(tmp_path)

    def broken(_self: SqliteOwners, _email: str) -> None:
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(SqliteOwners, "owner_by_email", broken)
    token = _csrf(client.get("/login").text)
    response = client.post("/login", data={"email": "dono@loja.com", "password": PASSWORD, "csrf_token": token})
    assert response.status_code == 503 and "indisponível" in response.text
