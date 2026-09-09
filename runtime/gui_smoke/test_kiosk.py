"""Kiosk Mode (frameless/fullscreen, Engineer-PIN-gated exit, F1 Help
still reachable, menu bar visibility tracking access level) and
Fullscreen Mode (the unrelated, unrestricted View menu/F11 convenience).

Split out of the old test_gui_smoke.py (refactor/test-suite-split task,
"work modes" axis).
"""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest

from epw_os.i18n import tr

from gui_smoke._mocks import (
    MockAccessManager, MockAuditLogger, MockCommandManager, MockControllableAccessManager, MockProjectManager,
    MockTagManager,
)


def test_kiosk_off_by_default_matches_every_other_window(make_window):
    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    assert w.kiosk is False
    assert not (w.windowFlags() & Qt.WindowType.FramelessWindowHint)
    assert w.close(), "non-kiosk close() must succeed exactly as before"


def _kiosk_window(make_window, access=None, audit=None):
    access = access or MockControllableAccessManager()
    audit = audit or MockAuditLogger()
    w = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(),
                     audit, None, None, None, kiosk=True)
    w.show()
    return w, access, audit


def test_kiosk_on_frameless_and_fullscreen(make_window, qapp):
    w, access, audit = _kiosk_window(make_window)
    qapp.processEvents()
    assert w.kiosk is True
    assert w.windowFlags() & Qt.WindowType.FramelessWindowHint, "kiosk window must be frameless"
    assert w.isFullScreen(), "kiosk window must be fullscreen"


def test_kiosk_f1_help_reachable_despite_hidden_menu_bar(make_window, qapp):
    # A QAction's shortcut only fires while one of its owning widgets is
    # visible - the fix registers this same action on the MainWindow
    # itself (always visible for the whole time Kiosk Mode is active),
    # not just on the (currently invisible) Help QMenu.
    w, access, audit = _kiosk_window(make_window)
    qapp.processEvents()
    assert not w.menuBar().isVisible(), "sanity: menu bar must be hidden at User level in Kiosk Mode"
    assert getattr(w, "_help_window", None) is None
    QTest.keyClick(w, Qt.Key.Key_F1)
    assert w._help_window is not None and w._help_window.isVisible(), \
        "F1 must open Help in Kiosk Mode even though the menu bar is hidden"
    assert w.isFullScreen() and (w.windowFlags() & Qt.WindowType.FramelessWindowHint), \
        "opening Help must not disturb Kiosk Mode's own window state"
    w._help_window.hide()


def test_kiosk_f11_esc_doubleclick_are_no_ops_at_user_level(make_window, qapp):
    # Kiosk Mode hard requirement: F11/Esc/double-click must all be
    # no-ops while Kiosk Mode is active - if any of them worked, they
    # would bypass the Engineer-PIN exit gate entirely. Checked three
    # independent ways, not just "the menu action is disabled" (that
    # alone wouldn't stop a raw key event or a direct call).
    w, access, audit = _kiosk_window(make_window)
    qapp.processEvents()

    assert not w._fullscreen_action.isEnabled(), "Fullscreen action must be disabled in Kiosk Mode"
    assert not w._fullscreen_action.isChecked()
    w._fullscreen_action.setEnabled(True)  # simulate a bypass attempt
    w._on_fullscreen_toggled(True)
    assert not w._fullscreen_action.isChecked(), \
        "toggling Fullscreen Mode must be rejected outright while self.kiosk is True"
    w._fullscreen_action.setEnabled(False)

    esc_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    w.keyPressEvent(esc_event)
    assert w.isFullScreen() and (w.windowFlags() & Qt.WindowType.FramelessWindowHint), \
        "Esc must not change Kiosk Mode's window state"

    dbl_event = QEvent(QEvent.Type.MouseButtonDblClick)
    w.eventFilter(w.stacked_widget, dbl_event)
    assert w.isFullScreen() and (w.windowFlags() & Qt.WindowType.FramelessWindowHint), \
        "Double-click in the work area must not change Kiosk Mode's window state"

    assert not w._act_kiosk.isVisible(), "Settings > Kiosk Mode entry must stay hidden once already in Kiosk Mode"
    assert not w.menuBar().isVisible(), "menu bar must stay hidden in Kiosk Mode below Engineer"


