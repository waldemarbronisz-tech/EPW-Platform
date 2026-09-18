# Point Registry

**Live and forcing.** "Live from the controller" on the main toolbar
adds a column with every point's value read from the controller (a
quality other than GOOD in brackets, orange background). Force mode
(the padlock on the registry's toolbar, after a dialog with the rules,
Engineer token) lets a row's menu force a value or release the force; a
forced point is red with "F →". "Release All Forces" or leaving the mode
drops everything; the controller drops them itself when the link to
Studio is lost and on restart. The protection path is never forced.

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
