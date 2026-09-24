"""The controller's operating mode - MODE.* in the signal register.

One exclusive mode at a time: NORMAL, AUTO, MANUAL, SERVICE, MAINTENANCE,
TEST, EMERGENCY. The mode is a FACT about the controller that logic,
screens and the panel read (MODE.<mode> is TRUE for exactly one of them);
what a mode is allowed to do is decided by whoever reads it - a
schematic that inhibits automatic sequences in MANUAL, a page that
unlocks service actions in SERVICE. Nothing here inhibits anything by
itself.

Who may change it (rule Z2 of the register work: the same level from the
logic as from the panel) is one table, REQUIRED_LEVEL, used by the REST
endpoint, the panel's status-bar menu and the REQ.MODE.* requests alike.
Every change and every refusal is an audit entry. The mode survives a
restart in runtime_state.json - a controller left in MAINTENANCE for the
night must not come back in NORMAL because somebody rebooted it.

The three modes the register also names but this module does NOT hold:
TRAINING (TrainingModeManager), SIMULATION (TagManager.mode) and
DEGRADED (HealthManager) - they are read from their own sources by
runtime_state_signals.py.

THE CONTROL PLACE (owner's decision 2026-09-24): LOCAL / REMOTE is a
second, independent axis - where control is allowed to come from, like
the local/remote switch on a switchgear panel. In LOCAL the controller
refuses every CHANGE arriving over the engineering link (Studio's REST:
commands, forces, bits, mode, project install, restore) and over remote
control (MQTT / Home Assistant / VPN); reads keep working and the panel
itself is not affected. It is set from the panel only (Operator), never
over the link it locks, and survives a restart like the mode does. The
register reads it as MODE.LOCAL / MODE.REMOTE. Default REMOTE: a fresh
controller accepts its first project over the link.
"""
from epw_os.core.access_manager import AccessLevel
from epw_os.core.logging import log

NORMAL, AUTO, MANUAL, SERVICE, MAINTENANCE, TEST, EMERGENCY = (
    "NORMAL", "AUTO", "MANUAL", "SERVICE", "MAINTENANCE", "TEST", "EMERGENCY")
MODES = (NORMAL, AUTO, MANUAL, SERVICE, MAINTENANCE, TEST, EMERGENCY)
DEFAULT_MODE = NORMAL

# Operating choices are an operator's; service, maintenance and test put
# the plant outside its normal rules and are an engineer's. EMERGENCY may
# be declared by an operator - the one mode nobody should have to look
# for a higher PIN to enter.
REQUIRED_LEVEL = {
    NORMAL: AccessLevel.OPERATOR,
    AUTO: AccessLevel.OPERATOR,
    MANUAL: AccessLevel.OPERATOR,
    EMERGENCY: AccessLevel.OPERATOR,
    SERVICE: AccessLevel.ENGINEER,
    MAINTENANCE: AccessLevel.ENGINEER,
    TEST: AccessLevel.ENGINEER,
}


LOCAL, REMOTE = "LOCAL", "REMOTE"
CONTROL_PLACES = (LOCAL, REMOTE)
DEFAULT_CONTROL_PLACE = REMOTE
CONTROL_PLACE_LEVEL = AccessLevel.OPERATOR


LOCAL, REMOTE = "LOCAL", "REMOTE"
CONTROL_PLACES = (LOCAL, REMOTE)
DEFAULT_CONTROL_PLACE = REMOTE
CONTROL_PLACE_LEVEL = AccessLevel.OPERATOR


LOCAL, REMOTE = "LOCAL", "REMOTE"
CONTROL_PLACES = (LOCAL, REMOTE)
DEFAULT_CONTROL_PLACE = REMOTE
CONTROL_PLACE_LEVEL = AccessLevel.OPERATOR


def _rank(level) -> int:
    try:
        return AccessLevel._ORDER.index(level)
    except ValueError:
        return -1


