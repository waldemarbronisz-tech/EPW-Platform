# Changing a PIN

The **Settings → Change PIN...** window has two separate sections — one
for the Operator PIN, one for the Engineer PIN. Both work identically
and independently.

## What's needed to change it

To change a level's PIN, you need to know **that level's current PIN**
— it doesn't matter what level the current session is logged in at.
This means:

- someone logged in as Engineer can change the Operator PIN, but only
  by knowing the Operator's old PIN;
- simply being logged in as Engineer isn't enough to change the
  Engineer PIN without knowing the old one.

## Steps

1. Open Settings → Change PIN...
2. In the relevant section, enter the old PIN, the new PIN, and confirm
   the new PIN.
3. Click Save.

The new PIN must consist only of digits and must differ from the old
one. The change is saved immediately, with no need to save the project.

## Where PINs are stored

PINs are never stored as plain text — the program keeps only their
hash (SHA-256), in a separate file outside the project. More in
[Forgotten PIN](help://ts_forgot_pin).
