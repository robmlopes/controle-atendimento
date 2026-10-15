"""CSRF, link resolution and templates for the public flow."""

from urllib.parse import quote

from fastapi import Request
from fastapi.responses import Response

from domain.models import Business, Professional, Service
from web.auth import csrf_ok
from web.services import Services, render

PUBLIC_CSRF_COOKIE = "public_csrf"


def public_page(
    request: Request, services: Services, name: str, context: dict[str, object], status: int = 200
) -> Response:
    csrf = request.cookies.get(PUBLIC_CSRF_COOKIE) or services.tokens.new_token()
    response = render(request, name, {"csrf_token": csrf, **context}, status)
    response.set_cookie(
        PUBLIC_CSRF_COOKIE, csrf, httponly=True, samesite="lax", secure=services.cookie_secure, max_age=86400
    )
    return response


def public_csrf_ok(request: Request, csrf_token: str) -> bool:
    return csrf_ok(csrf_token, request.cookies.get(PUBLIC_CSRF_COOKIE))


def resolve_pro(services: Services, slug: str, professional_id: int) -> tuple[Business, Professional] | None:
    business = services.catalog.business_by_slug(slug)
    if business is None:
        return None
    pro = services.admin.professional(business.id, professional_id)
    return None if pro is None else (business, pro)


def resolve_pair(
    services: Services, slug: str, professional_id: int, service_id: int
) -> tuple[Business, Professional, Service] | None:
    found = resolve_pro(services, slug, professional_id)
    if found is None:
        return None
    business, pro = found
    service = services.catalog.service(service_id)
    if service is None or service.business_id != business.id:
        return None
    if service.id not in services.admin.linked_service_ids(pro.id):
        return None
    return business, pro, service


def wa_link(number: str | None, text: str) -> str | None:
    if not number:
        return None
    digits = "".join(ch for ch in number if ch.isascii() and ch.isdigit())
    return f"https://wa.me/{digits}?text={quote(text)}"
