from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QLineEdit
from PySide6.QtCore import Qt

from epw_os.gui.theme_manager import error_text_style
from epw_os.i18n import tr


def _level_name(level):
    return tr(f"access.{str(level).lower()}", default=str(level))


class PinPromptPopup(QDialog):
    """Asks for the PIN of `target_level` and validates it directly against
    AccessManager - Accept means the caller is now actually logged in at
    that level (attempt_login() already ran and succeeded), not just that
    a PIN was typed. A wrong PIN shows an inline error and lets the
    operator retry without the dialog closing; Cancel rejects outright."""
    def __init__(self, access_manager, target_level, parent=None):
        super().__init__(parent)
        self.access_manager = access_manager
        self.target_level = target_level
        # Was Qt.WindowType.Popup - the actual, confirmed-by-reasoning
        # cause of "clicking the on-screen keyboard closes this dialog"
        # (see SESSION_REPORT.md): a Popup window auto-closes on a mouse
        # press outside its own geometry (the same built-in behavior a
        # QMenu/QComboBox dropdown uses to dismiss itself) - completely
        # independent of any focus-policy setting, which is why the
        # previous session's WA_ShowWithoutActivating/NoFocus fix had no
        # effect. The on-screen keyboard is a separate top-level window,
        # so every click on it was, to this Popup, "a click outside my
        # geometry". A plain Dialog has no such behavior - .exec() gives
        # it standard Qt::ApplicationModal modality instead, which (unlike
        # Popup) does not auto-close on unrelated clicks - and does not
        # block the keyboard's own Tool-type window from receiving clicks
        # either, confirmed directly (see SESSION_REPORT.md).
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("IndustrialDialog")

        layout = QVBoxLayout(self)

        title = QLabel(tr("pin_prompt.title", level=_level_name(target_level).upper()))
        title.setObjectName("SectionHeader")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addWidget(QLabel(tr("pin_prompt.prompt", level=_level_name(target_level))))

        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_edit.setMaxLength(8)
        layout.addWidget(self.pin_edit)

        # Follow-up to the fix above: switching to Dialog stopped this
        # popup from closing itself, but exposed a DEEPER, confirmed-on-
        # real-hardware problem - Qt::ApplicationModal (what .exec() gives
        # this Dialog) blocks input delivery to every top-level window
        # OUTSIDE this dialog's own hierarchy, and the floating on-screen
        # keyboard is exactly such a window: clicking its digits stopped
        # reaching this field entirely. Two attempts at patching that
        # cross-window communication failed. The fix is architectural,
        # not another patch: embed the keypad as a plain child widget
        # right here, so there is no separate window - and therefore no
        # cross-window delivery - to fail in the first place.
        #
        # Always built, regardless of the Settings "On-Screen Keyboard"
        # toggle (unlike the first version of this fix): on the target
        # touchscreen device (no physical keyboard), turning that toggle
        # off would cut the ONLY way to type a PIN at all - including the
        # PIN needed to reach Settings and turn it back on, a permanent
        # lockout at User level. A physical keyboard, where attached,
        # still works fully in parallel - this keypad only ever adds an
        # input method, never removes one. The Settings toggle keeps
        # controlling the separate FLOATING keyboard for every other
        # field (DI/DO descriptions, analog points) exactly as before.
        from epw_os.gui.widgets.onscreen_keyboard import EmbeddedNumericKeypad, mark_embedded_keypad_field
        mark_embedded_keypad_field(self.pin_edit)  # stop the floating keyboard from ALSO attaching here
        self._keypad = EmbeddedNumericKeypad(self)
        self._keypad.attach(self.pin_edit)
        layout.addWidget(self._keypad)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(error_text_style("font-weight: bold;"))
        layout.addWidget(self.lbl_error)

        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton(tr("pin_prompt.cancel"))
        self.btn_ok = QPushButton(tr("pin_prompt.unlock"))
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._try_unlock)
        self.pin_edit.returnPressed.connect(self._try_unlock)
        self.pin_edit.setFocus()

    def _try_unlock(self):
        pin = self.pin_edit.text()
        if self.access_manager.attempt_login(self.target_level, pin):
            self.accept()
        else:
            self.lbl_error.setText(tr("pin_prompt.incorrect"))
            self.pin_edit.clear()
            self.pin_edit.setFocus()


class AccessTimeoutPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("IndustrialDialog")

        layout = QVBoxLayout(self)

        title = QLabel(tr("timeout_popup.title"))
        title.setObjectName("SectionHeader")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        msg = QLabel(tr("timeout_popup.message"))
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)

        btn = QPushButton(tr("timeout_popup.ok"))
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
