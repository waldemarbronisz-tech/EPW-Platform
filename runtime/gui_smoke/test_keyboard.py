"""The on-screen keyboard: default-off behavior, never-steal-focus
configuration, the embedded PIN/Change-PIN keypads (Bug 1's real root
cause - PinPromptPopup's window TYPE, not focus), field-type routing,
Polish diacritics via long-press, the floating window's drag/resize
floor/manual-close/persisted position, and the --kiosk default.

Split out of the old test_gui_smoke.py (refactor/test-suite-split task,
"keyboard and modal windows" axis) - by far the largest single section
in the original file (~650 lines), which is exactly why it gets its own
file rather than being folded into another axis.
"""
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QFocusEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QLineEdit, QPushButton, QWidget

from gui_smoke._mocks import (
    MockAccessManager, MockCommandManager, MockControllableAccessManager, MockProjectManager, MockTagManager,
)


def _focus_in(controller, obj):
    """Feeds the exact event type/shape OnScreenKeyboardController
    watches for straight into its eventFilter - deterministic, not
    dependent on whether the offscreen QPA platform actually delivers
    real focus events the same way a real display would."""
    controller.eventFilter(obj, QFocusEvent(QFocusEvent.Type.FocusIn))


def test_keyboard_off_by_default_focusing_a_field_shows_nothing(make_window):
    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    assert w.keyboard_enabled is False
    probe_field = QLineEdit()
    _focus_in(w._keyboard_controller, probe_field)
    assert not w._keyboard_controller._full.isVisible()
    assert not w._keyboard_controller._numeric.isVisible()


def test_keyboard_never_steals_focus_configuration(make_window):
    # An earlier task's Part 1 fix, kept in place though later shown NOT
    # to be the actual cause of Bug 1 (see the dedicated Bug 1 test below
    # for the real root cause and fix, PinPromptPopup's window TYPE).
    # Still a reasonable defensive measure on its own.
    #
    # IMPORTANT LIMITATION, stated plainly: this exact failure is a
    # real-window-manager focus/activation behavior. The offscreen QPA
    # platform this whole test suite runs under has no real window
    # manager to simulate that behavior at all, so this cannot be a true
    # behavioral reproduction here; it instead verifies the actual fix is
    # in place - the documented, standard Qt recipe for "a virtual
    # keyboard that never steals focus" (WA_ShowWithoutActivating +
    # WindowDoesNotAcceptFocus + NoFocus on every interactive child) - on
    # both keyboard windows. See SESSION_REPORT.md for the full reasoning.
    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    for kb in (w._keyboard_controller._numeric, w._keyboard_controller._full):
        assert kb.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating), \
            "keyboard window must never activate itself on show()"
        assert kb.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus, \
            "keyboard window must never accept focus"
        assert kb.focusPolicy() == Qt.FocusPolicy.NoFocus
        buttons = kb.findChildren(QPushButton)
        assert buttons, "expected at least one button to check"
        for btn in buttons:
            assert btn.focusPolicy() == Qt.FocusPolicy.NoFocus, \
                f"button {btn.text()!r} must not be able to take focus on click"


def test_keyboard_space_key_label_fits_at_minimum_width(make_window):
    # DOWÓD ("przy okazji" fix): the Space key's label used to get the
    # same tiny per-key square minimum every other key gets, sized for
    # one character - too narrow for "Space"/"Spacja". Can't literally
    # render pixels in this offscreen sandbox, but the fix IS the
    # button's own minimum width.
    from epw_os.i18n import tr

    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    full_kb = w._keyboard_controller._full
    space_btn = next(b for b in full_kb.findChildren(QPushButton) if b.text() == tr("keyboard.space"))
    assert space_btn.minimumWidth() >= space_btn.fontMetrics().horizontalAdvance(space_btn.text()), \
        "the Space key's minimum width must fit its own label at every keyboard size"


