# Point Registry

Every channel of every card gets its own row here — empty until you
name it. Columns:

- **Address** — card-relative, read-only (`ELA1.DI.1`).
- **Description** — the point's name, e.g. "Main breaker — closed".
- **Location** — from the Locations list.
- **Technical Note** — free text for the technician (terminal, cable).
- **Signal Type / Raw Min/Max / Eng Min/Max / Unit / Decimals** —
  scaling, analog points (AI/AO) only; grayed and hidden for DI/DO when
  filtered to one card.
- **Device** — read-only: which apparatus (from the Apparatus
  Registry) already claimed this point, if any.

The **Card** filter at the top narrows the view to one card at a time.
