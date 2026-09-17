"""Punkt 2 / luka 7 ("unify the two apparatus registries"): Studio's
"Aparaty" (the SPEC's flat Device - feedback[0] = CLOSED contact,
command[0] = CLOSE, command[1] = OPEN, commandStyle/pulseMs) and
Synoptic's per-behavior DeviceSchema.ts Device describe the same
apparatus. project_panels.py's device_to_synoptic_dict()/
device_from_synoptic_dict() translate between them, and main_window.py's
_sync_device_registry_with_synoptic() bridges the two lists ADD-ONLY in
both directions, exactly like cards and locations.
"""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Device
from studio.shell.project_panels import device_designation, device_from_synoptic_dict, device_to_synoptic_dict


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


def _close(win):
    """A window left alive keeps polling its (fake) panels on a timer
    during later tests - detach the fake, schedule deletion, flush the
    event loop. (Not close(): a dirty project's close asks a modal
    question, which blocks forever offscreen.)"""
    win._synoptic_panel = None
    win.deleteLater()
    _app().processEvents()


class _FakeSynopticPanel:
    def __init__(self, registry):
        self._registry = registry
        self.pushed = None

    def query_device_registry(self, callback):
        callback(self._registry)

    def push_device_registry(self, cards, locations, devices=()):
        self.pushed = (cards, locations, list(devices))

    # main_window.py's dirty-marker poll asks these on a timer for as
    # long as the window lives - a fake that lacks them raises inside
    # Qt's event loop and takes later tests down with it.
    def is_page_ready(self) -> bool:
        return False

    def query_state(self, callback):
        callback(None)


# --- converters ----------------------------------------------------------------------

def test_designation_is_the_iec_minus_plus_the_part_after_the_location():
    assert device_designation("KOT_KM1") == "-KM1"
    assert device_designation("KM1") == "-KM1"
    assert device_designation("KOT_") == ""


def test_switched_pulse_toggle_maps_to_synoptic_and_back():
    km1 = Device(id="KOT_KM1", behavior="SWITCHED", kind="contactor", feedback=["ELA1.DI.2"],
                 command=["ADA1.DO.3", "ADA1.DO.4"], command_style="PULSE_TOGGLE", pulse_ms=100,
                 supervision={"confirmTimeoutMs": 2000, "discrepancyAlarm": True},
                 safe_state={"onStartup": "NO_CHANGE", "onLinkLoss": "OPEN"})

    out = device_to_synoptic_dict(km1)

    assert out["id"] == "KOT_KM1" and out["designation"] == "-KM1" and out["name"] == "KOT_KM1"
    assert out["behavior"] == "SWITCHED" and out["kind"] == "contactor" and out["publishToHa"] is False
    assert out["feedback"] == {"mode": "SINGLE", "diClosed": "ELA1.DI.2"}
    assert out["command"] == {"outputCount": 2, "style": "PULSE_TOGGLE", "doClose": "ADA1.DO.3",
                              "doOpen": "ADA1.DO.4", "pulseMs": 100}
    assert out["supervision"] == {"confirmTimeoutMs": 2000, "discrepancyAlarm": True}
    assert out["safeState"] == {"onStartup": "NO_CHANGE", "onLinkLoss": "OPEN"}
    assert out["switchCounter"] is False
    assert device_from_synoptic_dict(out) == km1


def test_switched_dual_feedback_maintained_and_no_feedback_one_output():
    dual = Device(id="KOT_Q1", behavior="SWITCHED", feedback=["DI1.DI.1", "DI1.DI.2"], command=["DO1.DO.1"])
    out = device_to_synoptic_dict(dual)
    assert out["feedback"] == {"mode": "DUAL", "diClosed": "DI1.DI.1", "diOpen": "DI1.DI.2"}
    assert out["command"] == {"outputCount": 1, "style": "MAINTAINED", "doClose": "DO1.DO.1"}
    assert "pulseMs" not in out["command"]
    assert out["kind"] == "contactor"  # Synoptic refuses an empty kind - a default is given
    assert out["supervision"] == {"confirmTimeoutMs": 1000, "discrepancyAlarm": False}
    assert out["safeState"] == {"onStartup": "NO_CHANGE", "onLinkLoss": "NO_CHANGE"}
    back = device_from_synoptic_dict(out)
    assert (back.feedback, back.command, back.command_style, back.pulse_ms) == (dual.feedback, dual.command, "MAINTAINED", 0)

    bare = device_to_synoptic_dict(Device(id="KOT_X", behavior="SWITCHED"))
    assert bare["feedback"] == {"mode": "NONE"}
    assert bare["command"]["doClose"] == "" and "doOpen" not in bare["command"]


def test_signal_measured_modulated_selector_round_trip_their_addresses():
    signal = Device(id="KOT_ALARM", behavior="SIGNAL", kind="lamp", feedback=["DI1.DI.6"])
    measured = Device(id="MH_T1", behavior="MEASURED", feedback=["AI1.AI.1"])
    modulated = Device(id="MH_V1", behavior="MODULATED", feedback=["AI1.AI.2"], command=["AO1.AO.1"])
    selector = Device(id="KOT_S1", behavior="SELECTOR", feedback=["DI1.DI.7", "DI1.DI.8", "DI1.DI.9"])

    s, m, mo, se = (device_to_synoptic_dict(d) for d in (signal, measured, modulated, selector))
    assert s["feedback"] == {"di": "DI1.DI.6", "invert": False} and s["alarmState"] == "HIGH"
    assert m["input"] == "AI1.AI.1" and m["unit"] == "" and m["format"] == "0.0"
    assert mo["setpointOutput"] == "AO1.AO.1" and mo["feedbackInput"] == "AI1.AI.2"
    assert se["positions"] == [{"name": "1", "feedback": "DI1.DI.7"}, {"name": "2", "feedback": "DI1.DI.8"},
                               {"name": "3", "feedback": "DI1.DI.9"}]
    for original, out in ((signal, s), (measured, m), (modulated, mo), (selector, se)):
        back = device_from_synoptic_dict(out)
        assert (back.id, back.behavior, back.feedback, back.command) == (
            original.id, original.behavior, original.feedback, original.command)