def _pin_dialog_check(qapp, keyboard_enabled):
    from PySide6.QtCore import QTimer
    from epw_os.gui.main_window import MainWindow
    from epw_os.gui.widgets.engineer_popups import PinPromptPopup

    win = MainWindow(MockTagManager(), MockCommandManager(), MockControllableAccessManager(),
                      MockProjectManager())
    try:
        win.keyboard_enabled = keyboard_enabled
        result = {}

        def _inspect_and_close():
            popups = [w for w in QApplication.topLevelWidgets()
                      if isinstance(w, PinPromptPopup) and w.parent() is win]
            assert popups, "PinPromptPopup was never constructed"
            p = popups[0]
            result["popup_visible"] = p.isVisible()
            result["field_visible"] = p.pin_edit.isVisible()
            result["ok_visible"] = p.btn_ok.isVisible()
            result["cancel_visible"] = p.btn_cancel.isVisible()
            # The embedded keypad is ALWAYS present, regardless of the
            # Settings on-screen-keyboard toggle - making it conditional
            # was a real lockout risk on a touchscreen-only device
            # (Orange Pi target, no physical keyboard).
            result["embedded_keypad_present"] = p._keypad is not None
            numeric = win._keyboard_controller._numeric
            result["floating_numeric_not_attached"] = not numeric.isVisible()
            btn_1 = next(b for b in p._keypad.findChildren(QPushButton) if b.text() == "1")
            btn_1.click()
            result["popup_visible_after_click"] = p.isVisible()
            result["pin_field_after_click"] = p.pin_edit.text()
            p.reject()

        QTimer.singleShot(50, _inspect_and_close)
        win.request_access("Engineer")
        return result
    finally:
        win.shutdown_gui()


def test_pin_dialog_embedded_keypad_present_with_keyboard_toggle_off(qapp):
    r_off = _pin_dialog_check(qapp, False)
    assert r_off["popup_visible"] and r_off["field_visible"] and r_off["ok_visible"] and r_off["cancel_visible"], r_off
    assert r_off["embedded_keypad_present"], \
        "the PIN dialog's embedded keypad must be present even when the on-screen keyboard Settings toggle " \
        "is OFF - a touchscreen-only device with the toggle off must still be able to type a PIN"
    assert r_off["popup_visible_after_click"], "clicking a keypad digit must not close the PIN dialog"
    assert r_off["pin_field_after_click"] == "1", r_off["pin_field_after_click"]


def test_pin_dialog_embedded_keypad_present_with_keyboard_toggle_on(qapp):
    r_on = _pin_dialog_check(qapp, True)
    assert r_on["popup_visible"] and r_on["field_visible"] and r_on["ok_visible"] and r_on["cancel_visible"], r_on
    assert r_on["embedded_keypad_present"], \
        "the embedded numeric keypad should appear inside the PIN dialog when the on-screen keyboard is ON too"
    assert r_on["floating_numeric_not_attached"], \
        "the separate floating keyboard must not ALSO attach to the PIN field now that it has its own embedded keypad"
    assert r_on["popup_visible_after_click"], "clicking a keypad digit must not close the PIN dialog"
    assert r_on["pin_field_after_click"] == "1", r_on["pin_field_after_click"]


def test_bug1_pin_prompt_popup_is_dialog_type_not_popup_type():
    # Bug 1's real mechanism: Qt.WindowType.Popup dismisses itself on ANY
    # mouse press outside its own geometry - the exact thing QMenu/
    # QComboBox use to close a dropdown - completely independent of focus
    # policy. The on-screen keyboard is a separate top-level window, so
    # every click on it was, to the popup, "a click outside my geometry".
    # Fixed by using Qt.WindowType.Dialog instead. .windowType() (not a
    # raw bitwise AND against windowFlags()) is the correct check here:
    # Qt::WindowType::Dialog and ::Popup both share the base Window bit,
    # so `flags & Qt.WindowType.Popup` would come back truthy for ANY
    # top-level window, Dialog included, and silently prove nothing.
    from epw_os.gui.widgets.engineer_popups import PinPromptPopup

    bug1_probe = PinPromptPopup(MockControllableAccessManager(), "Engineer")
    assert bug1_probe.windowType() == Qt.WindowType.Dialog, \
        f"PinPromptPopup must be a Dialog-type window (Bug 1 fix), got {bug1_probe.windowType()}"
    assert bug1_probe.windowType() != Qt.WindowType.Popup, \
        "PinPromptPopup must NOT be a Popup-type window anymore - Popup auto-dismisses on any " \
        "outside click, independent of focus policy, which was Bug 1's actual cause"
    bug1_probe.deleteLater()


