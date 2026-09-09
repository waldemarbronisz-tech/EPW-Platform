# Floating and Built-In Keyboards

The program has two SEPARATE on-screen keyboard solutions, deliberately
built differently.

## The floating keyboard

A separate, movable, resizable little window that appears next to a
text field in ordinary tables (digital input/output descriptions,
analog point descriptions and notes). Controlled by the switch in
[Turning It On](help://kb_enable), in Settings. It automatically picks a
full alphanumeric keyboard or a numeric-only one, depending on the
field type.

## The keyboard built into the PIN window

The PIN entry windows (logging in to a higher level, changing a PIN)
have a **built-in** numeric keypad — not a separate window, but part of
that same window. It is **always** visible, regardless of the floating
keyboard switch's state in Settings.

## Why this distinction exists

A separate, floating keyboard window could not reliably type characters
into a field inside a modal window (like the PIN window) — a modal
window in Qt blocks input delivery from other, separate windows.
Rather than fix that cross-window communication, the numeric keypad was
built directly into the PIN window itself, where that problem simply
doesn't occur structurally. And because, on a device with no physical
keyboard, turning off the floating keyboard in Settings must never cut
off the only way to enter a PIN (including the PIN needed to reach
Settings and turn it back on) — the PIN keypad doesn't depend on that
switch at all.

A physical keyboard, wherever one is connected, always works alongside
both solutions — neither one replaces it.