def test_selector_with_fewer_than_two_positions_is_padded_to_synoptics_minimum():
    out = device_to_synoptic_dict(Device(id="KOT_S2", behavior="SELECTOR", feedback=["DI1.DI.1"]))
    assert out["positions"] == [{"name": "1", "feedback": "DI1.DI.1"}, {"name": "2"}]
    assert device_from_synoptic_dict(out).feedback == ["DI1.DI.1"]


def test_synoptics_own_form_fields_are_read_without_crashing_on_partial_data():
    assert device_from_synoptic_dict({"id": "KOT_K", "behavior": "SWITCHED"}) == Device(id="KOT_K", behavior="SWITCHED")
    odd = device_from_synoptic_dict({"id": "KOT_K", "behavior": "SWITCHED",
                                     "command": {"style": "FLIP", "doClose": "DO1.DO.1", "pulseMs": "x"}})
    assert (odd.command, odd.command_style, odd.pulse_ms) == (["DO1.DO.1"], "MAINTAINED", 0)
    pulse = device_from_synoptic_dict({"id": "KOT_K", "behavior": "SWITCHED",
                                       "command": {"style": "PULSE", "doClose": "DO1.DO.1", "pulseMs": "250"}})
    assert (pulse.command_style, pulse.pulse_ms) == ("PULSE", 250)


# --- the sync ------------------------------------------------------------------------------

def test_sync_pulls_synoptics_devices_studio_lacks_and_pushes_studios_own(tmp_path):
    _app()
    win = _window(tmp_path)
    win._project.devices = [Device(id="KOT_Q1", behavior="SWITCHED", feedback=["DI1.DI.1"], command=["DO1.DO.1"])]
    win._open_devices()
    registry = {
        "cards": [], "locations": [],
        "devices": [
            {"id": "KOT_Q1", "designation": "-Q1", "name": "Wylacznik glowny", "behavior": "SWITCHED",
             "kind": "breaker", "publishToHa": True, "feedback": {"mode": "DUAL", "diClosed": "X.DI.1", "diOpen": "X.DI.2"},
             "command": {"outputCount": 1, "style": "MAINTAINED", "doClose": "X.DO.1"}},  # already have this id
            {"id": "KOT_KM1", "designation": "-KM1", "name": "Stycznik", "behavior": "SWITCHED", "kind": "contactor",
             "publishToHa": False, "feedback": {"mode": "SINGLE", "diClosed": "ELA1.DI.2"},
             "command": {"outputCount": 2, "style": "PULSE_TOGGLE", "doClose": "ADA1.DO.3", "doOpen": "ADA1.DO.4",
                         "pulseMs": 100},
             "supervision": {"confirmTimeoutMs": 2000, "discrepancyAlarm": True},
             "safeState": {"onStartup": "NO_CHANGE", "onLinkLoss": "NO_CHANGE"}, "switchCounter": True},
            {"designation": "-X", "behavior": "SIGNAL"},  # no id - ignored
        ],
    }
    win._synoptic_panel = _FakeSynopticPanel(registry)

    win._sync_device_registry_with_synoptic()

    devices = {d.id: d for d in win._project.devices}
    assert set(devices) == {"KOT_Q1", "KOT_KM1"}
    assert devices["KOT_Q1"].feedback == ["DI1.DI.1"]  # add-only: Studio's own row untouched
    km1 = devices["KOT_KM1"]
    assert (km1.feedback, km1.command, km1.command_style, km1.pulse_ms) == (
        ["ELA1.DI.2"], ["ADA1.DO.3", "ADA1.DO.4"], "PULSE_TOGGLE", 100)
    assert km1.supervision == {"confirmTimeoutMs": 2000, "discrepancyAlarm": True}
    assert win._devices_panel.table.rowCount() == 2
    assert win._project.is_dirty

    cards, locations, pushed = win._synoptic_panel.pushed
    assert [d["id"] for d in pushed] == ["KOT_Q1", "KOT_KM1"]
    assert pushed[0]["designation"] == "-Q1"
    assert pushed[0]["feedback"] == {"mode": "SINGLE", "diClosed": "DI1.DI.1"}
    _close(win)


def test_sync_with_no_synoptic_registry_still_pushes_studios_devices(tmp_path):
    _app()
    win = _window(tmp_path)
    win._project.devices = [Device(id="KOT_ALARM", behavior="SIGNAL", feedback=["DI1.DI.6"]),
                            Device(id="", behavior="SIGNAL")]  # a row still being typed - not pushed
    win._synoptic_panel = _FakeSynopticPanel(None)

    win._sync_device_registry_with_synoptic()

    assert [d["id"] for d in win._synoptic_panel.pushed[2]] == ["KOT_ALARM"]
    assert [d.id for d in win._project.devices] == ["KOT_ALARM", ""]
    _close(win)
