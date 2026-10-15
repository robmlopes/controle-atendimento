# Spec 001: Multi-niche scheduling system

Status: IMPLEMENTED (all 5 phases completed and verified) (design validated with the user, section by section).

## Goal
A web system where a business owner logs in, registers professionals, services and weekly availability, and shares a personalised public link. A customer opens the link without login, picks a professional, a service and a free time slot, and books. Niches: barbershop, manicure, hairdresser, dentist, etc.

## Understanding summary
- Multi-niche web scheduling app. Python, FastAPI, server-rendered HTML, SQLite behind a port.
- One account = one business with several professionals; each professional has their own agenda.
- Only the owner logs in. Customers are anonymous and give name and phone (WhatsApp).
- Owner manages professionals, services (name, duration, optional price), the professional-service N:N link, weekly recurring availability (several ranges per day, so lunch breaks work) and day/range blocks.
- Booking is confirmed automatically. Cancel via link with a random token. No rescheduling in v1.
- No automatic notifications in v1; only an "open WhatsApp" button with a prepared message (`wa.me`).

## Out of scope (v1)
Payments, rescheduling, automatic notifications (e-mail/WhatsApp API), mobile app, Google Calendar sync, staff logins/roles, multiple owner accounts per business.

## Assumptions
- A1. Public link uses a business slug: `/n/{slug}`.
- A2. A booked slot is unavailable immediately; reservation is atomic (no double booking).
- A3. Fixed time zone: America/Sao_Paulo.
- A4. Scale: tens of businesses, hundreds of bookings per day; public page under 1 s.
- A5. Password hashed with a strong algorithm (argon2); session cookie `HttpOnly` + `SameSite`; customer phone visible only to the owner; cancel token long and random.
- A6. 99% availability is enough.
- A7. `aif.toml` `third_party` and `pyproject.toml` must list new dependencies.
- A8. Only the owner logs in; professionals have no login.
- A9. Each professional has their own service list (N:N).
- A10. Slot grid is 15 minutes (default parameter).

## Non-functional
- Performance: free-slot calculation on demand is cheap at this scale.
- Security: CSRF protection on POST forms, login rate limit, every owner query filtered by the session `business_id`.
- Reliability: DB failure -> `logger.error` + explicit HTTP 503 page; never an empty page.
- Maintenance: web layer in `web/` is thin; business rules stay in `domain/`.

## Design (approach A: compute free slots on demand)
### Domain (`domain/`, pure, `@contract`)
Entities (immutable): Business(id, slug, name), Professional(id, business_id, name, active), Service(id, business_id, name, duration_min, price_cents?), ProfessionalService, WeeklyRule(professional_id, weekday 0-6, start_min, end_min), Block(professional_id, date, optional range), Booking(id, professional_id, service_id, date, start_min, end_min, customer_name, customer_phone, status confirmed|cancelled, cancel_token).
Time: `datetime` is forbidden in domain, so dates are plain values and times are integer minutes since midnight. Adapters convert.
Core function: `free_slots(rules, blocks, bookings, duration_min, date, now) -> list[start_min]`. Contracts:
1. every returned slot fits entirely inside a weekly rule range;
2. no slot overlaps a block or a `confirmed` booking;
3. no slot is in the past relative to `now`;
4. output is sorted and has no duplicates.

### Ports (`ports/`, Protocols)
`Clock`, `BusinessRead/Write`, `CatalogRead/Write`, `BookingRead/Write`, `Auth`, `TokenSource`.
`BookingWrite.create` returns `Booked | SlotTaken`.

### Adapters (`adapters/`)
SQLite implementations. Atomic reservation: one transaction checks overlap with `confirmed` bookings of the same professional, then inserts. Idempotent, backward-compatible migrations that inspect existing tables/columns; never assume `:memory:`. Errors are logged and re-raised. Also: system clock, secure token source, password auth.

### Web (`web/`)
Public: `GET /n/{slug}`, `GET /n/{slug}/p/{id}`, `GET /n/{slug}/p/{id}/horarios?servico=&data=`, `POST /n/{slug}/agendar`, `GET /agendamento/{token}`, `POST /agendamento/{token}/cancelar`.
Owner: `/login`, `/logout`, `/painel` (day agenda, upcoming bookings), CRUD for professionals, services, links, weekly rules, blocks; owner can cancel bookings.
Errors: invalid input -> form re-rendered with field messages and kept values; `SlotTaken` -> "slot just taken" + refreshed list; DB failure -> 503 page; invalid/used token -> "invalid link" page; unknown slug/id -> 404; cancelling twice is idempotent.
Phone normalised to E.164 Brazilian format (`+55DDDNUMBER`).

### Tests
Hypothesis for the 4 `free_slots` contracts (strategies in `tests/strategies.py`); SQLite adapter tests on a temp file, including migration over a legacy on-disk DB with data and a same-slot race (only one wins); FastAPI test client for the full public flow, business isolation, CSRF and login; final `aif check --json` with `ok: true`.

## AIF configuration decisions (to verify before implementing)
- `forbidden_imports` (`sqlite3`, `datetime`, `random`, `os`, ...) applies to all `source_dirs`. Keep `domain/` and `ports/` strict and relax only `adapters/` if `aif.toml` supports per-directory settings; otherwise use an allow list for adapters. Check the AIF docs first and log the result.
- Add to `third_party` and `pyproject.toml`: fastapi, uvicorn, jinja2, python-multipart, argon2-cffi.

## Phases (one loop demand each; 1-2 modules per task)
1. Domain core: models and `free_slots` with contracts and tests.
2. Persistence: ports and SQLite adapters, migrations, atomic booking.
3. Owner authentication: login, session, CSRF.
4. Owner panel: CRUD for professionals, services, hours, blocks.
5. Public page and booking: customer flow, cancellation, WhatsApp button.

## Risks
- R1. Double booking under concurrency (mitigated by the atomic transaction + test).
- R2. AIF restrictions block adapters/web imports until configuration is adjusted.
- R3. Time zone and DST edge cases (Brazil has no DST today, but dates must be handled consistently).
- R4. Customer phone is personal data (LGPD): show only to the owner, do not log it.

## Decision log
- D1. Business with several professionals (option B) instead of one agenda per account: user's choice; more flexible, needs the Professional entity from the start.
- D2. Customer gives name + phone only: lowest friction; e-mail left for later.
- D3. Weekly recurring availability + blocks (not manual slots): less work for the owner; slots computed from service duration.
- D4. Automatic confirmation with token cancel link, no rescheduling: simpler, no idle pending slots.
- D5. No automatic notifications in v1: no cost or external dependency; later added through a port without touching the domain.
- D6. Server-rendered FastAPI app (not API + SPA): one deploy, fast mobile page.
- D7. Approach A (compute slots on demand) over B (pre-generated slot rows) and C (third-party calendar): fewer tables, rule changes apply instantly, pure testable logic.
- D8. 15-minute slot grid.
- D9. Only the owner logs in; per-professional service lists (N:N).
- D10. Time as integer minutes and plain dates in domain because `datetime` is forbidden there; `Clock` port supplies "now".
- D11. Editable personalized business URL (slug) with uniqueness and format validation, displayed with a copy-to-clipboard button and direct client test link.
- D12. Consolidated catalog overview lists in `/painel`, `/profissionais` and `/servicos` showing professionals with their linked services and schedules, and services with durations and prices.

## Intent id
One intent per phase, created when the architect starts it, e.g. `aif intent new domain-core "Scheduling domain and free_slots"`, plus `catalog-overview-and-custom-url` for the overview lists and personalized URL.
