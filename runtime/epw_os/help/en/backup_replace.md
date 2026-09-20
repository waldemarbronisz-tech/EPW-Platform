# Replacing a Dead Controller

The card died, or the whole controller did. There is a spare on the
shelf. This is the order.

## Before you start

You need the **backup** (see [Backing Up This
Controller](help://backup_what)) and Engineer access to the spare. If
there is no backup, you still have the project — in Studio or in version
control — and everything else has to be rebuilt from memory, which is
what the backup exists to prevent.

## The order

1. **Put the spare in place** and give it power and the bus. It comes up
   on whatever project it had, or on none.
2. **Restore** — Settings → Restore from a backup..., point it at the
   file. It shows what is in the bundle; say yes. The controller rebuilds
   itself, without restarting.
3. **Set the access PINs** — Settings → Change PIN. The spare generated
   its own random ones on first start; nobody knows them.
4. **Set each person's keypad code** — Settings → Alarm system users.
   The people are already there: they come from the project. Only their
   secrets are missing, and the restore listed them by name.
5. **Issue the remote tokens** for whoever had one — the same dialog.
   A token is shown once. Paste it into that person's Home Assistant
   automation.
6. **Enter the MQTT broker password** — Settings → MQTT, if this
   installation uses it.
7. **Issue REST API tokens** if Studio connects to this controller.
8. **Check what the panel says**: the status bar's logic indicator, the
   alarm system's state, the cards responding on the bus. See [A New
   Controller, Step by Step](help://gs_first_steps) for what each of
   those should look like.
9. **Walk the lines** if anything on the alarm side was touched —
   [walk-test mode](help://intr_walk_test).
10. **Write it down** — [service notes](help://dio_service_notes). What
    died, when, what was swapped, what was re-issued.

## What you cannot get back

The trend history, and the audit entries recorded on the dead card since
the backup was taken. Everything else — the project, the counters, the
arming state, the alarm memory, the retentive bits, the audit log up to
the backup — is in the bundle.

Which is the argument for taking backups on a schedule rather than only
before changes.
