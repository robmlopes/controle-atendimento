"""Manual appointment booking form for owners and staff."""

from typing import Annotated

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import RedirectResponse, Response

from domain.models import NewBooking, Service
from domain.panel import format_time
from domain.public import PublicPolicy, normalize_phone
from domain.slots import free_slots
from web.forms import iso_day, parse_day
from web.guard import Owned, guard, guard_post, not_found, page
from web.services import render

router = APIRouter()


def _resolve_pro(owned: Owned, pro_id: int | None) -> int | None:
    return owned.professional_id if not owned.is_owner else pro_id


def _compute_slots(owned: Owned, pro_id: int, srv: Service, day: int) -> tuple[int, ...]:
    now = owned.services.clock.now()
    return free_slots(
        pro_id,
        owned.services.catalog.rules(pro_id),
        owned.services.catalog.blocks(pro_id, day),
        owned.services.bookings.for_day(pro_id, day),
        srv.duration_min,
        day,
        now.day,
        now.minute,
        PublicPolicy.SLOT_STEP,
    )


def _create_booking(owned: Owned, pro_id: int, srv: Service, day: int, start_min: int, name: str, phone: str) -> object:
    token = owned.services.tokens.new_token()
    nb = NewBooking(
        professional_id=pro_id,
        service_id=srv.id,
        day=day,
        start_min=start_min,
        end_min=start_min + srv.duration_min,
        customer_name=name.strip(),
        customer_phone=phone.strip(),
        cancel_token=token,
    )
    return owned.services.booking_write.create(nb)


@router.get("/agenda/novo")
def new_manual_booking_form(
    request: Request,
    pro: Annotated[int | None, Query()] = None,
    servico: Annotated[int | None, Query()] = None,
    data: Annotated[str | None, Query()] = None,
) -> Response:
    owned = guard(request)
    if isinstance(owned, Response):
        return owned

    today_day = owned.services.clock.now().day
    selected_day = parse_day(data) if data else today_day
    if selected_day is None:
        selected_day = today_day

    pro_id = _resolve_pro(owned, pro)
    pros = owned.services.catalog.professionals(owned.business_id)
    if not pro_id and pros:
        pro_id = pros[0].id

    services = owned.services.catalog.services_of(pro_id) if pro_id else ()
    chosen_srv = next((s for s in services if s.id == servico), services[0] if services else None)

    slots = _compute_slots(owned, pro_id, chosen_srv, selected_day) if pro_id and chosen_srv else ()
    return page(
        request,
        owned,
        "agenda_nova.html",
        {
            "professionals": pros if owned.is_owner else (),
            "selected_pro_id": pro_id,
            "services": services,
            "selected_service_id": chosen_srv.id if chosen_srv else None,
            "selected_date": iso_day(selected_day),
            "today_date": iso_day(today_day),
            "slots": [{"minute": m, "time": format_time(m)} for m in slots],
            "error": None,
        },
    )


@router.post("/agenda/novo")
def save_manual_booking(
    request: Request,
    csrf_token: Annotated[str, Form()],
    professional_id: Annotated[int, Form()],
    service_id: Annotated[int, Form()],
    date: Annotated[str, Form()],
    start_min: Annotated[int, Form()],
    customer_name: Annotated[str, Form()],
    customer_phone: Annotated[str, Form()],
) -> Response:
    owned = guard_post(request, csrf_token)
    if isinstance(owned, Response):
        return owned

    active_pro = _resolve_pro(owned, professional_id)
    if active_pro is None or (not owned.is_owner and active_pro != owned.professional_id):
        return not_found(request)

    day = parse_day(date)
    wa = normalize_phone(customer_phone)
    if day is None or wa is None or not customer_name.strip():
        return render(request, "erro.html", {"message": "Dados inválidos.", "back": "/agenda/novo"}, 400)

    srv = owned.services.catalog.service(service_id)
    if srv is None:
        return not_found(request)

    outcome = _create_booking(owned, active_pro, srv, day, start_min, customer_name, customer_phone)
    if hasattr(outcome, "professional_id") and not hasattr(outcome, "booking"):
        return render(
            request, "erro.html", {"message": "Horário não está mais disponível.", "back": "/agenda/novo"}, 409
        )

    return RedirectResponse(f"/agenda?agendado=1&data={date}", status_code=303)