class OperatingModeManager:
    def __init__(self, event_bus=None, audit_logger=None, load=None, save=None,
                 load_place=None, save_place=None):
        self.event_bus = event_bus
        self.audit_logger = audit_logger
        self._save = save
        self._save_place = save_place
        stored = load() if callable(load) else None
        self._mode = stored if stored in MODES else DEFAULT_MODE
        stored_place = load_place() if callable(load_place) else None
        self._control_place = stored_place if stored_place in CONTROL_PLACES else DEFAULT_CONTROL_PLACE

    # --- the control place ---------------------------------------------------------

    @property
    def control_place(self) -> str:
        return self._control_place

    def remote_allowed(self) -> bool:
        """Whether a CHANGE may arrive over the engineering link or remote
        control right now - False in LOCAL."""
        return self._control_place == REMOTE

    def set_control_place(self, place: str, actor: str, level: str = None) -> tuple:
        """(True, "") when set (or already so); (False, reason) when
        refused. Operator level from the panel; audited both ways."""
        if place not in CONTROL_PLACES:
            reason = f"unknown control place {place!r}"
            self._audit("CONTROL_PLACE_REFUSED", actor, f"{place}: {reason}", success=False)
            return False, reason
        if level is not None and _rank(level) < _rank(CONTROL_PLACE_LEVEL):
            reason = f"{place} requires {CONTROL_PLACE_LEVEL}, {actor} is {level}"
            self._audit("CONTROL_PLACE_REFUSED", actor, f"{place}: {reason}", success=False)
            log.warning(f"Control place {place} refused for {actor}: {reason}")
            return False, reason
        if place == self._control_place:
            return True, ""
        previous, self._control_place = self._control_place, place
        if callable(self._save_place):
            try:
                self._save_place(place)
            except Exception as e:  # noqa: BLE001 - a state file that cannot be written must not undo the switch
                log.error(f"Control place {place} not persisted: {e}")
        self._audit("CONTROL_PLACE_CHANGED", actor, f"{previous} -> {place}")
        log.info(f"Control place {previous} -> {place} ({actor})")
        if self.event_bus is not None:
            self.event_bus.emit("control_place_changed", place, previous)
        return True, ""

    @property
    def mode(self) -> str:
        return self._mode

    def is_mode(self, mode: str) -> bool:
        return self._mode == mode

    @staticmethod
    def required_level(mode: str):
        return REQUIRED_LEVEL.get(mode)

    def set_mode(self, mode: str, actor: str, level: str = None) -> tuple:
        """(True, "") when the mode changed or already was `mode`;
        (False, reason) when refused. `level` is the access level of
        whoever asks (None = do not check - only for internal callers
        that have already checked); the refusal is audited so a request
        from the logic that nobody could see is never silent."""
        if mode not in MODES:
            reason = f"unknown operating mode {mode!r}"
            self._audit("OPERATING_MODE_REFUSED", actor, f"{mode}: {reason}", success=False)
            return False, reason
        required = REQUIRED_LEVEL[mode]
        if level is not None and _rank(level) < _rank(required):
            reason = f"{mode} requires {required}, {actor} is {level}"
            self._audit("OPERATING_MODE_REFUSED", actor, f"{mode}: {reason}", success=False)
            log.warning(f"Operating mode {mode} refused for {actor}: {reason}")
            return False, reason
        if mode == self._mode:
            return True, ""
        previous, self._mode = self._mode, mode
        if callable(self._save):
            try:
                self._save(mode)
            except Exception as e:  # noqa: BLE001 - a state file that cannot be written must not undo the mode
                log.error(f"Operating mode {mode} not persisted: {e}")
        self._audit("OPERATING_MODE_CHANGED", actor, f"{previous} -> {mode}")
        log.info(f"Operating mode {previous} -> {mode} ({actor})")
        if self.event_bus is not None:
            self.event_bus.emit("operating_mode_changed", mode, previous)
        return True, ""

    def _audit(self, event, actor, detail, success=True):
        if self.audit_logger is not None:
            self.audit_logger.record(event, actor, detail, success=success)
