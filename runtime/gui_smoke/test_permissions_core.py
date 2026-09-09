"""Real, enforced per-level permissions (User/Operator/Engineer) - the
"permissions" axis (refactor/test-suite-split task). Every check here
calls the actual page HANDLER METHOD directly (bypassing whatever the UI
would or wouldn't let a click reach) - proving the gate lives in the
execution path itself, not just in a disabled/hidden widget, per the
original task's explicit "EGZEKWOWANIE MUSI BYĆ REALNE, NIE TYLKO
WIZUALNE" requirement.

This file covers the gates on pages/features that already exist without
their own extra state to manage (device control, description fields,
Force menus, Protection Settings, alarms, Engineer/Audit/Bus nav,
Language/Screen Sleep). Permission-gated features that carry their own
persistent state (switching counters, Training Mode, service notes,
Analog Inputs add/edit) are in test_permissions_features.py instead, to
keep any one file from re-growing back into a single giant block.
"""
from PySide6.QtCore import Qt

from gui_smoke._mocks import (
    CountingCommandManager, MockAuditLogger, MockCommandManager, MockControllableAccessManager, MockProjectManager,
    MockTagManager,
)


def _access_at(level):
    am = MockControllableAccessManager()
    if level != "User":
        assert am.attempt_login(level, MockControllableAccessManager.CORRECT_PIN)
    return am


def _denied(audit, needle=None):
    return any(e[0] == "ACCESS_DENIED" and (needle is None or needle in e[2]) for e in audit.entries)


def _stub_dialog_execs():
    """Every dialog a gated action might open, stubbed to accept(1)
    immediately - never blocks, and lets an ALLOWED level's handler run
    to completion so this proves the gate doesn't ALSO block Operator/
    Engineer, not just that it blocks User. A DENIED level's handler
    returns before ever constructing one of these, so the stub is simply
    unused on that path."""
    from epw_os.gui.pages.page_analog_inputs import AnalogChannelConfigDialog
    from epw_os.gui.widgets.popups import ConfirmationPopup, DeviceControlPopup, SettingChangePopup
    from epw_os.gui.widgets.settings_popups import LanguageDialog, ScreenSleepDialog

    stubbed = [DeviceControlPopup, ConfirmationPopup, SettingChangePopup, AnalogChannelConfigDialog,
               LanguageDialog, ScreenSleepDialog]
    origs = {cls: cls.exec for cls in stubbed}
    for cls in stubbed:
        cls.exec = lambda self: 1
    return origs


def _unstub_dialog_execs(origs):
    for cls, orig in origs.items():
        cls.exec = orig


def test_device_control_from_synoptic_matrix(make_window):
    # page_entry_gate.py: device control from synoptic (matrix: User NO,
    # Operator/Engineer YES).
    origs = _stub_dialog_execs()
    try:
        for level, allowed in (("User", False), ("Operator", True), ("Engineer", True)):
            access, audit, cmd = _access_at(level), MockAuditLogger(), CountingCommandManager()
            w = make_window(MockTagManager(), cmd, access, MockProjectManager(), audit)
            # Bug 3 fix: handle_control_request() used to reference an
            # undefined `delay` variable right after the
            # command_manager.request_command() call this test cares
            # about, so every permitted command raised a NameError right
            # here. `delay` is now a defined placeholder constant, so
            # this must complete with no exception at all - letting it
            # propagate uncaught is itself the DOWÓD proof.
            w.page_entry_gate.handle_control_request((w.page_entry_gate.q1, w.pos()))
            if allowed:
                assert not _denied(audit), (level, audit.entries)
                assert cmd.calls, f"{level} should have reached command_manager"
            else:
                assert _denied(audit, "synoptic"), (level, audit.entries)
                assert not cmd.calls, "a denied level must never reach command_manager"
    finally:
        _unstub_dialog_execs(origs)


def test_control_outputs_description_edit_engineer_only(make_window):
    # (matrix: Engineer only) - Force is unaffected/already covered by
    # existing tests, untouched here.
    for level, allowed in (("User", False), ("Operator", False), ("Engineer", True)):
        access, audit = _access_at(level), MockAuditLogger()
        w = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(), audit)
        item = w.page_do.table.item(0, 2)
        assert bool(item.flags() & Qt.ItemFlag.ItemIsEditable) == allowed, (level, "visual flag")
        # Direct model mutation - what the in-place editor committing
        # would also do - independent of whether the flag above would
        # have let a real double-click editor open at all.
        item.setText("HACKED")
        if allowed:
            assert w.page_do.device_rows[0].description == "HACKED"
            assert not _denied(audit)
        else:
            assert item.text() != "HACKED", f"{level} must not be able to change the description"
            assert _denied(audit, "Control Outputs description"), audit.entries


