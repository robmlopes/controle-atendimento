# MEMORY

## Project
- Name: controle-atendimento
- Goal: service/ticket tracking ("controle de atendimentos").

## Stack
- Python 3.11+, AIF framework (ruff, mypy --strict, Hypothesis, pytest).
- Test/stop command: `aif check --json`.
- Layout: `domain/` (pure, @contract), `ports/` (Protocols), `adapters/` (implementations), `tests/`.

## Graft map (initial)
- 5 files, 0 symbols, 0 edges: empty AIF scaffold (only `__init__.py` files and `tests/strategies.py`).

## Conventions
- Code, comments and docs in English. Commits end with `Intent: <id>`.
- Use `aif patch FILE SYMBOL` for edits; never edit `.aif/index.json` by hand.

## Lessons learned
- (none yet)

## Lessons (phase 1)
- AIF006 resolves `from x import y` against `.aif/index.json`, which lists only classes and functions. Module-level constants are rejected: use `Enum`/class members. Run `aif index` after adding symbols.
- `forbidden_imports` applies only to `pure_dirs` (domain/); adapters may use sqlite3/datetime.
- `aif check` can exceed the 60 s EATMCP timeout: run it with nohup in the background and read the output file.
- Domain time model: day = integer (0 = Monday, weekday = day % 7), time = minutes since midnight.

## Lessons (phase 2)
- Adapters: `Database.connection(write=True)` opens `BEGIN IMMEDIATE`; use it for any check-then-write. Reads use plain `BEGIN`.
- New columns go in `LATER_COLUMNS` in `adapters/sqlite_db.py` (added only when missing); never edit the first-version `TABLES` columns.
- mypy --strict flags `type: ignore`; type DB rows as `tuple[Any, ...]`.

## Lessons (phase 3)
- `web/` is now in `source_dirs`; `third_party` lists fastapi, starlette, jinja2, argon2, multipart, uvicorn (import names, not pip names).
- Contracts in `domain/auth.py`: module-level constants must be classes (`AuthPolicy`) because AIF006 only indexes classes/functions.
- Owner creation: `PYTHONPATH=. python scripts/create_owner.py --db app.db --slug x --name X --email a@b.com` (password prompt).
- Run in production: `CONTROLE_DB=app.db CONTROLE_HTTPS=1 uvicorn --factory web.app:default_app`.
- Quick start (Windows): double-click `iniciar.bat` (calls `scripts/iniciar.sh` in WSL; creates the owner on first run; `.db` files are git-ignored).
- Every owner query in phase 4 must filter by `SessionInfo.business_id`.

## Lessons (phase 4)
- Owner routes use `web/guard.py`: `guard()` for GET, `guard_post()` for POST (session + CSRF), `not_found()` for foreign ids. Always pass `owned.business_id` to the ports.
- Tests: use `tests/web_support.py` (`make_env`, `add_owner`, `login`, `post`). Two `TestClient`s on one app give two separate sessions.
- Domain day numbers: day = `date.toordinal() - 1` (e.g. 0001-06-01 = 151). Keep test dates in sync.
- `aif check` error entries from the tests stage have no `rule` key (they have `test` and `cause`).

## Lessons (phase 5)
- Public routes: use `web/public_common.py` (`public_page`, `public_csrf_ok`, `resolve_pair`, `wa_link`).
- CSRF for anonymous users: double-submit cookie `public_csrf`.
- Private tokens in URLs: always send `Referrer-Policy: no-referrer` on pages containing outbound links (e.g. `wa.me`) to prevent the token from leaking in the `Referer` header.
- AIF005 limits: files <= 200 lines, functions <= 40 lines. Split routers by flow: `public_pages.py` (read/search), `public_book.py` (confirm/submit), `public_view.py` (view/cancel).
- Verification summary: 75 automated tests (Hypothesis property tests, SQLite race conditions, legacy migrations, web isolation, full flow) + manual end-to-end smoke test on a real `uvicorn` instance.

## Custom URL & Catalog Overview Lists
- `/negocio` allows the owner to change the public link slug (`/n/{slug}`) with real-time feedback, clipboard copy button, open-in-new-tab link, and slug uniqueness check.
- `/painel` now features the personalized URL banner plus consolidated overview tables for registered professionals (with linked services and weekly hours) and registered services (duration, price).
- `/profissionais` and `/servicos` display cross-linked associations so the owner can verify exactly what was registered.

## UI Redesign (frontend-design skill)
- Installed `/root/.agents/skills/frontend-design` from official Anthropic skills repository.
- Replaced generic SaaS card-soup with an editorial "paper & ink" visual system:
  - Typography: Bricolage Grotesque (display/headlines) + Figtree (body/forms).
  - Palette: Deep ink `#16202e`, off-white paper `#f5f6f8`, yellow marker accent `#ffd23f`, cobalt buttons `#1f46d6`.
  - Layout: `split` layout on desktop (primary lists + right-hand creation panel), cleanly collapsing on mobile.
  - Public flow: branded header with avatar initial, 3-step progress bar, hour-grouped slot picker, clean summary facts list.
  - Micro-interactions: instant `data-copy` feedback, `data-confirm` prompts, `data-autosubmit` for service radio selection.
- All 76 automated tests pass, zero regressions, `aif check` clean.

## Framework Upgrade (ai-first-framework upstream @ 6fede70)
- Upgraded `aif-starter` from upstream `robmlopes/ai-first-framework`.
- New architectural rules adopted:
  - `entry_dirs = ["web"]` and `composition_roots = ["web.app"]`: prevents accidental adapter imports across random web routes; only `web.app` (composition root) connects adapters to `Services`.
  - `count_code_lines = true`: AIF005 line counting now ignores blank lines, comments, and docstrings.
  - `parallel = true`: concurrent execution of typecheck, fuzzing, and pytest (~15s total).
  - `history = true`: telemetry in `.aif/history.jsonl` queryable via `aif stats`.
  - `limit_warn_ratio = 0.9`: surfaces proactive warnings before files/functions hit the hard 40/200 limit.
- `aif check --json` verified clean with `{"ok": true, "errors": []}`.

## Spec 002: Professional Portal, Financials & Dedicated Pages
- Spec created at `.loop/specs/002-pro-portal-and-financials.md`.
- Shifted from single-owner overview to role-based access:
  - `owner`: global agenda, financial consolidation, staff commissions, business settings.
  - `professional`: private agenda, manual booking, status completion, individual balance/commission.
- Booking lifecycle: `confirmed` (previsão) -> `completed` (saldo realizado) or `cancelled` (estornado).
- Separate pages: `/agenda` (atendimentos diários e ações rápidas), `/financeiro` (saldo previsto vs realizado e extrato), `/profissionais`, `/servicos`, `/negocio`.
