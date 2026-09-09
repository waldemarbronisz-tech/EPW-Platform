# Kiosk Mode vs. Fullscreen Mode

These are two completely separate mechanisms, even though both show
the program covering the whole screen.

| | Fullscreen Mode (View → Fullscreen Mode, F11) | Kiosk Mode |
|---|---|---|
| Availability | every level, no PIN | entering and exiting: Engineer only |
| Window frame | unchanged | removed |
| Menu bar | always visible | hidden below Engineer |
| Exiting | F11, Esc, or double-click in the work area | only with the Engineer PIN |
| Purpose | convenience, more screen space | protecting the operator station from an accidental or unauthorized change |

Fullscreen Mode is disabled and unavailable while Kiosk Mode is active
— the kiosk takes full ownership of the window state, so there's no
second, PIN-free way to change it.
