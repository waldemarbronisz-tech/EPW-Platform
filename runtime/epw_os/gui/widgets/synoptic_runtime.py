import json
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from epw_os.core.logging import log

class SynopticRuntimeAdapter(QWidget):
    # DTO mapping events
    command_requested = Signal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.objects = []
        self._project = None
        self.ready = False

    def load_synoptic_definition(self, filepath: str):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            if data.get("format") != "EPW_SYNOPTIC":
                return False
                
            self._project = data
            self.ready = True
            
            # Simplified mock DTO binding representation
            self.objects = data.get("objects", [])
            return True
        except Exception as e:
            # Not referenced/instantiated anywhere else in this codebase
            # today (confirmed by search) - early scaffolding for a
            # future real Synoptic Editor integration. Logged anyway for
            # consistency/safety once it IS wired up somewhere - a
            # synoptic diagram silently failing to load with zero trace
            # is the same "polykane wyjatki" pattern System.Mode had.
            log.warning(f"Could not load synoptic definition {filepath!r}: {e}")
            return False

    def handle_telemetry(self, tag_name: str, value, quality: str):
        # Stub for resolving incoming TagManager bindings to objects
        if not self.ready: return
        for obj in self.objects:
            if obj.get("bindings", {}).get("value") == tag_name:
                pass # Trigger UI render update

    def user_clicked(self, obj_id: str):
        for obj in self.objects:
            if obj.get("id") == obj_id:
                cmd = obj.get("bindings", {}).get("command")
                if cmd:
                    target, action = cmd.split('.')
                    self.command_requested.emit(target, action)
