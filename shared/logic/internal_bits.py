"""Internal signal registry (feat/internal-bits §1) — project-defined BOOL/
REAL signals (project.settings["internal_bits"]) that replace free-text
"Tag" on virtual.input/virtual.output with a validated, unique, typed
registry entry. Kept dependency-free (no PySide6 import) so core/project.py
stays importable headlessly, same reasoning as core/grid.py.

An entry:
    {
      "name": "BLOKADA_ZS",
      "type": "BOOL",              # "BOOL" or "REAL"
      "retentive": False,          # survives a controller restart — but see
                                    # note below, Logic Studio never simulates
                                    # this itself
      "description": "Blokada załączenia od zabezpieczenia szyn",
      "label": "BLOK ZS",          # short HMI/schematic text, optional
      "category": "Blokady"        # grouping in the signal picker, optional
    }

Retentiveness note: Logic Studio only STORES and EXPORTS the `retentive`
flag. Whether/how a value actually survives a controller restart (where
it's persisted, how often, what happens on power loss) is EPW-OS's
responsibility entirely — see ARCHITECTURE.md "Przestrzenie nazw sygnałów".
Nothing in this module or the simulation engine makes retentive values
survive anything.
"""
import re

VALID_TYPES = ("BOOL", "REAL")

# Disallowed in a signal NAME (the identifier, not the description/label):
# whitespace, the path-ish separators / and \, quote characters, and Polish
# diacritics (both cases) — the identifier must be safe to embed verbatim in
# an M./MR./MW./MWR.-prefixed id and in file paths/JSON keys elsewhere.
_FORBIDDEN_CHARS_PATTERN = re.compile(r'[\s/\\\'"ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]')


def internal_bit_id(entry: dict) -> str:
    """The one, derived (never stored) identifier for a registry entry —
    §1.2. Changing `type` or `retentive` on an entry changes this; callers
    that persist an id (blocks referencing a signal by name+type+retentive
    combination, the exporter) must be kept in sync when an entry is
    edited — see ProjectSettingsDialog's registry editor (§7.3), which
    re-points every block using a changed entry."""
    name = entry.get("name", "")
    type_ = entry.get("type", "BOOL")
    retentive = bool(entry.get("retentive", False))

    if type_ == "REAL":
        prefix = "MWR" if retentive else "MW"
    else:
        prefix = "MR" if retentive else "M"

    return f"{prefix}.{name}"


# --- direction and writers (internal bits IN/OUT, owner's decisions 2026-09-22) ---
#
# Direction is from the LOGIC's point of view: IN = written by something
# outside the logic (the panel, a Studio force, REST/MQTT when allowed),
# the logic only reads it; OUT = written only by the logic, the rest of
# the system consumes it. A bit the logic both writes and reads (a wire
# between sheets) is an OUT nobody else reads - there is no third kind.
# An entry saved before this existed has no "direction" and is OUT.
#
# Who may write an IN bit is declared PER BIT:
#   panel_level  the panel's access level that may set it ("User",
#                "Operator", "Engineer"), or "" = the panel may not.
#                Default Operator.
#   remote_write REST / MQTT / Home Assistant may set it. Default False:
#                HA is a window, not a brain - a write from outside only
#                where the designer allowed it.
# A Studio force is always allowed on an IN bit, on the force rules
# (Engineer, audit, expiry), never on an OUT bit.
DIRECTION_IN = "IN"
DIRECTION_OUT = "OUT"
DIRECTIONS = (DIRECTION_IN, DIRECTION_OUT)
DEFAULT_DIRECTION = DIRECTION_OUT
PANEL_LEVELS = ("", "User", "Operator", "Engineer")
DEFAULT_PANEL_LEVEL = "Operator"


def direction_of(entry: dict) -> str:
    value = str((entry or {}).get("direction") or DEFAULT_DIRECTION).upper()
    return value if value in DIRECTIONS else DEFAULT_DIRECTION


def is_input_bit(entry: dict) -> bool:
    return direction_of(entry) == DIRECTION_IN


def panel_level_of(entry: dict) -> str:
    """The panel level that may write the bit; "" when the panel may not
    (or the bit is OUT, which nobody outside the logic writes)."""
    if not is_input_bit(entry):
        return ""
    if "panel_level" not in (entry or {}):
        return DEFAULT_PANEL_LEVEL
    level = str(entry.get("panel_level") or "")
    return level if level in PANEL_LEVELS else DEFAULT_PANEL_LEVEL


def remote_writable(entry: dict) -> bool:
    return is_input_bit(entry) and bool((entry or {}).get("remote_write", False))


