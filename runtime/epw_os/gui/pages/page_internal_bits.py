"""BITY WEWNĘTRZNE - the logic program's internal bits on the panel
(internal bits IN/OUT, owner's decisions 2026-09-22).

One row per bit of the loaded program's registry (they are tags M.<name>
- see core/logic_runtime.py): its direction, description and live
value. An IN bit whose registry entry lets the panel write it gets a
SET / CLEAR pair (a number editor for a REAL register), enabled only
while the operator holds the level the entry names; the write goes
through core/internal_bit_gate.py, the one door for every write from
outside the logic, which audits it. An OUT bit is read-only here - only
the logic writes it.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from epw_os.core.logging import log
from epw_os.gui.logger import ui_logger
from epw_os.gui.table_helpers import apply_table_button_style, set_resizable_columns, style_transparent_cell_container
from epw_os.i18n import tr

COL_ID, COL_DIRECTION, COL_DESCRIPTION, COL_VALUE, COL_WRITERS, COL_SET = range(6)


class _RealValueDialog(QDialog):
    def __init__(self, bit_id: str, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("pages.internal_bits.set_value_title", bit=bit_id))
        layout = QFormLayout(self)
        self.spin = QDoubleSpinBox()
        self.spin.setRange(-1_000_000.0, 1_000_000.0)
        self.spin.setDecimals(3)
        try:
            self.spin.setValue(float(current or 0.0))
        except (TypeError, ValueError):
            self.spin.setValue(0.0)
        layout.addRow(tr("pages.internal_bits.value"), self.spin)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class PageInternalBits(QWidget):
    def __init__(self, tag_manager, access_manager, internal_bits, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.access_manager = access_manager
        self.gate = internal_bits
        self._rows = {}            # bit id -> row
        self._buttons = {}         # bit id -> [buttons]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        title = QLabel(tr("pages.internal_bits.title"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)
        intro = QLabel(tr("pages.internal_bits.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            tr("pages.internal_bits.col_id"), tr("pages.internal_bits.col_direction"),
            tr("pages.internal_bits.col_description"), tr("pages.internal_bits.col_value"),
            tr("pages.internal_bits.col_writers"), tr("pages.internal_bits.col_set"),
        ])
        set_resizable_columns(self.table.horizontalHeader(), [160, 90, 320, 110, 200, 170])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        self.empty = QLabel(tr("pages.internal_bits.none"))
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty)

        self.tag_manager.tag_changed.connect(self._on_tag_changed)
        if hasattr(self.access_manager, "level_changed"):
            self.access_manager.level_changed.connect(self._refresh_buttons)
        self.rebuild()

    # --- rows ------------------------------------------------------------------------------------

    def rebuild(self):
        """The registry as the loaded program declares it now - called at
        construction and after a program (re)load."""
        entries = self.gate.entries() if self.gate is not None else {}
        self.table.setRowCount(0)
        self._rows.clear()
        self._buttons.clear()
        for bit_id in sorted(entries):
            entry = entries[bit_id]
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._rows[bit_id] = row
            direction = entry.get("direction", "OUT")
            self.table.setItem(row, COL_ID, QTableWidgetItem(bit_id))
            self.table.setItem(row, COL_DIRECTION, QTableWidgetItem(
                tr("pages.internal_bits.direction_in") if direction == "IN" else tr("pages.internal_bits.direction_out")))
            self.table.setItem(row, COL_DESCRIPTION, QTableWidgetItem(entry.get("description", "")))
            self.table.setItem(row, COL_VALUE, QTableWidgetItem(self._format(self.tag_manager.get_value(bit_id))))
            self.table.setItem(row, COL_WRITERS, QTableWidgetItem(self._writers_text(entry)))
            if direction == "IN" and entry.get("panel_level"):
                self._add_buttons(row, bit_id, entry)
        self.empty.setVisible(not entries)
        self.table.setVisible(bool(entries))
        self._refresh_buttons()

    def _writers_text(self, entry) -> str:
        if entry.get("direction") != "IN":
            return tr("pages.internal_bits.writers_logic")
        parts = []
        level = entry.get("panel_level")
        if level:
            parts.append(tr("pages.internal_bits.writer_panel", level=tr(f"access.{level.lower()}", level)))
        parts.append(tr("pages.internal_bits.writer_force"))
        if entry.get("remote_write"):
            parts.append(tr("pages.internal_bits.writer_remote"))
        return ", ".join(parts)

    def _add_buttons(self, row, bit_id, entry):
        container = QWidget()
        style_transparent_cell_container(container)
        box = QHBoxLayout(container)
        box.setContentsMargins(2, 2, 2, 2)
        buttons = []
        if entry.get("type") == "REAL":
            button = QPushButton(tr("pages.internal_bits.btn_value"))
            button.clicked.connect(lambda _c=False, b=bit_id: self._set_real(b))
            buttons.append(button)
        else:
            on = QPushButton(tr("pages.internal_bits.btn_set"))
            on.clicked.connect(lambda _c=False, b=bit_id: self._write(b, True))
            off = QPushButton(tr("pages.internal_bits.btn_clear"))
            off.clicked.connect(lambda _c=False, b=bit_id: self._write(b, False))
            buttons.extend([on, off])
        for button in buttons:
            apply_table_button_style(button)
            box.addWidget(button)
        self.table.setCellWidget(row, COL_SET, container)
        self._buttons[bit_id] = buttons

    def _refresh_buttons(self, *_):
        level = getattr(self.access_manager, "level", None)
        for bit_id, buttons in self._buttons.items():
            allowed = self.gate is not None and self.gate.writable_from_panel(bit_id, level)
            for button in buttons:
                button.setEnabled(allowed)
                button.setToolTip("" if allowed else tr("pages.internal_bits.no_access"))

    # --- writing ----------------------------------------------------------------------------------

    def _write(self, bit_id: str, value):
        if self.gate is None:
            return
        actor = getattr(self.access_manager, "level", None) or "Operator"
        ok, reason = self.gate.write(bit_id, value, actor=actor, source="PANEL")
        if not ok:
            ui_logger.log("WARNING", "OPERATION", bit_id, f"Internal bit write refused: {reason}", actor,
                          getattr(self.tag_manager, "mode", ""), "")
            QMessageBox.warning(self, tr("pages.internal_bits.refused_title"),
                                tr("pages.internal_bits.refused_text", bit=bit_id, reason=reason))
            self._refresh_buttons()
            return
        ui_logger.log("INFO", "OPERATION", bit_id, f"Internal bit set to {value!r} from the panel", actor,
                      getattr(self.tag_manager, "mode", ""), "")

    def _set_real(self, bit_id: str):
        dialog = _RealValueDialog(bit_id, self.tag_manager.get_value(bit_id), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._write(bit_id, float(dialog.spin.value()))

    # --- live values ----------------------------------------------------------------------------

    @staticmethod
    def _format(value) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, float):
            return f"{value:.3f}".rstrip("0").rstrip(".") or "0"
        return "" if value is None else str(value)

    def showEvent(self, event):
        super().showEvent(event)
        self.rebuild()            # a program reloaded while the page was hidden

    def _on_tag_changed(self, tag_name, new_value, quality):
        row = self._rows.get(tag_name)
        if row is None:
            if tag_name.split(".", 1)[0] in ("M", "MR", "MW", "MWR"):
                self.rebuild()    # a bit of a newly loaded program
            return
        item = self.table.item(row, COL_VALUE)
        if item is not None:
            item.setText(self._format(new_value))
        else:
            log.debug(f"internal bits page: no value cell for {tag_name}")
