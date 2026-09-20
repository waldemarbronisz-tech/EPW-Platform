# Restoring From a Backup

**Settings → Restore from a backup...**, Engineer level, audited.

## What happens

1. The file is read and checked: the format, the schema version and a
   checksum over the whole bundle. A file that was altered or truncated
   since it was written is **refused before anything is touched** — a
   restore is never half-applied.
2. You are shown what is in it — which project, which revision, how
   many counters, which zones were armed at the time — **before**
   anything is overwritten.
3. On yes: the project, the state file and the local settings are
   written, and the controller **rebuilds itself from them without
   restarting** (the same rebuild an
   [install](help://proj_install) goes through).
4. You get the list of what nobody could restore for you.

## What is not overwritten

The settings that describe **this** controller rather than the
installation: its REST address, its I/O driver and its file paths. A
replacement sits on a different network and may have a different bus,
and the backup was taken from the hardware that died.

## The arming state comes back as it was left

A zone that was armed comes back armed, in the mode it was armed in.
That is the same rule the controller already applies to its own restart
— a restore is a restart with extra steps — and the audit log records
it. A controller that came back disarmed would be lying about the
building.

## The checklist

Every restore ends with it, because the backup deliberately carries no
secrets (see [Backing Up This Controller](help://backup_what)):

- the access PINs — [Changing a PIN](help://al_change_pin);
- each alarm user's keypad code and remote token, by name —
  [Alarm System Users](help://intr_users);
- the REST API tokens;
- the MQTT broker password — [MQTT](help://mqtt_what).

Until those are set, the controller runs the right installation with
its own freshly generated PINs, which nobody knows.
