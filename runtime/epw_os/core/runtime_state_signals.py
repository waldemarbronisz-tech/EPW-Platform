"""The controller's own state for the logic - SYS.* lifecycle and
configuration, RT.LOGIC.*, RT.SYNOPTIC.*, MODE.* and the REQ.MODE.*
requests (register groups SYS, Logic Runtime, Synoptic Runtime, MODES,
REQ MODES).

Every bit here has a source that really changes it (rule Z1 of the
register work): the core's lifecycle attribute, HealthManager's
subsystem states, ProjectManager's load result, LogicEngine's own flags,
the screens verdict core/synoptic_status.py computes at project load,
OperatingModeManager, TrainingModeManager and TagManager.mode. What has
no source on this controller is not served - MODE.LOCAL/MODE.REMOTE
(no notion of a control place exists here) stay out of the catalogue and
are named in the register status with that reason.

The collaborators are read through the core object at every read, never
captured: several of them are replaced while the controller runs
(project reload, feature switches), and a reference taken at start
would describe a manager that no longer exists.
"""
from epw_os.core import operating_mode as modes
from epw_os.core.health_manager import SubsystemState
from epw_os.core.logging import log

LIFECYCLE_STARTING, LIFECYCLE_RUNNING, LIFECYCLE_STOPPING, LIFECYCLE_STOPPED = (
    "STARTING", "RUNNING", "STOPPING", "STOPPED")

_MODE_READS = {f"MODE.{mode}": mode for mode in modes.MODES}
_MODE_REQUESTS = {f"REQ.MODE.{mode}": mode for mode in modes.MODES}


