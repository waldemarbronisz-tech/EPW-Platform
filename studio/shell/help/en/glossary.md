# Glossary

**Address** — `card_id.KIND.number`, e.g. `ELA1.DI.1`. The only way a
channel is named anywhere on the platform.

**Apparatus** — a thing handled as a whole (a breaker, a contactor, a
valve), tied to feedback and command points. See [Apparatus
Registry](help://apparatus).

**Card** — a physical I/O module. See [I/O Cards](help://io_cards).

**Device composition** — which modules a controller is made of. See
[Composition](help://devices).

**Force** — a technician pinning a tag to a value. Needs Engineer, is
audited, and survives neither a restart nor a project reload. See [Point
Registry](help://points).

**Live mode** — showing the controller's real values in the tables and
in the screen editor.

**Location** — a place code, inherited from a card by its points. See
[Locations](help://locations).

**Object** (`obiekt.epwsite`) — several controllers as one installation.
See [Object](help://site).

**Point** — one channel of a card, with its description, location and
(for analog ones) its scaling. See [Point Registry](help://points).

**Retentive bit** (`MR.` / `MWR.`) — a logic bit that survives a
controller restart.

**Revision** — the project's save counter.

**Setting** — a value the panel is allowed to change. The opposite of
structure. See [Saving and revisions](help://save_versioning).

**Settings hash** — a digest of every setting, used to detect a
divergence from the controller.

**`SSWIN.*`** — the alarm system's signals available in logic: armed,
alarm, memory, tamper, the sounder, the commands.

**Supervised line** — one alarm detector on one point. See
[Lines](help://lines).

**`SYS.*`** — the controller's system signals available in logic.

**Tag** — a named value in the controller. A point's address is a tag;
so are `Security.*`, `Process.*`, `Link.*` and `System.*`.

**Zone** — a part of the site armed as one. See [Zones](help://zones).
