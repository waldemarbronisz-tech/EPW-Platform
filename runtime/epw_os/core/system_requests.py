"""REQ.SYSTEM.* - the logic asking the controller about itself (etap 6
of the signal register).

    RESTART_RUNTIME  EPWCore.request_restart(): the process ends with the
                     restart exit code and the service manager starts it
                     again (main.py listens for "restart_requested")
    RELOAD_LOGIC     EPWCore.reload_logic(): the program re-read from
                     projekt.epw and put back into the scan
    RELOAD_SYNOPTIC  EPWCore.reload_synoptic(): the screens re-read, the
                     apparatus roles rebound, RT.SYNOPTIC.* recomputed,
                     the panel's pages rebuilt

All three are an engineer's (rule Z2: the same level the panel needs).
They run on their own thread, never inside the scan that issued them:
reloading the logic STOPS the scan, and a scan waiting for itself to
stop would never finish. The request is audited when accepted or
refused (SYSTEM_REQUEST / SYSTEM_REQUEST_REFUSED); the core audits the
outcome itself (LOGIC_PROGRAM_RELOADED, SYNOPTIC_RELOADED,
RESTART_REQUESTED).
"""
import threading

from epw_os.core.access_manager import AccessLevel
from epw_os.core.logging import log

_REQUESTS = {
    "REQ.SYSTEM.RESTART_RUNTIME": "request_restart",
    "REQ.SYSTEM.RELOAD_LOGIC": "reload_logic",
    "REQ.SYSTEM.RELOAD_SYNOPTIC": "reload_synoptic",
}


class SystemRequests:
    def __init__(self, core):
        self.core = core
        self.threads = []          # what was started, for a test or a shutdown to join

    def serves(self, signal_id: str) -> bool:
        return signal_id in _REQUESTS

    def read(self, signal_id: str):
        return None

    def required_level(self, signal_id: str):
        return AccessLevel.ENGINEER if signal_id in _REQUESTS else None

    def _audit(self, event, actor, detail, success=True):
        audit = getattr(self.core, "audit_logger", None) if self.core is not None else None
        if audit is not None:
            audit.record(event, actor, detail, success=success)

    def execute(self, signal_id: str, actor: str, level: str = None) -> bool:
        method_name = _REQUESTS.get(signal_id)
        if method_name is None:
            return False
        method = getattr(self.core, method_name, None) if self.core is not None else None
        if not callable(method):
            self._audit("SYSTEM_REQUEST_REFUSED", actor, f"{signal_id}: this controller cannot {method_name}",
                        success=False)
            log.warning(f"{signal_id} from {actor} refused: the core has no {method_name}().")
            return False
        if getattr(self.core, "restart_requested", None):
            self._audit("SYSTEM_REQUEST_REFUSED", actor, f"{signal_id}: a restart is already pending", success=False)
            log.warning(f"{signal_id} from {actor} refused: a restart is already pending.")
            return False

        def run():
            try:
                if method_name == "request_restart":
                    method(f"{signal_id} issued by {actor}", actor)
                else:
                    result = method(actor, level)
                    if isinstance(result, dict) and not result.get("success", False):
                        log.warning(f"{signal_id} from {actor}: {result.get('reason') or 'not carried out'}")
            except Exception as e:  # noqa: BLE001 - a request must never take the scan down
                log.error(f"{signal_id} from {actor} failed: {type(e).__name__}: {e}")
                self._audit("SYSTEM_REQUEST_REFUSED", actor, f"{signal_id}: {type(e).__name__}: {e}", success=False)

        thread = threading.Thread(target=run, name=f"SystemRequest-{method_name}", daemon=True)
        self.threads.append(thread)
        self._audit("SYSTEM_REQUEST", actor, f"{signal_id}: accepted, {method_name}() started", success=True)
        log.info(f"{signal_id} from {actor}: {method_name}() started.")
        thread.start()
        return True
