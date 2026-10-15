# Scheduling domain models and free_slots

## Why
Customers must only see time slots that are really bookable. The pure core computes free slots from weekly rules, blocks and bookings so every later layer (SQLite, web) reuses one verified rule.

## Scope
- domain/models.py
- domain/slots.py
- tests/strategies.py
- tests/test_slots.py

## Acceptance
- `free_slots` returns only slots inside a weekly rule, not overlapping blocks or confirmed bookings, not in the past, sorted and unique.
- `aif check --json` returns ok.
