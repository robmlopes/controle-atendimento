"""Customer view of a booking and cancellation via private token."""

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from domain.models import BookingStatus, BookingView
from domain.panel import format_time
from web.forms import br_day, weekday_name
from web.guard import not_found
from web.public_common import public_csrf_ok, public_page, wa_link
from web.services import services_of

router = APIRouter()


def _view_context(view: BookingView) -> dict[str, object]:
    b = view.booking
    date_label = f"{weekday_name(b.day)}, {br_day(b.day)}"
    text = (
        f"Olá! Agendei {view.service_name} com {view.professional_name} para {date_label} às {format_time(b.start_min)}"
        f" ({view.business_name}). Meu nome: {b.customer_name}."
    )
    return {
        "view": view,
        "date_label": date_label,
        "start": format_time(b.start_min),
        "end": format_time(b.end_min),
        "wa_link": wa_link(view.business_whatsapp, text),
        "is_confirmed": b.status == BookingStatus.CONFIRMED,
    }


@router.get("/agendamento/{token}")
def booking_page(request: Request, token: str) -> Response:
    services = services_of(request)
    view = services.bookings.view_by_token(token)
    if view is None:
        return not_found(request)
    response = public_page(request, services, "public_booking.html", _view_context(view))
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.post("/agendamento/{token}/cancelar")
def cancel_booking(request: Request, token: str, csrf_token: Annotated[str, Form()] = "") -> Response:
    services = services_of(request)
    if not public_csrf_ok(request, csrf_token):
        return public_page(request, services, "erro.html", {"message": "Requisição inválida."}, 403)
    if services.booking_write.cancel(token) is None:
        return not_found(request)
    return RedirectResponse(f"/agendamento/{token}", status_code=303)
