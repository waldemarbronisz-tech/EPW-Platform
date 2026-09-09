import json
from typing import Tuple, List, Dict
from epw_os.core.logging import log

class LogicEngine:
    def __init__(self, tag_manager):
        self.tag_manager = tag_manager
        self.is_running = False
        self._project = None
        # Bug 2 fix: set to True only when load_program() is actually
        # called - i.e. project.json's "logic_project" pointed at a file
        # at all. This is deliberately a separate flag from self._project
        # (which reflects a config that actually loaded successfully):
        # before this flag existed, "no logic project was ever
        # configured" and "a project WAS configured but failed to load"
        # were indistinguishable inside this class - self._project was
        # None either way, so validate_command() below fail-safe-blocked
        # both cases identically. Only the second one is a real fault.
        self._configured = False

    def is_configured(self) -> bool:
        """True once a logic_project file was ever handed to
        load_program() (whether or not it actually loaded). Used by the
        GUI (widgets/popups.py) to show a neutral "no logic configured"
        message instead of implying an interlock graph was evaluated."""
        return self._configured

    def load_program(self, filepath: str) -> bool:
        self._configured = True
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if data.get("format") != "EPW_RUNTIME_LOGIC":
                    log.error("Invalid logic runtime schema")
                    return False
                self._project = data
                return True
        except FileNotFoundError:
            log.warning(f"Logic runtime artifact {filepath} not found.")
            return False
        except Exception as e:
            log.error(f"Failed to load logic runtime: {e}")
            return False

    def validate_command(self, device_tag: str, command: str) -> Tuple[bool, List[str]]:
        # Bug 2 fix: distinguish "no logic project configured at all"
        # (normal, expected - project.json's logic_project is null) from
        # "a project WAS configured but never loaded successfully, or -
        # in the future - stopped responding" (a genuine fault). Only
        # the second one fail-safe-blocks. Every OTHER gate that runs
        # around this method (access level in the calling page, and
        # safety_kernel.validate_command_safety() in command_manager.py)
        # is completely independent of this check and is unchanged.
        if not self._configured:
            return True, []
        if not self._project:
            return False, ["Logic Runtime Unavailable - Commands Blocked (Fail Safe)"]

        # In a real engine, we'd evaluate the interlock graph.
        return True, []
