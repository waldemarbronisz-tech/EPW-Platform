"""Shared mocks for the gui_smoke/ test package (refactor/test-suite-split
task, section 3: "MOCKS THAT DON'T KEEP UP WITH THE CODE").

Every one of these classes used to be a private copy pasted (with small
variations) into different sections of the old, monolithic
test_gui_smoke.py: MockTagManager, _ThemeCapableTagManager,
_DICapableTagManager and _PageMockTM all separately hand-rolled a
TagManager-shaped mock, and three sessions in a row the SAME bug hit: a
mock was missing a method (add_tag, list_tags) that production code
(ProtectionVerifier's constructor) started calling, and nothing caught it
until the script was actually run.

This module is the fix for that recurring class of bug (task option c):
one copy of each mock, imported everywhere it's needed, so there is only
ever one place to add a method production code starts requiring.

It is deliberately NOT a full replacement of every mock with the real
headless TagManager/AccessManager (task option b) - see QtTagManagerBridge
below for where that preferred approach IS used, and
test_mock_interfaces.py for why a hand-written mock is still appropriate
for the rest: several of these mocks (_DICapableTagManager's DI1-DI64
tracking, MockControllableAccessManager's PIN state machine,
_CountingCommandManager's call recording) exist specifically to give a
test deterministic, minimal state a real object's full constructor
(EventBus wiring, project file I/O, PIN hashing) doesn't need to build
just to prove one thing - replacing them would mean dragging in
project_manager/config-file plumbing new tests can most likely do without.

Instead, drift is now caught by test_mock_interfaces.py: it parses the
REAL production adapters GUI code actually receives (main.py's
GUITagManagerAdapter/GUIAccessManagerAdapter/GUIAlarmAdapter - option a),
straight out of main.py's source text via `ast` (main.py itself boots a
QApplication/FastAPI thread at import time, so it is never imported here
or anywhere else in this test suite), and fails loudly if a mock in this
file no longer has every method the real adapter has.
"""
from PySide6.QtCore import QObject, Signal


# ---------------------------------------------------------------------------
# Command managers
# ---------------------------------------------------------------------------

class MockCommandManager:
    def request_command(self, *args, **kwargs):
        return True, []


