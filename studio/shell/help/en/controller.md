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