def force_allowed(entry: dict) -> bool:
    """Whether a Studio force may pin this bit. An IN bit: always (the
    owner's rule). An OUT bit: only where the designer said so
    (`force_allowed`, owner 2026-09-24: "wymuszamy bity - ma być
    zezwolenie") - a force on an OUT bit overrides what the logic
    computed, and that is a decision to make per bit, not by default."""
    if is_input_bit(entry):
        return True
    return bool((entry or {}).get("force_allowed", False))


def normalize_entry(entry: dict) -> dict:
    """A copy with the direction and writer fields made explicit - what
    the exporter, the controller and the panels all read."""
    out = dict(entry or {})
    out["direction"] = direction_of(out)
    out["panel_level"] = panel_level_of(out)
    out["remote_write"] = remote_writable(out)
    out["force_allowed"] = force_allowed(out)
    return out


def validate_direction_fields(entry: dict) -> list:
    """Errors for a malformed direction / panel level (format only)."""
    errors = []
    name = entry.get("name", "")
    direction = entry.get("direction")
    if direction is not None and str(direction).upper() not in DIRECTIONS:
        errors.append(f"{name!r}: invalid direction {direction!r} (must be IN or OUT).")
    level = entry.get("panel_level")
    if level is not None and str(level) not in PANEL_LEVELS:
        errors.append(f"{name!r}: invalid panel level {level!r} (must be empty, User, Operator or Engineer).")
    return errors


# The four block types whose "Bit" property names a registry entry.
# Here rather than in either editor, because "which blocks use a marker"
# has to mean the same thing in both of them.
SIGNAL_BLOCK_TYPE_IDS = ("virtual.input", "virtual.output",
                         "internal.reg_in", "internal.reg_out")


def blocks_using(blocks, name: str) -> list:
    """Every block referencing registry entry `name`.

    Case-insensitive, the same comparison the uniqueness rule uses: if
    BLOKADA_ZS and blokada_zs cannot both exist, then a block saying
    either one refers to the single entry that does.
    """
    if not name:
        return []
    lname = name.lower()
    return [b for b in blocks
            if getattr(b, "type_id", None) in SIGNAL_BLOCK_TYPE_IDS
            and (b.properties.get("Bit", "") or "").lower() == lname]


def rename_in_blocks(blocks, old_name: str, new_name: str) -> int:
    """Re-points every block from `old_name` to `new_name`; returns how
    many were changed.

    A block stores only the bare NAME - its resolved M./MR./MW./MWR.<name>
    id is derived fresh from whatever the registry says (internal_bit_id
    above), so changing an entry's type or retentive flag needs no
    propagation at all. Changing its NAME does: without this, every block
    keeps pointing at a name the registry no longer has, and the next
    compile reports each one as an unknown signal.
    """
    if not old_name or not new_name or old_name == new_name:
        return 0
    touched = blocks_using(blocks, old_name)
    for block in touched:
        block.properties["Bit"] = new_name
    return len(touched)


def validate_internal_bit_name(name: str):
    """Format-only validation of a single name (§1.3) — doesn't check
    uniqueness, which needs the full registry. Returns an error message
    string, or None if the name is valid on its own."""
    if not name:
        return "The name cannot be empty."
    if _FORBIDDEN_CHARS_PATTERN.search(name):
        return ("The name cannot contain spaces, the characters / \\ \" ' "
                "or Polish diacritic letters.")
    return None


def validate_internal_bits_registry(entries: list) -> list:
    """Validates the WHOLE registry (§1.3) — uniqueness needs the full
    list, so this can't be done entry-by-entry. Returns a list of
    human-readable error message strings; empty means the registry is
    valid. Comparison for uniqueness is case-insensitive (BLOKADA_ZS and
    blokada_zs are the same conflict, not two signals)."""
    errors = []
    seen_lower = {}

    for entry in entries:
        name = entry.get("name", "")
        name_error = validate_internal_bit_name(name)
        if name_error:
            errors.append(f"{name!r}: {name_error}")
        else:
            lname = name.lower()
            if lname in seen_lower:
                errors.append(
                    f"Signal name {name!r} clashes with the existing "
                    f"{seen_lower[lname]!r} (case-insensitive "
                    f"comparison)."
                )
            else:
                seen_lower[lname] = name

        if entry.get("type") not in VALID_TYPES:
            errors.append(f"{name!r}: invalid type {entry.get('type')!r} (must be BOOL or REAL).")
        errors.extend(validate_direction_fields(entry))

    return errors
