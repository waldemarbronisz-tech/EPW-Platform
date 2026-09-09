"""Tools > Presentation Mode... (Task: "przygotowany scenariusz
demonstracyjny uruchamiany jednym poleceniem"). Non-modal (unlike most
dialogs in this app) - Task: the presenter needs to see the rest of the
program (the synoptic, alarms, ...) react to the scenario while this
stays open with its controls, not a blocking popup.

Reused across repeated Tools > Presentation Mode clicks (same pattern
as HelpWindow - see main_window.py's _open_help_window()) so a demo
in progress isn't lost if the menu item is clicked again.
"""
import os

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                             QPushButton, QListWidget, QListWidgetItem, QMessageBox)
from PySide6.QtCore import Qt

from epw_os.core.logging import log
from epw_os.core.presentation_mode import PresentationModeError, load_scenario, list_scenarios
from epw_os.core.access_manager import AccessLevel
from epw_os.gui.theme_manager import get_theme_manager, current_colors, error_text_style, neutral_text_style
from epw_os.i18n import tr


class PresentationDialog(QDialog):
    def __init__(self, presentation_mode, training_mode, access_manager,
                 started_signal=None, stopped_signal=None, paused_signal=None,
                 resumed_signal=None, step_signal=None, parent=None):
        super().__init__(parent)
        self.presentation_mode = presentation_mode
        self.training_mode = training_mode
        self.access_manager = access_manager

        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("presentation.title"))
        self.setModal(False)
        self.setMinimumSize(420, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        header = QLabel(tr("presentation.header"))
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        hint = QLabel(tr("presentation.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        picker_row = QHBoxLayout()
        picker_row.addWidget(QLabel(tr("presentation.lbl_scenario")))
        self.combo_scenario = QComboBox()
        self.combo_scenario.setToolTip(tr("presentation.tooltip_scenario"))
        self.combo_scenario.currentIndexChanged.connect(self._on_scenario_selected)
        picker_row.addWidget(self.combo_scenario, 1)
        layout.addLayout(picker_row)

        self.lbl_description = QLabel("")
        self.lbl_description.setWordWrap(True)
        self.lbl_description.setStyleSheet(neutral_text_style("font-style: italic;"))
        layout.addWidget(self.lbl_description)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("SectionHeader")
        layout.addWidget(self.lbl_status)

        buttons_row = QHBoxLayout()
        self.btn_start = QPushButton(tr("presentation.btn_start"))
        self.btn_start.setToolTip(tr("presentation.tooltip_btn_start"))
        self.btn_start.clicked.connect(self._on_start_clicked)
        buttons_row.addWidget(self.btn_start)

        self.btn_pause = QPushButton(tr("presentation.btn_pause"))
        self.btn_pause.setToolTip(tr("presentation.tooltip_btn_pause"))
        self.btn_pause.clicked.connect(self._on_pause_clicked)
        buttons_row.addWidget(self.btn_pause)

        self.btn_step = QPushButton(tr("presentation.btn_step"))
        self.btn_step.setToolTip(tr("presentation.tooltip_btn_step"))
        self.btn_step.clicked.connect(self._on_step_clicked)
        buttons_row.addWidget(self.btn_step)

        self.btn_stop = QPushButton(tr("presentation.btn_stop"))
        self.btn_stop.setToolTip(tr("presentation.tooltip_btn_stop"))
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        buttons_row.addWidget(self.btn_stop)
        layout.addLayout(buttons_row)

        layout.addWidget(QLabel(tr("presentation.lbl_log")))
        self.log_list = QListWidget()
        layout.addWidget(self.log_list, stretch=1)

        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self.close)
        close_row.addWidget(btn_close)
        layout.addLayout(close_row)

        self._populate_scenarios()

        if started_signal is not None:
            started_signal.connect(self._on_started)
        if stopped_signal is not None:
            stopped_signal.connect(self._on_stopped)
        if paused_signal is not None:
            paused_signal.connect(self._on_paused)
        if resumed_signal is not None:
            resumed_signal.connect(self._on_resumed)
        if step_signal is not None:
            step_signal.connect(self._on_step)

        self._refresh_controls()

    # --- scenario picker -------------------------------------------

    def _populate_scenarios(self):
        self.combo_scenario.clear()
        for path in list_scenarios():
            try:
                scenario = load_scenario(path)
            except (OSError, ValueError) as e:
                # A broken scenario file just doesn't show up in the list
                # (kept unchanged, no crash) - but an installer who
                # authored it would otherwise have zero clue why it's
                # missing from the dropdown, the same "polykane wyjatki"
                # pattern as System.Mode.
                log.warning(f"Skipping unreadable presentation scenario {path!r}: {e}")
                continue
            self.combo_scenario.addItem(scenario.name, path)
        self._on_scenario_selected()

    def _on_scenario_selected(self, *_):
        path = self.combo_scenario.currentData()
        if not path:
            self.lbl_description.setText(tr("presentation.no_scenarios"))
            return
        try:
            scenario = load_scenario(path)
            self.lbl_description.setText(scenario.description or "")
        except (OSError, ValueError) as e:
            # Same reasoning as _populate_scenarios() above - most likely
            # the file was removed/became unreadable between listing and
            # selecting it.
            log.warning(f"Could not re-read presentation scenario {path!r} for its description: {e}")
            self.lbl_description.setText("")

    # --- controls ----------------------------------------------------

    def _on_start_clicked(self):
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Presentation Mode")
            return
        path = self.combo_scenario.currentData()
        if not path:
            return

        # Task: hard requirement - starting requires Training Mode, and
        # this dialog must OFFER to enable it, never enable it silently.
        if not self.training_mode.active:
            reply = QMessageBox.question(
                self, tr("presentation.title"), tr("presentation.confirm_enable_training_mode"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.training_mode.set_active(True, actor=self.access_manager.level)

        try:
            scenario = load_scenario(path)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, tr("presentation.title"), tr("presentation.err_load_failed", error=str(e)))
            return

        self.log_list.clear()
        try:
            self.presentation_mode.start(scenario, actor=self.access_manager.level)
        except PresentationModeError as e:
            QMessageBox.warning(self, tr("presentation.title"), str(e))
            return

    def _on_pause_clicked(self):
        if self.presentation_mode.paused:
            self.presentation_mode.resume()
        else:
            self.presentation_mode.pause()

    def _on_step_clicked(self):
        self.presentation_mode.step_forward()

    def _on_stop_clicked(self):
        self.presentation_mode.stop(actor=self.access_manager.level)

    # --- live updates --------------------------------------------------

    def _on_started(self, name):
        self._refresh_controls()

    def _on_stopped(self):
        self._refresh_controls()

    def _on_paused(self):
        self._refresh_controls()

    def _on_resumed(self):
        self._refresh_controls()

    def _on_step(self, index, total, description):
        self.log_list.addItem(QListWidgetItem(tr("presentation.log_step", n=index + 1, total=total, description=description)))
        self.log_list.scrollToBottom()
        self._refresh_controls()

    def _refresh_controls(self, *_):
        active = self.presentation_mode.active
        paused = self.presentation_mode.paused
        self.btn_start.setEnabled(not active)
        self.combo_scenario.setEnabled(not active)
        self.btn_pause.setEnabled(active)
        self.btn_pause.setText(tr("presentation.btn_resume") if paused else tr("presentation.btn_pause"))
        self.btn_step.setEnabled(active)
        self.btn_stop.setEnabled(active)

        colors = current_colors()
        if not active:
            self.lbl_status.setText(tr("presentation.status_idle"))
            self.lbl_status.setStyleSheet("")
        elif paused:
            self.lbl_status.setText(tr("presentation.status_paused", n=self.presentation_mode.step_index,
                                        total=len(self.presentation_mode.scenario.steps) if self.presentation_mode.scenario else 0))
            self.lbl_status.setStyleSheet(f"color: {colors['state_warning_dark']}; font-weight: bold;")
        else:
            self.lbl_status.setText(tr("presentation.status_running", n=self.presentation_mode.step_index,
                                        total=len(self.presentation_mode.scenario.steps) if self.presentation_mode.scenario else 0))
            self.lbl_status.setStyleSheet(f"color: {colors['state_ok_text']}; font-weight: bold;")
