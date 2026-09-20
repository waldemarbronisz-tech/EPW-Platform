"""The night arm and the per-user refusal, on the real page.

The core rules are covered headlessly (epw_os/tests/
test_intrusion_night_and_users.py); what these check is that an operator
standing at the panel can actually reach them: the second button appears
where a night arm would differ from a full one, it arms in NIGHT mode,
the row says so, and a refusal is put in front of the person instead of
being swallowed.
"""
import pytest
from PySide6.QtWidgets import QMessageBox, QPushButton

from epw_os.core.intrusion_manager import ArmMode, ZoneState
from epw_os.gui.pages.page_intrusion import PageIntrusionOverview
from gui_smoke._mocks import PageMockAccessManager


class FakeIntrusion:
    """The slice of IntrusionManager this page reads, with arming that
    records how it was called."""

    def __init__(self, night_lines=True):
        self.calls = []
        self.state = ZoneState.DISARMED
        self.mode = ArmMode.FULL
        self.arm_result = _Result(True)
        self.disarm_result = True
        self._lines = [
            {"id": "L1", "name": "Door", "zone_id": "Z1", "tag": "ELA1.DI.1",
             "line_type": "INSTANT", "active_at_night": True},
            {"id": "L2", "name": "Motion", "zone_id": "Z1", "tag": "ELA1.DI.2",
             "line_type": "INSTANT", "active_at_night": not night_lines},
        ]

    # -- structure
    def get_zones(self): return [{"id": "Z1", "name": "Hall"}]
    def get_lines(self): return [dict(line) for line in self._lines]
    def get_zone_state(self, zone_id): return self.state
    def get_zone_arm_mode(self, zone_id): return self.mode
    def get_countdown_remaining(self, zone_id): return 0
    def get_alarm_memory(self, zone_id): return {"active": False}
    def is_walk_test_active(self, zone_id): return False
    def is_line_violated_now(self, line_id): return False
    def is_line_bypassed(self, line_id): return False
    def is_line_locked(self, line_id): return False
    def is_line_fault(self, line_id): return False
    def is_line_suspect(self, line_id): return False
    def get_line_state(self, line_id): return "SECURE"
    def get_line_life_snapshot(self, line_id): return {}
    def get_walk_test_status(self, zone_id): return {}

    # -- the sounder, which the page shows a "Silence" button for
    siren = False
    silence_result = True

    def siren_active(self): return self.siren

    def silence(self, actor="SYSTEM", user=None):
        self.calls.append(("silence", None, None, user))
        if self.silence_result:
            self.siren = False
        return self.silence_result

    # -- actions
    def arm_zone(self, zone_id, actor, level=None, force=False, mode=ArmMode.FULL, user=None):
        self.calls.append(("arm", zone_id, mode, user))
        if self.arm_result.success:
            self.state, self.mode = ZoneState.ARMED, mode
        return self.arm_result

    def disarm_zone(self, zone_id, actor, level=None, user=None):
        self.calls.append(("disarm", zone_id, user))
        if self.disarm_result:
            self.state, self.mode = ZoneState.DISARMED, ArmMode.FULL
        return self.disarm_result


class _Result:
    def __init__(self, success, reason="", needs_confirmation=False):
        self.success = success
        self.reason = reason
        self.needs_confirmation = needs_confirmation
        self.violated_line_ids = []
        self.fault_line_ids = []


class _Access(PageMockAccessManager):
    """Operator, optionally signed in as a named person."""

    def __init__(self, user_id=None, name="Kowalski"):
        super().__init__()
        self.level = "Operator"
        self._user_id = user_id
        self._name = name

    def has_access(self, required): return True
    def current_user_id(self): return self._user_id
    def current_actor(self): return self._name if self._user_id else self.level


def _page(qapp, manager, access=None):
    page = PageIntrusionOverview(manager, access or _Access())
    # The page asks its window for access; standalone there is none, so
    # the one call it makes is stubbed to "granted" - the access matrix
    # itself is covered in test_permissions_core.py.
    page.window().request_access = lambda level: True
    return page


def _zone_buttons(page):
    container = page.zone_table.cellWidget(0, page.zone_table.columnCount() - 1)
    return container.findChildren(QPushButton) if container else []


