"""Permission-gated features that carry their own persistent state:
mechanical-wear switching counters, Training Mode, service history
notes, and Analog Inputs Add/Edit/Remove. Split out of the same original
"Part 2 of the follow-up task: real, enforced per-level permissions"
block as test_permissions_core.py - kept separate so neither file grows
back into one 680-line block (refactor/test-suite-split task).
"""
import re
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QPushButton, QTableWidget

from gui_smoke._mocks import (
    DICapableTagManager, MockAccessManager, MockAuditLogger, MockCommandManager, MockControllableAccessManager,
    MockProjectManager, MockTagManager,
)


def _access_at(level):
    am = MockControllableAccessManager()
    if level != "User":
        assert am.attempt_login(level, MockControllableAccessManager.CORRECT_PIN)
    return am


def _denied(audit, needle=None):
    return any(e[0] == "ACCESS_DENIED" and (needle is None or needle in e[2]) for e in audit.entries)


# --- Switching (mechanical wear) counters (Task: liczba przelaczen i
# czas w stanie zamknietym per aparat) -------------------------------

def test_switching_counter_increments_and_shown_in_di_table(make_window):
    from epw_os.core.events import EventBus
    from epw_os.core.switching_counters import SwitchingCounterManager

    sw_bus = EventBus()
    sw_pm = MockProjectManager()
    sw_mgr = SwitchingCounterManager(sw_bus, sw_pm)
    sw_tm = DICapableTagManager(sw_bus)
    sw_audit = MockAuditLogger()
    w = make_window(sw_tm, MockCommandManager(), MockControllableAccessManager(), sw_pm,
                     sw_audit, switching_counters=sw_mgr)

    # DOWÓD: the counter increases on a state change and is reflected in
    # the Digital Inputs table (Closes=6, Opens=7, Closed Time=8).
    sw_tm.update_tag("DI1", False)  # seed - not counted (no previous state)
    sw_tm.update_tag("DI1", True)   # -> 1 close
    assert w.page_di.table.item(0, 6).text() == "1", w.page_di.table.item(0, 6).text()
    assert w.page_di.table.item(0, 7).text() == "0"
    time.sleep(0.15)
    sw_tm.update_tag("DI1", False)  # -> 1 open, closed_seconds >= 0.15
    assert w.page_di.table.item(0, 6).text() == "1"
    assert w.page_di.table.item(0, 7).text() == "1"

    # DOWÓD: closed time is counted correctly. format_duration() only
    # shows whole-second resolution, so the table cell legitimately still
    # reads "00:00:00" for a 0.15s interval - the precise programmatic
    # value (a float, seconds) is the real proof here.
    closed_seconds = sw_mgr.get_snapshot("DI1")["closed_seconds"]
    assert closed_seconds >= 0.15, closed_seconds
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", w.page_di.table.item(0, 8).text())

    # Also shown in Main View's device window for the 4 tracked devices
    # (DI1-4, see page_entry_gate.py's device_map/counter_tag).
    from epw_os.gui.widgets.popups import DeviceControlPopup, DevicePropertiesPopup
    from epw_os.i18n import tr

    assert w.page_entry_gate.q1.counter_tag == "DI1"
    popup = DeviceControlPopup(w.page_entry_gate.q1, w.page_entry_gate, switching_counters=sw_mgr)
    from PySide6.QtWidgets import QLabel
    popup_labels = " | ".join(l.text() for l in popup.findChildren(QLabel))
    assert "1" in popup_labels and "0" in popup_labels, popup_labels  # 1 close, 0 opens so far
    popup.deleteLater()

    props = DevicePropertiesPopup(w.page_entry_gate.q1, w.page_entry_gate, switching_counters=sw_mgr)
    props_labels = " | ".join(l.text() for l in props.findChildren(QLabel))
    assert tr("pages.popups.lbl_switching_closes") in props_labels, props_labels
    props.deleteLater()

    # DOWÓD: the counter survives a restart - flush, then a fresh manager
    # (new EventBus, same persisted project store) restores it.
    sw_mgr.flush_to_project()
    assert sw_pm.config.get("switching_counters", {}).get("DI1", {}).get("closes") == 1
    sw_mgr2 = SwitchingCounterManager(EventBus(), sw_pm)
    restored = sw_mgr2.get_snapshot("DI1")
    assert restored["closes"] == 1
    assert restored["opens"] == 1
    assert restored["closed_seconds"] >= 0.15


