import re
from pathlib import Path

from fastapi.testclient import TestClient

from domain.models import Now, WeeklyRule
from tests.web_support import Env, add_owner, csrf, make_env

MONDAY_DAY = 140


def _seed(env: Env) -> tuple[int, int, int]:
    bid = add_owner(env, "barbearia", "dono@barba.com")
    pro = env.catalog.add_professional(bid, "Zé")
    service = env.catalog.add_service(bid, "Corte", 30, 3500)
    env.catalog.link_service(pro.id, service.id)
    env.catalog.add_rule(WeeklyRule(pro.id, 0, 540, 660))  # Monday 09:00 to 11:00
    env.clock.current = Now(MONDAY_DAY, 500)  # Monday 08:20
    return bid, pro.id, service.id


def _token(html: str) -> str:
    match = re.search(r"/agendamento/([a-zA-Z0-9_-]+)", html)
    assert match, html
    return match.group(1)


def test_public_home_lists_professionals(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    _seed(env)
    assert env.client.get("/n/inexistente").status_code == 404
    response = env.client.get("/n/barbearia")
    assert response.status_code == 200 and "Zé" in response.text


def test_full_customer_booking_flow_and_agenda_reflection(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    _, pid, sid = _seed(env)
    client = env.client
    page = client.get(f"/n/barbearia/p/{pid}?servico={sid}&data=0001-05-21")
    assert page.status_code == 200 and "09:00" in page.text and "10:30" in page.text
    confirm_page = client.get(f"/n/barbearia/agendar?profissional={pid}&servico={sid}&data=0001-05-21&horario=540")
    assert confirm_page.status_code == 200 and "09:00" in confirm_page.text
    token = csrf(confirm_page.text)
    book = client.post(
        "/n/barbearia/agendar",
        data={
            "professional_id": pid,
            "service_id": sid,
            "day_iso": "0001-05-21",
            "start_min": 540,
            "customer_name": "Maria",
            "customer_phone": "(11) 98765-4321",
            "csrf_token": token,
        },
    )
    assert book.status_code == 303
    booking_token = _token(book.headers["location"])
    view = client.get(f"/agendamento/{booking_token}")
    assert view.status_code == 200 and "Agendamento confirmado!" in view.text and "09:00 às 09:30" in view.text
    assert "no-store" in view.headers["cache-control"]
    after = client.get(f"/n/barbearia/p/{pid}?servico={sid}&data=0001-05-21")
    assert "09:00" not in [line for line in after.text.splitlines() if "horario=540" in line]
    agenda = env.services.agenda.agenda(1, MONDAY_DAY, MONDAY_DAY + 1)
    assert len(agenda) == 1 and agenda[0].booking.customer_name == "Maria"
    cancel_token = csrf(view.text)
    cancel = client.post(f"/agendamento/{booking_token}/cancelar", data={"csrf_token": cancel_token})
    assert cancel.status_code == 303
    cancelled = client.get(f"/agendamento/{booking_token}")
    assert "Agendamento cancelado" in cancelled.text and "liberado" in cancelled.text
    freed = client.get(f"/n/barbearia/p/{pid}?servico={sid}&data=0001-05-21")
    assert "horario=540" in freed.text


def test_concurrent_booking_gives_one_winner_and_one_409(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    _, pid, sid = _seed(env)
    c1, c2 = env.client, TestClient(env.client.app, follow_redirects=False)
    t1 = csrf(c1.get(f"/n/barbearia/agendar?profissional={pid}&servico={sid}&data=0001-05-21&horario=540").text)
    t2 = csrf(c2.get(f"/n/barbearia/agendar?profissional={pid}&servico={sid}&data=0001-05-21&horario=540").text)
    data1 = {
        "professional_id": pid,
        "service_id": sid,
        "day_iso": "0001-05-21",
        "start_min": 540,
        "customer_name": "Cli 1",
        "customer_phone": "11987654321",
        "csrf_token": t1,
    }
    data2 = {
        "professional_id": pid,
        "service_id": sid,
        "day_iso": "0001-05-21",
        "start_min": 540,
        "customer_name": "Cli 2",
        "customer_phone": "11987654322",
        "csrf_token": t2,
    }
    r1, r2 = c1.post("/n/barbearia/agendar", data=data1), c2.post("/n/barbearia/agendar", data=data2)
    statuses = sorted([r1.status_code, r2.status_code])
    assert statuses == [303, 409]


def test_customer_active_limit_is_enforced(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    _, pid, sid = _seed(env)
    client = env.client
    for m in (540, 570, 600):
        t = csrf(client.get(f"/n/barbearia/agendar?profissional={pid}&servico={sid}&data=0001-05-21&horario={m}").text)
        assert (
            client.post(
                "/n/barbearia/agendar",
                data={
                    "professional_id": pid,
                    "service_id": sid,
                    "day_iso": "0001-05-21",
                    "start_min": m,
                    "customer_name": "Ana",
                    "customer_phone": "11987654321",
                    "csrf_token": t,
                },
            ).status_code
            == 303
        )
    t = csrf(client.get(f"/n/barbearia/agendar?profissional={pid}&servico={sid}&data=0001-05-21&horario=630").text)
    r = client.post(
        "/n/barbearia/agendar",
        data={
            "professional_id": pid,
            "service_id": sid,
            "day_iso": "0001-05-21",
            "start_min": 630,
            "customer_name": "Ana",
            "customer_phone": "11987654321",
            "csrf_token": t,
        },
    )
    assert r.status_code == 422 and "Limite de agendamentos" in r.text


def test_invalid_input_and_csrf_protection(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    _, pid, sid = _seed(env)
    client = env.client
    page = client.get(f"/n/barbearia/agendar?profissional={pid}&servico={sid}&data=0001-05-21&horario=540")
    t = csrf(page.text)
    assert client.post("/n/barbearia/agendar", data={"csrf_token": "wrong"}).status_code == 403
    bad = client.post(
        "/n/barbearia/agendar",
        data={
            "professional_id": pid,
            "service_id": sid,
            "day_iso": "0001-05-21",
            "start_min": 540,
            "customer_name": "Ana",
            "customer_phone": "telefone-ruim",
            "csrf_token": t,
        },
    )
    assert bad.status_code == 422 and "Telefone inválido" in bad.text
    assert client.get("/agendamento/token-que-nao-existe").status_code == 404


def test_business_settings_allows_owner_to_set_custom_slug_and_whatsapp(tmp_path: Path) -> None:
    from tests.web_support import login, post

    env = make_env(tmp_path)
    bid, pid, sid = _seed(env)
    client = env.client
    assert login(client, "dono@barba.com") == 303
    assert (
        post(
            client,
            "/negocio",
            {"name": "Barba Top", "slug": "barba-top", "whatsapp": "(11) 99999-8888"},
            "/negocio",
        )
        == 303
    )
    assert env.catalog.business_by_slug("barba-top").whatsapp == "+5511999998888"  # type: ignore[union-attr]
    html = client.get("/negocio?salvo=1").text
    assert "/n/barba-top" in html
    assert "Dados atualizados com sucesso" in html
    # Invalid slug gives 422
    assert (
        post(
            client,
            "/negocio",
            {"name": "Barba Top", "slug": "slug invalido!", "whatsapp": ""},
            "/negocio",
        )
        == 422
    )
