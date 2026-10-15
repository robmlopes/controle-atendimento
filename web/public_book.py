"""Public booking: confirm form, atomic submit, confirmation page and cancellation."""

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from domain.models import Business, NewBooking, Professional, Service, SlotTaken
from domain.panel import clean_name, format_price, format_time, is_valid_name
from domain.public import (
    PublicPolicy,
    booking_end,
    can_book_more,
    day_in_window,
    normalize_phone,
)
from domain.slots import free_slots
from web.forms import br_day, parse_day, weekday_name
from web.guard import not_found
from web.public_common import public_csrf_ok, public_page, resolve_pair
from web.services import Services, services_of

router = APIRouter()
PHONE_ERROR = "Telefone inválido: use DDD + número (ex.: 11 99999-8888)."
NAME_ERROR = "Informe seu nome (1 a 80 caracteres)."
LIMIT_ERROR = "Limite de agendamentos atingido para este número. Cancele um horário anterior para agendar outro."


def _verify_slot(services: Services, pro_id: int, duration: int, day: int, start: int) -> bool:
    now = services.clock.now()
    free = free_slots(
        pro_id,
        services.catalog.rules(pro_id),
        services.catalog.blocks(pro_id, day),
        services.bookings.for_day(pro_id, day),
        duration,
        day,
        now.day,
        now.minute,
        PublicPolicy.SLOT_STEP,
    )
    return start in free


def _confirm_error(
    request: Request,
    services: Services,
    business: Business,
    pro: Professional,
    service: Service,
    day_iso: str,
    day: int,
    start_min: int,
    error: str,
    name: str,
    phone: str,
) -> Response:
    price = None if service.price_cents is None else format_price(service.price_cents)
    return public_page(
        request,
        services,
        "public_confirm.html",
        {
            "business": business,
            "pro": pro,
            "service": service,
            "price": price,
            "day_iso": day_iso,
            "day_label": f"{weekday_name(day)}, {br_day(day)}",
            "start": format_time(start_min),
            "start_min": start_min,
            "error": error,
            "customer_name": name,
            "customer_phone": phone,
        },
        422,
    )


@router.get("/n/{slug}/agendar")
def confirm_form(
    request: Request, slug: str, profissional: int = -1, servico: int = -1, data: str = "", horario: int = -1
) -> Response:
    services = services_of(request)
    pair = resolve_pair(services, slug, profissional, servico)
    day = parse_day(data)
    today = services.clock.now().day
    if pair is None or day is None or not day_in_window(day, today) or horario < 0 or horario >= 1440:
        return not_found(request)
    business, pro, service = pair
    if not _verify_slot(services, pro.id, service.duration_min, day, horario):
        return RedirectResponse(f"/n/{slug}/p/{pro.id}?servico={service.id}&data={data}", status_code=303)
    price = None if service.price_cents is None else format_price(service.price_cents)
    return public_page(
        request,
        services,
        "public_confirm.html",
        {
            "business": business,
            "pro": pro,
            "service": service,
            "price": price,
            "day_iso": data,
            "day_label": f"{weekday_name(day)}, {br_day(day)}",
            "start": format_time(horario),
            "start_min": horario,
            "error": None,
            "customer_name": "",
            "customer_phone": "",
        },
    )


def _do_book(
    request: Request,
    services: Services,
    business_id: int,
    pro_id: int,
    service: Service,
    day: int,
    start_min: int,
    name: str,
    phone: str,
    slug: str,
    day_iso: str,
) -> Response:
    token = services.tokens.new_token()
    new = NewBooking(
        pro_id, service.id, day, start_min, booking_end(start_min, service.duration_min), name, phone, token
    )
    if isinstance(services.booking_write.create(new), SlotTaken):
        back = f"/n/{slug}/p/{pro_id}?servico={service.id}&data={day_iso}"
        return public_page(
            request,
            services,
            "erro.html",
            {"message": "Este horário acabou de ser ocupado. Escolha outro.", "back": back},
            409,
        )
    return RedirectResponse(f"/agendamento/{token}", status_code=303)


@router.post("/n/{slug}/agendar")
def submit_booking(
    request: Request,
    slug: str,
    professional_id: Annotated[int, Form()] = -1,
    service_id: Annotated[int, Form()] = -1,
    day_iso: Annotated[str, Form()] = "",
    start_min: Annotated[int, Form()] = -1,
    customer_name: Annotated[str, Form()] = "",
    customer_phone: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    services = services_of(request)
    if not public_csrf_ok(request, csrf_token):
        return public_page(request, services, "erro.html", {"message": "Formulário expirado. Tente novamente."}, 403)
    pair = resolve_pair(services, slug, professional_id, service_id)
    day = parse_day(day_iso)
    today = services.clock.now().day
    if pair is None or day is None or not day_in_window(day, today) or start_min < 0:
        return not_found(request)
    business, pro, service = pair
    name, phone = clean_name(customer_name), normalize_phone(customer_phone)
    err = NAME_ERROR if not is_valid_name(name) else (PHONE_ERROR if phone is None else None)
    if err is not None or phone is None:
        return _confirm_error(
            request, services, business, pro, service, day_iso, day, start_min, err or PHONE_ERROR, name, customer_phone
        )
    if not can_book_more(services.bookings.active_count_for_phone(business.id, phone, today)):
        return public_page(request, services, "erro.html", {"message": LIMIT_ERROR, "back": f"/n/{slug}"}, 422)
    return _do_book(request, services, business.id, pro.id, service, day, start_min, name, phone, slug, day_iso)