def test_bug1_scope_other_text_entry_dialogs_already_safe():
    # "sprawdź też pozostałe okna, w których wpisuje się tekst":
    # PinPromptPopup was the ONLY class in the codebase combining
    # Qt.WindowType.Popup with a keyboard-reachable QLineEdit (confirmed
    # by grepping every dialog file for both). ChangePinDialog/
    # ScreenSleepDialog are plain Qt.WindowType.Dialog already
    # (HistorianExportDialog has no QLineEdit at all - not re-checked
    # here). AccessTimeoutPopup and every confirmation popup legitimately
    # stay Qt.WindowType.Popup - none of them contain a QLineEdit the
    # keyboard could ever attach to.
    from epw_os.gui.widgets.engineer_popups import AccessTimeoutPopup
    from epw_os.gui.widgets.settings_popups import ChangePinDialog, ScreenSleepDialog

    assert ChangePinDialog(MockControllableAccessManager()).windowType() != Qt.WindowType.Popup
    assert ScreenSleepDialog(300).windowType() != Qt.WindowType.Popup
    assert AccessTimeoutPopup().windowType() == Qt.WindowType.Popup, \
        "AccessTimeoutPopup has no QLineEdit - correctly untouched by the Bug 1 fix"


def _change_pin_dialog_check(w_default, keyboard_enabled):
    from PySide6.QtCore import QTimer
    from epw_os.gui.widgets.settings_popups import ChangePinDialog

    dlg = ChangePinDialog(MockControllableAccessManager())
    result = {}

    def _inspect_and_close():
        result["dialog_visible_before"] = dlg.isVisible()
        result["embedded_keypad_present"] = dlg.operator_section._keypad is not None
        w_default.keyboard_enabled = keyboard_enabled
        dlg.operator_section.edit_old.setFocus()
        QApplication.instance().processEvents()
        numeric = w_default._keyboard_controller._numeric
        result["floating_numeric_not_attached"] = not numeric.isVisible()

        btn_7 = next(b for b in dlg.operator_section._keypad.findChildren(QPushButton) if b.text() == "7")
        btn_7.click()
        result["dialog_visible_after_click"] = dlg.isVisible()
        result["old_field_after_click"] = dlg.operator_section.edit_old.text()

        # Switching focus to a DIFFERENT field in the same section must
        # retarget the one shared embedded keypad to it.
        dlg.operator_section.edit_new.setFocus()
        QApplication.instance().processEvents()
        btn_3 = next(b for b in dlg.operator_section._keypad.findChildren(QPushButton) if b.text() == "3")
        btn_3.click()
        result["new_field_after_click"] = dlg.operator_section.edit_new.text()
        result["old_field_unchanged_after_switch"] = dlg.operator_section.edit_old.text()
        dlg.reject()

    QTimer.singleShot(50, _inspect_and_close)
    dlg.exec()
    return result


def test_change_pin_dialog_embedded_keypad_retargets_toggle_off(make_window):
    w_default = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    r = _change_pin_dialog_check(w_default, False)
    assert r["dialog_visible_before"], r
    assert r["embedded_keypad_present"], \
        "Change PIN's embedded keypad must be present even when the on-screen keyboard Settings toggle is OFF"
    assert r["floating_numeric_not_attached"]
    assert r["dialog_visible_after_click"]
    assert r["old_field_after_click"] == "7", r["old_field_after_click"]
    assert r["new_field_after_click"] == "3", r["new_field_after_click"]
    assert r["old_field_unchanged_after_switch"] == "7"


