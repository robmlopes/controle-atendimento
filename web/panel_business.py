"""Owner page for business settings (name, slug, WhatsApp, public link preview)."""

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from domain.panel import clean_name, is_valid_name
from domain.public import is_valid_slug, normalize_phone
from web.guard import Owned, guard_owner, guard_owner_post, not_found, page

router = APIRouter()
PHONE_ERROR = "WhatsApp inválido: use DDD + número (ex.: 11 99999-8888), ou deixe em branco."
NAME_ERROR = "Nome inválido (1 a 80 caracteres)."
SLUG_ERROR = "URL personalizada inválida: use 3 a 40 letras minúsculas, números ou hífen (sem hífen nas pontas)."
SLUG_TAKEN = "Esta URL personalizada já está em uso por outro negócio. Escolha outra."


def _business_page(request: Request, owned: Owned, error: str | None, status: int = 200) -> Response:
    business = owned.services.admin.business(owned.business_id)
    if business is None:
        return not_found(request)
    saved = request.query_params.get("salvo") == "1"
    host = request.headers.get("host", "localhost:8000")
    scheme = "https" if owned.services.cookie_secure else "http"
    base_url = f"{scheme}://{host}"
    return page(
        request,
        owned,
        "negocio.html",
        {"business": business, "error": error, "saved": saved, "base_url": base_url},
        status,
    )


@router.get("/negocio")
def business_settings(request: Request) -> Response:
    owned = guard_owner(request)
    if isinstance(owned, Response):
        return owned
    return _business_page(request, owned, None)


@router.post("/negocio")
def update_business(
    request: Request,
    name: Annotated[str, Form()] = "",
    slug: Annotated[str, Form()] = "",
    whatsapp: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    owned = guard_owner_post(request, csrf_token)
    if isinstance(owned, Response):
        return owned
    name = clean_name(name)
    clean_slug = slug.strip().lower()
    wa = normalize_phone(whatsapp) if whatsapp.strip() else None
    if not is_valid_name(name):
        return _business_page(request, owned, NAME_ERROR, 422)
    if not is_valid_slug(clean_slug):
        return _business_page(request, owned, SLUG_ERROR, 422)
    if whatsapp.strip() and wa is None:
        return _business_page(request, owned, PHONE_ERROR, 422)
    if not owned.services.admin.is_slug_available(clean_slug, owned.business_id):
        return _business_page(request, owned, SLUG_TAKEN, 422)
    owned.services.admin.update_business(owned.business_id, name, clean_slug, wa)
    return RedirectResponse("/negocio?salvo=1", status_code=303)