def test_the_night_button_appears_only_where_it_would_differ(qapp):
    with_night = _page(qapp, FakeIntrusion(night_lines=True))
    assert [b.text() for b in _zone_buttons(with_night)] == ["Arm", "Arm (night)"]

    # Every line watches at night: a night arm would protect exactly as
    # much as a full one, so there is nothing to choose between.
    without = _page(qapp, FakeIntrusion(night_lines=False))
    assert [b.text() for b in _zone_buttons(without)] == ["Arm"]


def test_pressing_it_arms_in_night_mode_and_the_row_says_so(qapp):
    manager = FakeIntrusion()
    page = _page(qapp, manager)

    _zone_buttons(page)[1].click()

    assert manager.calls == [("arm", "Z1", ArmMode.NIGHT, None)]
    assert "NIGHT" in page.zone_table.item(0, 1).text(), page.zone_table.item(0, 1).text()


def test_a_plain_arm_is_still_a_full_arm(qapp):
    manager = FakeIntrusion()
    page = _page(qapp, manager)

    _zone_buttons(page)[0].click()

    assert manager.calls == [("arm", "Z1", ArmMode.FULL, None)]
    assert "NIGHT" not in page.zone_table.item(0, 1).text()


def test_the_signed_in_person_is_handed_to_the_alarm_system(qapp):
    """What makes "only Kowalski may disarm the warehouse" possible: the
    page tells the manager WHO is asking, not just which level."""
    manager = FakeIntrusion()
    page = _page(qapp, manager, access=_Access(user_id="U1"))

    _zone_buttons(page)[0].click()
    manager.state = ZoneState.ARMED
    page.refresh()
    _zone_buttons(page)[0].click()

    assert manager.calls == [("arm", "Z1", ArmMode.FULL, "U1"), ("disarm", "Z1", "U1")]


def test_a_refused_arm_is_put_in_front_of_the_operator(qapp, monkeypatch):
    manager = FakeIntrusion()
    manager.arm_result = _Result(False, reason="Kowalski may not arm zone 'Hall'")
    page = _page(qapp, manager, access=_Access(user_id="U2"))
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text, *a, **k: shown.append(text))

    _zone_buttons(page)[0].click()

    assert shown and "may not arm" in shown[0]


def test_a_refused_disarm_is_too(qapp, monkeypatch):
    manager = FakeIntrusion()
    manager.state = ZoneState.ARMED
    manager.disarm_result = False
    page = _page(qapp, manager, access=_Access(user_id="U2"))
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text, *a, **k: shown.append(text))

    _zone_buttons(page)[0].click()

    assert shown and "not allowed" in shown[0].lower()


# --- silencing the sounder ---------------------------------------------------
# Not disarming: the zone stays in alarm, the memory and the strobe stay
# on. The button exists because "turn the noise off" and "the break-in
# is dealt with" are two different decisions, often made minutes apart.

def test_the_silence_button_is_offered_only_while_there_is_noise_to_stop(qapp):
    quiet = _page(qapp, FakeIntrusion())
    assert quiet.btn_silence.isHidden() is True

    manager = FakeIntrusion()
    manager.siren = True
    sounding = _page(qapp, manager)
    assert sounding.btn_silence.isHidden() is False


def test_pressing_it_silences_and_the_button_goes_away(qapp):
    manager = FakeIntrusion()
    manager.siren = True
    manager.state = ZoneState.ALARM
    page = _page(qapp, manager, access=_Access(user_id="U1"))

    page.btn_silence.click()

    assert ("silence", None, None, "U1") in manager.calls, "the person is handed over, as with arm/disarm"
    assert manager.siren is False
    assert page.btn_silence.isHidden() is True
    assert manager.state == ZoneState.ALARM, "silencing is not disarming"


def test_a_refused_silence_is_put_in_front_of_the_operator(qapp, monkeypatch):
    manager = FakeIntrusion()
    manager.siren = True
    manager.silence_result = False
    page = _page(qapp, manager, access=_Access(user_id="U2"))
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text, *a, **k: shown.append(text))

    page.btn_silence.click()

    assert shown and "may not silence" in shown[0]
