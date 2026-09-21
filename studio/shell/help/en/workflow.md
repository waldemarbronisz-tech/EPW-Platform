# How a project is built, step by step

The order is not arbitrary: each step uses what the previous one
created. **Cards give birth to points**, and points are the addresses
apparatus, supervised lines, protections, screens and logic all refer
to. Start by drawing a screen and there is nothing to bind symbols to.

Steps 1–4 can be done for you by the [Device
Wizard](help://wizard) (File → Device Wizard). The rest is ordinary
work in the tree.

---

## Step 1. A new project and its information

Top toolbar → **New**, then [Project
Information](help://info): the name (this is what the controller reports
as its project), the author, the description.

The root of the tree carries the same name — double-click renames it in
place.

## Step 2. Device composition

[Device Composition](help://devices) — tick the modules this controller
actually **has**. A module outside the composition does not exist: its
branch is not shown, and on the controller no object, no thread and no
tags are created for it.

Do this before configuring anything, so you do not fill in departments
that will not be there.

## Step 3. Locations

[Locations](help://locations) — short codes for places (a cabinet, the
boiler room, the gate). A card sits in one location and every point on
it inherits that location by default. Without this you cannot later
answer "where is this terminal".

## Step 4. I/O cards and the bus

[I/O Cards](help://io_cards) — one row per physical module: the id (the
first segment of every address), the model, which channel kinds it has
and how many of each, its Modbus address, its location.

**This is the moment points come into existence.** A card `ELA1` with 32
DI channels creates `ELA1.DI.1` … `ELA1.DI.32` in the point registry,
automatically.

The bus itself is configured here too (RTU or TCP, port, baud rate,
parity).

## Step 5. Describing the points

[Point Registry](help://points) — for each channel, write **what is
wired to it**, a technical note and, if it differs from the card's, its
own location. For analog points: signal type, the conversion from the
raw value to an engineering value, the unit and the decimals.

This description travels to the controller and is what the operator at
the cabinet reads. An address with no description is a channel number
and nothing more.

## Step 6. Apparatus

[Apparatus Registry](help://apparatus) — a breaker, a contactor, a
valve: its behavior, its feedback points and command points, the command
style (MAINTAINED / PULSE / PULSE_TOGGLE).

The apparatus is what the operator presses on the screen and what the
logic sees as one thing rather than as two raw outputs.

## Step 7. The synoptic diagram

[Synoptic Diagram](help://screens) — draw the installation and bind the
symbols to apparatus and points. The screen is stored **in the project**,
so the controller draws exactly what you drew, with no separate file.

Measurement visualisation lives here too — gauges, tanks and numeric
readouts bound to real points.

## Step 8. Logic

[Logic](help://logic) — a block diagram on those same addresses. Inputs,
gates, flip-flops, timers, analog blocks, the system signals `SYS.*` and
the alarm's `SEC.*/REQ.SEC.*`, outputs.

This is where you close everything the controller does not do by itself
— for instance routing `SEC.SYSTEM.SIREN_ACTIVE` to the output a siren
physically hangs on.

## Step 9. The intrusion alarm (if it is in the composition)

In order: [Zones](help://zones) → [Supervised
Lines](help://lines) → [Users](help://intrusion_users). A line needs a
zone, and a user needs zones they are allowed to operate.

Power supervision and the sounder settings are on the Zones panel too.

## Step 10. Protection (if it is in the composition)

[Electrical Protection](help://protection_electrical) — ANSI function
settings, executed by the ADA01 card.
[Process Protection](help://protection_process) — upper and lower
thresholds on analog points, evaluated on the controller.

## Step 11. Check and save

[Check Project](help://validation) finds the mismatches tables do not
show: an apparatus pointing at a point that no longer exists, a point
owned by two apparatus at once, a line with no point, a module with data
but outside the composition.

Then **Save**. Only a saved file can be sent — the controller receives
the file on disk, not the contents of the window.

## Step 12. Send it to the controller

[Controller Connection](help://controller) — the address, an Engineer
token, **Send to Device**. Studio first compares revisions and settings:
if somebody changed something on the panel, you see a table of the
differences before anything is overwritten.

The controller **rebuilds itself from the new project without
restarting** — cards, points, apparatus, commands, the alarm system, the
logic and the panel. On the same page you can then check the [logic's
state](help://controller), the live settings and the counters.

---

## Worth doing as well

- [MQTT Integration](help://mqtt) — if the controller is to talk to Home
  Assistant.
- [Object Links](help://object_links) — if controllers are to see each
  other's values.
- [Protection Tests](help://protection_tests) — after commissioning, as
  proof that a protection tripped within a measured time.