def test_change_pin_dialog_embedded_keypad_retargets_toggle_on(make_window):
    w_default = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    r = _change_pin_dialog_check(w_default, True)
    assert r["dialog_visible_before"], r
    assert r["embedded_keypad_present"], \
        "Change PIN's password fields must get an embedded numeric keypad when the on-screen keyboard is ON too"
    assert r["floating_numeric_not_attached"], \
        "the separate floating keyboard must not ALSO attach to Change PIN's fields"
    assert r["dialog_visible_after_click"], \
        "clicking a keypad digit must not close the Change PIN dialog either"
    assert r["old_field_after_click"] == "7", r["old_field_after_click"]
    assert r["new_field_after_click"] == "3", r["new_field_after_click"]
    assert r["old_field_unchanged_after_switch"] == "7", \
        "switching focus to a different field must retarget the shared keypad, not keep typing into the old one"


def test_floating_keyboard_setting_off_leaves_di_do_description_alone(make_window):
    # DOWÓD: making the PIN keypad always-on must NOT have leaked into
    # the separate FLOATING keyboard's own toggle behavior for ordinary
    # fields elsewhere in the app - the Settings toggle still controls
    # that one exactly as before. A real DI/DO Description cell editor
    # (Engineer access, so the column is actually editable).
    do_access = MockControllableAccessManager()
    do_access.attempt_login("Engineer", MockControllableAccessManager.CORRECT_PIN)
    w = make_window(MockTagManager(), MockCommandManager(), do_access, MockProjectManager())
    w.keyboard_enabled = False
    desc_item = w.page_do.table.item(0, 2)
    assert bool(desc_item.flags() & Qt.ItemFlag.ItemIsEditable), "Engineer must be able to edit Description"
    w.page_do.table.editItem(desc_item)  # creates the real in-place QLineEdit editor
    desc_editor = next(iter(w.page_do.table.findChildren(QLineEdit)), None)
    assert desc_editor is not None, "expected a real cell editor to be created"
    w._keyboard_controller.eventFilter(desc_editor, QFocusEvent(QFocusEvent.Type.FocusIn))
    assert not w._keyboard_controller._full.isVisible(), \
        "the floating keyboard must NOT appear for DI/DO description fields when the Settings toggle is OFF"
    assert not w._keyboard_controller._numeric.isVisible()


def test_floating_keyboard_types_into_analog_inputs_description(make_window):
    # DOWÓD: Analog Inputs' Description column is now inline-editable
    # exactly like DI/DO's own Description column - same double-click/
    # EditKeyPressed triggers, same underlying mechanism - and, unlike
    # AnalogChannelConfigDialog (a modal QDialog the floating keyboard
    # can never reliably reach), a table cell editor belongs to the main
    # window, so the on-screen keyboard DOES reach it here.
    ai_kb_access = MockControllableAccessManager()
    ai_kb_access.attempt_login("Engineer", MockControllableAccessManager.CORRECT_PIN)
    w = make_window(MockTagManager(), MockCommandManager(), ai_kb_access, MockProjectManager())
    w.keyboard_enabled = True
    ai_desc_item = w.page_ai.table.item(0, 1)
    assert bool(ai_desc_item.flags() & Qt.ItemFlag.ItemIsEditable), \
        "Engineer must be able to edit Analog Inputs Description"
    w.page_ai.table.editItem(ai_desc_item)  # creates the real in-place QLineEdit editor
    ai_desc_editor = next(iter(w.page_ai.table.findChildren(QLineEdit)), None)
    assert ai_desc_editor is not None, "expected a real cell editor to be created"
    w._keyboard_controller.eventFilter(ai_desc_editor, QFocusEvent(QFocusEvent.Type.FocusIn))
    ai_full_kb = w._keyboard_controller._full
    assert ai_full_kb.isVisible(), "Analog Inputs Description must get the full QWERTY keyboard, same as DI/DO"
    ai_h_btn = next(b for b in ai_full_kb.findChildren(QPushButton) if b.text() == "h")
    ai_h_btn.click()
    assert ai_desc_editor.text() == "h", \
        "a real on-screen keyboard click must land a character in the Analog Inputs Description editor"


