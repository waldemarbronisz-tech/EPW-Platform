# Installing a Project

**File → Open**, Engineer level, audited. This is how a project designed
in EPW Studio comes into service on this controller.

## What happens, in order

1. The file is read by the **same reader Studio writes with**. A file it
   refuses never replaces anything — you are told why.
2. The previous project is kept as `projekt.epw.bak`.
3. The panel asks whether to **rebuild the controller now, without
   restarting**.
4. On yes: cards, channel tags, the bus driver, the device register,
   apparatus, commands, alarm users, the modules of the composition,
   point descriptions, command definitions and the logic program are all
   rebuilt from the new file, and this window is rebuilt with them.

Saying no is not a failure — the file is installed and takes effect at
the controller's next start, the way it always used to.

## What the rebuild stops, briefly

The logic scan and the alarm system, for as long as the rebuild takes.
[Forces](help://dio_force) are released first, deliberately: a force
pins a tag the new project may not even have.

Everything that outlives projects keeps running — the database, the
historical record, the safety kernel, MQTT, the REST API, the audit log,
and the access level you are signed in at.

## What disappears, and why that is right

A card deleted in Studio **takes its channel tags with it**. An
apparatus deleted in Studio stops being operable. A channel that exists
nowhere in the device should not stay readable on the panel for ever.

## If the new file cannot be read at a later start

The previous project comes back from `.bak` on its own and the refused
file is kept for inspection. The controller reports this as a startup
problem rather than starting on nothing.

## Sending from Studio instead

The same thing happens when Studio sends the project over REST — see
[The REST API](help://api_what). Studio compares revisions first and
stops if this controller has moved on in the meantime.
