# Professional portal, financial balance and clean dedicated pages

## Why
The business owner and individual professionals need separate, dedicated views: professionals have their own logins, see only their own appointments, can book for clients directly, complete appointments, and view their balance/commission. The owner retains overall visibility. Navigation is clean and mobile-first, removing information clutter.

## Scope
- domain/models.py
- domain/auth.py
- domain/panel.py
- ports/admin.py
- ports/agenda.py
- ports/auth.py
- ports/catalog.py
- ports/financial.py
- adapters/sqlite_db.py
- adapters/sqlite_admin.py
- adapters/sqlite_agenda.py
- adapters/sqlite_auth.py
- adapters/sqlite_catalog.py
- adapters/sqlite_financial.py
- web/guard.py
- web/services.py
- web/app.py
- web/auth.py
- web/panel.py
- web/panel_agenda.py
- web/panel_booking_manual.py
- web/panel_financial.py
- web/panel_people.py
- web/panel_business.py
- web/templates/base.html
- web/templates/panel_base.html
- web/templates/_style.html
- web/templates/_ui.html
- web/templates/painel.html
- web/templates/agenda.html
- web/templates/agenda_nova.html
- web/templates/financeiro.html
- web/templates/profissionais.html
- web/templates/profissional.html
- web/templates/servicos.html
- web/templates/negocio.html
- tests/test_financial_domain.py
- tests/test_financial_adapters.py
- tests/test_pro_auth_and_agenda.py
- tests/web_support.py

## Acceptance
- Professionals can log in and see only their own agenda and balance.
- Owners can see all professionals or filter by professional.
- Appointments can be completed ("Concluir"), transitioning status from confirmed to completed.
- Completed appointments are calculated into realized balance; confirmed appointments into projected balance.
- Financial statement displays daily ledger with gross value and professional commission split based on commission_pct.
- Manual booking on the agenda validates against professional's available slots without double-booking.
- Mobile-first app layout with bottom navigation on phone, top bar on desktop, and distinct dedicated pages.
- `aif check --json` passes cleanly with 0 errors.
