"""Visual themes (Task: "przelaczane motywy wizualne"): switching,
persistence across a restart, tag-driven control from logic, and the
Automatyczny/Staly work-mode gate.

Split out of the old test_gui_smoke.py (refactor/test-suite-split task):
kept as its own file/axis, distinct from "translations", since these
checks are about color palettes and the day/night work mode, not
language.
"""
from PySide6.QtCore import QTime

from gui_smoke._mocks import (
    MockAccessManager, MockAuditLogger, MockCommandManager, MockControllableAccessManager,
    MockProjectManager, ThemeCapableTagManager,
)


def test_default_theme_is_industrial_and_tag_seeded_to_match(make_window):
    from epw_os.gui import window_state as theme_window_state
    from epw_os.gui.theme_manager import reset_theme_manager_for_tests

    reset_theme_manager_for_tests()
    tag_mgr = ThemeCapableTagManager()
    w = make_window(tag_mgr, MockCommandManager(), MockAccessManager(), MockProjectManager())

    assert w.theme_manager.current_index() == 0, "Industrial (index 0) must be the default"
    assert tag_mgr.get_value("System.Theme") == 0, \
        "the tag must be seeded to match the active theme as soon as MainWindow binds it"
    reset_theme_manager_for_tests()


def test_theme_switch_changes_colors_live_no_restart(make_window):
    from epw_os.core import themes
    from epw_os.gui.style import build_stylesheet
    from epw_os.gui.theme_manager import reset_theme_manager_for_tests
    from epw_os.gui.widgets.settings_popups import ThemeDialog

    reset_theme_manager_for_tests()
    tag_mgr = ThemeCapableTagManager()
    w = make_window(tag_mgr, MockCommandManager(), MockAccessManager(), MockProjectManager())

    before_style = w.styleSheet()
    w.theme_manager.apply_index(1)  # Night - the menu-equivalent call (ThemeDialog._apply() does the same)
    after_style = w.styleSheet()
    assert after_style != before_style
    assert after_style == build_stylesheet(themes.get_theme(1)["colors"])

    # DOWÓD: a menu-driven change is visible in the tag, and vice versa.
    assert tag_mgr.get_value("System.Theme") == 1, "a menu-driven change must push to the System.Theme tag"
    dlg = ThemeDialog(w.theme_manager, w)
    assert dlg.combo_theme.currentData() == 1, "the dialog must open pre-selected to the theme actually active"
    dlg.deleteLater()
    reset_theme_manager_for_tests()


def test_tag_write_switches_theme_control_from_logic(make_window):
    # Task 4: "sterowanie motywem z logiki" - a tag write must switch the
    # theme end-to-end, not just be asserted against ThemeManager
    # directly. A tag write is also not gated by access level at all
    # (GRANICE: "zmiana motywu przez tag nie moze wymagac uprawnien") -
    # MockAccessManager denies everything (has_access() always False) and
    # the write still takes effect, since ThemeManager never consults
    # access_manager.
    from epw_os.core import themes
    from epw_os.gui.style import build_stylesheet
    from epw_os.gui.theme_manager import reset_theme_manager_for_tests

    reset_theme_manager_for_tests()
    tag_mgr = ThemeCapableTagManager()
    w = make_window(tag_mgr, MockCommandManager(), MockAccessManager(), MockProjectManager())

    tag_mgr.update_tag("System.Theme", 3)  # Cyberpunk, simulating a write from logic
    assert w.theme_manager.current_index() == 3
    assert w.styleSheet() == build_stylesheet(themes.get_theme(3)["colors"])

    # DOWÓD: an invalid/out-of-range tag write is ignored - never crashes,
    # never applies, the previous theme stays active.
    tag_mgr.update_tag("System.Theme", 99)
    assert w.theme_manager.current_index() == 3, "an out-of-range write must be ignored, not applied"
    reset_theme_manager_for_tests()


def test_every_theme_has_distinguishable_state_colors():
    # DOWÓD: in every one of the five themes, the state colors (OK/
    # warning/alarm/...) are distinguishable from each other and from
    # the background - re-checked here (through the real palette data)
    # in addition to epw_os/tests/test_themes.py's headless version.
    from epw_os.core import themes

    for idx in range(themes.theme_count()):
        ok, problems = themes.state_color_report(themes.get_theme(idx)["colors"])
        assert ok, (themes.get_theme(idx)["id"], problems)