class CountingCommandManager:
    """Part 2 (permission matrix) needs to prove a denied access level
    never reaches command dispatch at all - a plain True/[] stub like
    MockCommandManager can't tell "never called" from "called and
    permitted", so this records every call instead."""
    def __init__(self):
        self.calls = []

    def request_command(self, tag, cmd, **kwargs):
        self.calls.append((tag, cmd))
        return True, []

    def request_command_ex(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        class _Record:
            state = "DONE"
            reason = ""
        return _Record()


# ---------------------------------------------------------------------------
# Tag managers
# ---------------------------------------------------------------------------

class MockTagManager(QObject):
    """The default, minimal tag manager mock - values are never tracked
    (get_value/get_tag always None, update_tag a no-op) because most
    sections that use it never care about a tag's actual value, only
    that a MainWindow constructs and behaves correctly around it."""
    tag_changed = Signal(str, object, str)

    def __init__(self):
        super().__init__()
        self.mode = "SIMULATION"
        from epw_os.core.analog_scaling import default_channel_config
        self._analog_points = [
            {"tag": "AI1", "description": "Analog Input Channel 1", "technical_note": "",
             **default_channel_config()},
        ]

    def get_value(self, name): return None
    def get_tag(self, name): return None

    def list_tags(self):
        # Task: signal-list export - a small, fixed, representative set
        # (one plain hardware input, the one genuinely logic-writable
        # tag, one SIMULATED measurement) so a test can assert on real
        # content, not just "didn't crash".
        from epw_os.core.tag_manager import Tag, TagType, TagQuality
        return [
            Tag(name="DI1", value=True, data_type=TagType.BOOL, description="Feeder 1", quality=TagQuality.GOOD),
            Tag(name="System.Theme", value=0, data_type=TagType.INT, description="Active theme",
                quality=TagQuality.GOOD),
            Tag(name="Meas.L1", value=230.0, data_type=TagType.REAL, description="Sim voltage",
                quality=TagQuality.SIMULATED),
        ]

    # Pre-existing gap, found while adding the language-switch checks in
    # an earlier task: page_entry_gate.py's simulated device-feedback path
    # calls update_tag() from a deferred QTimer.singleShot() callback -
    # harmless every time nothing in a test happens to call
    # app.processEvents() again before the MainWindow using it is torn
    # down, which is why this never surfaced before.
    def update_tag(self, name, val, q=None): pass

    # Task (safety_kernel.py device-status gate / protection_verifier.py
    # System.PendingCommand+System.ActiveTrip fix): ProtectionVerifier's
    # constructor registers its own tags (add_tag()) - same
    # tolerate-and-no-op stance as update_tag() above, since this mock
    # never tracks real tag state either way.
    def add_tag(self, name, value, data_type, description="", timeout=5.0, source="SYSTEM", quality=None): pass
    def set_description(self, name, desc): pass
    def get_output_description(self, name, default=""): return default
    def set_output_description(self, name, desc): pass
    def get_analog_points(self): return list(self._analog_points)

    def add_analog_point(self, point):
        if any(p["tag"] == point["tag"] for p in self._analog_points):
            return False
        self._analog_points.append(dict(point))
        return True

    def remove_analog_point(self, tag_name):
        before = len(self._analog_points)
        self._analog_points = [p for p in self._analog_points if p["tag"] != tag_name]
        return len(self._analog_points) < before

    def update_analog_point(self, tag_name, point):
        for p in self._analog_points:
            if p["tag"] == tag_name:
                p.update(point)

    # Found by test_mock_interfaces.py (task section 3a) while building
    # this module: the real GUITagManagerAdapter (main.py) has had a
    # toggle_mode() passthrough (for the status-bar mode button,
    # MainWindow.toggle_mode()) since the SIMULATION/LIVE mode toggle was
    # added, and NOTHING in this test suite ever exercises that button -
    # so this exact mock has been silently missing it, undetected, the
    # whole time; a bare label-text check (`btn_sb_mode.text()`) is the
    # only place this script ever touches that button. A real report of
    # this gap, fixed here per GRANICE ("a small, unambiguous real bug
    # found by a test may be fixed") - see SESSION_REPORT.md.
    def toggle_mode(self): pass


class ThemeCapableTagManager(QObject):
    """Unlike MockTagManager (no real update_tag() at all), this one has
    a real, minimal add_tag()/update_tag() so a tag write can actually
    switch the active theme end-to-end, not just be asserted against
    ThemeManager directly."""
    tag_changed = Signal(str, object, str)

    def __init__(self):
        super().__init__()
        self.mode = "SIMULATION MODE"
        self._tags = {"System.Theme": 0}

    def get_value(self, name): return self._tags.get(name)
    def get_tag(self, name): return None
    def get_output_description(self, name, default=""): return default
    def get_analog_points(self): return []

    def update_tag(self, name, val, q=None):
        if name not in self._tags:
            raise ValueError(f"Unknown tag: {name}")
        self._tags[name] = val
        self.tag_changed.emit(name, val, "GOOD")

    # Task (protection_verifier.py System.PendingCommand+System.ActiveTrip
    # fix): ProtectionVerifier's constructor registers its own tags - a
    # real add_tag() semantic (idempotent if already present), matching
    # this mock's own real-ish update_tag() above rather than a bare
    # no-op.
    def add_tag(self, name, value, data_type, description="", timeout=5.0, source="SYSTEM", quality=None):
        self._tags.setdefault(name, value)

    # Task (protection_verifier.py System.ActiveTrip fix): ProtectionVerifier's
    # constructor also calls list_tags() (scanning for any already-Exceeded
    # Process.* tag at construction time) - this mock tracks no such tags,
    # so an empty list is exactly correct, not just a tolerated no-op.
    def list_tags(self): return []
    # See MockTagManager.toggle_mode()'s comment above - the same real,
    # previously-undetected gap, found by test_mock_interfaces.py.
    def toggle_mode(self): pass
    # This mock builds a full MainWindow (not just one page - see the
    # theme tests), so the same full-interface reasoning as MockTagManager
    # applies: any page's construction path could in principle reach one
    # of these. Untracked, like get_output_description above - only the
    # theme-related tags/methods above are ever actually exercised.
    def set_description(self, name, desc): pass
    def set_output_description(self, name, desc): pass
    def add_analog_point(self, point): return False
    def remove_analog_point(self, tag_name): return False
    def update_analog_point(self, tag_name, point): pass


class DICapableTagManager(QObject):
    """Unlike MockTagManager, this one has real add/update semantics for
    DI1..DI64 AND bridges every write through BOTH a real EventBus (so
    SwitchingCounterManager actually counts, exactly as it does off the
    real core event bus in production) and its own Qt tag_changed signal
    (so the GUI pages react) - the same two-path bridging main.py itself
    does for the real app."""
    tag_changed = Signal(str, object, str)

    def __init__(self, event_bus):
        super().__init__()
        self.mode = "SIMULATION MODE"
        self._event_bus = event_bus
        self._tags = {f"DI{i}": False for i in range(1, 65)}

    def get_value(self, name): return self._tags.get(name)
    def get_tag(self, name): return None
    def get_output_description(self, name, default=""): return default
    def get_analog_points(self): return []

    def update_tag(self, name, val, q=None):
        if name not in self._tags:
            raise ValueError(f"Unknown tag: {name}")
        self._tags[name] = val
        self._event_bus.emit("tag_changed", name, val, "GOOD")
        self.tag_changed.emit(name, val, "GOOD")

    def add_tag(self, name, value, data_type, description="", timeout=5.0, source="SYSTEM", quality=None):
        self._tags.setdefault(name, value)

    def list_tags(self): return []
    # See MockTagManager.toggle_mode()'s comment above - the same real,
    # previously-undetected gap, found by test_mock_interfaces.py.
    def toggle_mode(self): pass
    # This mock builds a full MainWindow (not just one page - see the
    # switching-counter tests), same reasoning as ThemeCapableTagManager's
    # own methods just above.
    def set_description(self, name, desc): pass
    def set_output_description(self, name, desc): pass
    def add_analog_point(self, point): return False
    def remove_analog_point(self, tag_name): return False
    def update_analog_point(self, tag_name, point): pass


class QtTagManagerBridge(QObject):
    """Wraps a REAL, headless epw_os.core.tag_manager.TagManager in the
    same Qt-signal shape main.py's own real GUITagManagerAdapter uses -
    "wrap only what crosses a thread boundary" (task option b: prefer the
    real object over a hand-written mock wherever practical, since a real
    object cannot drift from itself). Use this instead of a mock whenever
    a test actually needs real tag storage/quality/EventBus behavior
    (e.g. proving a real tag_changed event reaches GUI code), not just a
    MainWindow that constructs without error.

    This exact shape was independently reinvented at least twice before
    this module existed (inline in test_gui_smoke.py's own System.Mode
    check, and in epw_os/tests/test_protection_verifier.py) - this is the
    one shared copy task option c asks for."""
    tag_changed = Signal(str, object, str)

    def __init__(self, core_tm):
        super().__init__()
        self._core_tm = core_tm
        core_tm.event_bus.subscribe("tag_changed", lambda n, v, q: self.tag_changed.emit(n, v, q))

    def get_value(self, name): return self._core_tm.get_value(name)
    def get_tag(self, name): return self._core_tm.get_tag(name)
    def list_tags(self): return self._core_tm.list_tags()

    def update_tag(self, name, val, q=None):
        from epw_os.core.tag_manager import TagQuality
        self._core_tm.update_tag(name, val, q if q is not None else TagQuality.GOOD)

    def add_tag(self, name, value, data_type, description="", timeout=5.0, source="SYSTEM", quality=None):
        from epw_os.core.tag_manager import TagQuality
        return self._core_tm.add_tag(name, value, data_type, description=description, timeout=timeout,
                                      source=source, quality=quality if quality is not None else TagQuality.GOOD)

    @property
    def mode(self): return self._core_tm.mode

    def toggle_mode(self): self._core_tm.toggle_mode()


# ---------------------------------------------------------------------------
# Access managers
# ---------------------------------------------------------------------------

class MockAccessManager(QObject):
    """Always denies everything - fine for most construction/visibility
    checks, useless for anything that needs a real grant/deny
    distinction (use MockControllableAccessManager for that)."""
    level_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.level = "User"

    def has_access(self, required_level): return False
    def attempt_login(self, level, pin): return False
    def logout(self): pass
    def demote(self, level): return False
    def verify_pin(self, level, pin): return False
    def set_pin(self, level, new_pin): return False


class MockControllableAccessManager(QObject):
    """Behaves like the real AccessManager's level state machine:
    attempt_login() succeeds only for a known-correct PIN and actually
    raises self.level."""
    level_changed = Signal(str)
    _ORDER = ["User", "Operator", "Engineer"]
    CORRECT_PIN = "1234"

    def __init__(self):
        super().__init__()
        self.level = "User"

    def has_access(self, required_level):
        return self._ORDER.index(self.level) >= self._ORDER.index(required_level)

    def attempt_login(self, level, pin):
        if pin == self.CORRECT_PIN:
            self.level = level
            self.level_changed.emit(level)
            return True
        return False

    def logout(self): self.demote("User")

    def demote(self, level):
        if self._ORDER.index(level) > self._ORDER.index(self.level):
            return False
        # Bug 4 fix: the real AccessManager.demote()/logout() emit
        # access_level_changed via the event bus, which main.py's
        # GUIAccessManagerAdapter bridges straight to this same Qt
        # level_changed signal - only emit when the level actually
        # changes, matching the real implementation exactly.
        if level != self.level:
            self.level = level
            self.level_changed.emit(level)
        return True

    def verify_pin(self, level, pin): return pin == self.CORRECT_PIN
    def set_pin(self, level, new_pin): return True


# ---------------------------------------------------------------------------
# Audit logger / project manager
# ---------------------------------------------------------------------------

class MockAuditLogger:
    """Captures record() calls so a test can assert on them without a
    real database."""
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))

    def query(self, limit=500):
        return []