def test_digital_inputs_description_edit_engineer_only(make_window):
    for level, allowed in (("User", False), ("Operator", False), ("Engineer", True)):
        access, audit = _access_at(level), MockAuditLogger()
        w = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(), audit)
        item = w.page_di.table.item(0, 2)
        assert bool(item.flags() & Qt.ItemFlag.ItemIsEditable) == allowed, (level, "visual flag")
        item.setText("HACKED DI")
        if allowed:
            assert item.text() == "HACKED DI"
            assert not _denied(audit)
        else:
            assert item.text() != "HACKED DI"
            assert _denied(audit, "Digital Input description"), audit.entries


def test_digital_inputs_force_simulation_menu_engineer_only(make_window):
    for level, allowed in (("User", False), ("Operator", False), ("Engineer", True)):
        access, audit = _access_at(level), MockAuditLogger()
        w = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(), audit)
        w.tag_manager.mode = "SIMULATION MODE"  # the menu is a no-op outside simulation regardless of access
        # Called directly (bypassing the actual right-click) - the
        # context menu itself would call QMenu.exec() and block, so this
        # exercises exactly the access-check prefix of the method
        # without needing to also stub QMenu.
        if not allowed:
            w.page_di.open_simulation_menu(w.page_di.table.rect().topLeft())
            assert _denied(audit, "Force Digital Input"), audit.entries


def test_protection_settings_engineer_only_no_simulation_bypass(make_window):
    # (matrix: Engineer only, no more SIMULATION MODE bypass)
    for level, allowed in (("User", False), ("Operator", False), ("Engineer", True)):
        access, audit = _access_at(level), MockAuditLogger()
        w = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(), audit)
        w.tag_manager.mode = "SIMULATION MODE"  # must NOT bypass the gate anymore - part of what's being proven
        assert w.page_protection_electrical.btn_reset_stats.isEnabled() == allowed, (level, "Reset Statistics button")

        prot_id = next(iter(w.page_protection_electrical.protection_manager.protections))
        stage = w.page_protection_electrical.protection_manager.protections[prot_id].stages[0]
        old_enabled, old_setting, old_action = stage.enabled, stage.setting, stage.action

        class _FakeCheckbox:
            def __init__(self): self._checked = old_enabled
            def blockSignals(self, b): pass
            def setChecked(self, v): self._checked = v

        class _FakeCombo:
            def __init__(self): self.text = old_action
            def blockSignals(self, b): pass
            def setCurrentText(self, t): self.text = t

        w.page_protection_electrical.on_stage_enabled_changed(prot_id, stage, 0 if old_enabled else 2, _FakeCheckbox())
        w.page_protection_electrical.on_action_changed(
            prot_id, stage, "Trip" if old_action != "Trip" else "Warning", _FakeCombo())
        if allowed:
            assert stage.enabled != old_enabled, "Engineer must be able to toggle a stage"
            assert stage.action != old_action, "Engineer must be able to change Action"
            assert not _denied(audit)
        else:
            assert stage.enabled == old_enabled, f"{level} must not be able to toggle a stage, even in SIMULATION MODE"
            assert stage.action == old_action, f"{level} must not be able to change Action, even in SIMULATION MODE"
            assert _denied(audit, "Protection Settings"), audit.entries


def test_system_mode_tag_registered_and_wiring_fires():
    # Bug fix (Task: "System.Mode nie jest zarejestrowany"): "warunek w
    # page_protection.py oparty na System.Mode dziala poprawnie" -
    # end-to-end, against the REAL (headless) TagManager/EventBus, not
    # MockTagManager (which never actually fires tag_changed for
    # anything) - proves the wiring PageProtectionElectrical.on_tag_changed()
    # has always had for "System.Mode" now actually receives real events,
    # where before this fix update_tag("System.Mode", ...) always raised
    # before ever reaching event_bus.emit("tag_changed", ...), so this
    # signal EMISSION never once happened in this program's history.
    from epw_os.core.events import EventBus
    from epw_os.core.tag_manager import TagManager as RealTagManager
    from epw_os.gui.pages.page_protection_electrical import PageProtectionElectrical
    from gui_smoke._mocks import QtTagManagerBridge

    mode_bus = EventBus()
    real_tm = RealTagManager(mode_bus)
    real_tm.event_bus = mode_bus  # exposed for the bridge below
    bridge_tm = QtTagManagerBridge(real_tm)

    assert real_tm.get_value("System.Mode") == "SIMULATION MODE", \
        "System.Mode must be readable immediately after TagManager() construction, before any mode change"

    mode_access = MockControllableAccessManager()
    page_mode = PageProtectionElectrical(bridge_tm, mode_access)
    update_mode_calls = []
    orig_update_mode = page_mode.update_mode
    page_mode.update_mode = lambda *a: (update_mode_calls.append(a), orig_update_mode(*a))[-1]

    real_tm.set_mode("LIVE MODE")  # must not raise (the bug) and must reach the tag
    assert real_tm.get_value("System.Mode") == "LIVE MODE"
    assert len(update_mode_calls) >= 1, \
        "PageProtectionElectrical.on_tag_changed()'s System.Mode branch did not fire - the tag_changed " \
        "signal for System.Mode never reached it"

    # The condition itself (is_engineer, from access_manager - not from
    # the tag's VALUE, which update_mode() no longer reads at all) still
    # runs cleanly at both access levels post-fix, with no error either
    # way.
    mode_access.level = "User"
    page_mode.update_mode()
    mode_access.level = "Engineer"
    page_mode.update_mode()
    page_mode.deleteLater()