def test_theme_choice_survives_a_restart(make_window):
    # DOWÓD: the chosen theme survives a restart. No in-memory cache
    # exists outside window_state.py's file - a fresh load_theme_index()
    # call already IS "as if the app restarted", and a brand-new
    # MainWindow restoring it end-to-end is the stronger, additional
    # proof.
    from epw_os.gui import window_state as theme_window_state
    from epw_os.gui.theme_manager import reset_theme_manager_for_tests
    from gui_smoke._mocks import MockTagManager

    reset_theme_manager_for_tests()
    tag_mgr = ThemeCapableTagManager()
    w = make_window(tag_mgr, MockCommandManager(), MockAccessManager(), MockProjectManager())
    w.theme_manager.apply_index(3)
    assert theme_window_state.load_theme_index() == 3
    w.shutdown_gui()
    reset_theme_manager_for_tests()

    w2 = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    assert w2.theme_manager.current_index() == 3, "a fresh MainWindow must restore the last-saved theme"
    w2.shutdown_gui()
    reset_theme_manager_for_tests()


def test_work_mode_change_is_engineer_gated_and_audited(make_window):
    # Task 4 (page-split branch): work-mode change (Staly <-> Automatyczny)
    # is Engineer-gated and reaches the audit log, while a plain theme
    # pick while STAYING in Staly is not (already proven above via
    # MockAccessManager, which denies everything and yet the plain pick
    # still took effect through apply_index()).
    from epw_os.gui import theme_manager as theme_manager_mod
    from epw_os.gui.theme_manager import reset_theme_manager_for_tests
    from epw_os.gui.widgets.engineer_popups import PinPromptPopup
    from epw_os.gui.widgets.settings_popups import ThemeDialog

    reset_theme_manager_for_tests()
    mode_access = MockControllableAccessManager()  # starts at "User"
    mode_audit = MockAuditLogger()
    mode_tag_mgr = ThemeCapableTagManager()
    w = make_window(mode_tag_mgr, MockCommandManager(), mode_access, MockProjectManager(),
                     audit_logger=mode_audit)

    # request_access() below Engineer opens a REAL PinPromptPopup - stub
    # .exec() itself rather than let a real modal loop run (there's
    # nothing to click in an offscreen test), simulating a wrong/
    # dismissed PIN (Rejected).
    dlg_denied = ThemeDialog(w.theme_manager, w)
    idx = dlg_denied.combo_mode.findData(theme_manager_mod.THEME_MODE_AUTO)
    dlg_denied.combo_mode.setCurrentIndex(idx)
    orig_pin_exec = PinPromptPopup.exec

    def _denied_pin_exec(self):
        self.pin_edit.setText("0000")
        self._try_unlock()
        return 0  # QDialog.DialogCode.Rejected

    PinPromptPopup.exec = _denied_pin_exec
    try:
        dlg_denied._try_apply()
    finally:
        PinPromptPopup.exec = orig_pin_exec
    assert w.theme_manager.get_mode() == "constant", \
        "switching to Automatyczny must be refused below Engineer level"
    assert not any(e[0] == "THEME_MODE_CHANGE" for e in mode_audit.entries)
    dlg_denied.deleteLater()

    mode_access.level = "Engineer"
    dlg_allowed = ThemeDialog(w.theme_manager, w)
    idx = dlg_allowed.combo_mode.findData(theme_manager_mod.THEME_MODE_AUTO)
    dlg_allowed.combo_mode.setCurrentIndex(idx)
    dlg_allowed.edit_day_start.setTime(QTime(0, 0))
    dlg_allowed.edit_night_start.setTime(QTime(23, 59))  # covers "now" -> day theme applies
    dlg_allowed._try_apply()
    assert w.theme_manager.get_mode() == "auto", "Engineer must be able to switch to Automatyczny"
    assert w.theme_manager.current_index() == w.theme_manager.get_day_index()
    assert any(e[0] == "THEME_MODE_CHANGE" and e[1] == "Engineer" for e in mode_audit.entries), \
        "the mode change must reach the audit log"
    dlg_allowed.deleteLater()

    # Logic override note (Task: "Pokaz w Ustawieniach, gdy motyw jest
    # narzucony przez logike") - a genuine external tag write, exactly
    # like the "control from logic" test above.
    mode_tag_mgr.update_tag("System.Theme", 2)
    assert w.theme_manager.is_logic_override_active() is True
    dlg_override = ThemeDialog(w.theme_manager, w)  # constructs without error with the note shown
    dlg_override.deleteLater()

    w.theme_manager.set_mode("constant", constant_index=0)
    reset_theme_manager_for_tests()