def test_switching_counter_no_disk_write_on_every_state_change(make_window):
    # GRANICE: no disk write happened on any of the individual state
    # changes - only flush_to_project() actually touches project_manager.
    from epw_os.core.events import EventBus
    from epw_os.core.switching_counters import SwitchingCounterManager

    sw_pm2 = MockProjectManager()
    sw_bus3 = EventBus()
    SwitchingCounterManager(sw_bus3, sw_pm2)
    sw_tm3 = DICapableTagManager(sw_bus3)
    for _ in range(5):
        sw_tm3.update_tag("DI1", True)
        sw_tm3.update_tag("DI1", False)
    assert "switching_counters" not in sw_pm2.config, \
        "GRANICE: must not write to disk on every state change, only periodically/on flush"


def test_switching_counter_manual_reset_engineer_only_audited(make_window):
    from epw_os.core.events import EventBus
    from epw_os.core.switching_counters import SwitchingCounterManager

    sw_bus = EventBus()
    sw_pm = MockProjectManager()
    sw_mgr = SwitchingCounterManager(sw_bus, sw_pm)
    sw_tm = DICapableTagManager(sw_bus)
    sw_audit = MockAuditLogger()
    w = make_window(sw_tm, MockCommandManager(), MockControllableAccessManager(), sw_pm,
                     sw_audit, switching_counters=sw_mgr)
    sw_tm.update_tag("DI1", True)  # 1 close, so the reset below has something to zero

    orig_qmb_question = QMessageBox.question
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    try:
        # Denied for User/Operator - never reaches QMessageBox.question at all.
        for level in ("User", "Operator"):
            reset_access, reset_audit = _access_at(level), MockAuditLogger()
            w_reset = make_window(DICapableTagManager(EventBus()), MockCommandManager(),
                                   reset_access, MockProjectManager(), reset_audit,
                                   switching_counters=SwitchingCounterManager(EventBus(), MockProjectManager()))
            w_reset.page_di._reset_counter("DI1")
            assert _denied(reset_audit, "Reset switching counter"), reset_audit.entries

        # Allowed for Engineer, and lands in the audit log specifically
        # (not just the operational Event Recorder) - COUNTER_RESET, not
        # the generic SETTING_CHANGE type.
        assert w.access_manager.attempt_login("Engineer", MockControllableAccessManager.CORRECT_PIN)
        w.page_di._reset_counter("DI1")
        assert any(e[0] == "COUNTER_RESET" and e[1] == "Engineer" and "DI1" in e[2] for e in sw_audit.entries), \
            sw_audit.entries
        assert sw_mgr.get_snapshot("DI1")["closes"] == 0, "reset must actually zero the counter"
    finally:
        QMessageBox.question = orig_qmb_question


# --- Training Mode (Task: tryb cwiczebny) -------------------------------

def test_training_mode_settings_entry_engineer_only(make_window):
    from epw_os.core.training_mode import TrainingModeManager

    for level, visible in (("User", False), ("Operator", False), ("Engineer", True)):
        tr_access = _access_at(level)
        w = make_window(MockTagManager(), MockCommandManager(), tr_access,
                         MockProjectManager(), MockAuditLogger(),
                         training_mode=TrainingModeManager(event_bus=None, audit_logger=MockAuditLogger()))
        assert w._act_training_mode.isVisible() is visible, level
        assert w._act_training_mode.isEnabled() is visible, level


def test_training_mode_indicator_and_audit_on_toggle(make_window):
    # DOWÓD/Task 3+5: enabling as Engineer flips the indicator on (both
    # the status-bar label AND the workspace border - "niemozliwe do
    # przeoczenia") and reaches the audit log; disabling reverses both.
    from epw_os.core.training_mode import TrainingModeManager

    tr_audit = MockAuditLogger()
    tr_mgr = TrainingModeManager(event_bus=None, audit_logger=tr_audit)
    tr_access = _access_at("Engineer")
    w = make_window(MockTagManager(), MockCommandManager(), tr_access,
                     MockProjectManager(), tr_audit, training_mode=tr_mgr)

    assert w.lbl_sb_training.isHidden()
    assert w.stacked_widget.styleSheet() == ""

    w._act_training_mode.setChecked(True)
    assert tr_mgr.active is True
    assert not w.lbl_sb_training.isHidden()
    assert "border" in w.stacked_widget.styleSheet()
    assert any(e[0] == "TRAINING_MODE_ON" and e[1] == "Engineer" for e in tr_audit.entries), tr_audit.entries

    w._act_training_mode.setChecked(False)
    assert tr_mgr.active is False
    assert w.lbl_sb_training.isHidden()
    assert w.stacked_widget.styleSheet() == ""
    assert any(e[0] == "TRAINING_MODE_OFF" and e[1] == "Engineer" for e in tr_audit.entries), tr_audit.entries

    # DOWÓD/Task 1: re-checked at toggle time, not just menu-open time -
    # a level dropped after the menu opened (5-minute auto-logout) must
    # still deny the change and put the checkbox back, not trust the click.
    w.access_manager.demote("User")
    w._act_training_mode.setChecked(True)
    assert tr_mgr.active is False, "must not have been enabled by a User-level click"
    assert w._act_training_mode.isChecked() is False, "checkbox must revert, not stay checked"
    assert _denied(tr_audit, "Training Mode"), tr_audit.entries