def test_alarms_acknowledge_matrix(make_window):
    # (matrix: Operator+ - already partly gated before an earlier task;
    # this confirms the denial dialog + audit record were added)
    class _MockAlarmManager:
        def get_all_alarms(self): return []
        def get_active_alarms(self): return []
        def acknowledge_alarm(self, alarm_id, user=""): pass

    for level, allowed in (("User", False), ("Operator", True), ("Engineer", True)):
        access, audit = _access_at(level), MockAuditLogger()
        w = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(),
                         audit, None, _MockAlarmManager())
        # A real AlarmManager would no-op on an unknown id too, so this
        # exercises exactly the access-check prefix without needing a
        # real alarm to acknowledge.
        w.page_alarms._acknowledge("nonexistent-alarm-id")
        if not allowed:
            assert _denied(audit, "Acknowledge alarm"), audit.entries
        else:
            assert not _denied(audit)


def test_engineer_mode_audit_log_bus_diagnostics_nav_matrix(make_window):
    # main_window.py: Engineer Mode / Audit Log nav - NO PIN prompt on
    # denial (Task: the operator raises their own level via the top-bar
    # dropdown, never prompted on demand).
    for level, allowed in (("User", False), ("Operator", False), ("Engineer", True)):
        access, audit = _access_at(level), MockAuditLogger()
        w = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(), audit)
        w._navigate_to("engineer_mode")
        if allowed:
            assert w.stacked_widget.currentIndex() == w._page_index["engineer_mode"], \
                "Engineer must actually navigate to Engineer Mode"
            assert not _denied(audit)
        else:
            assert w.stacked_widget.currentIndex() != w._page_index["engineer_mode"]
            assert _denied(audit, "Engineer Mode"), audit.entries

        audit.entries.clear()
        w._navigate_to("audit_log")
        if allowed:
            assert w.stacked_widget.currentIndex() == w._page_index["audit_log"]
            assert not _denied(audit)
        else:
            assert w.stacked_widget.currentIndex() != w._page_index["audit_log"]
            assert _denied(audit, "Audit Log"), audit.entries

        audit.entries.clear()
        w._navigate_to("bus_diagnostics")
        if allowed:
            assert w.stacked_widget.currentIndex() == w._page_index["bus_diagnostics"]
            assert not _denied(audit)
        else:
            assert w.stacked_widget.currentIndex() != w._page_index["bus_diagnostics"]
            assert _denied(audit, "Bus Diagnostics"), audit.entries


def test_language_screen_sleep_available_to_every_level(make_window):
    # Language / Screen Sleep stay available to every level, unchanged by
    # the permission-matrix task - a plain User (always denied by
    # MockAccessManager) must still be able to open both.
    from gui_smoke._mocks import MockAccessManager

    origs = _stub_dialog_execs()
    try:
        w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
        w._open_language_dialog()
        w._open_screen_sleep_dialog()
    finally:
        _unstub_dialog_execs(origs)


def test_language_switch_callback_fires_only_on_a_real_change(make_window, qapp):
    # Task: switch language without restarting the kiosk -
    # _open_language_dialog() must invoke the language_changed_callback
    # exactly once when the saved language actually changed, and never
    # when it didn't (dialog cancelled, or the same language re-picked).
    from gui_smoke._mocks import MockAccessManager
    import epw_os.gui.main_window as mw_module

    class _FakeLanguageDialogChanges:
        def __init__(self, project_manager, parent=None):
            self._pm = project_manager
        def exec(self):
            self._pm.set_language("pl" if self._pm.get_language() != "pl" else "en")
            return 1

    class _FakeLanguageDialogNoChange:
        def __init__(self, project_manager, parent=None):
            pass
        def exec(self):
            return 0  # Cancel - project_manager untouched

    orig_language_dialog = mw_module.LanguageDialog
    try:
        calls = []
        pm = MockProjectManager()
        w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), pm,
                         language_changed_callback=lambda: calls.append(1))

        mw_module.LanguageDialog = _FakeLanguageDialogChanges
        w._open_language_dialog()
        qapp.processEvents()  # flush the QTimer.singleShot(0, ...) deferral
        assert calls == [1], "callback must fire once when the language actually changed"

        mw_module.LanguageDialog = _FakeLanguageDialogNoChange
        w._open_language_dialog()
        qapp.processEvents()
        assert calls == [1], "callback must NOT fire again when the language didn't change"
    finally:
        mw_module.LanguageDialog = orig_language_dialog
