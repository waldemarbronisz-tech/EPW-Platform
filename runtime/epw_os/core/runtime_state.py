"""runtime_state.json - what changes by itself while the controller runs
(task "runtime czyta projekt.epw", etap 2; SPEC_PROJEKT_EPW.md, "Plik
stanu").

    switching_counters   closes, opens, closed_seconds, closed_since
    intrusion_state      armed zones, bypassed lines, alarm memory,
                         line supervision (violation counters)
    last_screen          the screen last open on the panel

Written only by runtime, never part of the project, never carried to
another device. Kept apart from projekt.epw so that counters ticking
over no longer change the project file (the old project.json held both,
which is why verification scripts kept dirtying it).

Losing this file is harmless - every section falls back to its default -
with ONE exception the contract names explicitly: the arming state
("uzbrojona wstaje uzbrojona, rozbrojona - rozbrojona"). That is why
`load_problem` exists: EPWCore turns a missing or damaged state file into
a visible alarm whenever the project has intrusion zones, instead of
quietly starting every zone disarmed. The arming state itself is written
through save() immediately on every change (see IntrusionManager) - never
buffered, never only at shutdown.

Headless, no Qt. The rest of runtime sees the sections as flat keys of
ProjectManager.config (STATE_KEYS below) - this module only translates
between those keys and the file's own nested layout.
"""
import time
from pathlib import Path

from epw_os.core.local_json import atomic_write_json, read_json_object
from epw_os.core.logging import log

STATE_FORMAT = "EPW_RUNTIME_STATE"
STATE_SCHEMA_VERSION = 1

# flat ProjectManager.config key -> (path in the file, default factory)
_LAYOUT = {
    "switching_counters": (("switching_counters",), dict),
    "intrusion_armed_zones": (("intrusion_state", "armed_zones"), list),
    "intrusion_bypassed_lines": (("intrusion_state", "bypassed_lines"), list),
    "intrusion_alarm_memory": (("intrusion_state", "alarm_memory"), dict),
    "intrusion_line_supervision": (("intrusion_state", "line_supervision"), dict),
    "last_screen": (("last_screen",), lambda: None),
    # Which SYNOPTIC screen the panel had open (task punkt 3: a project
    # can carry several). Separate from "last_screen" above, which is
    # the page of the navigation tree.
    "last_synoptic_screen": (("last_synoptic_screen",), lambda: None),
}

STATE_KEYS = tuple(_LAYOUT)

# Sections whose loss is harmful (SPEC_PROJEKT_EPW.md: "To jedyny element
# stanu, którego utrata jest szkodliwa").
ARMING_KEYS = ("intrusion_armed_zones",)


def default_state() -> dict:
    return {key: factory() for key, (_path, factory) in _LAYOUT.items()}


class RuntimeStateStore:
    def __init__(self, path):
        self.path = Path(path)
        # None, "missing", "corrupt" or "newer" - what load() found.
        self.load_problem = None

    def load(self) -> dict:
        """The state as flat config keys. Never raises: a missing file,
        an unreadable one, or one from a newer program version all load
        as defaults, with `load_problem` saying which. A damaged file is
        kept aside as runtime_state.json.corrupt for whoever investigates,
        so the next save() does not destroy the evidence."""
        state = default_state()
        data, problem = read_json_object(self.path)
        if problem == "missing":
            self.load_problem = "missing"
            return state
        if problem == "corrupt" or data.get("format") != STATE_FORMAT:
            self.load_problem = "corrupt"
            self._keep_damaged_copy()
            return state
        version = data.get("schema_version")
        if not isinstance(version, int) or isinstance(version, bool) or version > STATE_SCHEMA_VERSION:
            self.load_problem = "newer" if isinstance(version, int) and not isinstance(version, bool) else "corrupt"
            return state

        self.load_problem = None
        for key, (path, factory) in _LAYOUT.items():
            node = data
            for part in path:
                node = node.get(part) if isinstance(node, dict) else None
                if node is None:
                    break
            expected = type(factory())
            if node is None:
                continue
            if factory() is None:
                state[key] = node if isinstance(node, str) else None
            elif isinstance(node, expected):
                state[key] = node
            else:
                log.warning(f"{self.path}: section {'.'.join(path)} has the wrong type - default used.")
                if key in ARMING_KEYS:
                    self.load_problem = "corrupt"
        return state

    def save(self, state: dict) -> bool:
        """Writes every state key atomically (see local_json.py). Returns
        False - after logging why - when the write failed."""
        data = {"format": STATE_FORMAT, "schema_version": STATE_SCHEMA_VERSION, "saved_at": time.time()}
        for key, (path, factory) in _LAYOUT.items():
            node = data
            for part in path[:-1]:
                node = node.setdefault(part, {})
            value = state.get(key, factory())
            node[path[-1]] = value
        try:
            atomic_write_json(self.path, data)
        except OSError as e:
            log.error(f"Could not write runtime state {self.path}: {e}")
            return False
        return True

    def _keep_damaged_copy(self):
        try:
            damaged = self.path.with_name(self.path.name + ".corrupt")
            damaged.write_bytes(self.path.read_bytes())
        except OSError:
            pass
