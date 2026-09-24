"""Writes to the logic's internal bits from OUTSIDE the logic (internal
bits IN/OUT - owner's decisions, 2026-09-22).

An internal bit is a tag M.<name> (MR./MW./MWR.) published by the
program's registry (core/logic_runtime.py TagIOProvider). Its direction
is the logic's: an OUT bit is written only by the scan and nobody else
may touch it; an IN bit is written from outside and the logic only reads
it. Every write from outside comes through here, and the bit's own
registry entry says who may:

    PANEL  the operator at the controller's panel, at the access level
           the entry names (`panel_level`; "" = the panel may not)
    REST / MQTT (Home Assistant) only when the entry says
           `remote_write` - off by default, enabled per bit in Studio -
           and never below the level the panel needs either
    a Studio FORCE goes through ForceManager on the force rules, never
           through here

Every write and every refusal reaches the audit log with who, from
where, when, and the old and new value. A bit pinned by a force belongs
to the person forcing it and is refused, like an output would be.
"""
from epw_os.core.access_manager import AccessLevel
from epw_os.core.logging import log
from shared.logic.internal_bits import DIRECTION_IN, DIRECTION_OUT, panel_level_of, remote_writable

SOURCE_PANEL = "PANEL"
SOURCE_REST = "REST"
SOURCE_MQTT = "MQTT"
REMOTE_SOURCES = (SOURCE_REST, SOURCE_MQTT)


def _rank(level) -> int:
    try:
        return AccessLevel._ORDER.index(level)
    except (ValueError, TypeError):
        return -1


class InternalBitGate:
    def __init__(self, core):
        self.core = core

    # --- the registry as the running program declares it ---------------------------------

    def _io(self):
        engine = getattr(self.core, "logic_engine", None) if self.core is not None else None
        return getattr(engine, "_io", None)

    def entries(self) -> dict:
        """{bit id: normalized registry entry} of the loaded program."""
        io = self._io()
        getter = getattr(io, "internal_bit_entries", None)
        return dict(getter()) if callable(getter) else {}

    def entry(self, bit_id: str):
        return self.entries().get(bit_id)

    def direction_of(self, bit_id: str):
        """IN, OUT, or None for a name the program does not declare."""
        entry = self.entry(bit_id)
        return None if entry is None else entry.get("direction", DIRECTION_OUT)

    def force_allowed(self, bit_id: str) -> bool:
        """Whether a Studio force may pin the bit (shared/logic/internal_bits.force_allowed)."""
        from shared.logic.internal_bits import force_allowed
        entry = self.entry(bit_id)
        return entry is not None and force_allowed(entry)

    def writable_from_panel(self, bit_id: str, level=None) -> bool:
        entry = self.entry(bit_id)
        if entry is None or entry.get("direction") != DIRECTION_IN:
            return False
        needed = panel_level_of(entry)
        if not needed:
            return False
        if level is None:
            level = getattr(getattr(self.core, "access_manager", None), "level", None)
        return _rank(level) >= _rank(needed)

    # --- the one door -------------------------------------------------------------------

    def write(self, bit_id: str, value, actor: str, source: str = SOURCE_PANEL, level=None) -> tuple:
        """(True, "") when the bit was written, (False, reason) when
        refused. Audited either way."""
        who = f"{source}:{actor}" if actor else source
        entry = self.entry(bit_id)
        if entry is None:
            return self._refuse(who, bit_id, value, f"{bit_id} is not an internal bit of the loaded logic program")
        if entry.get("direction") != DIRECTION_IN:
            return self._refuse(who, bit_id, value, f"{bit_id} is an OUT bit - written only by the logic")
        needed = panel_level_of(entry)
        if source in REMOTE_SOURCES:
            if not remote_writable(entry):
                return self._refuse(who, bit_id, value,
                                    f"remote writes to {bit_id} are not enabled in the project")
            if level is None:
                # A remote caller's level is the one its token proved -
                # never the level of whoever is standing at the panel.
                return self._refuse(who, bit_id, value, "no valid token for a remote write")
        elif level is None:
            level = getattr(getattr(self.core, "access_manager", None), "level", None)
        if not needed:
            return self._refuse(who, bit_id, value, f"the project allows no writes to {bit_id} from the panel")
        if _rank(level) < _rank(needed):
            return self._refuse(who, bit_id, value, f"{bit_id} needs {needed} level, {level or 'nobody'} is present")
        tags = getattr(self.core, "tag_manager", None)
        forces = getattr(self.core, "force_manager", None)
        if forces is not None and forces.is_forced(bit_id):
            return self._refuse(who, bit_id, value, f"{bit_id} is forced from Studio - release the force first")
        try:
            new_value = float(value) if entry.get("type") == "REAL" else bool(value)
        except (TypeError, ValueError):
            return self._refuse(who, bit_id, value, f"{value!r} is not a value for {bit_id}")
        old_value = tags.get_value(bit_id) if tags is not None else None
        if tags is None or not tags.update_tag(bit_id, new_value):
            return self._refuse(who, bit_id, value, f"{bit_id} could not be written")
        self._audit("INTERNAL_BIT_WRITTEN", who, f"{bit_id}: {old_value!r} -> {new_value!r} (from {source})")
        log.info(f"{who} wrote {bit_id}: {old_value!r} -> {new_value!r}")
        return True, ""

    def _refuse(self, who, bit_id, value, reason) -> tuple:
        self._audit("INTERNAL_BIT_WRITE_REFUSED", who, f"{bit_id} = {value!r}: {reason}", success=False)
        log.warning(f"{who}: write of {bit_id} refused - {reason}")
        return False, reason

    def _audit(self, event, actor, detail, success=True):
        audit = getattr(self.core, "audit_logger", None) if self.core is not None else None
        if audit is not None:
            audit.record(event, actor, detail, success=success)
