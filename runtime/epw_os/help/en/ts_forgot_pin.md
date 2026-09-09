# Forgotten PIN

If the PIN keeps getting rejected right after 5 wrong attempts, it may
not be forgotten at all — see
[PIN lockout](help://al_pin) first; that clears itself in 30 seconds
and needs none of the steps below.

The program has no built-in PIN recovery feature accessible from the
interface — there is no "forgot my PIN" option in the login window.

PINs are stored only as a hash (SHA-256), in the file
`epw_os/config/access.local.json`, outside the project file. This file
is created automatically the first time the program runs — that's also
when the program generates random PINs for Operator and Engineer and
shows them ONCE in the startup log (console).

## What to do if a PIN is forgotten

The only way out requires access to the computer itself running the
program (not through the EPW OS interface):

1. Close the program.
2. Delete the file `epw_os/config/access.local.json`.
3. Start the program again — it will generate new random PINs and show
   them in the startup log.

This resets BOTH existing PINs (Operator and Engineer) at once, so
write down both new values right away. There is no way to recover the
old, forgotten PIN — only to replace it with a new one.
