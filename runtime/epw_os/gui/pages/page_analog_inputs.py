from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame,
                             QTableWidget, QTableWidgetItem, QLabel, QLineEdit, QComboBox,
                             QDoubleSpinBox, QSpinBox, QDialog, QDialogButtonBox, QPushButton,
                             QMessageBox, QAbstractItemView)
from PySide6.QtCore import Qt

from epw_os.gui.logger import ui_logger
from epw_os.gui.table_helpers import (
    set_resizable_columns, set_header_tooltips,
    apply_table_button_style, style_transparent_cell_container,
)
from epw_os.core.analog_scaling import (
    SIGNAL_TYPES, DEFAULT_RAW_RANGE, needs_scaling, normalize_config, format_display_value,
)
from epw_os.core.access_manager import AccessLevel
from epw_os.gui.theme_manager import error_text_style, current_colors
from epw_os.i18n import tr


class AnalogChannelConfigDialog(QDialog):
    """Opened by "Add Point" (a brand-new point - tag_name=None) or by
    the per-row Configure button (editing one). Narrowed scope (task:
    "ujednolicic edycje punktow analogowych"): Description, Unit and
    Technical note used to live here too, but all three are a modal
    QDialog field the floating on-screen keyboard can never reliably
    reach (Qt::ApplicationModal blocks input to any top-level window
    outside this dialog's own hierarchy - the exact same mechanism
    behind the PIN dialog's earlier bug, confirmed again here on real
    hardware). Rather than patch this dialog too, those three fields
    moved to the Analog Inputs table itself as double-click-editable
    cells - the cell editor belongs to the main window, not a separate
    modal window, so the keyboard reaches it exactly like it already
    does for Digital Inputs/Control Outputs' own Description column.
    See page_analog_inputs.py's PageAnalogInputs and SESSION_REPORT.md
    for the full reasoning, including why Technical note moved but
    Tag/Address did not.

    What's left here: Tag/Address, Signal type, raw/engineering ranges,
    Decimal places - all either identifiers set once at creation
    (Tag/Address) or a handful of numeric spin boxes/a dropdown, none of
    which the on-screen keyboard has ever needed to reach.

    Tag/Address is only editable when adding a new point - a point's
    identity, once created, isn't renamed here (same as every other tag
    in this system: remove and re-add under the new name instead)."""

    def __init__(self, tag_name=None, config=None, existing_tags=None, parent=None):
        super().__init__(parent)
        self.is_new = tag_name is None
        self.existing_tags = existing_tags or set()

        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.analog_inputs.dialog_add_title") if self.is_new
                             else tr("pages.analog_inputs.dialog_edit_title", tag=tag_name))
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        header = QLabel(tr("pages.analog_inputs.dialog_add_header") if self.is_new
                         else tr("pages.analog_inputs.dialog_edit_header", tag=tag_name))
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        form = QFormLayout()
        layout.addLayout(form)

        self.edit_tag = QLineEdit()
        if self.is_new:
            self.edit_tag.setPlaceholderText(tr("pages.analog_inputs.placeholder_tag"))
        else:
            self.edit_tag.setText(tag_name)
            self.edit_tag.setReadOnly(True)
            self.edit_tag.setStyleSheet("background-color: #D8D8D8;")
        form.addRow(tr("pages.analog_inputs.lbl_tag"), self.edit_tag)

        self.combo_type = QComboBox()
        self.combo_type.addItems(SIGNAL_TYPES)
        form.addRow(tr("pages.analog_inputs.lbl_signal_type"), self.combo_type)

        # Raw/engineering ranges only make sense (and are only shown) for
        # signal types that need linear scaling - hidden entirely for
        # "ready value", matching the spec.
        self.scaling_frame = QFrame()
        self.scaling_frame.setFrameShape(QFrame.Shape.NoFrame)
        scaling_form = QFormLayout(self.scaling_frame)
        scaling_form.setContentsMargins(0, 0, 0, 0)

        def _range_row(low_default, high_default):
            row = QHBoxLayout()
            spin_min = QDoubleSpinBox()
            spin_min.setRange(-1_000_000.0, 1_000_000.0)
            spin_min.setDecimals(3)
            spin_min.setValue(low_default)
            spin_max = QDoubleSpinBox()
            spin_max.setRange(-1_000_000.0, 1_000_000.0)
            spin_max.setDecimals(3)
            spin_max.setValue(high_default)
            row.addWidget(QLabel(tr("pages.analog_inputs.lbl_min")))
            row.addWidget(spin_min)
            row.addWidget(QLabel(tr("pages.analog_inputs.lbl_max")))
            row.addWidget(spin_max)
            return row, spin_min, spin_max

        raw_row, self.spin_raw_min, self.spin_raw_max = _range_row(0.0, 100.0)
        scaling_form.addRow(tr("pages.analog_inputs.lbl_raw_range"), raw_row)

        eng_row, self.spin_eng_min, self.spin_eng_max = _range_row(0.0, 100.0)
        scaling_form.addRow(tr("pages.analog_inputs.lbl_eng_range"), eng_row)

        form.addRow(self.scaling_frame)

        self.spin_decimals = QSpinBox()
        self.spin_decimals.setRange(0, 6)
        form.addRow(tr("pages.analog_inputs.lbl_decimals"), self.spin_decimals)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(error_text_style())
        self.lbl_error.setWordWrap(True)
        layout.addWidget(self.lbl_error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Populate from the persisted/default config BEFORE wiring the
        # "auto-fill raw range on type change" handler below - otherwise
        # setting combo_type while loading would immediately stomp a
        # persisted custom raw range with that type's generic default.
        self._load(config)
        self._update_scaling_visibility()
        self.combo_type.currentTextChanged.connect(self._on_type_changed)

    def _load(self, config):
        cfg = normalize_config(config)
        self.spin_raw_min.setValue(float(cfg["raw_min"]))
        self.spin_raw_max.setValue(float(cfg["raw_max"]))
        self.spin_eng_min.setValue(float(cfg["eng_min"]))
        self.spin_eng_max.setValue(float(cfg["eng_max"]))
        self.spin_decimals.setValue(int(cfg["decimals"]))
        self.combo_type.setCurrentText(cfg["signal_type"])

    def _update_scaling_visibility(self):
        self.scaling_frame.setVisible(needs_scaling(self.combo_type.currentText()))

    def _on_type_changed(self, signal_type):
        """Only runs for genuine, interactive dropdown changes (connected
        after _load()) - reseeds the raw range to that signal type's
        standard wire range, since 4-20mA/0-10V/0-3.3V are physical
        constants, not per-channel calibration."""
        self._update_scaling_visibility()
        if signal_type in DEFAULT_RAW_RANGE:
            raw_min, raw_max = DEFAULT_RAW_RANGE[signal_type]
            self.spin_raw_min.setValue(raw_min)
            self.spin_raw_max.setValue(raw_max)

    def _try_accept(self):
        if self.is_new:
            tag = self.edit_tag.text().strip()
            if not tag:
                self.lbl_error.setText(tr("pages.analog_inputs.err_tag_required"))
                return
            if tag in self.existing_tags:
                self.lbl_error.setText(tr("pages.analog_inputs.err_tag_duplicate", tag=tag))
                return
        self.accept()

    def result_tag(self) -> str:
        return self.edit_tag.text().strip()

    def result_config(self) -> dict:
        return {
            "signal_type": self.combo_type.currentText(),
            "raw_min": self.spin_raw_min.value(),
            "raw_max": self.spin_raw_max.value(),
            "eng_min": self.spin_eng_min.value(),
            "eng_max": self.spin_eng_max.value(),
            "decimals": self.spin_decimals.value(),
        }


# Table columns - Description/Unit/Technical note are the ones a
# double-click edits in place (see PageAnalogInputs docstring); the rest
# are read-only or the Configure button.
_COL_TAG = 0
_COL_DESCRIPTION = 1
_COL_VALUE = 2
_COL_UNIT = 3
_COL_TIMESTAMP = 4
_COL_NOTE = 5
_COL_CONFIGURE = 6
_EDITABLE_COLUMNS = {_COL_DESCRIPTION: "description", _COL_UNIT: "unit", _COL_NOTE: "technical_note"}
# Human-readable field names for deny_access()'s action text and the
# "X changed from... to..." log line - _EDITABLE_COLUMNS' own values
# ("technical_note") are the project.json/point-dict key, not something
# to show an operator.
_FIELD_LABELS = {"description": "Description", "unit": "Unit", "technical_note": "Technical note"}


class PageAnalogInputs(QWidget):
    """Analog Inputs is a dynamic points manager, not a fixed-slot list
    like Digital Inputs/Control Outputs. I2C/1-Wire sensors share a bus -
    the number of measurement points isn't bounded by a physical
    terminal count the way DI/DO are, so the operator adds and removes
    points freely instead of picking from a fixed AI1..AI16 range.
    See SESSION_REPORT.md for the migration from the old fixed format.

    Description/Unit/Technical note are edited in place, double-click
    like Digital Inputs/Control Outputs' own Description column -
    reusing that exact, already-working mechanism (task: "Uzyj
    istniejacego rozwiazania - nie pisz nowego"), not a new one. Every
    other point setting (Tag/Address, Signal type, raw/engineering
    ranges, Decimal places) still goes through the Configure button /
    AnalogChannelConfigDialog, mirroring Control Outputs' own Force
    button - a per-row button, visible Engineer-only, opening a
    per-point dialog."""

    def __init__(self, tag_manager, access_manager, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.access_manager = access_manager
        # Row index -> tag name, kept in sync with the table by
        # _rebuild_table() - the table no longer has a fixed, computable
        # row<->tag relationship (AI{row+1}) now that tags are arbitrary,
        # operator-chosen names.
        self._row_tags = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.analog_inputs"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.btn_add = QPushButton(tr("pages.analog_inputs.btn_add"))
        self.btn_add.setToolTip(tr("pages.analog_inputs.tooltip_btn_add"))
        self.btn_add.clicked.connect(self._add_point)
        toolbar.addWidget(self.btn_add)
        self.btn_remove = QPushButton(tr("pages.analog_inputs.btn_remove"))
        self.btn_remove.setToolTip(tr("pages.analog_inputs.tooltip_btn_remove"))
        self.btn_remove.clicked.connect(self._remove_point)
        toolbar.addWidget(self.btn_remove)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # No "Address" column - unlike DI/DO's %IX0.N/%QX0.N (a real PLC
        # register slot), a dynamic point has no fixed hardware address;
        # Tag *is* the address now, per the task's own framing.
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            tr("pages.common.col_tag"), tr("pages.common.col_description"),
            tr("pages.common.col_value"), tr("pages.common.col_unit"),
            tr("pages.common.col_timestamp"), tr("pages.analog_inputs.col_technical_note"),
            tr("pages.common.col_configure"),
        ])
        set_header_tooltips(self.table, [
            "", "", "", "",
            tr("pages.common.tooltip_col_timestamp"),
            tr("pages.analog_inputs.tooltip_col_technical_note"), "",
        ])
        set_resizable_columns(self.table.horizontalHeader(), [130, 260, 110, 60, 160, 220, 80])
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Description/Unit/Technical note are editable in place
        # (double-click / Enter) - same trigger set as Digital
        # Inputs/Control Outputs. Everything else (Tag/Address, Signal
        # type, ranges, Decimal places) still goes through the Configure
        # button / AnalogChannelConfigDialog.
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )

        layout.addWidget(self.table, stretch=1)

        self.table.itemChanged.connect(self._on_item_edited)
        self.tag_manager.tag_changed.connect(self.on_tag_changed)
        self.access_manager.level_changed.connect(self._refresh_edit_permissions)
        from epw_os.gui.theme_manager import get_theme_manager
        get_theme_manager().theme_changed.connect(self.refresh_theme)

        self._rebuild_table()

    def refresh_theme(self, *_):
        """Re-applies the Configure buttons' color under the new theme -
        they're recreated by _refresh_edit_permissions() (called via
        _refresh_configure_buttons()), which already reads the CURRENT
        theme each time, so simply re-running it is enough."""
        self._refresh_edit_permissions()

    def _refresh_edit_permissions(self, *_):
        """Add/Remove/Configure and the Description/Unit/Technical note
        cells are all Engineer-only (Task: real per-level permissions).
        Toggling ItemIsEditable and the Configure buttons is the visual
        half; _add_point()/_remove_point()/_open_point_config()/
        _on_item_edited() below are the real, execution-time half - each
        re-checks independently, not just trusting these stayed
        disabled/hidden.

        blockSignals around the loop: QTableWidgetItem.setFlags() can
        itself emit itemChanged (observed directly, same as Digital
        Inputs/Control Outputs) - harmless with a real TagManager
        (_on_item_edited()'s own "did the text actually change" guard
        catches it first) but not something to rely on."""
        can_edit = self.access_manager.has_access(AccessLevel.ENGINEER)
        self.btn_add.setEnabled(can_edit)
        self.btn_remove.setEnabled(can_edit)

        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            for col in _EDITABLE_COLUMNS:
                item = self.table.item(row, col)
                if item is None:
                    continue
                flags = item.flags()
                item.setFlags(flags | Qt.ItemFlag.ItemIsEditable if can_edit
                              else flags & ~Qt.ItemFlag.ItemIsEditable)
        self.table.blockSignals(False)

        self._refresh_configure_buttons(can_edit)

    def _refresh_configure_buttons(self, can_edit: bool):
        """Mirrors Control Outputs' SwitchingDeviceRow.refresh_force_button():
        the button only EXISTS in its cell's container while Engineer
        access is active - hidden by removal, not just disabled, matching
        the task's "widoczny dla poziomu Engineer" requirement (Force's
        own wording, deliberately reused here)."""
        for row in range(self.table.rowCount()):
            container = self.table.cellWidget(row, _COL_CONFIGURE)
            if container is None:
                continue
            container_layout = container.layout()
            while container_layout.count():
                child = container_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            if can_edit:
                btn = QPushButton(tr("pages.common.btn_configure"))
                btn.setToolTip(tr("pages.common.configure_tooltip"))
                # Task (button-look fix): apply_table_button_style()
                # redraws the full Win98 bevel every time - a partial
                # local setStyleSheet (just color/font-size/padding, as
                # this used to be) loses the inherited border entirely,
                # which was the actual cause of Configure looking flat.
                apply_table_button_style(
                    btn,
                    extra_css=f"QPushButton {{ color: {current_colors()['accent_bg']}; }}",
                )
                btn.clicked.connect(lambda checked=False, r=row: self._open_point_config(r, _COL_TAG))
                container_layout.addWidget(btn)

    # --- display ------------------------------------------------------

    def _rebuild_table(self):
        """Full repaint from the current points list - called at
        construction and after every Add/Remove. Point count is small
        (a handful to a few dozen sensors, not thousands), so a full
        rebuild is simpler and plenty fast, unlike a per-row incremental
        update that would need to track insertion/deletion positions."""
        points = self.tag_manager.get_analog_points()
        self._row_tags = [p["tag"] for p in points]

        self.table.setRowCount(len(points))
        for row, point in enumerate(points):
            tag_item = QTableWidgetItem(point["tag"])
            desc_item = QTableWidgetItem(point.get("description", ""))
            value_item = QTableWidgetItem("-")
            unit_item = QTableWidgetItem("")
            time_item = QTableWidgetItem("-")
            note_item = QTableWidgetItem(point.get("technical_note", ""))
            for item in (tag_item, value_item, time_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # desc_item/unit_item/note_item's editable flag is set below
            # by _refresh_edit_permissions() (current access level) -
            # start them non-editable here so there's no editable window
            # before that first call.
            for item in (desc_item, unit_item, note_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, _COL_TAG, tag_item)
            self.table.setItem(row, _COL_DESCRIPTION, desc_item)
            self.table.setItem(row, _COL_VALUE, value_item)
            self.table.setItem(row, _COL_UNIT, unit_item)
            self.table.setItem(row, _COL_TIMESTAMP, time_item)
            self.table.setItem(row, _COL_NOTE, note_item)

            configure_container = QWidget()
            style_transparent_cell_container(configure_container)
            configure_layout = QHBoxLayout(configure_container)
            configure_layout.setContentsMargins(2, 2, 2, 2)
            configure_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, _COL_CONFIGURE, configure_container)

            self._refresh_value_cell(row)

        self._refresh_edit_permissions()

    def _row_for_tag(self, tag_name):
        try:
            return self._row_tags.index(tag_name)
        except ValueError:
            # Deliberate, not logged: routine "not one of this page's own
            # rows" lookup (same as list.index()'s standard "not found"
            # case) - not a problem, would fire constantly for every
            # other tag in the system.
            return None

    def _refresh_value_cell(self, row: int):
        tag_name = self._row_tags[row]
        raw_value = self.tag_manager.get_value(tag_name)
        points = self.tag_manager.get_analog_points()
        config = next((p for p in points if p["tag"] == tag_name), None)
        cfg = normalize_config(config)
        value_str = format_display_value(raw_value, config)
        unit = cfg["unit"]
        display = value_str if (value_str == "-" or not unit) else f"{value_str} {unit}"
        self.table.item(row, _COL_VALUE).setText(display)
        # Unit is now independently editable (see _on_item_edited()) -
        # blocked here too, same reason as _rebuild_table()'s initial
        # population: this refresh runs on every tag_changed tick
        # (SimulatorDriver, ~1/s), and setText() unconditionally emits
        # itemChanged in Qt regardless of whether the text actually
        # changed - without blockSignals, that would re-fire
        # _on_item_edited() for the Unit column every single tick.
        self.table.blockSignals(True)
        self.table.item(row, _COL_UNIT).setText(unit)
        self.table.blockSignals(False)

    def on_tag_changed(self, tag_name, new_value, quality):
        row = self._row_for_tag(tag_name)
        if row is None:
            return
        self._refresh_value_cell(row)
        self.table.item(row, _COL_TIMESTAMP).setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _on_item_edited(self, item):
        """Description/Unit/Technical note - the same three fields that
        used to live in AnalogChannelConfigDialog - are now edited here,
        in place, exactly like Digital Inputs/Control Outputs' own
        Description column. Value/Timestamp updates from
        _refresh_value_cell()/on_tag_changed() also fire itemChanged (see
        that method's blockSignals note), so this only ever reacts to the
        three columns actually meant to be edited."""
        col = item.column()
        field = _EDITABLE_COLUMNS.get(col)
        if field is None:
            return
        row = item.row()
        tag_name = self._row_tags[row]
        points = self.tag_manager.get_analog_points()
        point = next((p for p in points if p["tag"] == tag_name), None)
        if point is None:
            return

        new_value = item.text().strip() if field in ("unit",) else item.text()
        old_value = point.get(field, "")
        if new_value == old_value:
            return

        # Execution-time re-check (Task: real per-level permissions) -
        # the ItemIsEditable flag already stops the in-place editor from
        # opening for non-Engineer, but this is the actual save path, so
        # it's checked independently too, not just trusted. Reverts the
        # cell text rather than leaving the edited-but-rejected value
        # visible - see Digital Inputs/Control Outputs for the same
        # pattern.
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, f"Edit Analog Point {_FIELD_LABELS[field]}")
            self.table.blockSignals(True)
            item.setText(old_value)
            self.table.blockSignals(False)
            return

        updated_point = dict(point)
        updated_point[field] = new_value
        self.tag_manager.update_analog_point(tag_name, updated_point)
        ui_logger.log(
            "INFO", "SYSTEM", tag_name,
            f"{_FIELD_LABELS[field]} changed from \"{old_value}\" to \"{new_value}\"",
            "Operator", self.tag_manager.mode, ""
        )
        if field == "unit":
            # The Value column's display embeds the unit suffix - keep it
            # in sync immediately rather than waiting for the next tag
            # update tick.
            self._refresh_value_cell(row)

    # --- configuration --------------------------------------------

    def _selected_row(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            return None
        return selected[0].row()

    def _open_point_config(self, row: int, column: int):
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Edit Analog Point configuration")
            return
        tag_name = self._row_tags[row]
        points = self.tag_manager.get_analog_points()
        point = next((p for p in points if p["tag"] == tag_name), {})

        dialog = AnalogChannelConfigDialog(tag_name=tag_name, config=point, parent=self)
        if not dialog.exec():
            return

        # Description/Unit/Technical note are edited only inline now (see
        # _on_item_edited()) - preserved unchanged here, since the dialog
        # no longer collects them at all.
        updated_point = dict(point)
        updated_point.update(dialog.result_config())
        self.tag_manager.update_analog_point(tag_name, updated_point)

        ui_logger.log(
            "INFO", "SYSTEM", tag_name,
            f"Analog point configuration updated (signal type: {updated_point['signal_type']})",
            "Operator", self.tag_manager.mode, ""
        )

        self._refresh_value_cell(row)

    def _add_point(self):
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Add Analog Point")
            return
        existing_tags = set(self._row_tags)
        dialog = AnalogChannelConfigDialog(existing_tags=existing_tags, parent=self)
        if not dialog.exec():
            return

        tag_name = dialog.result_tag()
        # New point: Description/Unit/Technical note default empty - the
        # dialog no longer collects them, the operator fills them in via
        # the table's own inline editing right after creation, same as
        # any other DI/DO description.
        point = {
            "tag": tag_name,
            "description": "",
            "technical_note": "",
            "unit": "",
            **dialog.result_config(),
        }
        if not self.tag_manager.add_analog_point(point):
            QMessageBox.warning(
                self, tr("pages.analog_inputs.msgbox_add_title"),
                tr("pages.analog_inputs.msgbox_add_duplicate", tag=tag_name)
            )
            return

        ui_logger.log(
            "INFO", "SYSTEM", tag_name, "Analog point added",
            "Operator", self.tag_manager.mode, ""
        )
        self._rebuild_table()

    def _remove_point(self):
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Remove Analog Point")
            return
        row = self._selected_row()
        if row is None:
            QMessageBox.information(
                self, tr("pages.analog_inputs.msgbox_remove_title"),
                tr("pages.analog_inputs.msgbox_remove_select_first"))
            return
        tag_name = self._row_tags[row]

        confirm = QMessageBox.question(
            self, tr("pages.analog_inputs.msgbox_remove_title"),
            tr("pages.analog_inputs.msgbox_remove_confirm", tag=tag_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        if self.tag_manager.remove_analog_point(tag_name):
            ui_logger.log(
                "WARNING", "SYSTEM", tag_name, "Analog point removed",
                "Operator", self.tag_manager.mode, ""
            )
            self._rebuild_table()
