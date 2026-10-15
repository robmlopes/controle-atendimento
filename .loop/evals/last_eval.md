# Last eval

Demand: Scheduling system (intent `catalog-overview-and-custom-url`)
Verdict: PASS (ALL 6 PHASES COMPLETED AND VERIFIED)

- `aif check --json` -> `{"ok": true, "errors": []}`; 76 automated tests pass across the whole project.
- Quality suite details:
  - Ruff formatting and linting: clean.
  - AIF Intent scopes: all touched files matched within their intent declarations.
  - AIF001-AIF015 AST lint and effects verification: clean (no I/O in domain, functions <= 40 lines, files <= 200 lines, imports match `.aif/index.json`).
  - Mypy `--strict`: 0 errors.
  - Hypothesis contract fuzzing: passed for all invariants.
  - Pytest: 76 tests passed.

- Verified Features:
  1. **Personalized Public URL (`/negocio`)**:
     - Owner can configure and edit their slug (`/n/{slug}`).
     - Strict format validation (3 to 40 lowercase alphanumeric + hyphens).
     - Unique check preventing collision with other businesses (422).
     - Prominent URL card with interactive "Copiar link" button and direct "Abrir página pública" test link.
  2. **Catalog Overview Lists**:
     - `/painel` displays consolidated overview of all registered professionals (linked services, weekly schedule summary) and services (duration, formatted price).
     - `/profissionais` table shows linked services and schedule per professional.
     - `/servicos` table shows duration, price and who performs each service.
     - Direct access links to configure or deactivate.
  3. **Customer Anonymous Booking Flow**:
     - Customer accesses `/n/{slug}` without login.
     - Real-time computation of available slots based on service duration.
     - Double-submit CSRF cookie protection.
     - Per-phone limit (max 3 active bookings per business).
     - Atomic write via `BEGIN IMMEDIATE` guaranteeing zero double-booking under concurrency.
     - Direct `wa.me` pre-filled button on confirmation page.
     - Private cancellation token (`/agendamento/{token}`) releasing slot immediately upon cancel.
     - `Referrer-Policy: no-referrer` preventing token leakage to external sites.
  4. **Multi-tenancy & Isolation**:
     - Every catalog and agenda query is strictly scoped by `business_id` from the authenticated session.
     - Database error degraded-mode (503) without exposing tracebacks to end users.
EOF
