# Visual redesign of owner panel and public booking pages

## Why
The first UI was unstyled and hard to use. The owner panel and the public booking flow need a clean, modern, mobile-first look with a clear visual hierarchy.

## Scope
- web/templates/base.html
- web/templates/_style.html
- web/templates/_ui.html
- web/templates/panel_base.html
- web/templates/login.html
- web/templates/erro.html
- web/templates/painel.html
- web/templates/negocio.html
- web/templates/profissionais.html
- web/templates/servicos.html
- web/templates/profissional.html
- web/templates/public_home.html
- web/templates/public_pro.html
- web/templates/public_confirm.html
- web/templates/public_booking.html

## Acceptance
- One shared design system (colors, typography, buttons, cards, forms, tables, chips) is used by every page.
- The public flow shows the business brand, a step indicator, professional cards, service cards and time slots as tappable chips grouped by period.
- The owner panel has a top navigation with the active page highlighted, summary cards and responsive tables.
- All pages are usable on a phone (no horizontal page scroll, large tap targets).
- Behaviour, routes and form fields are unchanged; `aif check --json` returns ok.