def test_kiosk_bug4_engineer_reveals_menu_bar_without_exiting_kiosk(make_window, qapp):
    # Bug 4: raising access to Engineer WHILE already in Kiosk Mode must
    # reveal the menu bar (for on-site service work) without leaving
    # Kiosk Mode itself, and the hard F11/Esc/double-click no-op
    # requirement must still hold even with the menu bar visible.
    w, access, audit = _kiosk_window(make_window)
    qapp.processEvents()

    access.attempt_login("Engineer", MockControllableAccessManager.CORRECT_PIN)
    assert w.kiosk is True, "entering Engineer must NOT exit Kiosk Mode"
    assert w.windowFlags() & Qt.WindowType.FramelessWindowHint, "still frameless after raising to Engineer"
    assert w.isFullScreen(), "still fullscreen after raising to Engineer"
    assert w.menuBar().isVisible(), "menu bar must appear once Engineer is reached in Kiosk Mode"
    assert w._act_kiosk.isVisible() and w._act_kiosk.isEnabled(), \
        "Settings > Kiosk Mode entry must become usable again at Engineer level, to allow exiting"
    assert w._act_kiosk.text() == tr("menu.settings_kiosk_mode_exit"), \
        "the entry must switch to its exit wording while already in Kiosk Mode"

    # Hard requirement, re-checked with the menu bar now visible and the
    # level at Engineer - a real regression here would be "the menu bar
    # being visible reactivates the shortcuts".
    assert not w._fullscreen_action.isEnabled(), "Fullscreen action must stay disabled even at Engineer in Kiosk Mode"
    w._fullscreen_action.setEnabled(True)  # simulate a bypass attempt
    w._on_fullscreen_toggled(True)
    assert not w._fullscreen_action.isChecked(), \
        "F11/Fullscreen Mode must still be rejected outright at Engineer level in Kiosk Mode"
    w._fullscreen_action.setEnabled(False)

    esc_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    w.keyPressEvent(esc_event)
    assert w.isFullScreen() and (w.windowFlags() & Qt.WindowType.FramelessWindowHint), \
        "Esc must still not change Kiosk Mode's window state at Engineer level"

    dbl_event = QEvent(QEvent.Type.MouseButtonDblClick)
    w.eventFilter(w.stacked_widget, dbl_event)
    assert w.isFullScreen() and (w.windowFlags() & Qt.WindowType.FramelessWindowHint), \
        "Double-click in the work area must still not change Kiosk Mode's window state at Engineer level"

    # Demoting back below Engineer must hide the menu bar again (manual
    # downgrade here; the 5-minute auto-logout uses the same
    # access_manager.demote()/logout() -> level_changed path, exercised
    # separately below via on_access_timeout()).
    access.demote("User")
    assert w.kiosk is True, "demoting must NOT exit Kiosk Mode"
    assert not w.menuBar().isVisible(), "menu bar must hide again once level drops below Engineer"
    assert not w._act_kiosk.isVisible(), "Settings > Kiosk Mode entry must hide again below Engineer"


def test_kiosk_auto_logout_hides_menu_bar(make_window, qapp):
    # Via the actual auto-logout code path (on_access_timeout() ->
    # access_manager.logout() -> demote() -> level_changed), not just a
    # direct demote() call, since that's what really fires after 5
    # minutes. on_access_timeout() itself opens a real
    # AccessTimeoutPopup(self).exec() - stubbed to accept(1) immediately
    # so this doesn't block forever under the offscreen platform.
    from epw_os.gui.widgets.engineer_popups import AccessTimeoutPopup

    w, access, audit = _kiosk_window(make_window)
    qapp.processEvents()
    access.attempt_login("Engineer", MockControllableAccessManager.CORRECT_PIN)
    assert w.menuBar().isVisible()

    orig_atp_exec = AccessTimeoutPopup.exec
    AccessTimeoutPopup.exec = lambda self: 1
    try:
        w.on_access_timeout()
    finally:
        AccessTimeoutPopup.exec = orig_atp_exec
    assert access.level == "User"
    assert not w.menuBar().isVisible(), \
        "the 5-minute auto-logout must hide the menu bar again, same as any other downgrade below Engineer"


