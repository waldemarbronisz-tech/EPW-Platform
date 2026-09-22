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
runtime_state_signals.py. LOCAL/REMOTE have no source on this
controller and are reported as such, not faked.
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


def _rank(level) -> int:
    try:
        return AccessLevel._ORDER.index(level)
    except ValueError:
        return -1


class OperatingModeManager:
    def __init__(self, event_bus=None, audit_logger=None, load=None, save=None):
        self.event_bus = event_bus
        self.audit_logger = audit_logger
        self._save = save
        stored = load() if callable(load) else None
        self._mode = stored if stored in MODES else DEFAULT_MODE

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
