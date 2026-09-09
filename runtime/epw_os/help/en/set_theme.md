# Visual Themes

**Settings → Theme...** picks the program's color palette. Five
built-in themes: **Industrial** (the program's original look, and the
default), **Night** (dark background), **High Contrast** (for
readability in direct sunlight, e.g. an outdoor cabinet), **Cyberpunk**
(neon accents), and **SimCity 2000** (a warm, retro palette). A theme
changes colors only — shapes, layout, and every window's content stay
exactly the same, and it takes effect immediately, no restart needed.

## Work mode: constant, or automatic day/night

The dialog's own **work mode** choice controls how the active theme is
picked:

- **Constant theme** (default) — pick one theme, it applies always,
  exactly like every earlier version of this program. Picking a
  different theme here is available at **every access level, no PIN**
  — a display preference, not a security control, same reasoning as
  Language or Screen Sleep.
- **Automatic day/night** — pick a day theme, a night theme, and the
  two times of day the switch happens (sensible defaults: 06:00/20:00,
  both adjustable). The program switches between them on its own, with
  no restart, checked every 30 seconds.

**Switching the work mode itself** — entering or leaving Automatic, or
adjusting an already-active day/night schedule — requires **Engineer**
level and is written to the audit log. Only the plain "pick one theme
while staying in Constant mode" path stays open to everyone.

## Controlling the theme from logic

A logic program can also switch the theme directly, by writing the
`System.Theme` tag (0 = Industrial … 4 = SimCity 2000; an out-of-range
write is ignored, the previous theme stays active). This works at any
time, regardless of the current work mode, and needs no access level
of its own to take effect.

**A logic-driven write always wins over Automatic mode.** The moment
logic sets the theme, automatic day/night switching stops acting —
until the work mode is changed again here, in Settings. The dialog
shows a note when this is currently the case, so it's clear why
Automatic mode looks configured but isn't switching. This is
deliberate: theme-switching rules (a light sensor, an active alarm, an
installation's own state) are expected to eventually live in logic —
Automatic mode is a stand-in for while that isn't built yet, and it
must never fight a logic program once one exists.

Your choice — theme, work mode, and the day/night schedule — is
remembered the next time you start the program.
