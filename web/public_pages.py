"""Public routes: business page, professional page and slot query."""

from fastapi import APIRouter, Request
from fastapi.responses import Response

from domain.panel import format_price, format_time
from domain.public import PublicPolicy, day_in_window
from domain.slots import free_slots
from web.forms import br_day, iso_day, parse_day, to_int, weekday_name
from web.guard import not_found
from web.public_common import public_page, resolve_pro
from web.services import Services, services_of

router = APIRouter()


def _compute_slots(services: Services, pro_id: int, duration_min: int, day: int) -> tuple[int, ...]:
    now = services.clock.now()
    return free_slots(
        pro_id,
        services.catalog.rules(pro_id),
        services.catalog.blocks(pro_id, day),
        services.bookings.for_day(pro_id, day),
        duration_min,
        day,
        now.day,
        now.minute,
        PublicPolicy.SLOT_STEP,
    )


@router.get("/n/{slug}")
def business_home(request: Request, slug: str) -> Response:
    services = services_of(request)
    business = services.catalog.business_by_slug(slug)
    if business is None:
        return not_found(request)
    pros = services.catalog.professionals(business.id)
    return public_page(request, services, "public_home.html", {"business": business, "people": pros})


@router.get("/n/{slug}/p/{professional_id}")
def professional_slots(request: Request, slug: str, professional_id: int) -> Response:
    services = services_of(request)
    found = resolve_pro(services, slug, professional_id)
    if found is None:
        return not_found(request)
    business, pro = found
    today = services.clock.now().day
    available = services.catalog.services_of(pro.id)
    sid = to_int(request.query_params.get("servico", ""))
    day = parse_day(request.query_params.get("data", "")) or today
    service = next((s for s in available if s.id == sid), None)
    slots = _compute_slots(services, pro.id, service.duration_min, day) if service and day_in_window(day, today) else ()
    return public_page(
        request,
        services,
        "public_pro.html",
        {
            "business": business,
            "pro": pro,
            "services": [
                {
                    "id": s.id,
                    "name": s.name,
                    "duration": s.duration_min,
                    "price": None if s.price_cents is None else format_price(s.price_cents),
                }
                for s in available
            ],
            "selected_service_id": sid,
            "selected_day": iso_day(day),
            "selected_day_label": f"{weekday_name(day)}, {br_day(day)}",
            "slots": [{"start": format_time(m), "minute": m} for m in slots],
            "has_searched": service is not None,
            "min_date": iso_day(today),
            "max_date": iso_day(today + PublicPolicy.MAX_DAYS_AHEAD),
        },
    )
