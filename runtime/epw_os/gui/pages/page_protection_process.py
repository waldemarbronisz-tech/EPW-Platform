from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QLineEdit, QComboBox, QDoubleSpinBox,
                             QCheckBox, QDialog, QDialogButtonBox, QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from epw_os.gui.table_helpers import set_resizable_columns, set_header_tooltips
from epw_os.core.access_manager import AccessLevel
from epw_os.gui.theme_manager import get_theme_manager, neutral_text_style, error_text_style
from epw_os.i18n import tr

_COL_NAME, _COL_TAG, _COL_UPPER, _COL_LOWER, _COL_HYSTERESIS, _COL_DELAY, _COL_EXCEEDED, _COL_OUTPUT_TAG = range(8)


class ProcessProtectionConfigDialog(QDialog):
    """Add (protection=None) or edit an existing process protection -
    Task's own minimal field list: analog point, upper/lower threshold,
    hysteresis, delay. Same type-restricted-picker convention
    intrusion_manager.py's own PARAMETRIZED-mode line input already
    established (`analog_candidates` only ever lists real, configured
    analog points - see ProcessProtectionManager.get_analog_input_
    candidates(), itself reusing intrusion_manager.list_analog_input_
    candidates() directly)."""

    def __init__(self, analog_candidates, protection=None, parent=None):
        super().__init__(parent)
        self.is_new = protection is None
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.protection_process.dialog_add_title") if self.is_new
                             else tr("pages.protection_process.dialog_edit_title", name=protection["name"]))
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        form = QFormLayout()
        layout.addLayout(form)

        self.edit_name = QLineEdit(protection["name"] if protection else "")
        form.addRow(tr("pages.protection_process.lbl_name"), self.edit_name)

        self.combo_tag = QComboBox()
        self.combo_tag.addItem("", "")
        for t in analog_candidates:
            self.combo_tag.addItem(t, t)
        if protection:
            idx = self.combo_tag.findData(protection["analog_tag"])
            if idx >= 0:
                self.combo_tag.setCurrentIndex(idx)
        form.addRow(tr("pages.protection_process.lbl_analog_point"), self.combo_tag)

        self.spin_upper = QDoubleSpinBox()
        self.spin_upper.setRange(-1_000_000.0, 1_000_000.0)
        self.spin_upper.setDecimals(2)
        self.spin_upper.setValue(float(protection["upper_threshold"]) if protection else 100.0)
        form.addRow(tr("pages.protection_process.lbl_upper_threshold"), self.spin_upper)

        self.spin_lower = QDoubleSpinBox()
        self.spin_lower.setRange(-1_000_000.0, 1_000_000.0)
        self.spin_lower.setDecimals(2)
        self.spin_lower.setValue(float(protection["lower_threshold"]) if protection else 0.0)
        form.addRow(tr("pages.protection_process.lbl_lower_threshold"), self.spin_lower)

        self.spin_hysteresis = QDoubleSpinBox()
        self.spin_hysteresis.setRange(0.0, 1_000_000.0)
        self.spin_hysteresis.setDecimals(2)
        self.spin_hysteresis.setToolTip(tr("pages.protection_process.tooltip_hysteresis"))
        self.spin_hysteresis.setValue(float(protection["hysteresis"]) if protection else 0.0)
        form.addRow(tr("pages.protection_process.lbl_hysteresis"), self.spin_hysteresis)

        self.spin_delay = QDoubleSpinBox()
        self.spin_delay.setRange(0.0, 3600.0)
        self.spin_delay.setDecimals(1)
        self.spin_delay.setSuffix(" s")
        self.spin_delay.setToolTip(tr("pages.protection_process.tooltip_delay"))
        self.spin_delay.setValue(float(protection["delay_seconds"]) if protection else 0.0)
        form.addRow(tr("pages.protection_process.lbl_delay"), self.spin_delay)

        self.chk_enabled = QCheckBox(tr("pages.protection_process.lbl_enabled"))
        self.chk_enabled.setChecked(bool(protection["enabled"]) if protection else True)
        form.addRow("", self.chk_enabled)

        if protection:
            # Read-only - an id (and so the tag name derived from it) only
            # exists once the protection has actually been added; see the
            # module docstring on why this is auto-generated, not a
            # user-typed field.
            form.addRow(tr("pages.protection_process.lbl_output_tag"),
                         QLabel(f"Process.{protection['id']}.Exceeded"))

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(error_text_style())
        self.lbl_error.setWordWrap(True)
        layout.addWidget(self.lbl_error)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _try_accept(self):
        if not self.edit_name.text().strip():
            self.lbl_error.setText(tr("pages.intrusion.err_name_required"))
            return
        if not self.result_analog_tag():
            self.lbl_error.setText(tr("pages.protection_process.err_point_required"))
            return
        if self.spin_lower.value() > self.spin_upper.value():
            self.lbl_error.setText(tr("pages.protection_process.err_lower_above_upper"))
            return
        self.accept()

    def result_name(self) -> str:
        return self.edit_name.text().strip()

    def result_analog_tag(self) -> str:
        return (self.combo_tag.currentData() or "").strip()

    def result_upper_threshold(self) -> float:
        return self.spin_upper.value()

    def result_lower_threshold(self) -> float:
        return self.spin_lower.value()

    def result_hysteresis(self) -> float:
        return self.spin_hysteresis.value()

    def result_delay_seconds(self) -> float:
        return self.spin_delay.value()

    def result_enabled(self) -> bool:
        return self.chk_enabled.isChecked()


