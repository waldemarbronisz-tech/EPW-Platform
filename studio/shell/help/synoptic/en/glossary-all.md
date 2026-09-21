# 13. Glossary

**Behavior** — What classifies a device: SWITCHED, SIGNAL, MEASURED or MODULATED - not its descriptive kind. [→](help://synoptic/dev-behavior-classification)

**Boundary point** — A symbol representing where the installation meets the outside world - a source or a sink. [→](help://synoptic/sch-boundary-point)

**Busbar** — A wire in BUS style, drawn thicker, meant to have many loads tapped along its whole length. [→](help://synoptic/sch-wire-style)

**Card** — The registry's representation of a physical controller I/O card: an id, a channel kind, a channel count. [→](help://synoptic/reg-cards)

**Channel** — A single input or output on a card, numbered starting from 1. [→](help://synoptic/reg-cards)

**Channel address** — A text address in CARD.KIND.CHANNEL format pointing at a physical I/O channel, e.g. ELA1.DI.12. [→](help://synoptic/reg-addressing)

**Channel collision** — Two devices pointing at the same physical channel - detected and flagged on save. [→](help://synoptic/dev-form-validation)

**Designation** — What is shown on the diagram next to a symbol, e.g. -K1 - distinct from the device id. [→](help://synoptic/dev-naming)

**Device** — A unit of configuration defined once in the Device List; a screen symbol only points at it by id. [→](help://synoptic/dev-why-not-in-screen)

**Discrepancy** — A command sent to a SWITCHED device that feedback did not confirm within the configured time. [→](help://synoptic/dev-switched)

**Editor preview** — A manually set state shown on a symbol while designing - never a reading from real hardware. [→](help://synoptic/sym-states-preview)

**EPW-Logic-Studio** — The EPW platform application that builds automation: control rules, interlocks and sequences. [→](help://synoptic/intro-platform)

**EPW-OS** — The EPW platform's runtime application - displays screens and works against real hardware. [→](help://synoptic/intro-platform)

**Feedback** — An input (or two) confirming a SWITCHED device's actual state - mode DUAL, SINGLE or NONE. [→](help://synoptic/dev-switched)

**Frame** — Pure graphics illustrating a cabinet, room or zone - no terminals and no Aparat field. [→](help://synoptic/elem-frame-building)

**Home Assistant** — An additional layer (monitoring/notifications via the publishToHa field), never a control path. [→](help://synoptic/intro-platform)

**Id** — A device's immutable machine key, e.g. KOT_KMG1 - its location is derived from it. [→](help://synoptic/dev-naming)

**Indicator diode** — A symbol with three allowed states: ON, OFF and QUALITY. [→](help://synoptic/elem-indicator-diode)

**Inhibit signal** — A signal letting logic FORBID a command from executing, not only send one. [→](help://synoptic/dev-signals-commands)

**Junction dot** — A marker at a grid point where three or more wire/terminal branches meet. [→](help://synoptic/sch-junction-dot)

**Live validation** — Checking the device form on every field change, withholding Save while an error exists. [→](help://synoptic/dev-form-validation)

**Location** — A short, uppercase prefix of a device id, e.g. KOT. [→](help://synoptic/reg-locations)

**Medium** — One of the three installation kinds a wire belongs to: electrical, water or ventilation. [→](help://synoptic/sch-media)

**Meter** — A dynamic screen element built from measurement rows, with its height always computed. [→](help://synoptic/elem-meter)

**Migration** — The automatic reshaping of an older project file into the current shape on load. [→](help://synoptic/file-versioning)

**Node** — A grid point where wires and terminals can geometrically touch, forming one net. [→](help://synoptic/sch-node-model)

**Project file** — The .epwsyn file (JSON, EPW_SYNOPTIC format) holding the whole project state. [→](help://synoptic/file-contents)

**Registry** — A project-wide list (locations, cards or devices) the screen only draws references from. [→](help://synoptic/reg-locations)

**Safe state** — A device's defined behavior on startup or link loss - belongs to the hardware, not to the screen. [→](help://synoptic/dev-switched)

**Schema version** — A number in the project file that only increases on a backward-incompatible change. [→](help://synoptic/file-versioning)

**Signal panel** — A dynamic screen element like the meter, but every row ends in a two-state diode. [→](help://synoptic/elem-signal-panel)

**Switch counter** — Optional counting of a SWITCHED device's operations (the .COUNTER signal) - with no built-in warning threshold. [→](help://synoptic/dev-switched)

**Terminal** — A point on a symbol where a wire can touch it - always at the middle of one of its four edges. [→](help://synoptic/sym-terminals)

**Undo history** — A sequence of drawing-state snapshots, one per saved action, capped at 100 entries. [→](help://synoptic/edit-undo-redo)
