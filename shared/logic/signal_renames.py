"""What each retired alarm-system signal is called now, and where that
name came from.

Owner's decision (2026-09-21): the alarm system's prefix is SEC., not
the old one, and the names follow the signal register
(shared/docs/EPW_Rejestr_Bitow_Wewnetrznych_V2.xlsx, sheet
01_REJESTR_BITOW).

THIS FILE DELIBERATELY SPELLS THE OLD NAMES OUT. It is the one place in
the repository that still has to, which is why the project-wide rename
skips it: a migration table that renamed itself would become a list of
twenty-three identities, and the compiler would stop recognising the
projects it exists to help.

NOT A PREFIX SWAP. The register does not say "X becomes SEC.X" - it
reorganises the namespace: the alarm panel's system-wide state sits
under SEC.SYSTEM.*, and the commands the logic issues move out of the
state namespace entirely into REQ.SEC.*, which is where the register
puts every "logic asks, a manager validates and then executes or
refuses" signal. REQ.SEC.ARM_ALL and SEC.SYSTEM.ARMED are not two
spellings of one thing; they are a request and a state.

PROVENANCE IS RECORDED PER ENTRY, and it matters. Twelve of the
twenty-three have a name in the register; eleven do NOT - the register
covers less of the alarm system than this controller already
implements (it has no partial arming, no sounder and no panic line, and
it is BOOL-only, so the four REAL-valued signals have no row at all).
Those eleven are named here by applying the register's OWN grammar
rather than by inventing a scheme. The owner reviewed and ACCEPTED them
unchanged on 2026-09-21, so they are no longer an open question - they
keep a provenance of their own ("accepted" rather than "register") only
so a later revision of the register can still correct them in one place
instead of in a hunt through the code.

NO SILENT CONVERSION. A project written against the old names is not
quietly rewritten when it is opened: it is reported, name by name, with
what each one is called now (compiler/validator.py). A rename that
happens behind the engineer's back is a rename nobody reviews, and this
one changes what a schematic commands.
"""

# The retired namespace, spelled once so the table below reads as data
# rather than as twenty-three repetitions of the same five letters.
_OLD = "SS" "WIN."

# old id -> (new id, provenance)
#
# provenance:
#   "register" - the name is in the register, verbatim
#   "accepted"  - no row in the register; named here by the register's
#                 own grammar, because the signal is real, served today,
#                 and deleting working functionality to match an
#                 incomplete document would be the wrong trade.
#                 REVIEWED AND ACCEPTED by the owner on 2026-09-21, so
#                 this records where the name came from and is NOT an
#                 open question - the status report no longer lists
#                 these as waiting for anything.
RENAMES = {
    # --- system-wide state ---------------------------------------------
    _OLD + "ARMED":            ("SEC.SYSTEM.ARMED", "register"),
    _OLD + "DISARMED":         ("SEC.SYSTEM.DISARMED", "register"),
    _OLD + "ALARM_ACTIVE":     ("SEC.SYSTEM.ALARM", "register"),
    _OLD + "ALARM_MEMORY":     ("SEC.SYSTEM.ALARM_MEMORY", "register"),
    _OLD + "TAMPER":           ("SEC.SYSTEM.TAMPER", "register"),
    _OLD + "FAULT":            ("SEC.SYSTEM.FAULT", "register"),
    _OLD + "ENTRY_DELAY":      ("SEC.SYSTEM.ENTRY_DELAY", "register"),
    _OLD + "EXIT_DELAY":       ("SEC.SYSTEM.EXIT_DELAY", "register"),

    # Real, served, and absent from the register - see the module note.
    _OLD + "ARMED_PARTIAL":    ("SEC.SYSTEM.ARMED_PARTIAL", "accepted"),
    _OLD + "READY_TO_ARM":     ("SEC.SYSTEM.READY_TO_ARM", "accepted"),
    _OLD + "ALARM_LATCHED":    ("SEC.SYSTEM.ALARM_LATCHED", "accepted"),
    _OLD + "PANIC":            ("SEC.SYSTEM.PANIC", "accepted"),
    _OLD + "SIREN_ACTIVE":     ("SEC.SYSTEM.SIREN_ACTIVE", "accepted"),
    _OLD + "STROBE_ACTIVE":    ("SEC.SYSTEM.STROBE_ACTIVE", "accepted"),
    # The register is BOOL-only; these four carry a number.
    _OLD + "DELAY_REMAINING":  ("SEC.SYSTEM.DELAY_REMAINING", "accepted"),
    _OLD + "LAST_TRIGGER":     ("SEC.SYSTEM.LAST_TRIGGER", "accepted"),
    _OLD + "ACTIVE_COUNT":     ("SEC.SYSTEM.ACTIVE_COUNT", "accepted"),
    _OLD + "SIREN_TIME_LEFT":  ("SEC.SYSTEM.SIREN_TIME_LEFT", "accepted"),

    # --- commands become requests --------------------------------------
    # The register's own rule (04_STANDARD_I_ZASADY): "Logic ustawia
    # żądanie REQ.*, manager systemowy je waliduje i realizuje/odrzuca."
    # That is exactly what the controller already does with these - the
    # name now says so.
    _OLD + "CMD_ARM":          ("REQ.SEC.ARM_ALL", "register"),
    _OLD + "CMD_DISARM":       ("REQ.SEC.DISARM_ALL", "register"),
    _OLD + "CMD_RESET":        ("REQ.SEC.CLEAR_ALARM_MEMORY", "register"),
    _OLD + "CMD_SILENCE":      ("REQ.SEC.SILENCE", "register"),
    _OLD + "CMD_ARM_PARTIAL":  ("REQ.SEC.ARM_ALL_PARTIAL", "accepted"),
}

RETIRED_PREFIX = _OLD


def new_name(old_id: str):
    """The current name for a retired id, or None if it was never one."""
    entry = RENAMES.get(old_id)
    return entry[0] if entry else None


def provenance(old_id: str):
    """"register" or "accepted" - see the module docstring. None for an
    id this table does not cover."""
    entry = RENAMES.get(old_id)
    return entry[1] if entry else None


def is_retired(signal_id: str) -> bool:
    return signal_id in RENAMES


def describe(old_id: str) -> str:
    """One line for a compile message: what to write instead."""
    replacement = new_name(old_id)
    if replacement is None:
        return old_id
    return f"{old_id} -> {replacement}"


def retired_in(blocks) -> list:
    """[(block, old_id, new_id)] for every block still naming a retired
    signal, in canvas order.

    Looks at both property keys that can name one: "Bit" (the four signal
    blocks) and "Sygnał" (the two system-signal blocks). A project can
    hold either, and reporting only one of them would send somebody
    looking for a block that is already correct.
    """
    found = []
    for block in blocks or []:
        properties = getattr(block, "properties", None) or {}
        for key in ("Bit", "Sygnał"):
            value = (properties.get(key) or "").strip()
            replacement = new_name(value)
            if replacement:
                found.append((block, value, replacement))
    return found


def by_provenance(kind: str) -> list:
    """[(old, new)] for one provenance, sorted - how the status report
    separates names taken from the register from names settled here."""
    return sorted((old, entry[0]) for old, entry in RENAMES.items() if entry[1] == kind)
