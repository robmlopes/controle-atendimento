"""Dedicated financial balance and movement ledger page."""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from domain.models import MovementItem
from domain.panel import format_price, format_time
from web.forms import br_day, digits_only, iso_day, parse_day, weekday_name
from web.guard import Owned, guard, page

router = APIRouter()


def _calculate_range(period: str, today: int) -> tuple[int, int]:
    if period == "semana":
        weekday = today % 7
        return (today - weekday, today - weekday + 6)
    if period == "mes":
        return (today - 30, today)
    return (today, today)


def _resolve_dates(periodo: str, today: int, d_in: str | None, d_out: str | None) -> tuple[int, int]:
    if d_in and d_out:
        d_start = parse_day(d_in) or today
        d_end = parse_day(d_out) or today
        return (min(d_start, d_end), max(d_start, d_end))
    return _calculate_range(periodo, today)


def _fmt_movement(m: MovementItem) -> dict[str, object]:
    price_str = "—" if m.price_cents is None else f"R$ {format_price(m.price_cents)}"
    comm_str = "—" if m.price_cents is None else f"R$ {format_price(m.commission_cents)}"
    return {
        "booking_id": m.booking_id,
        "date": br_day(m.day),
        "day_iso": iso_day(m.day),
        "weekday": weekday_name(m.day),
        "time": f"{format_time(m.start_min)}–{format_time(m.end_min)}",
        "customer": m.customer_name,
        "phone": m.customer_phone,
        "whatsapp": digits_only(m.customer_phone),
        "professional": m.professional_name,
        "service": m.service_name,
        "price": price_str,
        "commission_pct": m.commission_pct,
        "commission": comm_str,
        "status": m.status,
    }


def _resolve_pro(owned: Owned, pro_id: int | None) -> int | None:
    return owned.professional_id if not owned.is_owner else pro_id


@router.get("/financeiro")
def financeiro_view(
    request: Request,
    periodo: Annotated[str, Query()] = "hoje",
    pro: Annotated[int | None, Query()] = None,
    data_inicio: Annotated[str | None, Query()] = None,
    data_fim: Annotated[str | None, Query()] = None,
) -> Response:
    owned = guard(request)
    if isinstance(owned, Response):
        return owned

    today = owned.services.clock.now().day
    from_day, to_day = _resolve_dates(periodo, today, data_inicio, data_fim)
    active_pro = _resolve_pro(owned, pro)
    summary = owned.services.financial.summary(owned.business_id, from_day, to_day, active_pro)
    movements = owned.services.financial.statement(owned.business_id, from_day, to_day, active_pro)
    pros = owned.services.catalog.professionals(owned.business_id) if owned.is_owner else ()

    return page(
        request,
        owned,
        "financeiro.html",
        {
            "periodo": periodo,
            "from_date_iso": iso_day(from_day),
            "to_date_iso": iso_day(to_day),
            "from_date_br": br_day(from_day),
            "to_date_br": br_day(to_day),
            "active_pro_id": active_pro,
            "professionals": pros,
            "realized": f"R$ {format_price(summary.realized_cents)}",
            "projected": f"R$ {format_price(summary.projected_cents)}",
            "gross_realized": f"R$ {format_price(summary.gross_realized_cents)}",
            "completed_count": summary.completed_count,
            "projected_count": summary.projected_count,
            "movements": [_fmt_movement(m) for m in movements],
        },
    )
