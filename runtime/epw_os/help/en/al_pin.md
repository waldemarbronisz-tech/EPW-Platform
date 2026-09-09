# Changing Level and Entering a PIN

The access level changes ONLY through the dropdown switch on the top
bar (next to the clock), which shows the current level. It never
appears on its own in response to a denied action — raising your level
is a deliberate operator action.

## Raising your level

1. Click the access level switch on the top bar.
2. Choose Operator or Engineer.
3. If the session isn't already authenticated at that level (or higher),
   a PIN prompt appears.
4. Enter the PIN and confirm. A wrong PIN shows a message and lets you
   try again without closing the window.

## Too many wrong PINs in a row

After **5 consecutive wrong PINs** for a level, that level is locked out
for **30 seconds** — even the correct PIN is refused during that window,
so guessing repeatedly can never eventually succeed. The lockout is
per level (a locked-out Operator PIN doesn't affect Engineer) and
clears automatically once the 30 seconds pass; entering the right PIN
resets the wrong-attempt count back to zero. Every lockout is written
to the [audit log](help://ea_audit_log).

## Lowering your level

Lowering your level (e.g. from Engineer to User) **does not require a
PIN** — giving up privileges you already have doesn't need to be
confirmed by anything.

## Entering a PIN on a touchscreen

The PIN window has a built-in numeric keypad, ALWAYS visible regardless
of whether the general on-screen keyboard switch in Settings is on or
off — unlike every other window in the program. Reason: if the PIN
keypad depended on that switch, turning it off on a device with no
physical keyboard would make it impossible to log in at all — including
to reach Settings and turn the switch back on. More in
[Floating and Built-In Keyboards](help://kb_floating_embedded).
