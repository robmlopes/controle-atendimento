"""Owner pages for professionals and services."""

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from domain.auth import is_valid_email, is_valid_password, normalize_email
from domain.models import Professional, Service, WeeklyRule
from domain.panel import (
    PanelLimits,
    clean_name,
    format_price,
    format_time,
    is_valid_duration,
    is_valid_name,
    is_valid_price,
    parse_price,
)
from web.forms import to_int, weekday_name
from web.guard import Owned, guard_owner, guard_owner_post, not_found, page
from web.services import render

router = APIRouter()
NAME_ERROR = f"Nome inválido: use de 1 a {PanelLimits.MAX_NAME} caracteres."
DURATION_ERROR = f"Duração inválida: use de {PanelLimits.MIN_DURATION} a {PanelLimits.MAX_DURATION} minutos."
PRICE_ERROR = "Preço inválido: use por exemplo 35,00."


def _format_schedule_days(rules: tuple[WeeklyRule, ...]) -> str:
    if not rules:
        return "Nenhum horário cadastrado"
    ordered = sorted(rules, key=lambda r: (r.weekday, r.start_min))
    return ", ".join(
        f"{weekday_name(r.weekday)[:3]} {format_time(r.start_min)}–{format_time(r.end_min)}" for r in ordered
    )


def _pro_row(owned: Owned, pro: Professional) -> dict[str, object]:
    services = owned.services.catalog.services_of(pro.id)
    rules = owned.services.catalog.rules(pro.id)
    account = owned.services.owners.owner_by_professional(owned.business_id, pro.id)
    names = ", ".join(s.name for s in services) if services else "Nenhum serviço vinculado"
    return {
        "id": pro.id,
        "name": pro.name,
        "commission_pct": pro.commission_pct,
        "services": names,
        "schedule": _format_schedule_days(rules),
        "login_email": account.email if account else None,
    }


def _professionals_page(request: Request, owned: Owned, error: str | None, name: str, status: int = 200) -> Response:
    people = owned.services.catalog.professionals(owned.business_id)
    rows = [_pro_row(owned, p) for p in people]
    return page(request, owned, "profissionais.html", {"people": rows, "error": error, "name": name}, status)


def _service_row(owned: Owned, service: Service, people: tuple[Professional, ...]) -> dict[str, object]:
    price = "—" if service.price_cents is None else f"R$ {format_price(service.price_cents)}"
    pros_with_svc = [p.name for p in people if service.id in owned.services.admin.linked_service_ids(p.id)]
    pro_names = ", ".join(pros_with_svc) if pros_with_svc else "Nenhum profissional vinculado"
    return {"id": service.id, "name": service.name, "duration": service.duration_min, "price": price, "pros": pro_names}


def _services_page(
    request: Request, owned: Owned, error: str | None, values: dict[str, str], status: int = 200
) -> Response:
    people = owned.services.catalog.professionals(owned.business_id)
    rows = [_service_row(owned, s, people) for s in owned.services.admin.business_services(owned.business_id)]
    return page(request, owned, "servicos.html", {"rows": rows, "error": error, "values": values}, status)


@router.get("/profissionais")
def professionals(request: Request) -> Response:
    owned = guard_owner(request)
    if isinstance(owned, Response):
        return owned
    return _professionals_page(request, owned, None, "")


@router.post("/profissionais")
def add_professional(
    request: Request,
    name: Annotated[str, Form()] = "",
    commission_pct: Annotated[str, Form()] = "100",
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    owned = guard_owner_post(request, csrf_token)
    if isinstance(owned, Response):
        return owned
    name = clean_name(name)
    pct = to_int(commission_pct)
    if not is_valid_name(name) or pct is None or not (0 <= pct <= 100):
        return _professionals_page(request, owned, NAME_ERROR, name, 422)
    created = owned.services.catalog_write.add_professional(owned.business_id, name, pct)
    return RedirectResponse(f"/profissionais/{created.id}", status_code=303)


@router.post("/profissionais/{professional_id}/acesso")
def create_professional_login(
    request: Request,
    professional_id: int,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    owned = guard_owner_post(request, csrf_token)
    if isinstance(owned, Response):
        return owned
    pro = owned.services.admin.professional(owned.business_id, professional_id)
    if pro is None:
        return not_found(request)
    email = normalize_email(email)
    if not is_valid_email(email) or not is_valid_password(password):
        return render(
            request,
            "erro.html",
            {
                "message": "E-mail ou senha inválidos (senha mínima de 8 caracteres).",
                "back": f"/profissionais/{pro.id}",
            },
            422,
        )
    if owned.services.owners.owner_by_email(email) is not None:
        return render(
            request,
            "erro.html",
            {"message": "Este e-mail já está cadastrado.", "back": f"/profissionais/{pro.id}"},
            409,
        )
    pw_hash = owned.services.hasher.hash(password)
    owned.services.owner_write.add_owner(owned.business_id, email, pw_hash, role="professional", professional_id=pro.id)
    return RedirectResponse(f"/profissionais/{pro.id}?acesso=1", status_code=303)


@router.post("/profissionais/{professional_id}/desativar")
def deactivate_professional(
    request: Request, professional_id: int, csrf_token: Annotated[str, Form()] = ""
) -> Response:
    owned = guard_owner_post(request, csrf_token)
    if isinstance(owned, Response):
        return owned
    if not owned.services.admin.deactivate_professional(owned.business_id, professional_id):
        return not_found(request)
    return RedirectResponse("/profissionais", status_code=303)


@router.get("/servicos")
def services_list(request: Request) -> Response:
    owned = guard_owner(request)
    if isinstance(owned, Response):
        return owned
    return _services_page(request, owned, None, {"name": "", "duration": "", "price": ""})


@router.post("/servicos")
def add_service(
    request: Request,
    name: Annotated[str, Form()] = "",
    duration: Annotated[str, Form()] = "",
    price: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    owned = guard_owner_post(request, csrf_token)
    if isinstance(owned, Response):
        return owned
    name = clean_name(name)
    values = {"name": name, "duration": duration, "price": price}
    minutes = to_int(duration)
    cents = parse_price(price) if price.strip() else None
    error = (
        NAME_ERROR
        if not is_valid_name(name)
        else DURATION_ERROR
        if minutes is None or not is_valid_duration(minutes)
        else PRICE_ERROR
        if price.strip() and (cents is None or not is_valid_price(cents))
        else None
    )
    if error is not None or minutes is None:
        return _services_page(request, owned, error, values, 422)
    owned.services.catalog_write.add_service(owned.business_id, name, minutes, cents)
    return RedirectResponse("/servicos", status_code=303)


@router.post("/servicos/{service_id}/desativar")
def deactivate_service(request: Request, service_id: int, csrf_token: Annotated[str, Form()] = "") -> Response:
    owned = guard_owner_post(request, csrf_token)
    if isinstance(owned, Response):
        return owned
    if not owned.services.admin.deactivate_service(owned.business_id, service_id):
        return not_found(request)
    return RedirectResponse("/servicos", status_code=303)
