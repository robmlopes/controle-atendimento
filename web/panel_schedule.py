"""Owner page of one professional: linked services, weekly ranges and blocks."""

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from domain.models import Block, DayLimit, Professional, WeeklyRule
from domain.panel import clean_name, format_time, is_valid_name, is_valid_range, is_valid_weekday, parse_time
from web.forms import iso_day, parse_day, to_int, weekday_name, whole_day
from web.guard import Owned, guard_owner, guard_owner_post, not_found, page

router = APIRouter()
RANGE_ERROR = "Horário inválido: informe início e fim no formato HH:MM, com o fim depois do início."
DAY_ERROR = "Data inválida."
WEEKDAY_ERROR = "Dia da semana inválido."


def _rules_view(rules: list[WeeklyRule]) -> list[dict[str, object]]:
    return [
        {
            "weekday": r.weekday,
            "name": weekday_name(r.weekday),
            "start": format_time(r.start_min),
            "end": format_time(r.end_min),
            "start_min": r.start_min,
            "end_min": r.end_min,
        }
        for r in rules
    ]


def _blocks_view(blocks: tuple[Block, ...]) -> list[dict[str, object]]:
    return [
        {
            "date": iso_day(b.day),
            "start": format_time(b.start_min),
            "end": format_time(b.end_min),
            "whole": whole_day(b.start_min, b.end_min),
            "day": b.day,
            "start_min": b.start_min,
            "end_min": b.end_min,
        }
        for b in blocks
    ]


def _context(owned: Owned, pro: Professional, error: str | None) -> dict[str, object]:
    services = owned.services
    today = services.clock.now().day
    linked = set(services.admin.linked_service_ids(pro.id))
    rules = sorted(services.catalog.rules(pro.id), key=lambda r: (r.weekday, r.start_min))
    account = services.owners.owner_by_professional(owned.business_id, pro.id)
    blocks = services.admin.blocks_from(pro.id, today)
    return {
        "pro": pro,
        "commission_pct": pro.commission_pct,
        "login_email": account.email if account else None,
        "error": error,
        "all_services": [(s, s.id in linked) for s in services.admin.business_services(owned.business_id)],
        "rules": _rules_view(rules),
        "weekdays": list(enumerate(("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"))),
        "blocks": _blocks_view(blocks),
        "today": iso_day(today),
    }


def _show(request: Request, owned: Owned, pro: Professional, error: str | None, status: int = 200) -> Response:
    return page(request, owned, "profissional.html", _context(owned, pro, error), status)


def _own(request: Request, professional_id: int, csrf: str | None) -> tuple[Owned, Professional] | Response:
    owned = guard_owner(request) if csrf is None else guard_owner_post(request, csrf)
    if isinstance(owned, Response):
        return owned
    pro = owned.services.admin.professional(owned.business_id, professional_id)
    return not_found(request) if pro is None else (owned, pro)


def _back(professional_id: int) -> Response:
    return RedirectResponse(f"/profissionais/{professional_id}", status_code=303)


@router.get("/profissionais/{professional_id}")
def professional_page(request: Request, professional_id: int) -> Response:
    found = _own(request, professional_id, None)
    return found if isinstance(found, Response) else _show(request, found[0], found[1], None)


@router.post("/profissionais/{professional_id}/editar")
def update_professional_action(
    request: Request,
    professional_id: int,
    name: Annotated[str, Form()] = "",
    commission_pct: Annotated[str, Form()] = "100",
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    found = _own(request, professional_id, csrf_token)
    if isinstance(found, Response):
        return found
    owned, pro = found
    name = clean_name(name)
    pct = to_int(commission_pct)
    if not is_valid_name(name) or pct is None or not (0 <= pct <= 100):
        return _show(request, owned, pro, "Nome ou comissão inválidos.", 422)
    owned.services.admin.update_professional(owned.business_id, professional_id, name, pct)
    return _back(pro.id)


@router.post("/profissionais/{professional_id}/servicos")
def set_services(
    request: Request,
    professional_id: int,
    service_ids: Annotated[list[str], Form()] = [],  # noqa: B006
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    found = _own(request, professional_id, csrf_token)
    if isinstance(found, Response):
        return found
    wanted = tuple(i for i in (to_int(raw) for raw in service_ids) if i is not None)
    found[0].services.admin.set_services(found[0].business_id, professional_id, wanted)
    return _back(professional_id)


@router.post("/profissionais/{professional_id}/horarios")
def add_rule(
    request: Request,
    professional_id: int,
    weekday: Annotated[str, Form()] = "",
    start: Annotated[str, Form()] = "",
    end: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    found = _own(request, professional_id, csrf_token)
    if isinstance(found, Response):
        return found
    owned, pro = found
    day, begin, finish = (
        to_int(weekday),
        parse_time(start),
        parse_time(end) if end.strip() != "24:00" else DayLimit.MINUTES,
    )
    if day is None or not is_valid_weekday(day):
        return _show(request, owned, pro, WEEKDAY_ERROR, 422)
    if begin is None or finish is None or not is_valid_range(begin, finish):
        return _show(request, owned, pro, RANGE_ERROR, 422)
    owned.services.admin.add_rule(owned.business_id, WeeklyRule(pro.id, day, begin, finish))
    return _back(pro.id)


@router.post("/profissionais/{professional_id}/horarios/remover")
def remove_rule(
    request: Request,
    professional_id: int,
    weekday: Annotated[int, Form()] = -1,
    start_min: Annotated[int, Form()] = -1,
    end_min: Annotated[int, Form()] = -1,
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    found = _own(request, professional_id, csrf_token)
    if isinstance(found, Response):
        return found
    found[0].services.admin.remove_rule(found[0].business_id, WeeklyRule(professional_id, weekday, start_min, end_min))
    return _back(professional_id)


@router.post("/profissionais/{professional_id}/bloqueios")
def add_block(
    request: Request,
    professional_id: int,
    date: Annotated[str, Form()] = "",
    start: Annotated[str, Form()] = "",
    end: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    """Empty start and end block the whole day."""
    found = _own(request, professional_id, csrf_token)
    if isinstance(found, Response):
        return found
    owned, pro = found
    day = parse_day(date)
    if day is None:
        return _show(request, owned, pro, DAY_ERROR, 422)
    whole = not start.strip() and not end.strip()
    begin = 0 if whole else parse_time(start)
    finish = DayLimit.MINUTES if whole else (DayLimit.MINUTES if end.strip() == "24:00" else parse_time(end))
    if begin is None or finish is None or not is_valid_range(begin, finish):
        return _show(request, owned, pro, RANGE_ERROR, 422)
    owned.services.admin.add_block(owned.business_id, Block(pro.id, day, begin, finish))
    return _back(pro.id)


@router.post("/profissionais/{professional_id}/bloqueios/remover")
def remove_block(
    request: Request,
    professional_id: int,
    day: Annotated[int, Form()] = -1,
    start_min: Annotated[int, Form()] = -1,
    end_min: Annotated[int, Form()] = -1,
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    found = _own(request, professional_id, csrf_token)
    if isinstance(found, Response):
        return found
    found[0].services.admin.remove_block(found[0].business_id, Block(professional_id, day, start_min, end_min))
    return _back(professional_id)
