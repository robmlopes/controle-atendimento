from pathlib import Path

from fastapi.testclient import TestClient

from adapters.sqlite_auth import SqliteOwners
from adapters.sqlite_booking import SqliteBookings
from domain.models import NewBooking
from tests.web_support import PASSWORD, csrf, login, make_env, post


def test_professional_workflow_and_isolation(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    client_owner = env.client

    # Create business and owner
    business = env.catalog.add_business("salao-top", "Salão Top")
    SqliteOwners(env.db).add_owner(business.id, "dono@salao.com", env.hasher.hash(PASSWORD))
    assert login(client_owner, "dono@salao.com", PASSWORD) == 303

    # Owner adds two professionals
    assert post(client_owner, "/profissionais", {"name": "Bruna", "commission_pct": "60"}, "/profissionais") == 303
    assert post(client_owner, "/profissionais", {"name": "Carlos", "commission_pct": "50"}, "/profissionais") == 303

    pros = env.catalog.professionals(business.id)
    pro_bruna = next(p for p in pros if p.name == "Bruna")
    pro_carlos = next(p for p in pros if p.name == "Carlos")
    assert pro_bruna.commission_pct == 60

    # Add service and rules
    assert (
        post(client_owner, "/servicos", {"name": "Penteado", "duration": "30", "price": "100,00"}, "/servicos") == 303
    )
    service = env.services.admin.business_services(business.id)[0]
    p_page = f"/profissionais/{pro_bruna.id}"
    assert post(client_owner, f"{p_page}/servicos", {"service_ids": [str(service.id)]}, p_page) == 303
    assert post(client_owner, f"{p_page}/horarios", {"weekday": "0", "start": "09:00", "end": "12:00"}, p_page) == 303

    # Owner creates login for Bruna
    assert (
        post(client_owner, f"{p_page}/acesso", {"email": "bruna@salao.com", "password": "senha-bruna-1"}, p_page) == 303
    )

    # Create bookings for Bruna and Carlos
    bookings = SqliteBookings(env.db)
    day = 100  # Monday in our fake clock
    b1 = bookings.create(
        NewBooking(pro_bruna.id, service.id, day, 540, 570, "Cliente da Bruna", "+5511999990000", "tok1")
    )
    b2 = bookings.create(
        NewBooking(pro_carlos.id, service.id, day, 540, 570, "Cliente do Carlos", "+5511999991111", "tok2")
    )
    assert hasattr(b1, "booking") and hasattr(b2, "booking")

    # Bruna logs in with her client
    client_bruna = TestClient(env.client.app, follow_redirects=False)
    assert login(client_bruna, "bruna@salao.com", "senha-bruna-1") == 303

    # Bruna sees only her appointment on /agenda
    agenda_html = client_bruna.get("/agenda?data=0001-04-11").text  # day 100
    assert "Cliente da Bruna" in agenda_html
    assert "Cliente do Carlos" not in agenda_html

    # Bruna cannot access owner-only pages (/profissionais, /servicos, /negocio)
    assert client_bruna.get("/profissionais").status_code == 303
    assert client_bruna.get("/servicos").status_code == 303
    assert client_bruna.get("/negocio").status_code == 303

    # Bruna completes her appointment
    tok = csrf(client_bruna.get("/agenda").text)
    resp = client_bruna.post(f"/agendamentos/{b1.booking.id}/concluir", data={"csrf_token": tok})
    assert resp.status_code == 303

    # Bruna checks /financeiro: realized = 60% of 100 = R$ 60,00
    fin_html = client_bruna.get("/financeiro?periodo=hoje").text
    assert "60,00" in fin_html
    assert "Cliente do Carlos" not in fin_html
