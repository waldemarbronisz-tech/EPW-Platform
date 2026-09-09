# Three Levels: User, Operator, Engineer

EPW OS has three access levels, from lowest to highest:

1. **User** — the default level after every program start. View only,
   no PIN.
2. **Operator** — requires a PIN. Allows controlling switching devices
   from Main View.
3. **Engineer** — requires a PIN (different from Operator's). Full
   access, including configuration and settings.

Levels are cumulative: Engineer has everything Operator has, and
Operator has everything User has. The program **always** starts at the
User level, regardless of what level the previous session ended at —
the session itself isn't remembered between runs (the PINs are, but
that's a different thing — see [Changing a PIN](help://al_change_pin)).

Full list of what each level can do:
[the permission table](help://al_matrix).
