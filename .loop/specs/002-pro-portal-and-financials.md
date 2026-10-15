# Spec 002: Professional Portal, Financial Balance & UI Redesign

Status: APPROVED (design validated with the user via `/brainstorming`)

## Goal
Transform the system with dedicated, clean pages and a mobile-first app layout. Enable professionals to have individual logins to view only their own schedule, register manual appointments directly for walk-in/WhatsApp clients, mark appointments as completed or cancelled, and track their daily financial balance and commission statement. Business owners retain global visibility and configuration control.

## Understanding Summary
- **Dedicated Pages (No clutter)**: The panel is divided into dedicated pages: Agenda (`/agenda`), Financial statement (`/financeiro`), Team & Services (`/profissionais`, `/servicos`), and Business profile (`/negocio`).
- **Individual Professional Logins**: In addition to the owner, professionals can log in with their email and password to access their exclusive schedule and balance.
- **Manual Bookings**: Professionals and owners can book appointments directly on behalf of customers who reach out directly, selecting available slots from the schedule.
- **Appointment Lifecycle**: Bookings now transition between:
  - `confirmed`: initial reservation, counts towards "Saldo Previsto" (projected balance).
  - `completed`: service executed, transfers to "Saldo Realizado" (earned balance).
  - `cancelled`: appointment cancelled, zeroed out from balance.
- **Financial Balances & Daily Movement History**:
  - Each professional has a configurable commission percentage (`commission_pct`, e.g., 60%).
  - The financial page calculates projected balance vs. completed balance and provides a daily movement ledger detailing customer, service, gross amount, and professional commission split.
- **Mobile-First App Layout**: Streamlined, app-like navigation with bottom navigation / clean top bar, high-contrast touch targets, and responsive cards.

## Assumptions
- **A1. Unified Login Endpoint**: Both owners and professionals log in at `/login`; session credentials determine their role (`owner` vs `professional`) and target views.
- **A2. Professional Privacy Isolation**: Professionals see only their own bookings, their own commission rates, and their own balance. Only the owner sees consolidated figures.
- **A3. Concurrency Protection on Manual Bookings**: Manual bookings execute with the same atomic transaction engine (`BEGIN IMMEDIATE`) as public customer bookings to guarantee zero double-booking.
- **A4. Idempotent Migrations**: Database tables `professionals`, `owners`, and `bookings` are updated via non-destructive dynamic column migrations on disk.
- **A5. Zero Data Loss**: Existing bookings retain their `confirmed` status until manually completed or cancelled.

## Decision Log
- **D1. Polymorphic Session with Unified Login**: Rejected separate portals (`/pro/` vs `/admin/`) to avoid route and template duplication; session assigns role and bounds data access.
- **D2. Commission Percentage per Professional**: Configured at the professional level (e.g., 60% for professional, 40% for business) for simplicity and broad industry alignment (salons, clinics, barber shops).
- **D3. Scheduled Slot Validation for Manual Bookings**: Manual bookings adhere to the professional's schedule and free slot grid to prevent calendar conflicts.
- **D4. Dedicated Pages over Monolithic Dashboard**: Information is strictly separated into Agenda, Financial, Team, and Business views.
- **D5. Mobile-First App Navigation**: Bottom bar for phone screens and top bar for desktops, with responsive action buttons.

## Architecture & Implementation Plan

### Phase 1: Domain & Persistence
1. Update `domain/models.py`:
   - Extend `BookingStatus` with `COMPLETED = "completed"`.
   - Update `Professional` with `commission_pct: int`.
   - Add financial and movement view models (`FinancialSummary`, `MovementItem`).
   - Add role models (`UserRole`: `OWNER`, `PROFESSIONAL`).
2. Update `adapters/sqlite_db.py`:
   - Dynamic migrations for `professionals.commission_pct`, `owners.role`, `owners.professional_id`, `bookings.completed_at`.
3. Update `ports/` and `adapters/` for auth, agenda, booking transitions, and financial calculations:
   - Method `complete_booking(business_id, booking_id, pro_id=None) -> bool`.
   - Method `financial_statement(business_id, pro_id=None, start_day, end_day) -> tuple[MovementItem, ...]`.

### Phase 2: Dedicated Agenda Page & Manual Booking
1. Route `/agenda` (or `/painel` redirected):
   - Daily view with date navigation (Hoje, Amanhã, Seletor).
   - Filter by professional for owners; locked to own agenda for professionals.
   - Quick action buttons: "Concluir", "Cancelar", "WhatsApp".
2. Manual booking modal / action sheet:
   - Form with professional, service, day, free slot picker, customer name, and WhatsApp.

### Phase 3: Financial Page & Movement Statement
1. Route `/financeiro`:
   - Filter by period (Hoje, Esta Semana, Este Mês).
   - Summary cards: Saldo Realizado (Comissão Concluída), Previsão (Atendimentos Confirmados), Faturamento Bruto.
   - Daily movement history table/ledger showing customer, service, value, status, and commission.

### Phase 4: Team, Commission & Business Pages
1. Route `/profissionais`:
   - Add commission percentage input when creating or editing a professional.
   - Option to create login credentials (email and password) for the professional.
2. Distinct UI polish across all pages following mobile-first app navigation.

### Phase 5: Verification & End-to-End Testing
1. Automated tests for commission calculations, status transitions (`confirmed` -> `completed`), role permission boundaries, and manual booking atomic safety.
2. Full `aif check --json` verification.
