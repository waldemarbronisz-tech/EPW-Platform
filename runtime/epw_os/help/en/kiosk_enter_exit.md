# Entering and Exiting

## Entering

Kiosk Mode turns on in two ways:

1. **At program startup** — with the `--kiosk` parameter
   (`python main.py --kiosk`).
2. **While running** — Settings → Kiosk Mode, available only at the
   Engineer level.

Kiosk Mode is not remembered between runs — a plain restart without the
`--kiosk` parameter always starts normally.

## Exiting

Exiting Kiosk Mode requires the **Engineer** level and only ever
happens through a PIN — double-click, the Esc key, and F11 are
deliberately dead in kiosk, even when the menu bar happens to be
visible at the Engineer level.

Two ways out:

- **Settings → Kiosk Mode** (the same menu item used to enter it) —
  available only once you're already an Engineer, so clicking it
  immediately ends Kiosk Mode with no further PIN prompt.
- **Closing the program** (e.g. Alt+F4) — the program will ask for the
  Engineer PIN before it actually closes.

Every exit attempt — successful or not — is recorded to the audit log.
