"""Dedicated Agenda page and appointment lifecycle actions (complete/cancel)."""

from typing import Annotated

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import RedirectResponse, Response

from domain.models import AgendaItem, BookingStatus
from domain.panel import format_time
from web.forms import br_day, digits_only, iso_day, parse_day, weekday_name
from web.guard import Owned, guard, guard_post, not_found, page

router = APIRouter()


def _agenda_row(item: AgendaItem) -> dict[str, object]:
    b = item.booking
    return {
        "id": b.id,
        "date": br_day(b.day),
        "day_iso": iso_day(b.day),
        "weekday": weekday_name(b.day),
        "start": format_time(b.start_min),
        "end": format_time(b.end_min),
        "professional": item.professional_name,
        "service": item.service_name,
        "customer": b.customer_name,
        "phone": b.customer_phone,
        "whatsapp": digits_only(b.customer_phone),
        "status": b.status,
        "is_confirmed": b.status == BookingStatus.CONFIRMED,
        "is_completed": b.status == BookingStatus.COMPLETED,
    }


def _resolve_pro_id(owned: Owned, pro_id: int | None) -> int | None:
    return owned.professional_id if not owned.is_owner else pro_id


@router.get("/agenda")
def agenda_view(
    request: Request,
    data: Annotated[str | None, Query()] = None,
    pro: Annotated[int | None, Query()] = None,
) -> Response:
    owned = guard(request)
    if isinstance(owned, Response):
        return owned

    today_day = owned.services.clock.now().day
    selected_day = parse_day(data) if data else today_day
    if selected_day is None:
        selected_day = today_day

    active_pro_id = _resolve_pro_id(owned, pro)
    items = owned.services.agenda.agenda(owned.business_id, selected_day, selected_day, active_pro_id)

    pros = owned.services.catalog.professionals(owned.business_id) if owned.is_owner else ()
    row_data = [_agenda_row(i) for i in items]
    return page(
        request,
        owned,
        "agenda.html",
        {
            "selected_date": iso_day(selected_day),
            "today_date": iso_day(today_day),
            "selected_date_br": br_day(selected_day),
            "is_today": selected_day == today_day,
            "selected_weekday": weekday_name(selected_day),
            "active_pro_id": active_pro_id,
            "professionals": pros,
            "items": row_data,
            "rows": row_data,
            "saved": request.query_params.get("salvo") == "1",
            "cancelled": request.query_params.get("cancelado") == "1",
            "booked": request.query_params.get("agendado") == "1",
        },
    )


@router.post("/agendamentos/{booking_id}/concluir")
def complete_booking_action(
    request: Request,
    booking_id: int,
    csrf_token: Annotated[str, Form()],
    day: Annotated[str | None, Form()] = None,
) -> Response:
    owned = guard_post(request, csrf_token)
    if isinstance(owned, Response):
        return owned
    active_pro = _resolve_pro_id(owned, None)
    ok = owned.services.agenda_admin.complete_booking(owned.business_id, booking_id, active_pro)
    if not ok:
        return not_found(request)
    referer = request.headers.get("referer", "")
    dest = "/painel?salvo=1" if "/painel" in referer else f"/agenda?salvo=1{('&data=' + day) if day else ''}"
    return RedirectResponse(dest, status_code=303)


@router.post("/agendamentos/{booking_id}/cancelar")
def cancel_booking_action(
    request: Request,
    booking_id: int,
    csrf_token: Annotated[str, Form()],
    day: Annotated[str | None, Form()] = None,
) -> Response:
    owned = guard_post(request, csrf_token)
    if isinstance(owned, Response):
        return owned
    active_pro = _resolve_pro_id(owned, None)
    ok = owned.services.agenda_admin.cancel_for_business(owned.business_id, booking_id, active_pro)
    if not ok:
        return not_found(request)
    referer = request.headers.get("referer", "")
    dest = "/painel" if "/painel" in referer else f"/agenda?cancelado=1{('&data=' + day) if day else ''}"
    return RedirectResponse(dest, status_code=303)
