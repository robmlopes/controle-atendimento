# Owner authentication

## Why
Only the business owner may manage professionals, services and hours. Login must be safe: strong password hashing, server-side sessions, CSRF protection and a login rate limit.

## Scope
- .gitignore
- aif.toml
- pyproject.toml
- domain/auth.py
- ports/auth.py
- ports/catalog.py
- adapters/argon_hasher.py
- adapters/sqlite_db.py
- adapters/sqlite_auth.py
- adapters/sqlite_catalog.py
- web/__init__.py
- web/services.py
- web/auth.py
- web/app.py
- web/templates/base.html
- web/templates/login.html
- web/templates/painel.html
- web/templates/erro.html
- scripts/create_owner.py
- tests/strategies.py
- tests/test_auth_domain.py
- tests/test_auth_adapters.py
- tests/test_web_auth.py

## Acceptance
- A valid owner logs in and reaches `/painel`; wrong password or unknown e-mail gets the same generic error.
- After too many failures the login is refused (HTTP 429) even with the right password.
- POST without a valid CSRF token is rejected (403).
- `/painel` without a session redirects to `/login`; logout invalidates the session; expired sessions are refused.
- Passwords are stored only as argon2 hashes; session tokens only as hashes.
- A database failure shows an explicit 503 page.
- `aif check --json` returns ok.