def test_keyboard_on_field_type_routing_and_typing(make_window):
    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    w._on_keyboard_toggled(True)
    assert w.keyboard_enabled is True

    plain_field = QLineEdit()
    _focus_in(w._keyboard_controller, plain_field)
    full_kb = w._keyboard_controller._full
    assert full_kb.isVisible(), "plain QLineEdit must get the full QWERTY keyboard"
    assert not w._keyboard_controller._numeric.isVisible()
    # Simulate tapping "h" on the full keyboard - a real click, not
    # poking the field's text directly.
    h_btn = next(b for b in full_kb.findChildren(QPushButton) if b.text() == "h")
    h_btn.click()
    assert plain_field.text() == "h", plain_field.text()
    full_kb.btn_ok.click()
    # OK no longer hides the keyboard - it stays open, ready for the next
    # field, only detaching from this one. Only a manual close (X /
    # Settings toggle) hides it.
    assert full_kb.isVisible(), "OK must NOT close the keyboard window (Part 2 requirement)"
    assert full_kb._target is None, "OK must still detach from the field it just confirmed"
    assert plain_field.text() == "h", "OK must keep the typed text"

    # Polish diacritics via long-press - drive the same
    # pressed->timer-fires->released sequence _KeyButton's own QTimer
    # would, without a real 450ms wall-clock wait.
    another_field = QLineEdit()
    _focus_in(w._keyboard_controller, another_field)
    a_btn = next(b for b in full_kb.findChildren(QPushButton) if getattr(b, "_base", None) == "a")
    a_btn._on_pressed(); a_btn._emit_alt(); a_btn._on_released()
    assert another_field.text() == "ą", another_field.text()
    z_btn = next(b for b in full_kb.findChildren(QPushButton) if getattr(b, "_base", None) == "z")
    z_btn._on_pressed(); z_btn._emit_alt(); z_btn._on_released()
    z_btn._on_pressed(); z_btn._emit_alt(); z_btn._on_released()
    assert another_field.text() == "ąźż", another_field.text()
    # A plain (short) press of the same key must still type the base
    # letter, not an accent - long-press is additive, not a takeover.
    a_btn._on_pressed(); a_btn._on_released()
    assert another_field.text() == "ąźża"
    full_kb.btn_cancel.click()
    assert another_field.text() == "", "Cancel must restore this field's original (empty) text"
    assert full_kb.isVisible(), "Cancel must NOT close the keyboard window (Part 2 requirement)"

    pin_field = QLineEdit()
    pin_field.setEchoMode(QLineEdit.EchoMode.Password)
    _focus_in(w._keyboard_controller, pin_field)
    assert w._keyboard_controller._numeric.isVisible(), \
        "a password-echo field (PIN) must always get the numeric keypad"
    num_kb = w._keyboard_controller._numeric
    num_kb._type("1"); num_kb._type("2")
    assert pin_field.text() == "12"
    num_kb._cancel()
    assert pin_field.text() == "", "Cancel must restore the field's original (empty) text"
    assert num_kb.isVisible(), "Cancel must NOT close the keyboard window (Part 2 requirement)"

    spin_field = QDoubleSpinBox()
    _focus_in(w._keyboard_controller, spin_field)
    assert num_kb.isVisible(), "a spin box must also get the numeric keypad"

    read_only_field = QLineEdit("locked")
    read_only_field.setReadOnly(True)
    num_kb.hide(); full_kb.hide()
    _focus_in(w._keyboard_controller, read_only_field)
    assert not num_kb.isVisible() and not full_kb.isVisible(), \
        "a read-only field (e.g. an existing Analog point's Tag) must be skipped entirely"