class MockProjectManager:
    def __init__(self):
        self.config = {"project_id": "TEST", "language": "en"}
        self.project_file = "mock_project.json"

    def get_language(self): return self.config.get("language", "en")
    def set_language(self, code): self.config["language"] = code
    def is_dirty(self): return False
    def save_project(self): pass

    def save_project_as(self, path):
        self.project_file = path

    def load_from(self, path):
        self.project_file = path
        return True

    # --- Project Properties ---
    def get_metadata(self):
        meta = self.config.get("metadata", {})
        return {
            "name": meta.get("name", ""), "description": meta.get("description", ""),
            "location": meta.get("location", ""), "author": meta.get("author", ""),
            "created": meta.get("created"), "modified": meta.get("modified"),
        }

    def set_metadata(self, name="", description="", location="", author=""):
        meta = self.config.setdefault("metadata", {})
        meta.update({"name": name, "description": description, "location": location, "author": author})
        if meta.get("created") is None:
            meta["created"] = "2026-01-01T00:00:00+00:00"

    def touch_metadata_modified(self):
        meta = self.config.setdefault("metadata", {})
        if meta.get("created") is None:
            meta["created"] = "2026-01-01T00:00:00+00:00"
        meta["modified"] = "2026-01-01T00:00:00+00:00"

    def get_logic_file(self): return self.config.get("logic_project")
    def get_tag_descriptions(self): return self.config.get("tag_descriptions", {})
    def get_output_descriptions(self): return self.config.get("output_descriptions", {})
    def get_switching_counters(self): return self.config.get("switching_counters", {})
    def set_switching_counters(self, data): self.config["switching_counters"] = dict(data)
    def get_service_notes(self): return self.config.get("service_notes", {})
    def set_service_notes(self, data): self.config["service_notes"] = dict(data)

    # Task (feature/retention-and-test-fix): MainWindow.setup_statusbar()
    # now calls get_db_size_warning_config() unconditionally for every
    # MainWindow it constructs (the status-bar DB-size-warning indicator,
    # refreshed at construction time regardless of whether retention is
    # ever configured) - the exact "mock missing a method the real class
    # gained" bug class refactor/test-suite-split's own mock-conformance
    # work exists to prevent, just for ProjectManager rather than
    # TagManager/AccessManager this time.
    def get_db_size_warning_config(self):
        return dict(self.config.get("db_size_warning", {"enabled": False, "threshold_mb": 500}))

    def set_db_size_warning_config(self, enabled=None, threshold_mb=None):
        w = self.config.setdefault("db_size_warning", {"enabled": False, "threshold_mb": 500})
        if enabled is not None:
            w["enabled"] = bool(enabled)
        if threshold_mb is not None:
            w["threshold_mb"] = int(threshold_mb)

    def get_historian_retention_config(self):
        return dict(self.config.get("historian_retention", {"max_days": 0, "max_rows": 0}))

    def set_historian_retention_config(self, max_days=None, max_rows=None):
        r = self.config.setdefault("historian_retention", {"max_days": 0, "max_rows": 0})
        if max_days is not None:
            r["max_days"] = int(max_days)
        if max_rows is not None:
            r["max_rows"] = int(max_rows)

    def get_audit_retention_config(self):
        return dict(self.config.get("audit_retention", {"max_days": 0, "max_rows": 0, "archive_dir": ""}))

    def set_audit_retention_config(self, max_days=None, max_rows=None, archive_dir=None):
        r = self.config.setdefault("audit_retention", {"max_days": 0, "max_rows": 0, "archive_dir": ""})
        if max_days is not None:
            r["max_days"] = int(max_days)
        if max_rows is not None:
            r["max_rows"] = int(max_rows)
        if archive_dir is not None:
            r["archive_dir"] = str(archive_dir)


# ---------------------------------------------------------------------------
# Minimal page-level mocks (used to construct individual GUI *pages*
# directly, not a full MainWindow - e.g. the per-page translation sweep)
# ---------------------------------------------------------------------------

class _Sig:
    """A do-nothing stand-in for a Qt Signal's .connect() - used only
    where a page's constructor connects to tag_changed/level_changed but
    the test never needs either signal to actually fire."""
    def connect(self, *a, **k): pass


class PageMockTagManager:
    tag_changed = _Sig()
    mode = "SIMULATION MODE"

    def get_tag(self, name): return None
    def get_value(self, name): return None
    def get_output_description(self, name, default=""): return default
    def get_analog_points(self): return []
    def update_tag(self, name, val): pass

    # Task (protection_verifier.py System.PendingCommand+System.ActiveTrip
    # fix): PageEngineerMode's constructor builds a ProtectionVerifier,
    # which registers its own tags.
    def add_tag(self, name, value, data_type, description="", timeout=5.0, source="SYSTEM", quality=None): pass
    def list_tags(self): return []


class PageMockAccessManager:
    level_changed = _Sig()
    def has_access(self, level): return False


class PageMockProtectionManager:
    protections = {}