class RuntimeStateSignals:
    def __init__(self, core):
        self.core = core
        # The SystemSignalSource this source is attached to - the scan
        # writes its overrun flag there (LogicEngine._set_signal), and
        # RT.LOGIC.OVERRUN is that very flag, not a second measurement.
        self.system = None

    def attach(self, system_source):
        self.system = system_source

    # --- collaborators, looked up at every read -------------------------------------------

    def _get(self, name, default=None):
        return getattr(self.core, name, default) if self.core is not None else default

    def _health(self) -> dict:
        manager = self._get("health_manager")
        try:
            return dict(manager.get_health()) if manager is not None else {}
        except Exception:  # noqa: BLE001 - a health manager that cannot answer is not a fault of the logic
            return {}

    def _any_health(self, state) -> bool:
        # get_health() hands out the enum's VALUE ("DEGRADED"), so compare by value.
        wanted = getattr(state, "value", state)
        return any(getattr(value, "value", value) == wanted for value in self._health().values())

    def _project_manager(self):
        return self._get("project_manager")

    def _logic(self):
        return self._get("logic_engine")

    def _synoptic(self) -> dict:
        status = self._get("synoptic_status")
        return status if isinstance(status, dict) else {}

    def _operating_mode(self):
        return self._get("operating_mode")

    # --- the reads ------------------------------------------------------------------------

    def _lifecycle(self) -> str:
        return str(self._get("lifecycle", LIFECYCLE_STARTING) or LIFECYCLE_STARTING)

    def _config_loaded(self):
        """True / False / None (no project at all)."""
        pm = self._project_manager()
        if pm is None:
            return None
        try:
            if not pm.is_epw_project():
                return None
        except Exception:  # noqa: BLE001
            return None
        if getattr(pm, "load_error", None) is not None or getattr(pm, "rolled_back", None):
            return False
        return True

    def _logic_has_program(self) -> bool:
        engine = self._logic()
        return engine is not None and getattr(engine, "_program", None) is not None

    def _logic_configured(self) -> bool:
        engine = self._logic()
        if engine is None:
            return False
        checker = getattr(engine, "is_configured", None)
        return bool(checker()) if callable(checker) else bool(getattr(engine, "_configured", False))

    def _logic_error(self) -> str:
        engine = self._logic()
        return str(getattr(engine, "last_error", "") or "") if engine is not None else ""

    def _read_time_sync_fault(self) -> bool:
        monitor = self._get("time_sync_monitor")
        if monitor is None:
            return False
        return getattr(monitor, "status", None) != "SYNCED"

    def _read_mode(self, mode: str) -> bool:
        manager = self._operating_mode()
        return manager is not None and manager.mode == mode

    def _read_training(self) -> bool:
        return bool(getattr(self._get("training_mode"), "active", False))

    def _read_simulation(self) -> bool:
        tags = self._get("tag_manager")
        mode = getattr(tags, "mode", None)
        return bool(mode) and "SIM" in str(mode).upper()

    def _read_overrun(self) -> bool:
        return bool(getattr(self.system, "scan_overrun", False))

    def read(self, signal_id: str):
        if signal_id in _MODE_READS:
            return self._read_mode(_MODE_READS[signal_id])
        handler = self._HANDLERS.get(signal_id)
        if handler is None:
            return None
        return handler(self)

    def serves(self, signal_id: str) -> bool:
        return signal_id in self._HANDLERS or signal_id in _MODE_READS or signal_id in _MODE_REQUESTS

    # --- the requests ---------------------------------------------------------------------

    def required_level(self, signal_id: str):
        mode = _MODE_REQUESTS.get(signal_id)
        return modes.REQUIRED_LEVEL.get(mode) if mode else None

    def execute(self, signal_id: str, actor: str, level: str = None) -> bool:
        """REQ.MODE.<mode>: the operating mode changes, or the refusal is
        audited by the manager itself (rule Z2: every request is executed
        or refused with a reason, visibly)."""
        mode = _MODE_REQUESTS.get(signal_id)
        if mode is None:
            return False
        manager = self._operating_mode()
        if manager is None:
            log.warning(f"{signal_id} requested by {actor}, but this controller has no operating mode manager.")
            return False
        ok, _reason = manager.set_mode(mode, actor=actor, level=level)
        return ok

    _HANDLERS = {
        "SYS.RUNNING": lambda self: self._lifecycle() == LIFECYCLE_RUNNING,
        "SYS.STARTING": lambda self: self._lifecycle() == LIFECYCLE_STARTING,
        "SYS.STOPPING": lambda self: self._lifecycle() == LIFECYCLE_STOPPING,
        "SYS.DEGRADED": lambda self: self._any_health(SubsystemState.DEGRADED),
        "SYS.FAIL": lambda self: self._any_health(SubsystemState.FAULT),
        "SYS.CONFIG_OK": lambda self: self._config_loaded() is True,
        "SYS.CONFIG_FAULT": lambda self: self._config_loaded() is False,
        "SYS.TIME_SYNC_FAULT": _read_time_sync_fault,
        "RT.LOGIC.READY": lambda self: self._logic_has_program(),
        "RT.LOGIC.RUNNING": lambda self: bool(getattr(self._logic(), "is_running", False)),
        "RT.LOGIC.FAIL": lambda self: self._logic_configured() and not self._logic_has_program(),
        "RT.LOGIC.OVERRUN": _read_overrun,
        "RT.LOGIC.PROJECT_OK": lambda self: self._logic_has_program() and not self._logic_error(),
        "RT.LOGIC.PROJECT_FAULT": lambda self: self._logic_configured() and bool(self._logic_error()),
        "RT.SYNOPTIC.READY": lambda self: bool(self._synoptic().get("ready")),
        "RT.SYNOPTIC.FAIL": lambda self: bool(self._synoptic().get("fail")),
        "RT.SYNOPTIC.BINDING_FAULT": lambda self: bool(self._synoptic().get("binding_fault")),
        # The control place (owner 2026-09-24): LOCAL locks the engineering
        # link and remote control, REMOTE lets them through.
        "MODE.LOCAL": lambda self: getattr(self._operating_mode(), "control_place", None) == "LOCAL",
        "MODE.REMOTE": lambda self: getattr(self._operating_mode(), "control_place", None) == "REMOTE",
        # The control place (owner 2026-09-24): LOCAL locks the engineering
        # link and remote control, REMOTE lets them through.
        "MODE.LOCAL": lambda self: getattr(self._operating_mode(), "control_place", None) == "LOCAL",
        "MODE.REMOTE": lambda self: getattr(self._operating_mode(), "control_place", None) == "REMOTE",
        # The control place (owner 2026-09-24): LOCAL locks the engineering
        # link and remote control, REMOTE lets them through.
        "MODE.LOCAL": lambda self: getattr(self._operating_mode(), "control_place", None) == "LOCAL",
        "MODE.REMOTE": lambda self: getattr(self._operating_mode(), "control_place", None) == "REMOTE",
        "MODE.TRAINING": _read_training,
        "MODE.SIMULATION": _read_simulation,
        "MODE.DEGRADED": lambda self: self._any_health(SubsystemState.DEGRADED),
    }
