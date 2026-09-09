# Screen Layout: Menu, Status Bar, Navigation

## Menu Bar (top)

**File** — new/open/save/save as/export/import project (see
[The File Menu](help://gs_file_menu)).
**View** — fullscreen mode (see
[Kiosk Mode vs. Fullscreen Mode](help://kiosk_vs_fullscreen)).
**Project** — project properties and the recently-opened list (see
[The Project Menu](help://gs_project_menu)).
**Tools** — historical data export, presentation mode.
**Settings** — language, change PIN, screen sleep, on-screen keyboard,
visual theme, feature configuration, MQTT integration, training mode,
kiosk mode.
**Help** — this window, the index, and "About".

In Kiosk Mode the menu bar is hidden below the Engineer level — see
[Kiosk Mode](help://kiosk_what).

## Top Information Bar

Clock, project name, access level switch, alarm count, and
communication status ("COMM: OK" / "COMM: N OFFLINE" — depending on
whether any device has an OFFLINE status).

## Bottom Status Bar

On the left: several information fields, the time sync indicator
(green/red/olive — see
[Time Sync Indicator Shows Red](help://ts_time_sync)), and the version
number. On the right: the run-mode button (SIMULATION/LIVE) — clicking
it toggles the mode.

**User** — your current access level (User/Operator/Engineer), colored
the same way as the top-bar access dropdown. Updates immediately on
every level change, including the automatic 5-minute logout — it always
shows the level actually in effect, never a fixed name.

**DB** — Historian/database health, checked every few seconds (not on
every tag change): green **OK**, amber **SLOW** if the write queue is
backing up, red **ERROR** if the database or Historian isn't running.

**Latency** — round-trip time of the last completed command (request to
confirmed feedback, timeout, or rejection). Shows "no data" until the
first command has been issued this session.

**Scan** — the real, measured elapsed time of the driver's own polling
cycle, updated once per cycle. Shows "no data" until the first cycle
completes.

**Q: N%** (top bar) — percentage of the four core devices (Orange Pi,
ELA-01, ADA-01, Modbus) currently reporting ONLINE. The same figure
"COMM: OK" / "COMM: N OFFLINE" next to it is built from.

There used to be an **FPS** field here too. It was removed rather than
wired up: this program has no single continuous whole-window render
loop to measure a meaningful frame rate from (a couple of individual
pages redraw themselves on their own timer, e.g. the System Topology
diagram, but that isn't "the UI's FPS") — showing a number here would
just have been a differently-shaped made-up value, not a real one.

## Navigation Panel (left side)

A tree, grouped by subject: Main View; Control (Digital/Analog Inputs,
Control Outputs); Intrusion Alarm System (see
[What the Intrusion Alarm System Is](help://intr_what) for its own
three-page split); Measurements (Power Quality, Trends); Events (Event
Recorder, Alarms, Audit Log); Diagnostics (System Topology, Bus
Diagnostics, Engineer Mode); and Protection Settings (Electrical,
Process — see
[Electrical vs. Process Protections](help://prot_what)). Clicking a
group's own name opens the first page inside it; clicking the square
**[+]**/**[-]** box next to a group only expands or collapses it. A
group left with only one enabled page collapses to a single item
instead of a group you'd have to open first — how many pages a group
actually has (and therefore whether it currently collapses) depends on
Feature Configuration, same as the rest of this section.

Which groups and pages even appear here depends on which functions are
turned on — see [Feature Configuration](help://set_feature_config). A
group whose every page is off disappears entirely, not just its pages.
A colored square next to a group's own name (even while collapsed)
means something inside it needs attention — an unacknowledged alarm, an
active intrusion alarm, a line fault, or unacknowledged alarm memory.

What you can actually do on some of these pages depends on your access
level — see [Access Levels](help://al_matrix).

## Tooltips

Hovering over most buttons, status-bar fields, and indicators shows a
short tooltip explaining what it is or does — a passive hint, not a
separate feature to turn on or off.