def test_kiosk_screen_sleep_overlay_covers_fullscreen_window(make_window, qapp):
    w, access, audit = _kiosk_window(make_window)
    qapp.processEvents()
    w.enter_screen_sleep()
    qapp.processEvents()
    assert w.screen_sleep_overlay.isVisible()
    assert w.screen_sleep_overlay.geometry() == w.rect(), (w.screen_sleep_overlay.geometry(), w.rect())
    w.exit_screen_sleep()
    qapp.processEvents()
    assert not w.screen_sleep_overlay.isVisible()


def test_kiosk_auto_logout_timer_mechanism_unaffected(make_window, qapp):
    w, access, audit = _kiosk_window(make_window)
    qapp.processEvents()
    access.level = "Engineer"
    assert w.request_access("Engineer") is True
    assert w.access_timeout_timer.isActive(), "5-min auto-logout timer must still start in kiosk mode"


def test_kiosk_exit_denied_wrong_pin(make_window, qapp):
    # Drives the real PinPromptPopup -> AccessManager.attempt_login() path
    # (only popup.exec()'s blocking modal loop is stubbed out) rather
    # than calling attempt_login() directly, so this exercises exactly
    # what closeEvent() -> _kiosk_authorize_exit() -> request_access()
    # actually does.
    from epw_os.gui.widgets.engineer_popups import PinPromptPopup

    w, access, audit = _kiosk_window(make_window)
    qapp.processEvents()

    original_exec = PinPromptPopup.exec

    def _wrong_pin_exec(self):
        self.pin_edit.setText("0000")
        self._try_unlock()
        return 0  # QDialog.DialogCode.Rejected

    PinPromptPopup.exec = _wrong_pin_exec
    try:
        closed = w.close()
    finally:
        PinPromptPopup.exec = original_exec
    assert not closed, "wrong PIN must leave the kiosk window open"
    assert w.isVisible(), "kiosk window must still be open after a denied exit"
    assert access.level == "User", "a failed PIN attempt must not change the access level"
    assert audit.entries[-1][0] == "KIOSK_EXIT_DENIED", audit.entries
    assert audit.entries[-1][3] is False


def test_kiosk_exit_granted_correct_pin(make_window, qapp):
    from epw_os.gui.widgets.engineer_popups import PinPromptPopup

    w, access, audit = _kiosk_window(make_window)
    qapp.processEvents()

    def _correct_pin_exec(self):
        self.pin_edit.setText(MockControllableAccessManager.CORRECT_PIN)
        self._try_unlock()
        return 1  # QDialog.DialogCode.Accepted

    orig = PinPromptPopup.exec
    PinPromptPopup.exec = _correct_pin_exec
    try:
        closed = w.close()
    finally:
        PinPromptPopup.exec = orig
    assert closed, "correct Engineer PIN must close the kiosk window"
    assert audit.entries[-1][0] == "KIOSK_EXIT", audit.entries
    assert audit.entries[-1][3] is True


# --- Fullscreen Mode (View menu / F11) - convenience, not security -----
# available at every access level, no PIN, distinct from Kiosk Mode.