def test_training_mode_does_not_survive_a_restart():
    # DOWÓD: a brand-new manager (the real EPWCore only ever constructs
    # one, at process startup) is always inactive regardless of anything
    # a previous instance did.
    from epw_os.core.training_mode import TrainingModeManager

    assert TrainingModeManager(event_bus=None, audit_logger=MockAuditLogger()).active is False


# --- Service history / notes (Task: historia serwisowa przypisana do
# aparatu) -----------------------------------------------------------

def test_service_notes_user_cannot_add(make_window):
    from epw_os.core.service_notes import ServiceNoteManager
    from epw_os.gui.widgets.service_notes_widget import ServiceNotesDialog

    notes_pm = MockProjectManager()
    notes_mgr = ServiceNoteManager(notes_pm)
    notes_access = MockControllableAccessManager()  # starts at User
    w = make_window(MockTagManager(), MockCommandManager(), notes_access, notes_pm,
                     MockAuditLogger(), service_notes=notes_mgr)

    # DOWÓD: User level cannot add an entry - denied both by the widget's
    # own Add control (disabled) AND by the manager itself if something
    # bypassed the widget entirely.
    assert notes_access.level == "User"
    dlg_user = ServiceNotesDialog("DI1", notes_mgr, notes_access, {"Tag": "DI1"}, w)
    assert not dlg_user.notes_widget.btn_add.isEnabled(), "User must not be able to add a note"
    assert not dlg_user.notes_widget.edit_text.isEnabled()
    assert notes_mgr.add_note("DI1", "Sneaky user note.", "User") is None, \
        "the manager itself must refuse a User-level add, not just the GUI"
    assert notes_mgr.get_notes("DI1") == []
    dlg_user.deleteLater()


def test_service_notes_entry_saves_and_survives_a_restart(make_window):
    from epw_os.core.service_notes import ServiceNoteManager
    from epw_os.gui.widgets.service_notes_widget import ServiceNotesDialog

    notes_pm = MockProjectManager()
    notes_mgr = ServiceNoteManager(notes_pm)
    notes_access = MockControllableAccessManager()
    w = make_window(MockTagManager(), MockCommandManager(), notes_access, notes_pm,
                     MockAuditLogger(), service_notes=notes_mgr)

    notes_access.attempt_login("Operator", MockControllableAccessManager.CORRECT_PIN)
    dlg_op = ServiceNotesDialog("DI1", notes_mgr, notes_access, {"Tag": "DI1"}, w)
    assert dlg_op.notes_widget.btn_add.isEnabled(), "Operator must be able to add a note"
    dlg_op.notes_widget.edit_text.setPlainText("Replaced contact set after visible pitting.")
    dlg_op.notes_widget._add_note()
    assert dlg_op.notes_widget.table.rowCount() == 1
    assert dlg_op.notes_widget.table.item(0, 2).text() == "Replaced contact set after visible pitting."
    assert dlg_op.notes_widget.table.item(0, 1).text() == "Operator"
    dlg_op.deleteLater()

    # "Restart" - a fresh manager against the same persisted store: there
    # is no in-memory cache outside project_manager's config, so a fresh
    # ServiceNoteManager(notes_pm) already IS "as if the app restarted".
    notes_mgr2 = ServiceNoteManager(notes_pm)
    restored = notes_mgr2.get_notes("DI1")
    assert len(restored) == 1
    assert restored[0]["text"] == "Replaced contact set after visible pitting."
    assert restored[0]["author_level"] == "Operator"

    # DOWÓD: no way to edit or delete an entry, at any level - structural
    # (the table itself never allows in-place editing) plus the manager's
    # own API surface (already proven exhaustively in
    # epw_os/tests/test_service_notes.py; re-affirmed here through the
    # actual widget a user would interact with).
    notes_access.attempt_login("Engineer", MockControllableAccessManager.CORRECT_PIN)
    dlg_eng = ServiceNotesDialog("DI1", notes_mgr2, notes_access, {"Tag": "DI1"}, w)
    assert dlg_eng.notes_widget.table.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers, \
        "the notes table must never allow in-place editing, even for Engineer"
    button_texts = [b.text().lower() for b in dlg_eng.notes_widget.findChildren(QPushButton)]
    assert not any("delete" in t or "remove" in t or "edit" in t for t in button_texts), button_texts
    dlg_eng.deleteLater()


