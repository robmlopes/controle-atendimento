# SQLite persistence and atomic booking

## Why
The scheduling core needs durable storage. Booking must be atomic so two customers can never take the same slot, and the schema must migrate safely over databases that already exist on disk.

## Scope
- domain/models.py
- ports/clock.py
- ports/tokens.py
- ports/catalog.py
- ports/booking.py
- adapters/sqlite_db.py
- adapters/sqlite_catalog.py
- adapters/sqlite_booking.py
- adapters/system_clock.py
- tests/test_sqlite_booking.py
- tests/test_sqlite_migration.py
- tests/test_system_adapters.py

## Acceptance
- Concurrent attempts on the same slot produce exactly one `Booked`; the others get `SlotTaken`.
- Migration is idempotent and upgrades a legacy on-disk database without losing rows.
- `:memory:` is rejected; database errors are logged and re-raised.
- `aif check --json` returns ok.
