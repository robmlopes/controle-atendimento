"""Owner overview dashboard."""

from fastapi import APIRouter, Request
from fastapi.responses import Response

from domain.models import AgendaItem, Professional, Service, WeeklyRule
from domain.panel import format_price, format_time
from web.forms import br_day, digits_only, weekday_name
from web.guard import Owned, guard, page

router = APIRouter()
AGENDA_DAYS = 14


def _row(item: AgendaItem) -> dict[str, object]:
    booking = item.booking
    return {
        "id": booking.id,
        "date": br_day(booking.day),
        "weekday": weekday_name(booking.day),
        "start": format_time(booking.start_min),
        "end": format_time(booking.end_min),
        "professional": item.professional_name,
        "service": item.service_name,
        "customer": booking.customer_name,
        "phone": booking.customer_phone,
        "whatsapp": digits_only(booking.customer_phone),
    }


def _format_rules_summary(rules: tuple[WeeklyRule, ...]) -> str:
    if not rules:
        return "Nenhum horário cadastrado"
    ordered = sorted(rules, key=lambda r: (r.weekday, r.start_min))
    return ", ".join(
        f"{weekday_name(r.weekday)[:3]} {format_time(r.start_min)}–{format_time(r.end_min)}" for r in ordered
    )


def _pro_summary(owned: Owned, pro: Professional) -> dict[str, object]:
    services = owned.services.catalog.services_of(pro.id)
    rules = owned.services.catalog.rules(pro.id)
    names = ", ".join(s.name for s in services) if services else "Nenhum serviço vinculado"
    return {"id": pro.id, "name": pro.name, "services": names, "schedule": _format_rules_summary(rules)}


def _service_summary(s: Service) -> dict[str, object]:
    price = "—" if s.price_cents is None else f"R$ {format_price(s.price_cents)}"
    return {"id": s.id, "name": s.name, "duration": s.duration_min, "price": price}


@router.get("/painel")
def painel(request: Request) -> Response:
    owned = guard(request)
    if isinstance(owned, Response):
        return owned
    today = owned.services.clock.now().day
    items = owned.services.agenda.agenda(owned.business_id, today, today + AGENDA_DAYS)
    business = owned.services.admin.business(owned.business_id)
    pros = owned.services.catalog.professionals(owned.business_id)
    services_list = owned.services.admin.business_services(owned.business_id)
    host = request.headers.get("host", "localhost:8000")
    scheme = "https" if owned.services.cookie_secure else "http"
    return page(
        request,
        owned,
        "painel.html",
        {
            "business": business,
            "base_url": f"{scheme}://{host}",
            "professionals_summary": [_pro_summary(owned, p) for p in pros],
            "services_summary": [_service_summary(s) for s in services_list],
            "rows": [_row(i) for i in items],
            "days": AGENDA_DAYS,
        },
    )
