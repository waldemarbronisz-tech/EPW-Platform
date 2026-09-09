# Addressing Inventory: How Deep the DI1..DI64 Assumption Runs

Reconnaissance only - **zero changes to addressing, tags, or names
anywhere**, and no functional changes at all. Every claim below is
labeled **ZMIERZONE** (measured - grep with file:line, or an actual
script run against real `TagManager`/regex code, output captured) or
**ZAŁOŻONE** (inferred - a judgment call, not directly tested). Nothing
here touches Historian, Alembic, or `safety_kernel.py` - those were
read for context where unavoidable, never edited.

---

## 3.1 - Every place assuming a fixed count of 64

ZMIERZONE (`grep -rn '\b64\b'`, then read each hit for whether it's a
named constant or a bare literal): **no named constant exists anywhere**
in this codebase for the DI/DO channel count (searched for
`NUM_DI`/`NUM_DO`/`DI_COUNT`/`DO_COUNT`/`CHANNEL_COUNT` - zero hits).
Every one of the following is a **literal integer written directly
into a `range()`/constructor call**, independently, in four different
files that must agree with each other by convention alone:

| File | Line | Code |
|---|---|---|
| `epw_os/core/tag_manager.py` | 263 | `for i in range(1, 65):` (creates `DI1`..`DI64`) |
| `epw_os/core/tag_manager.py` | 282 | `for i in range(5, 65):` (creates `DO05`..`DO64`) |
| `epw_os/core/epw_core.py` | 468 | `for i in range(5, 65):` (default command definitions for `DO05`..`DO64` - a second, independent copy of tag_manager.py's own bound) |
| `epw_os/gui/pages/page_digital_inputs.py` | 107 | `self.table = QTableWidget(64, 10)` |
| `epw_os/gui/pages/page_digital_inputs.py` | 139 | `for i in range(64):` |
| `epw_os/gui/pages/page_control_outputs.py` | 257 | `for i in range(5, 65):` |

Six independent sites, four files, all agreeing only by convention.
None reads a shared constant, let alone a project-configurable count.

---

## 3.2 - Every place that parses or builds a `DI`/`DO` + number tag name

ZMIERZONE (`grep -rnE` for f-string patterns, `+` concatenation,
`.startswith(...)`, and the one regex in this codebase that matches DI
tags - see below). Two clearly different SHAPES of code showed up, and
they matter differently for what comes next:

### (a) Loop-built names - trivially re-parametrizable

| File:Line | Code |
|---|---|
| `tag_manager.py:264` | `self.add_tag(f"DI{i}", ...)` |
| `tag_manager.py:283` | `self.add_tag(f"DO{i:02d}", ...)` |
| `epw_core.py:469` | `do_tag = f"DO{i:02d}"` |
| `page_control_outputs.py:258` | `do_tag = f"DO{i:02d}"` |
| `page_digital_inputs.py:141,174,277,311,475` | `f"DI{di_num}"` / `f"DI{row + 1}"` (five call sites in one file) |

### (b) Literal, one-off tag names hardcoded into SITE-SPECIFIC BUSINESS LOGIC - not a loop, not mechanically renameable

This is the part that actually matters for a migration estimate - a
loop bound is a one-line change, but these are specific channel
numbers standing in for specific real-world equipment roles:

- `epw_os/core/protection_verifier.py:196,197,199,200,202,203,266,325,369,374` -
  a real safety-verification test sequence hardcodes `"DI2"` (feeder
  breaker feedback), `"DI3"`, `"DI4"` (interlock conditions) by literal
  name, not by loop. **Not touched** (GRANICE), only read.
- `epw_os/gui/pages/page_entry_gate.py:161-178,243-246,524-543` - the
  Main View synoptic demo widget hardcodes `"DO01"`..`"DO04"`
  (isolator/contactor widgets), `"DI1"`..`"DI4"` (their feedback), and
  `"DI14"`/`"DO21"` (a separate voltage-monitoring relay simulation) by
  literal name.

These two files are where "migrate the addressing" stops being a
mechanical rename and starts requiring new *configuration surface* -
see the MIGRACJA costing below.

### (c) Pattern-matching / prefix checks - and they don't all agree with each other

| File:Line | Check | What it actually matches |
|---|---|---|
| `page_digital_inputs.py:448` | `tag_name.startswith("DI")` | any name starting with the two letters "DI" |
| `presentation_mode.py:532` | `t.name.startswith("DI") and t.name[2:].isdigit()` | `DI` + digits only, from position 0 |
| `switching_counters.py:209` | `tag_name.startswith("DI") and tag_name[2:].isdigit()` | same as above - `DI` must be the literal first two characters |
| `intrusion_manager.py:147` | `_DIGITAL_INPUT_TAG_PATTERN = re.compile(r"(^|\.)DI\d+$")` | `DI` + digits at the **end** of the string, either at position 0 or right after a `.` |

**These four checks do not agree with each other.** ZMIERZONE (ran the
regex directly, see 3.3): `intrusion_manager.py`'s pattern already
matches this codebase's OWN multi-device tag shape
(`"ELA01.DI01"` - see 3.4), because it was explicitly written to
("Task: matches 'DIn' or '<device>.DIn'" - its own comment at line
142-146). `switching_counters.py` and `presentation_mode.py`'s
`startswith("DI")` checks do **not** - `"ELA01.DI01"` starts with `"E"`,
not `"DI"`, so it silently fails both of those checks even though the
tag is a perfectly real digital input this codebase itself created.
**Three subsystems, three independent opinions on what counts as "a DI
tag," already inconsistent with each other before any editor-format
question even comes up.**

### (d) Genuinely name-agnostic - worth noting these exist too

- `tag_export.py:104-119` (`_group_for_tag()`) - groups by the tag's
  leading alphabetic run or its first dotted segment, generically. Not
  DI/DO-specific at all; already documented (its own comment) to expect
  and gracefully label an unrecognized prefix.
- `command_manager.py:70-75` (`load_definitions()`) - splits a command
  key on `.`, taking the last segment as the action and everything
  before it as the target, generically - already tolerant of a
  multi-segment (`"ADA01.DO01.CLOSE"`-shaped) key, not just the flat
  `"DO01.CLOSE"` shape.

---

## 3.3 - Empirical test: what actually happens with an out-of-pattern tag name

ZMIERZONE - ran directly (no mocking, real `TagManager`/`EventBus`,
no project.json touched):

```
tm = TagManager(EventBus())
tm.configure([{"id": "ELA01", "type": "ELA", "channels": 32},
              {"id": "ADA01", "type": "ADA", "channels": 32}])

DI1 exists:        False   <- the flat scheme was never created at all
ELA01.DI01 exists: True
ELA01.DI32 exists: True
total tags:        64

tm.add_tag("DI1.DI.1", False, TagType.BOOL)   # the EDITOR's own exact shape
DI1.DI.1 accepted: True    <- no validation anywhere, no crash
value read back:   False   <- reads/writes work completely normally
```

**`TagManager.add_tag()` has zero name validation of any kind.** Any
string is accepted as a tag name, including the Synoptic Editor's own
literal `"DI1.DI.1"` channel-address format, verbatim. Nothing crashes,
anywhere, at the `TagManager` level.

**The real failure mode is silent, not a crash**, and it is already
live in this codebase today, not hypothetical: `epw_core.py:339-346`
picks EXACTLY ONE of two mutually exclusive startup paths -
`tag_manager.configure(devices)` if `project.json` has a non-empty
`"devices"` section, or `tag_manager.init_default_tags()` (the flat
DI1-64/DO1-64 scheme) if it doesn't. **A project using the multi-device
path has no `"DI1"`..`"DI64"` tags at all.** But `page_digital_inputs.py`
and `page_control_outputs.py` (3.1's hardcoded-64 sites) build their
tables unconditionally from the flat names regardless of which startup
path actually ran - ZMIERZONE by reading `page_digital_inputs.py:144-145`:
`tag = self.tag_manager.get_tag(tag_name); desc_text = tag.description
if tag else f"Digital Input Channel {di_num}"` - a missing tag doesn't
raise, it just falls back to a placeholder description and a
permanently-"OFF", never-updating row. **A project actually configured
with the multi-device path today would show 64 fake, dead rows on the
Digital Inputs page while its real, live channels sit under different
names, invisible on that page entirely.** This is a real, present-day
defect for anyone actually using `TagManager.configure()`'s own
multi-device feature, confirmed by reading the fallback code, not
assumed.

And even that multi-device convention (`ELA01.DI01`) is not the
editor's own convention (`DI1.DI.1`) - confirmed by running the exact
regex from `intrusion_manager.py` against both shapes:

```
DI1              -> True
ELA01.DI01       -> True   (this runtime's own multi-device shape)
DI1.DI.1         -> False  (the Synoptic Editor's channel-address shape)
ADA1.DO.2        -> False  (same editor shape, DO)
```

**Answer to 3.3, stated plainly: the system does not break. It
silently, gracefully ignores what it doesn't recognize** - a
resilience property, but one that means an editor-addressed project
would produce a running EPW-OS with completely blank/wrong DI-DO pages
and zero loud indication that anything is wrong, rather than an error
someone would actually notice.

---

## 3.4 - Which subsystems keep their own copy of the channel list

| Subsystem | Own copy? | Evidence |
|---|---|---|
| `TagManager` | **Yes - two independent, mutually exclusive copies** | `init_default_tags()` (flat, 64+64) vs. `configure()` (multi-device, `{dev}.DI{nn}`/`{dev}.DO{nn}`) - `epw_core.py:339-346` picks exactly one at startup |
| `page_digital_inputs.py` / `page_control_outputs.py` | **Yes, hardcoded, disconnected from either TagManager path** | `device_defs`/`range(64)` literals (3.1) - built the same way regardless of which startup path actually ran |
| `protection_verifier.py` | **Yes, as literal business-logic constants** | `"DI2"`/`"DI3"`/`"DI4"` (3.2b) |
| `page_entry_gate.py` | **Yes, as literal business-logic constants** | `"DO01"`-`"DO04"`/`"DI1"`-`"DI4"`/`"DI14"` (3.2b) |
| Historian | **No** - ZMIERZONE, zero `DI`/`DO` hits anywhere in `historian.py`. Stores whatever `(tag_name, value, timestamp)` arrives; fully name-agnostic. | |
| Simulator / drivers (`epw_os/simulation/`, `epw_os/drivers/`) | **No** - ZMIERZONE, zero `DI`/`DO`/`range(64)` hits. Operates on whatever tags already exist. | |
| Tag list export (`tag_export.py`) | **No** - generic grouping (3.2d), enumerates `tag_manager.list_tags()` live. | |
| MQTT (`mqtt_manager.py`) | **No** - ZMIERZONE, zero `DI`/`DO`-specific hits; publishes/subscribes generically off whatever tags exist plus a project-configured `link_in` mapping. | |
| REST API (`backend/api.py`) | **No** - ZMIERZONE; supports a generic `?prefix=` filter (line 121), not a fixed list. | |
| "Rejestr bitów" | **Not found as a code module.** The only artifact by that description is `Zestawienie bitów wewnętrznych.xlsx` at the repository root, outside every one of these three merged repos - a reference spreadsheet, not code. Flagging this rather than guessing which module it was meant to refer to. |

**The pattern: exactly four places (TagManager itself, both DI/DO
pages, and the two safety/demo modules with literal channel numbers)
actually hold their own idea of "what a digital channel is called."
Everything else downstream (Historian, simulator, export, MQTT, REST)
is already name-agnostic and would not need to change for either path
below.**

---

## 3.5 - Two paths, costed

### MOST (bridge): translate `DI1.DI.1` → `DI1` in one place

- A translation function itself is small (ZAŁOŻONE, not built: on the
  order of 50-100 lines - parse `<card>.<KIND>.<channel>`, look up a
  project-specific card→slot mapping, return the runtime's existing
  flat name or flag "no free slot").
- **But there is no formula from card+channel to slot number** - card
  ids are user-chosen text (`"DI1"`, `"ELA1"`, anything), and the
  runtime's slot numbering (1..64) has no structural relationship to
  any card at all. A bridge needs an explicit, persisted, per-project
  mapping table (which card+channel is runtime slot 17?), not a pure
  function - itself new configuration surface, not free (ZAŁOŻONE
  order of magnitude: 100-300 lines for the mapping table + a settings
  UI to edit it).
- **A second DI card has nowhere to go.** The flat namespace *is*
  `DI1..DI64` - there is no `DI65`. A second card's channels can only
  be bridged if the runtime's own ceiling is raised first, which means
  touching every one of 3.1's six hardcoded-64 sites anyway - the
  bridge does not avoid that work, it only postpones it until the day
  a second card actually shows up.
- **A card with a channel count other than 32 doesn't change the
  bridge function itself** (it's just a lookup either way), but it does
  make the "how many total flat slots do I need across every card in
  this project" question sharper - the real example file already has
  32 DI + 32 DO + 16 AI on three cards; two DI cards of 32 each already
  exhausts the entire 64-slot DI ceiling with zero margin.
- **Staged?** Yes, trivially, for a project that never exceeds 64
  channels per kind and never needs the literal-hardcoded safety/demo
  modules (3.2b) to participate - which is a real, narrow, but
  non-zero use case.

### MIGRACJA: runtime adopts the card-based addressing as its own

- Every site in 3.1/3.2a needs real rework, not a rename: `tag_manager.py`'s
  two competing creation paths would merge into one that reads a
  project's own card list (the exact shape `epwsyn_loader.py`'s
  `cards`/`locations` fields already carry - a real synergy with the
  other branch's work, noted but not acted on here). `page_digital_inputs.py`/
  `page_control_outputs.py` need to go from a fixed 64-row table to a
  dynamically-sized one built from however many cards×channels a
  project actually has - genuine UI rework (ZAŁOŻONE, a few hundred
  lines each, not a data change), likely needing a new "which card" column too.
- The two literal-hardcoded modules (3.2b) have **no natural
  card-based generalization** - "which physical DI is the feeder
  breaker feedback" is a per-site fact today expressed as a Python
  literal; migrating it means building real configuration surface (a
  settings screen letting an engineer bind that role to a real
  channel), not a find-and-replace.
- **Historian impact - the one place GRANICE said not to touch, but
  whose impact must still be named**: Historian rows are stored keyed
  by whatever tag name existed at write time (3.4, ZMIERZONE - no
  name-shape assumption). A project migrated from `"DI1"` to a
  card-based name would see its **existing historical data become
  unreachable under the new name** - Trends/history queries for the
  new name would return nothing before the cutover date - unless a
  separate aliasing/backfill step is added. This is a real data-
  continuity cost specific to MIGRACJA that the bridge path does not
  have (the bridge never renames anything that's already stored).
- **Staged?** Plausibly, and there is already a real head start:
  `TagManager.configure()`/`command_manager.load_definitions()`
  already run a working, project-configurable, multi-device path in
  parallel with the flat scheme today (not merged with it - mutually
  exclusive per `epw_core.py:339-346`, but present and working). The
  practical staged path is: (1) align that existing multi-device
  convention's own shape (today `{dev_id}.DI{nn}`, two segments) with
  the editor's exact three-segment `<card>.<KIND>.<channel>` shape
  instead of inventing a third convention, (2) migrate the DI/DO pages
  to read from *whichever* path actually ran, (3) leave old flat-scheme
  projects on `init_default_tags()` indefinitely for backward
  compatibility. The two literal-hardcoded safety/demo modules remain
  the hard, unavoidably manual part of any staging plan - they cannot
  be staged around, only rebuilt with real configuration.

**Order-of-magnitude estimate (ZAŁOŻONE, not a real implementation
estimate)**: at least 8 files, ~20 distinct call sites need real code
changes for MIGRACJA (vs. roughly 2 files - the bridge function + a
new mapping UI - for MOST, plus the same eventual 3.1 rework the day a
second card is added). MIGRACJA is more code and touches historical
data; MOST is less code today but only defers the same rework and adds
a translation layer + mapping table that has to be kept correct by
hand.

---

## Recommendation

Neither path is free, and they fail differently: MOST is cheaper right
now but caps out at exactly the same 64-per-kind ceiling this codebase
already has the moment a second real DI/DO card shows up, and adds a
hand-maintained mapping table as a new source of configuration error.
MIGRACJA removes the ceiling permanently and reuses a working
multi-device path that already exists (`TagManager.configure()`) rather
than inventing new machinery, but costs more up front, requires new
configuration surface for the two literal-hardcoded safety/demo
modules that cannot be mechanically migrated, and needs an explicit
answer for what happens to Historian data recorded under the old
names before it's attempted. No implementation was started for either
path - this is Waldek's decision.