def test_service_notes_content_never_translated(make_window):
    # GRANICE: note content is user data - never translated. Written in
    # Polish, must still read back byte-for-byte identical regardless of
    # the interface language.
    from epw_os.core.service_notes import ServiceNoteManager
    from epw_os.i18n import set_language

    notes_pm = MockProjectManager()
    notes_mgr = ServiceNoteManager(notes_pm)
    set_language("pl")
    try:
        notes_mgr.add_note("DI2", "Wymieniono styki – widoczne przypalenia.", "Engineer")
        assert notes_mgr.get_notes("DI2")[0]["text"] == "Wymieniono styki – widoczne przypalenia."
    finally:
        set_language("en")


# --- page_analog_inputs.py: Add/Remove/Edit point (matrix: Engineer
# only) -----------------------------------------------------------------

def test_analog_inputs_add_edit_remove_engineer_only(make_window):
    from epw_os.gui.pages.page_analog_inputs import AnalogChannelConfigDialog

    orig_exec = AnalogChannelConfigDialog.exec
    AnalogChannelConfigDialog.exec = lambda self: 1
    try:
        for level, allowed in (("User", False), ("Operator", False), ("Engineer", True)):
            access, audit = _access_at(level), MockAuditLogger()
            w = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(), audit)
            assert w.page_ai.btn_add.isEnabled() == allowed, (level, "Add button")
            assert w.page_ai.btn_remove.isEnabled() == allowed, (level, "Remove button")

            # DOWÓD: the Configure button, mirroring Control Outputs'
            # Force button, must be VISIBLE (not merely enabled/disabled)
            # only at Engineer - the container exists for every row
            # always, the button inside it does not.
            configure_container = w.page_ai.table.cellWidget(0, 6)
            assert configure_container is not None, "Configure button container must exist for every row"
            has_configure_button = configure_container.layout().count() > 0
            assert has_configure_button == allowed, (level, "Configure button visibility")

            # Description/Unit/Technical note inline editing - same
            # Engineer-only gate, both the visual flag and the real
            # execution-time save path (_on_item_edited()). Direct model
            # mutation is what the in-place editor committing would also
            # do.
            tag_for_row0 = w.page_ai._row_tags[0]
            for col, field in ((1, "description"), (3, "unit"), (5, "technical_note")):
                item = w.page_ai.table.item(0, col)
                assert bool(item.flags() & Qt.ItemFlag.ItemIsEditable) == allowed, \
                    (level, "column", col, "visual edit flag")
                item.setText("HACKED")
                point = next(p for p in w.tag_manager.get_analog_points() if p["tag"] == tag_for_row0)
                if allowed:
                    assert point.get(field) == "HACKED", (level, field)
                else:
                    assert point.get(field) != "HACKED", f"{level} must not be able to change {field}"
                    assert _denied(audit, "Analog Point"), audit.entries
                audit.entries.clear()

            before_count = len(w.tag_manager.get_analog_points())
            w.page_ai._add_point()  # AnalogChannelConfigDialog.exec() is stubbed
            # to accept directly (bypassing the real Ok/Cancel button flow), which
            # also bypasses _try_accept()'s own empty-Tag validation - so for the
            # allowed/Engineer case this really does add a point (with an empty
            # tag, a stub artifact, not a real scenario); what matters here is
            # only whether the ACCESS gate - not this dialog's own validation -
            # is what stopped User/Operator specifically.
            if allowed:
                assert not _denied(audit)
                assert len(w.tag_manager.get_analog_points()) == before_count + 1
            else:
                assert _denied(audit, "Add Analog Point"), audit.entries
                assert len(w.tag_manager.get_analog_points()) == before_count, \
                    "a denied level must never reach add_analog_point() at all"

            audit.entries.clear()
            w.page_ai._open_point_config(0, 1)
            if allowed:
                assert not _denied(audit)
            else:
                assert _denied(audit, "Edit Analog Point"), audit.entries
    finally:
        AnalogChannelConfigDialog.exec = orig_exec
