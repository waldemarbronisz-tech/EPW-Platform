"""Settings popups reachable from the top menu bar (Settings > ...).

Replaces the former full-page ``PageSettings`` view. Only the presentation
changes - the PIN-change flow keeps exactly the same security logic:
the *current* PIN must be entered here (not merely being logged in at that
level), and only the SHA-256 hash is ever persisted (AccessManager).
"""

from PySide6.QtCore import QEvent, QTime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QComboBox, QDialogButtonBox,
                             QCheckBox, QSpinBox, QTimeEdit)

from epw_os.core.access_manager import AccessLevel
from epw_os.core import themes
from epw_os.gui.logger import ui_logger
from epw_os.gui.theme_manager import error_text_style, success_text_style, neutral_text_style, THEME_MODE_CONSTANT, THEME_MODE_AUTO
from epw_os.i18n import tr, available_languages, get_language


def _level_name(level):
    return tr(f"access.{str(level).lower()}", default=str(level))


class LanguageDialog(QDialog):
    """Interface-language picker. This dialog only ever persists the
    choice to the project config immediately on OK - it does not itself
    apply it (no epw_os.i18n import here at all). Task: switch language
    without restarting - the caller (MainWindow._open_language_dialog())
    compares the saved language before/after this dialog closes and, if
    it actually changed, rebuilds the whole window (main.py's
    rebuild_window_for_language_change()) so every widget re-reads
    tr() fresh. Keeping that entirely outside this class means an
    isolated widget test can still construct/use this dialog with no
    QApplication-rebuild machinery in play at all.

    project_manager may be None in isolated widget tests - the dialog still
    works, it just can't persist."""

    def __init__(self, project_manager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("settings.language_section"))
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        header = QLabel(tr("settings.language_section"))
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("settings.language_label")))
        self.combo = QComboBox()
        for code, native_name in available_languages():
            self.combo.addItem(native_name, code)
        current = get_language()
        if self.project_manager is not None:
            current = self.project_manager.get_language()
        idx = self.combo.findData(current)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        row.addWidget(self.combo, 1)
        layout.addLayout(row)

        hint = QLabel(tr("settings.language_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self):
        code = self.combo.currentData()
        if code and self.project_manager is not None and code != self.project_manager.get_language():
            self.project_manager.set_language(code)
            self.project_manager.save_project()
            ui_logger.log("INFO", "SYSTEM", "Language",
                          f"Interface language set to '{code}'", "Operator", "", "")
            # self.parent() is the MainWindow (LanguageDialog is always
            # constructed as LanguageDialog(project_manager, main_window)) -
            # audit_logger may be missing in isolated widget tests.
            audit_logger = getattr(self.parent(), "audit_logger", None)
            if audit_logger is not None:
                audit_logger.record("LANGUAGE_CHANGE", "Operator", f"Interface language set to '{code}'", success=True)
        self.accept()


class PinChangeSection(QFrame):
    """One level's PIN-change form. Authorization is proven by knowing the
    *current* PIN, entered right here - not by the operator's current
    session level. That means changing the Engineer PIN never depends on
    whether anyone happens to still be logged in as Engineer, and someone
    who merely finds an unlocked session at Engineer level still can't
    change the PIN without knowing it."""

    def __init__(self, access_manager, level, parent=None):
        super().__init__(parent)
        self.access_manager = access_manager
        self.level = level
        self.setObjectName("SunkenFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        header = QLabel(tr("settings.pin_header", level=_level_name(level).upper()))
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        grid = QGridLayout()
        layout.addLayout(grid)

        grid.addWidget(QLabel(tr("settings.old_pin")), 0, 0)
        self.edit_old = QLineEdit()
        self.edit_old.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_old.setMaxLength(8)
        grid.addWidget(self.edit_old, 0, 1)

        grid.addWidget(QLabel(tr("settings.new_pin")), 1, 0)
        self.edit_new = QLineEdit()
        self.edit_new.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_new.setMaxLength(8)
        grid.addWidget(self.edit_new, 1, 1)

        grid.addWidget(QLabel(tr("settings.confirm_pin")), 2, 0)
        self.edit_confirm = QLineEdit()
        self.edit_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_confirm.setMaxLength(8)
        grid.addWidget(self.edit_confirm, 2, 1)

        # Same architectural fix as PinPromptPopup (see its docstring and
        # SESSION_REPORT.md): a separate floating on-screen keyboard can't
        # reliably deliver clicks into a field inside a modal dialog
        # (Qt::ApplicationModal blocks input to top-level windows outside
        # the dialog's own hierarchy). One embedded keypad here serves all
        # three fields above, retargeted on focus (see eventFilter()
        # below).
        #
        # Always built, regardless of the Settings "On-Screen Keyboard"
        # toggle - same reasoning as PinPromptPopup: on a touchscreen-only
        # device, that toggle being off must never remove the only way to
        # type a PIN, and changing a PIN is exactly such a case. The
        # toggle keeps controlling the separate FLOATING keyboard for
        # every other field exactly as before.
        from epw_os.gui.widgets.onscreen_keyboard import EmbeddedNumericKeypad, mark_embedded_keypad_field
        self._pin_fields = (self.edit_old, self.edit_new, self.edit_confirm)
        for field in self._pin_fields:
            mark_embedded_keypad_field(field)  # stop the floating keyboard from ALSO attaching here
            field.installEventFilter(self)
        self._keypad = EmbeddedNumericKeypad(self)
        self._keypad.attach(self.edit_old)  # sensible default before the first real focus event
        layout.addWidget(self._keypad)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        self.btn_save = QPushButton(tr("settings.save"))
        self.btn_save.clicked.connect(self.save)
        layout.addWidget(self.btn_save)

    def eventFilter(self, obj, event):
        # Retargets the one shared EmbeddedNumericKeypad to whichever of
        # this section's three fields currently has focus - only
        # installed on those three fields.
        if event.type() == QEvent.Type.FocusIn and obj in self._pin_fields:
            self._keypad.attach(obj)
        return super().eventFilter(obj, event)

    def save(self):
        old_pin = self.edit_old.text()
        new_pin = self.edit_new.text()
        confirm_pin = self.edit_confirm.text()

        if not self.access_manager.verify_pin(self.level, old_pin):
            self.lbl_status.setText(tr("settings.pin_old_wrong"))
            self.lbl_status.setStyleSheet(error_text_style())
            return
        if not new_pin or not new_pin.isdigit():
            self.lbl_status.setText(tr("settings.pin_not_numeric"))
            self.lbl_status.setStyleSheet(error_text_style())
            return
        if new_pin != confirm_pin:
            self.lbl_status.setText(tr("settings.pin_mismatch"))
            self.lbl_status.setStyleSheet(error_text_style())
            return
        if new_pin == old_pin:
            self.lbl_status.setText(tr("settings.pin_same"))
            self.lbl_status.setStyleSheet(error_text_style())
            return

        self.access_manager.set_pin(self.level, new_pin)
        self.edit_old.clear()
        self.edit_new.clear()
        self.edit_confirm.clear()
        self.lbl_status.setText(tr("settings.pin_updated"))
        self.lbl_status.setStyleSheet(success_text_style())
        ui_logger.log("WARNING", "SYSTEM", f"{self.level} PIN", "PIN changed",
                      self.level, self.access_manager.level, "")


class ChangePinDialog(QDialog):
    """Both PIN-change forms (Operator + Engineer) in one popup - same two
    ``PinChangeSection`` widgets the old Settings page used, unchanged."""

    def __init__(self, access_manager, parent=None):
        super().__init__(parent)
        self.access_manager = access_manager
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("settings.pin_change_title"))
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        info = QLabel(tr("settings.pin_info"))
        info.setWordWrap(True)
        layout.addWidget(info)

        sections = QHBoxLayout()
        self.operator_section = PinChangeSection(access_manager, AccessLevel.OPERATOR, self)
        self.engineer_section = PinChangeSection(access_manager, AccessLevel.ENGINEER, self)
        sections.addWidget(self.operator_section)
        sections.addWidget(self.engineer_section)
        layout.addLayout(sections)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class ScreenSleepDialog(QDialog):
    """Settings > Screen Sleep... - configurable idle time before the
    display blanks (screen_sleep_overlay.py). Independent of the 5-minute
    access-level auto-logout: this only ever affects what's on screen,
    never access_manager.level. Not access-gated (like Language) - it's
    a display comfort setting, not a security control.

    Takes effect immediately via MainWindow.set_screen_sleep_minutes()
    (self.parent() - always constructed as
    ScreenSleepDialog(minutes, main_window), matching LanguageDialog's
    established pattern for reaching back into MainWindow), and is
    persisted machine-locally (window_state.py)."""

    def __init__(self, current_minutes: int, parent=None):
        super().__init__(parent)
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("settings.screen_sleep_title"))
        self.setModal(True)
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        header = QLabel(tr("settings.screen_sleep_title"))
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        hint = QLabel(tr("settings.screen_sleep_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.chk_enabled = QCheckBox(tr("settings.screen_sleep_enable"))
        self.chk_enabled.setChecked(current_minutes > 0)
        self.chk_enabled.toggled.connect(self._on_enabled_toggled)
        layout.addWidget(self.chk_enabled)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("settings.screen_sleep_minutes_label")))
        self.spin_minutes = QSpinBox()
        self.spin_minutes.setRange(1, 240)
        self.spin_minutes.setValue(current_minutes if current_minutes > 0 else 2)
        self.spin_minutes.setEnabled(current_minutes > 0)
        row.addWidget(self.spin_minutes)
        row.addStretch()
        layout.addLayout(row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_enabled_toggled(self, checked):
        self.spin_minutes.setEnabled(checked)

    def _apply(self):
        minutes = self.spin_minutes.value() if self.chk_enabled.isChecked() else 0
        main_window = self.parent()
        if main_window is not None and hasattr(main_window, "set_screen_sleep_minutes"):
            main_window.set_screen_sleep_minutes(minutes)
        self.accept()


class ThemeDialog(QDialog):
    """Settings > Theme... - the menu-driven path for picking a visual
    theme (Task: przelaczane motywy wizualne), extended (Task 4,
    page-split branch) with a work-mode choice: MOTYW STALY (today's
    exact plain picker, still ungated - GRANICE: "zmiana z menu:
    dowolny poziom") or AUTOMATYCZNY DZIEN/NOC (day theme + night theme
    + two switch times).

    Access: picking a plain theme while STAYING in Stały mode is
    UNGATED, unchanged from before this task. Anything that touches the
    work MODE itself - entering/adjusting/leaving Automatyczny, or
    switching mode back to Staly - requires Engineer + reaches the
    audit log (Task 4: "Zmiana trybu: poziom Engineer, zapis do
    dziennika audytowego"), enforced here via
    self.parent().request_access()/deny_access() same as every other
    Engineer-gated Settings entry in this app, THEN via
    ThemeManager.set_mode() itself never gating (same "this app doesn't
    duplicate its own permission logic in every path" convention
    apply_index() already established for the plain pick)."""

    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self._initial_mode = theme_manager.get_mode()
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("settings.theme_title"))
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        header = QLabel(tr("settings.theme_title"))
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        hint = QLabel(tr("settings.theme_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        if theme_manager.is_logic_override_active():
            override_note = QLabel(tr("settings.theme_logic_override_note"))
            override_note.setWordWrap(True)
            override_note.setStyleSheet(neutral_text_style("font-style: italic;"))
            layout.addWidget(override_note)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel(tr("settings.theme_mode_label")))
        self.combo_mode = QComboBox()
        self.combo_mode.addItem(tr("settings.theme_mode_constant"), THEME_MODE_CONSTANT)
        self.combo_mode.addItem(tr("settings.theme_mode_auto"), THEME_MODE_AUTO)
        idx = self.combo_mode.findData(self._initial_mode)
        if idx >= 0:
            self.combo_mode.setCurrentIndex(idx)
        self.combo_mode.currentIndexChanged.connect(self._update_mode_visibility)
        mode_row.addWidget(self.combo_mode, 1)
        layout.addLayout(mode_row)

        # --- MOTYW STALY fields ------------------------------------------
        self.row_constant = QHBoxLayout()
        self.lbl_constant = QLabel(tr("settings.theme_label"))
        self.row_constant.addWidget(self.lbl_constant)
        self.combo_theme = QComboBox()
        for index, theme in enumerate(themes.THEMES):
            self.combo_theme.addItem(tr(theme["name_key"]), index)
        idx = self.combo_theme.findData(theme_manager.current_index())
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)
        self.row_constant.addWidget(self.combo_theme, 1)
        layout.addLayout(self.row_constant)

        # --- AUTOMATYCZNY DZIEN/NOC fields ---------------------------------
        self.form_auto = QFormLayout()
        self.combo_day_theme = QComboBox()
        self.combo_night_theme = QComboBox()
        for index, theme in enumerate(themes.THEMES):
            self.combo_day_theme.addItem(tr(theme["name_key"]), index)
            self.combo_night_theme.addItem(tr(theme["name_key"]), index)
        day_idx = self.combo_day_theme.findData(theme_manager.get_day_index())
        if day_idx >= 0:
            self.combo_day_theme.setCurrentIndex(day_idx)
        night_idx = self.combo_night_theme.findData(theme_manager.get_night_index())
        if night_idx >= 0:
            self.combo_night_theme.setCurrentIndex(night_idx)
        self.lbl_day_theme = QLabel(tr("settings.theme_day_label"))
        self.form_auto.addRow(self.lbl_day_theme, self.combo_day_theme)
        self.lbl_night_theme = QLabel(tr("settings.theme_night_label"))
        self.form_auto.addRow(self.lbl_night_theme, self.combo_night_theme)

        self.edit_day_start = QTimeEdit()
        self.edit_day_start.setDisplayFormat("HH:mm")
        self.edit_day_start.setTime(_parse_qtime(theme_manager.get_day_start()))
        self.lbl_day_start = QLabel(tr("settings.theme_day_start_label"))
        self.form_auto.addRow(self.lbl_day_start, self.edit_day_start)

        self.edit_night_start = QTimeEdit()
        self.edit_night_start.setDisplayFormat("HH:mm")
        self.edit_night_start.setTime(_parse_qtime(theme_manager.get_night_start()))
        self.lbl_night_start = QLabel(tr("settings.theme_night_start_label"))
        self.form_auto.addRow(self.lbl_night_start, self.edit_night_start)

        layout.addLayout(self.form_auto)
        self._update_mode_visibility()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._try_apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_mode_visibility(self, *_):
        is_auto = self.combo_mode.currentData() == THEME_MODE_AUTO
        self.lbl_constant.setVisible(not is_auto)
        self.combo_theme.setVisible(not is_auto)
        for w in (self.lbl_day_theme, self.combo_day_theme, self.lbl_night_theme, self.combo_night_theme,
                  self.lbl_day_start, self.edit_day_start, self.lbl_night_start, self.edit_night_start):
            w.setVisible(is_auto)

    def _try_apply(self):
        selected_mode = self.combo_mode.currentData()
        mode_changed = selected_mode != self._initial_mode

        if not mode_changed and selected_mode == THEME_MODE_CONSTANT:
            # Task's own preserved path: staying in Staly and just
            # re-picking a theme is a plain display preference, exactly
            # as ungated as it always was - never touches set_mode() or
            # the audit log.
            self.theme_manager.apply_index(self.combo_theme.currentData())
            self.accept()
            return

        # Everything else - entering/adjusting/leaving Automatyczny -
        # is a work-MODE change (Task 4: "Zmiana trybu: poziom Engineer,
        # zapis do dziennika audytowego").
        main_window = self.parent()
        if main_window is None or not hasattr(main_window, "request_access"):
            self.accept()
            return
        if not main_window.request_access(AccessLevel.ENGINEER):
            return

        if selected_mode == THEME_MODE_AUTO:
            day_start = self.edit_day_start.time().toString("HH:mm")
            night_start = self.edit_night_start.time().toString("HH:mm")
            self.theme_manager.set_mode(
                THEME_MODE_AUTO, day_index=self.combo_day_theme.currentData(),
                night_index=self.combo_night_theme.currentData(),
                day_start=day_start, night_start=night_start)
            detail = tr("settings.audit_theme_mode_auto", day=self.combo_day_theme.currentText(),
                         night=self.combo_night_theme.currentText(), day_start=day_start, night_start=night_start)
        else:
            self.theme_manager.set_mode(THEME_MODE_CONSTANT, constant_index=self.combo_theme.currentData())
            detail = tr("settings.audit_theme_mode_constant", theme=self.combo_theme.currentText())

        audit_logger = getattr(main_window, "audit_logger", None)
        if audit_logger is not None:
            audit_logger.record("THEME_MODE_CHANGE", "Engineer", detail, success=True)
        self.accept()


def _parse_qtime(hhmm: str) -> QTime:
    hh, mm = int(hhmm[:2]), int(hhmm[3:])
    return QTime(hh, mm)
