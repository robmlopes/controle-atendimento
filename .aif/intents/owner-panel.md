# Owner panel

## Why
The owner must manage professionals, services, weekly hours and blocks, see the agenda and cancel bookings. Every operation must be scoped to the business of the session so one owner can never read or change another business.

## Scope
- domain/models.py
- domain/panel.py
- ports/admin.py
- ports/agenda.py
- adapters/sqlite_db.py
- adapters/sqlite_admin.py
- adapters/sqlite_agenda.py
- web/app.py
- web/auth.py
- web/forms.py
- web/guard.py
- web/panel.py
- web/panel_people.py
- web/panel_schedule.py
- web/services.py
- web/templates/base.html
- web/templates/panel_base.html
- web/templates/painel.html
- web/templates/profissionais.html
- web/templates/profissional.html
- web/templates/servicos.html
- tests/strategies.py
- tests/web_support.py
- tests/test_panel_domain.py
- tests/test_admin_adapters.py
- tests/test_sqlite_migration.py
- tests/test_web_auth.py
- tests/test_web_panel.py

## Acceptance
- Owner can add and deactivate professionals and services, link services to professionals, add and remove weekly ranges and blocks, and cancel bookings.
- Ids from another business give 404 and change nothing; pages never list another business's data.
- Invalid input re-renders the form with a message (422) and keeps the typed values; names are HTML-escaped.
- Every POST needs the session CSRF token; every panel page needs a session.
- A database failure shows the explicit 503 page.
- The `services.active` column is added to legacy databases by the idempotent migration.
- `aif check --json` returns ok.
