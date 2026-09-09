"""Training Mode (Task: tryb, w ktorym caly interfejs dziala normalnie,
ale zaden rozkaz nie wychodzi na sprzet). Headless (no PyQt import),
same rule as every other core/ module.

For learning the system and demonstrating it with zero risk of actually
switching anything. Today the *only* thing standing between an operator
and real hardware is that the drivers happen to be simulated - once a
real driver is plugged in there is no such fuse. This module is that
fuse, made explicit and independent of which driver is configured.

The cutoff itself does NOT live here - it lives at the driver layer's
own boundary, epw_os/core/driver_manager.py's route_command() (see its
docstring). This module only holds the on/off flag and records it to
the audit log; everything upstream of route_command() - AccessManager,
CommandManager's safety_kernel/logic_engine validation - runs through
its completely normal path with no idea this module exists (GRANICE:
"odciecie ma nastepowac na granicy warstwy sterownikow, NIE przez
omijanie sprawdzen uprawnien czy blokad").

Deliberately never persisted anywhere (Task: "Tryb NIE jest
zapamietywany miedzy uruchomieniami - program zawsze wstaje w trybie
normalnym"): self.active is a plain runtime attribute, always False at
construction, with no project_manager/config file involvement of any
kind - there is simply no code path that could bring it back to True on
its own. A brand new instance (i.e. a restart, since EPWCore
constructs exactly one of these) is always inactive; nothing more is
needed to guarantee that.
"""
from epw_os.core.logging import log


class TrainingModeManager:
    def __init__(self, event_bus=None, audit_logger=None):
        self.event_bus = event_bus
        self.audit_logger = audit_logger
        self.active = False

    def set_active(self, active: bool, actor: str = "Engineer") -> bool:
        """Task: "wlaczenie i wylaczenie trybu zapisywane do dziennika
        audytowego" - every real transition is recorded, exactly once.
        Idempotent: calling this with the state it's already in (e.g. two
        rapid clicks, or a GUI re-sending its current checkbox state) is
        a silent no-op, not a duplicate audit entry - the audit log
        should read as a history of actual mode CHANGES, not of every
        time someone touched the control.

        `actor` is the access level that made the change - callers are
        expected to have already verified it's Engineer (Task: "dostepny
        TYLKO dla poziomu Engineer"); this method does not itself
        re-check access, the same division of responsibility
        switching_counters.py's manual reset and service_notes.py's
        add_note() already use (the GUI's own gate is the first check,
        the core method trusts what it's told but doesn't enforce a
        SPECIFIC level on its own - unlike those two, there's no lower
        level that's ever allowed to call this at all, so there is
        nothing further for this method to defend against; the real
        enforcement point is the GUI action being Engineer-only in the
        first place).

        Returns True if the state actually changed, False if it was
        already what was requested."""
        active = bool(active)
        if active == self.active:
            return False
        self.active = active
        log.info(f"Training Mode {'ENABLED' if active else 'DISABLED'} by {actor}")
        if self.audit_logger is not None:
            self.audit_logger.record(
                "TRAINING_MODE_ON" if active else "TRAINING_MODE_OFF",
                actor,
                "Training Mode enabled - commands no longer reach the driver layer" if active
                else "Training Mode disabled - commands reach the driver layer again",
                success=True,
            )
        if self.event_bus is not None:
            self.event_bus.emit("training_mode_changed", active)
        return True