def test_fullscreen_mode_toggle_and_all_three_exits(make_window, qapp):
    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    assert not w.kiosk
    assert w._fullscreen_action.isEnabled() and not w._fullscreen_action.isChecked()

    w.show()
    qapp.processEvents()
    w._fullscreen_action.setChecked(True)  # same effect as the menu click or F11
    qapp.processEvents()
    assert w.isFullScreen()
    assert w.menuBar().isVisible(), "Fullscreen Mode must keep the menu bar visible (unlike Kiosk Mode)"
    assert w.statusBar().isVisible(), "Fullscreen Mode must keep the status bar visible"

    # Exit #1: the menu action / F11 again (same QAction).
    w._fullscreen_action.setChecked(False)
    qapp.processEvents()
    assert not w.isFullScreen()

    # Exit #2: Esc.
    w._fullscreen_action.setChecked(True)
    qapp.processEvents()
    esc_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    w.keyPressEvent(esc_event)
    qapp.processEvents()
    assert not w.isFullScreen() and not w._fullscreen_action.isChecked()

    # Exit #3: double-click anywhere in the work area.
    w._fullscreen_action.setChecked(True)
    qapp.processEvents()
    dbl_event = QEvent(QEvent.Type.MouseButtonDblClick)
    w.eventFilter(w.stacked_widget, dbl_event)
    assert not w._fullscreen_action.isChecked() and not w.isFullScreen()

    # A double-click OUTSIDE the work area (e.g. the nav panel) must NOT
    # exit - "obszar roboczy" is specifically the page content area.
    w._fullscreen_action.setChecked(True)
    qapp.processEvents()
    w.eventFilter(w.nav_tree, dbl_event)
    assert w._fullscreen_action.isChecked() and w.isFullScreen(), \
        "a double-click outside the work area (nav panel) must not exit Fullscreen Mode"
    w._fullscreen_action.setChecked(False)


def test_settings_kiosk_mode_entry_engineer_only_toggles_kiosk(make_window):
    settings_access = MockControllableAccessManager()
    w = make_window(MockTagManager(), MockCommandManager(), settings_access, MockProjectManager())
    assert not w._act_kiosk.isVisible() and not w._act_kiosk.isEnabled(), \
        "Kiosk Mode entry must be hidden+disabled below Engineer"
    settings_access.attempt_login("Engineer", MockControllableAccessManager.CORRECT_PIN)
    assert w._act_kiosk.isVisible() and w._act_kiosk.isEnabled(), \
        "Kiosk Mode entry must become visible+enabled once logged in as Engineer"
    assert w.kiosk is False
    w._on_kiosk_action_triggered()
    assert w.kiosk is True, "triggering the entry must actually enter Kiosk Mode"
    assert w.windowFlags() & Qt.WindowType.FramelessWindowHint
    # Bug 4: the caller here was already Engineer at the moment of
    # entering, so the menu bar must come up visible immediately, and the
    # entry stays usable, now as the exit action.
    assert w.menuBar().isVisible(), \
        "menu bar must be visible immediately when Kiosk Mode is entered while already Engineer"
    assert w._act_kiosk.isVisible() and w._act_kiosk.isEnabled(), \
        "the entry must stay usable once already in Kiosk Mode, at Engineer level, to allow exiting"
    assert w._act_kiosk.text() == tr("menu.settings_kiosk_mode_exit")

    # Bug 4: triggering the SAME entry again now exits Kiosk Mode. No PIN
    # dialog needs mocking here - request_access() inside
    # _kiosk_authorize_exit() doesn't prompt when already at the target
    # level, and this caller already is Engineer.
    w._on_kiosk_action_triggered()
    assert w.kiosk is False, "triggering the entry again (exit wording) must exit Kiosk Mode"
    assert not (w.windowFlags() & Qt.WindowType.FramelessWindowHint), \
        "frameless flag must be cleared on kiosk exit"
    assert w.menuBar().isVisible(), "menu bar must be (unconditionally) visible outside Kiosk Mode"
    assert w._act_kiosk.isVisible() and w._act_kiosk.isEnabled(), \
        "still Engineer, so the entry stays visible - now back to its normal 'enter' wording"
    assert w._act_kiosk.text() == tr("menu.settings_kiosk_mode")


def test_settings_kiosk_mode_denied_without_engineer_even_calling_handler_directly(make_window):
    # Defense in depth - re-verified at click time, not just gated by the
    # menu item being hidden.
    denied_access = MockControllableAccessManager()
    w = make_window(MockTagManager(), MockCommandManager(), denied_access, MockProjectManager())
    w._on_kiosk_action_triggered()
    assert w.kiosk is False, "Kiosk Mode must not be enterable without Engineer access"
