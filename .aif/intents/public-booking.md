# Public booking page

## Why
A customer without login must open the business link, pick a professional, a service and a free slot, and book. The customer can cancel through a private token link, and the owner shares a personalised link and an optional WhatsApp number.

## Scope
- domain/models.py
- domain/public.py
- ports/booking.py
- ports/admin.py
- adapters/sqlite_db.py
- adapters/sqlite_catalog.py
- adapters/sqlite_booking.py
- adapters/sqlite_admin.py
- web/app.py
- web/services.py
- web/forms.py
- web/panel.py
- web/public_common.py
- web/public_pages.py
- web/public_book.py
- web/public_view.py
- web/panel_business.py
- web/templates/base.html
- web/templates/erro.html
- web/templates/panel_base.html
- web/templates/painel.html
- web/templates/negocio.html
- web/templates/public_home.html
- web/templates/public_pro.html
- web/templates/public_confirm.html
- web/templates/public_booking.html
- scripts/create_owner.py
- scripts/iniciar.sh
- tests/web_support.py
- tests/test_public_domain.py
- tests/test_public_adapters.py
- tests/test_web_public.py
- tests/test_sqlite_migration.py

## Acceptance
- A customer books a free slot without login; the slot disappears and the owner sees the booking in the agenda.
- Two customers taking the same slot: one gets the booking, the other a clear "slot taken" message with fresh slots.
- Past slots, dates beyond the booking window and professionals or services of another business are refused.
- Name and phone are validated; the phone is stored as +55DDDNUMBER; at most 3 active bookings per phone.
- Cancellation works only through the private token link, is idempotent, and frees the slot.
- Every public POST needs the CSRF cookie token; confirmation pages are `no-store` with `Referrer-Policy: no-referrer`.
- Names are HTML-escaped; a database failure shows the 503 page.
- The `businesses.whatsapp` column is added to legacy databases by the idempotent migration.
- `aif check --json` returns ok.
