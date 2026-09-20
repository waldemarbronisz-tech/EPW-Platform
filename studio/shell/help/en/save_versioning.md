# Saving, revisions and settings

## The controller's three files

| File | What is in it | Who writes it |
|---|---|---|
| `projekt.epw` | the project: cards, points, apparatus, composition, screens, logic, alarm, protections | Studio; the controller only settings |
| `runtime_state.json` | state: counters, arming, bypasses, alarm memory | the controller only |
| the controller's local files | codes, tokens, passwords, language, REST, retentions | the controller only |

Secrets are **never** in the project — a project travels to Studio, into
git and over the network.

## The revision

It grows on every save and carries **who saved it**: Studio or the
panel. That is how a send can tell that the controller holds a newer
version than the one you started from — and **stop** instead of
overwriting somebody else's change.

## Structure versus setting

This is the split that decides what may be changed at the cabinet:

**Structure** — what exists at all: cards, points, apparatus, the
composition, zones, lines, screens, logic. Designed **in Studio only**.
The panel refuses a structural change and writes that refusal to the
audit log.

**A setting** — the value of something that exists: zone delays,
protection thresholds, line filters, an analog point's scaling, MQTT,
the sounder. The panel may change those (with an audit entry and a
"panel" revision), and Studio sees the difference and can take it — see
[Controller Connection](help://controller).

**The settings hash** is a digest of every setting at once. Studio
compares it before sending, so it does not ask about differences that
are not there.

## What is saved with the project

The screen from the [screen editor](help://screens) and the
**compiled** [logic](help://logic). If the logic does not compile,
Studio says so and keeps the previously compiled version; if the screen
editor refuses to hand over its document, it asks whether to save the
project with the **previously** saved screens.

## Backup and rollback

Installing on the controller keeps the previous file as
`projekt.epw.bak`. If the new one turns out to be unreadable at a later
start, the previous one comes back by itself and the refused one is kept
for inspection.
