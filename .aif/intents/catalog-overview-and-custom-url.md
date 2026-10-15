# Catalog overview lists and custom URL

## Why
The business owner needs to customize their personalized access URL (slug) directly from the settings, and needs clear lists to verify everything that has been registered (professionals with their services and schedules, registered services with prices and durations, and the personalized public link).

## Scope
- ports/admin.py
- adapters/sqlite_admin.py
- web/panel.py
- web/panel_business.py
- web/panel_people.py
- web/templates/painel.html
- web/templates/negocio.html
- web/templates/profissionais.html
- web/templates/servicos.html
- tests/test_admin_adapters.py
- tests/test_web_panel.py
- tests/test_web_public.py

## Acceptance
- The owner can customize and change the business access URL (slug) from `/negocio` with format validation and uniqueness check.
- The public access link is prominently displayed on the panel and settings with a copy button.
- The panel (`/painel`) displays consolidated overview lists to verify all registered professionals (with linked services and weekly hours) and registered services (with duration and price).
- The professionals list (`/profissionais`) shows which services each professional performs and their working schedule.
- The services list (`/servicos`) shows duration, price and which professionals offer that service.
- `aif check --json` returns ok.
