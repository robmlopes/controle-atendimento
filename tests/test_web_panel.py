import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adapters.sqlite_booking import SqliteBookings
from domain.models import NewBooking
from tests.web_support import Env, add_owner, csrf, login, make_env, post


def _env(tmp_path: Path) -> tuple[Env, TestClient, TestClient, int, int]:
    env = make_env(tmp_path)
    a = add_owner(env, "alfa", "a@alfa.com")
    b = add_owner(env, "beta", "b@beta.com")
    client_a = env.client
    client_b = TestClient(env.client.app, follow_redirects=False)
    assert login(client_a, "a@alfa.com") == 303 and login(client_b, "b@beta.com") == 303
    return env, client_a, client_b, a, b


def test_every_panel_page_requires_login(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    for url in ("/painel", "/profissionais", "/servicos", "/profissionais/1"):
        assert env.client.get(url).status_code == 303, url
    for url in ("/profissionais", "/servicos", "/agendamentos/1/cancelar", "/profissionais/1/horarios"):
        assert env.client.post(url, data={"csrf_token": "x"}).status_code == 303, url


def test_post_without_valid_csrf_is_rejected(tmp_path: Path) -> None:
    _, client, _, _, _ = _env(tmp_path)
    assert client.post("/profissionais", data={"name": "Ana", "csrf_token": "forged"}).status_code == 403
    assert client.post("/profissionais", data={"name": "Ana"}).status_code == 403
    assert "Ana" not in client.get("/profissionais").text


def test_owner_builds_a_schedule_end_to_end(tmp_path: Path) -> None:
    env, client, _, a, _ = _env(tmp_path)
    assert post(client, "/profissionais", {"name": "  Ana   Souza "}, "/profissionais") == 303
    pro = env.catalog.professionals(a)[0]
    assert pro.name == "Ana Souza"
    assert post(client, "/servicos", {"name": "Corte", "duration": "30", "price": "35,5"}, "/servicos") == 303
    service = env.services.admin.business_services(a)[0]
    assert (service.duration_min, service.price_cents) == (30, 3550)
    page = f"/profissionais/{pro.id}"
    assert post(client, f"{page}/servicos", {"service_ids": [str(service.id)]}, page) == 303
    assert post(client, f"{page}/horarios", {"weekday": "0", "start": "09:00", "end": "12:00"}, page) == 303
    assert post(client, f"{page}/horarios", {"weekday": "0", "start": "13:00", "end": "24:00"}, page) == 303
    assert post(client, f"{page}/bloqueios", {"date": "0001-06-01"}, page) == 303
    assert [(r.start_min, r.end_min) for r in sorted(env.catalog.rules(pro.id), key=lambda r: r.start_min)] == [
        (540, 720),
        (780, 1440),
    ]
    blocks = env.catalog.blocks(pro.id, 151)
    assert len(blocks) == 1 and (blocks[0].start_min, blocks[0].end_min) == (0, 1440)
    assert [s.name for s in env.catalog.services_of(pro.id)] == ["Corte"]
    html = client.get(page).text
    assert "Dia inteiro" in html and "09:00–12:00" in html and "Corte" in html
    assert post(client, f"{page}/horarios/remover", {"weekday": 0, "start_min": 540, "end_min": 720}, page) == 303
    assert len(env.catalog.rules(pro.id)) == 1


def test_owner_cannot_reach_or_change_another_business(tmp_path: Path) -> None:
    env, client_a, client_b, a, b = _env(tmp_path)
    pro_b = env.catalog.add_professional(b, "Beto")
    service_b = env.catalog.add_service(b, "Barba", 20, None)
    page_b = f"/profissionais/{pro_b.id}"
    assert client_a.get(page_b).status_code == 404
    token = csrf(client_a.get("/profissionais").text)
    for url, data in (
        (f"{page_b}/horarios", {"weekday": "0", "start": "09:00", "end": "10:00"}),
        (f"{page_b}/bloqueios", {"date": "0001-01-12"}),
        (f"{page_b}/servicos", {"service_ids": [str(service_b.id)]}),
        (f"{page_b}/desativar", {}),
        (f"/servicos/{service_b.id}/desativar", {}),
    ):
        assert client_a.post(url, data={**data, "csrf_token": token}).status_code == 404, url
    assert env.catalog.rules(pro_b.id) == () and env.catalog.blocks(pro_b.id, 0) == ()
    assert env.services.admin.professional(b, pro_b.id) is not None
    assert [s.name for s in env.services.admin.business_services(b)] == ["Barba"]
    assert "Beto" not in client_a.get("/profissionais").text and "Barba" not in client_a.get("/servicos").text
    assert "Beto" in client_b.get("/profissionais").text


def test_agenda_shows_only_own_bookings_and_cancel_is_scoped(tmp_path: Path) -> None:
    env, client_a, client_b, a, b = _env(tmp_path)
    pa, pb = env.catalog.add_professional(a, "Ana"), env.catalog.add_professional(b, "Beto")
    sa, sb = env.catalog.add_service(a, "Corte", 30, None), env.catalog.add_service(b, "Barba", 20, None)
    bookings = SqliteBookings(env.db)
    bookings.create(NewBooking(pa.id, sa.id, 101, 600, 630, "Cliente Alfa", "+5511911112222", "tok-a"))
    bookings.create(NewBooking(pb.id, sb.id, 101, 600, 620, "Cliente Beta", "+5511933334444", "tok-b"))
    html_a = client_a.get("/painel").text
    assert "Cliente Alfa" in html_a and "Cliente Beta" not in html_a and "wa.me/5511911112222" in html_a
    booking_b = env.services.agenda.agenda(b, 0, 200)[0].booking.id
    assert post(client_a, f"/agendamentos/{booking_b}/cancelar", {}) == 404
    assert "Cliente Beta" in client_b.get("/painel").text
    booking_a = env.services.agenda.agenda(a, 0, 200)[0].booking.id
    assert post(client_a, f"/agendamentos/{booking_a}/cancelar", {}) == 303
    assert "Cliente Alfa" not in client_a.get("/painel").text
    assert bookings.by_token("tok-a") is not None and bookings.by_token("tok-a").status == "cancelled"  # type: ignore[union-attr]
    assert "Nenhum agendamento" in client_a.get("/painel").text


def test_invalid_input_rerenders_with_message_and_keeps_values(tmp_path: Path) -> None:
    env, client, _, a, _ = _env(tmp_path)
    token = csrf(client.get("/servicos").text)
    response = client.post("/servicos", data={"name": "Corte", "duration": "999", "price": "abc", "csrf_token": token})
    assert response.status_code == 422 and "Duração inválida" in response.text and 'value="Corte"' in response.text
    response = client.post("/servicos", data={"name": "Corte", "duration": "30", "price": "1,234", "csrf_token": token})
    assert response.status_code == 422 and "Preço inválido" in response.text
    assert client.post("/profissionais", data={"name": "  ", "csrf_token": token}).status_code == 422
    assert env.services.admin.business_services(a) == () and env.catalog.professionals(a) == ()
    pro = env.catalog.add_professional(a, "Ana")
    page = f"/profissionais/{pro.id}"
    for data in (
        {"weekday": "9", "start": "09:00", "end": "10:00"},
        {"weekday": "0", "start": "10:00", "end": "09:00"},
        {"weekday": "0", "start": "xx", "end": "09:00"},
    ):
        assert client.post(f"{page}/horarios", data={**data, "csrf_token": token}).status_code == 422
    assert client.post(f"{page}/bloqueios", data={"date": "2024-02-31", "csrf_token": token}).status_code == 422
    assert env.catalog.rules(pro.id) == () and env.catalog.blocks(pro.id, 0) == ()


def test_names_are_html_escaped(tmp_path: Path) -> None:
    env, client, _, a, _ = _env(tmp_path)
    assert post(client, "/profissionais", {"name": "<script>alert(1)</script>"}, "/profissionais") == 303
    html = client.get("/profissionais").text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_deactivated_professional_page_is_gone(tmp_path: Path) -> None:
    env, client, _, a, _ = _env(tmp_path)
    pro = env.catalog.add_professional(a, "Ana")
    assert post(client, f"/profissionais/{pro.id}/desativar", {}, "/profissionais") == 303
    assert client.get(f"/profissionais/{pro.id}").status_code == 404
    assert client.get("/profissionais").text.count("Ana") == 0


def test_database_failure_keeps_navigation_and_shows_503(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env, client, _, _, _ = _env(tmp_path)

    def broken(*_args: object, **_kwargs: object) -> None:
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(type(env.services.catalog), "professionals", broken)
    response = client.get("/profissionais")
    assert response.status_code == 503 and "indisponível" in response.text


def test_panel_overview_lists_and_custom_slug_conflict(tmp_path: Path) -> None:
    env, client_a, client_b, a, b = _env(tmp_path)
    pro = env.catalog.add_professional(a, "Carlos")
    svc = env.catalog.add_service(a, "Barba Completa", 45, 4000)
    env.catalog.link_service(pro.id, svc.id)
    # Check painel lists overview
    html_painel = client_a.get("/painel").text
    assert "/n/alfa" in html_painel
    assert "Carlos" in html_painel and "Barba Completa" in html_painel
    assert "45 min" in html_painel and "40,00" in html_painel
    # Check professionals list shows linked services
    html_pros = client_a.get("/profissionais").text
    assert "Carlos" in html_pros and "Barba Completa" in html_pros
    # Check services list shows who executes it
    html_svcs = client_a.get("/servicos").text
    assert "Barba Completa" in html_svcs and "Carlos" in html_svcs
    # Conflict when setting slug to another existing business slug
    resp = client_a.post(
        "/negocio",
        data={
            "name": "Alfa",
            "slug": "beta",  # belongs to business b
            "whatsapp": "",
            "csrf_token": csrf(client_a.get("/negocio").text),
        },
    )
    assert resp.status_code == 422 and "já está em uso" in resp.text
