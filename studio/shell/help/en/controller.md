# Controller Connection

This is where the project reaches the controller, and where you see what
it is actually doing.

## Connection

The **Address (URL)** and an **access token** (Engineer — issued on the
controller's panel), then **Test Connection**. The state shows beside
it: unknown / testing / connection OK / failed, with the reason.

## Project sync

### Send to Device

1. **The project must be saved** — the controller receives the file on
   disk, not the contents of the window. Studio offers to save.
2. Studio fetches the controller's header and compares the **revision**
   and the **settings hash**.
3. If the settings have diverged — a table of differences: the setting,
   Studio's value, the controller's value. You can send and overwrite,
   or cancel.
4. If the controller's revision changed while you were deciding,
   **nothing is sent** and you are told. A divergence means stop.
5. The controller **rebuilds itself from the new project without
   restarting**: cards, points, apparatus, commands, the alarm system,
   protections, the logic and the panel. The message says outright
   whether that is what happened.

### Receive from Device

Pulls `projekt.epw` exactly as the controller is running it — with the
settings changed on the panel and the service notes written there.

## Live preview

**Fetch Tag Preview** — a tag / value / quality table. The same channel
feeds Live mode in the [point registry](help://points), in
[cards](help://io_cards) and in the [screen editor](help://screens).

## Controller settings (live)

**Fetch Settings**, optionally **refresh every 5 s** and **differences
only**. The table: setting / Studio / controller, with the differences
highlighted.

**Take controller values into project** writes the controller's values
into the project — the way back for settings somebody corrected at the
cabinet. Save the project afterwards to keep them.

## Controller-local settings

**Fetch Local Settings** — read-only: the interface language, REST, the
historian's and audit log's retention, the I/O driver, file paths. These
describe **this one controller**, not the installation, so they are not
in the project — but nothing on the controller is invisible from Studio.

## Controller backup

**Take a backup...** pulls everything that exists only on that
controller: the switching counters, the arming state, the alarm memory,
the retentive logic bits, the audit log, the local settings and the
project itself.

It carries **no secrets** — no PINs, no alarm users' codes, no tokens,
no broker password. A backup is a file that leaves the site, and a
four-digit PIN behind a hash is not a secret. What it carries instead is
an inventory of who HAD what, so a restore ends with a checklist naming
exactly what to set by hand.

**Restore from a backup...** asks the controller to describe the bundle
first, shows you what it is about to overwrite, and only then sends it.
The controller rebuilds itself from it without restarting. The
replacement's own REST address and I/O driver are left alone — they
describe the hardware it is running on, not the hardware that died.

The whole replacement procedure is on the controller's own help, under
"Backup and replacement".

## Switching counters

**Fetch Counters** — the point, closes, opens, closed time, the warning
threshold (from the [point registry](help://points)).

**Reset Selected** / **Reset All** — irreversible, they need an Engineer
token and they go into the audit log. The warning threshold stays.

A controller with no Switching Counters module says so, rather than
showing an empty table.

## Logic state

One line, refreshed with the rest:

- **RUNNING** — how many blocks, the cycle time, the scan count, the
  longest scan, how many outputs the logic drives;
- **STOPPED** — a program is loaded but the scan is not running: **the
  interlocks in it are not being evaluated**;
- **none** — the controller runs without user logic;
- **NOT running** — the program was refused, with the reason.