class PageProtectionProcess(QWidget):
    """Task (page-split), part 1: ZABEZPIECZENIA > Procesowe - a
    brand-new, minimal page (built from scratch - no equivalent existed
    before this task; see SESSION_REPORT.md). "Prosty prog z histereza
    i zwloka" on an existing analog point, exposing a signal tag for
    logic - never drives an output itself, same GRANICE boundary as
    every other alarm/supervision page in this app. Viewing is open to
    everyone; adding/editing/removing a protection is Engineer-only
    (same view-vs-edit split page_protection_electrical.py already
    has, not a whole-page gate like PageIntrusionConfiguration - this
    page has no equivalent "installer does this once" framing, it's an
    ordinary status+config page like Electrical)."""

    def __init__(self, process_protection_manager, access_manager, parent=None):
        super().__init__(parent)
        self.process_protection_manager = process_protection_manager
        self.access_manager = access_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.protection_process"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.lbl_gate = QLabel("")
        self.lbl_gate.setStyleSheet(neutral_text_style("font-style: italic;"))
        toolbar.addWidget(self.lbl_gate)
        toolbar.addStretch()
        self.btn_add = QPushButton(tr("pages.intrusion.btn_add"))
        self.btn_add.clicked.connect(self._add)
        toolbar.addWidget(self.btn_add)
        self.btn_edit = QPushButton(tr("pages.intrusion.btn_edit"))
        self.btn_edit.clicked.connect(self._edit)
        toolbar.addWidget(self.btn_edit)
        self.btn_remove = QPushButton(tr("pages.intrusion.btn_remove"))
        self.btn_remove.clicked.connect(self._remove)
        toolbar.addWidget(self.btn_remove)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            tr("pages.protection_process.col_name"), tr("pages.common.col_tag"),
            tr("pages.protection_process.col_upper"), tr("pages.protection_process.col_lower"),
            tr("pages.protection_process.col_hysteresis"), tr("pages.protection_process.col_delay"),
            tr("pages.protection_process.col_exceeded"), tr("pages.protection_process.col_output_tag"),
        ])
        set_header_tooltips(self.table, [
            "", "", "", "", tr("pages.protection_process.tooltip_hysteresis"),
            tr("pages.protection_process.tooltip_delay"), "", tr("pages.protection_process.tooltip_output_tag"),
        ])
        set_resizable_columns(self.table.horizontalHeader(), [140, 110, 90, 90, 90, 90, 100, 160])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self.access_manager.level_changed.connect(self.refresh)
        get_theme_manager().theme_changed.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        can_configure = self.access_manager.has_access(AccessLevel.ENGINEER)
        for btn in (self.btn_add, self.btn_edit, self.btn_remove):
            btn.setEnabled(can_configure)
        self.lbl_gate.setText("" if can_configure else tr("pages.protection_process.gate_configure_message"))

        # process_protection_manager is None when the feature is off or
        # in isolated widget tests - same guard every other optional
        # core manager gets in this app.
        protections = self.process_protection_manager.get_protections() \
            if self.process_protection_manager is not None else []
        colors = get_theme_manager().current_colors()
        selected_ids = {self.table.item(r, _COL_NAME).data(Qt.ItemDataRole.UserRole)
                         for r in {i.row() for i in self.table.selectedIndexes()}
                         if self.table.item(r, _COL_NAME) is not None}

        self.table.setRowCount(len(protections))
        for row, protection in enumerate(protections):
            protection_id = protection["id"]
            exceeded = self.process_protection_manager.is_exceeded(protection_id)
            name_item = QTableWidgetItem(protection["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, protection_id)
            self.table.setItem(row, _COL_NAME, name_item)
            self.table.setItem(row, _COL_TAG, QTableWidgetItem(protection["analog_tag"]))
            self.table.setItem(row, _COL_UPPER, QTableWidgetItem(f"{protection['upper_threshold']:g}"))
            self.table.setItem(row, _COL_LOWER, QTableWidgetItem(f"{protection['lower_threshold']:g}"))
            self.table.setItem(row, _COL_HYSTERESIS, QTableWidgetItem(f"{protection['hysteresis']:g}"))
            self.table.setItem(row, _COL_DELAY, QTableWidgetItem(f"{protection['delay_seconds']:g} s"))
            exceeded_text = tr("pages.protection_process.exceeded_yes") if exceeded \
                else tr("pages.protection_process.exceeded_no")
            if not protection["enabled"]:
                exceeded_text += f" ({tr('pages.protection_process.disabled_suffix')})"
            self.table.setItem(row, _COL_EXCEEDED, QTableWidgetItem(exceeded_text))
            self.table.setItem(row, _COL_OUTPUT_TAG, QTableWidgetItem(f"Process.{protection_id}.Exceeded"))

            bg = QColor(colors["state_alarm_dark"]) if (exceeded and protection["enabled"]) else QColor(colors["field_bg"])
            fg = QColor(colors["accent_text"]) if (exceeded and protection["enabled"]) else QColor(colors["text"])
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                item.setBackground(bg)
                item.setForeground(fg)

            if protection_id in selected_ids:
                self.table.selectRow(row)

    # --- CRUD (Engineer-only) ------------------------------------------

    def _selected_protection(self):
        rows = {i.row() for i in self.table.selectedIndexes()}
        if not rows:
            return None
        row = next(iter(rows))
        item = self.table.item(row, _COL_NAME)
        if item is None:
            return None
        protection_id = item.data(Qt.ItemDataRole.UserRole)
        return self.process_protection_manager.get_protection(protection_id)

    def _add(self):
        if self.process_protection_manager is None:  # isolated widget test / mock - nothing to configure
            return
        if not self.window().request_access(AccessLevel.ENGINEER):
            return
        candidates = self.process_protection_manager.get_analog_input_candidates()
        dialog = ProcessProtectionConfigDialog(candidates, None, self)
        if dialog.exec():
            self.process_protection_manager.add_protection(
                dialog.result_name(), dialog.result_analog_tag(), dialog.result_upper_threshold(),
                dialog.result_lower_threshold(), hysteresis=dialog.result_hysteresis(),
                delay_seconds=dialog.result_delay_seconds(), level=self.access_manager.level)
        self.refresh()

    def _edit(self):
        if self.process_protection_manager is None:  # isolated widget test / mock - nothing to configure
            return
        protection = self._selected_protection()
        if protection is None:
            return
        if not self.window().request_access(AccessLevel.ENGINEER):
            return
        candidates = self.process_protection_manager.get_analog_input_candidates()
        dialog = ProcessProtectionConfigDialog(candidates, protection, self)
        if dialog.exec():
            self.process_protection_manager.update_protection(
                protection["id"], name=dialog.result_name(), analog_tag=dialog.result_analog_tag(),
                upper_threshold=dialog.result_upper_threshold(), lower_threshold=dialog.result_lower_threshold(),
                hysteresis=dialog.result_hysteresis(), delay_seconds=dialog.result_delay_seconds(),
                enabled=dialog.result_enabled(), level=self.access_manager.level)
        self.refresh()

    def _remove(self):
        if self.process_protection_manager is None:  # isolated widget test / mock - nothing to configure
            return
        protection = self._selected_protection()
        if protection is None:
            return
        if not self.window().request_access(AccessLevel.ENGINEER):
            return
        reply = QMessageBox.question(
            self, tr("nav.protection_process"),
            tr("pages.protection_process.remove_confirm_message", name=protection["name"]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.process_protection_manager.remove_protection(protection["id"], level=self.access_manager.level)
        self.refresh()