def test_floating_window_drag_resize_floor_persist_close(make_window, qapp):
    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    w._on_keyboard_toggled(True)
    plain_field = QLineEdit()
    _focus_in(w._keyboard_controller, plain_field)
    full_kb = w._keyboard_controller._full
    assert full_kb.isVisible()

    title_bar = full_kb.findChild(QWidget, "OnScreenKeyboardTitleBar")
    assert title_bar is not None, "keyboard must have its own draggable title bar"
    before_pos = full_kb.pos()
    # Simulate a drag: press on the title bar, move, release.
    press = QMouseEvent(QEvent.Type.MouseButtonPress, title_bar.rect().center(),
                         full_kb.pos() + title_bar.rect().center(),
                         Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    title_bar.mousePressEvent(press)
    moved_global = full_kb.pos() + title_bar.rect().center() + QPoint(40, 25)
    move = QMouseEvent(QEvent.Type.MouseMove, title_bar.rect().center(), moved_global,
                        Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    title_bar.mouseMoveEvent(move)
    assert full_kb.pos() == before_pos + QPoint(40, 25), (full_kb.pos(), before_pos)
    release = QMouseEvent(QEvent.Type.MouseButtonRelease, title_bar.rect().center(), moved_global,
                           Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    title_bar.mouseReleaseEvent(release)

    # Resize floor: a QSizeGrip drag ultimately just calls resize(),
    # which Qt itself clamps to minimumSize() - shrinking way below that
    # must still leave every key at least ~10mm, not a sliver nobody
    # could tap. Exercised on the full QWERTY board (10 columns - the
    # widest row, so the tightest fit).
    from epw_os.gui.widgets.onscreen_keyboard import _min_key_px

    full_kb.resize(10, 10)
    assert full_kb.width() >= full_kb.minimumWidth() and full_kb.height() >= full_kb.minimumHeight()
    smallest_letter_btn = next(b for b in full_kb.findChildren(QPushButton) if getattr(b, "_base", None) == "q")
    qapp.processEvents()
    assert smallest_letter_btn.width() >= _min_key_px() and smallest_letter_btn.height() >= _min_key_px(), \
        (smallest_letter_btn.width(), smallest_letter_btn.height(), _min_key_px())

    # Position + size remembered between runs - persisted immediately on
    # move/resize (not just at some later "close"), then read back by a
    # brand new controller instance the same way a fresh launch would.
    full_kb.resize(500, 300)
    full_kb.move(77, 88)
    from epw_os.gui.widgets.onscreen_keyboard import OnScreenKeyboardController

    fresh_controller = OnScreenKeyboardController(lambda: True)
    assert fresh_controller._full.size() == full_kb.size()
    assert fresh_controller._full.pos() == full_kb.pos()
    fresh_controller._numeric.hide(); fresh_controller._full.hide()

    # Manual close (title bar X) - the only two ways to make it go away
    # are this and the Settings toggle.
    close_btn = title_bar.findChildren(QPushButton)[0]
    close_btn.click()
    assert not full_kb.isVisible(), "title bar X must close the keyboard window"

    # Settings > On-Screen Keyboard OFF must close whatever keyboard
    # window happens to be open right now, not just stop reopening.
    pin_field = QLineEdit()
    pin_field.setEchoMode(QLineEdit.EchoMode.Password)
    _focus_in(w._keyboard_controller, pin_field)
    num_kb = w._keyboard_controller._numeric
    assert num_kb.isVisible()
    w._on_keyboard_toggled(False)
    assert not num_kb.isVisible() and not full_kb.isVisible(), \
        "turning the Settings toggle off must close any open keyboard window"


def test_kiosk_with_nothing_saved_defaults_keyboard_on(make_window):
    # --kiosk with nothing ever explicitly saved -> keyboard defaults to
    # enabled (still just a default - Settings can turn it back off).
    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager(), kiosk=True)
    assert w.keyboard_enabled is True, \
        "kiosk launch with no prior explicit choice must default the keyboard to ON"
