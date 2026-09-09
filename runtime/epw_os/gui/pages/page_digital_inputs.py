from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QLabel, QFrame, QMessageBox, QDialog, QCheckBox, QSpinBox, QDialogButtonBox,
                             QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from epw_os.gui.widgets.synoptic_objects import Lamp
from epw_os.gui.widgets.service_notes_widget import ServiceNotesDialog
from epw_os.gui.logger import ui_logger
from epw_os.gui.table_helpers import (
    set_resizable_columns, set_header_tooltips,
    apply_table_button_style, style_transparent_cell_container,
)
from epw_os.core.access_manager import AccessLevel
from epw_os.core.switching_counters import format_duration
from epw_os.gui.theme_manager import current_colors
from epw_os.i18n import tr

# Address, Tag, Description, State, LED, Timestamp, Closes, Opens, Closed Time, Notes
_COL_CLOSES = 6
_COL_OPENS = 7
_COL_CLOSED_TIME = 8
_COL_NOTES = 9
_COUNTER_COLUMNS = (_COL_CLOSES, _COL_OPENS, _COL_CLOSED_TIME)


class SwitchingThresholdDialog(QDialog):
    """Set (or clear) one device's optional warning threshold (Task:
    "opcjonalny prog ostrzegawczy per aparat") - reached via the
    Closes/Opens/Closed Time columns' right-click menu, Engineer-only.
    Same enable-checkbox + spinbox shape as ScreenSleepDialog
    (settings_popups.py) for a value that's "off unless explicitly
    turned on with a number"."""

    def __init__(self, current_threshold, parent=None):
        super().__init__(parent)
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.digital_inputs.threshold_title"))
        self.setModal(True)
        self.setMinimumWidth(340)
        self.result_threshold = current_threshold

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        header = QLabel(tr("pages.digital_inputs.threshold_title"))
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        hint = QLabel(tr("pages.digital_inputs.threshold_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.chk_enabled = QCheckBox(tr("pages.digital_inputs.threshold_enable"))
        self.chk_enabled.setChecked(current_threshold is not None)
        self.chk_enabled.toggled.connect(self._on_enabled_toggled)
        layout.addWidget(self.chk_enabled)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("pages.digital_inputs.threshold_label")))
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(1, 10_000_000)
        self.spin_threshold.setValue(current_threshold if current_threshold else 100000)
        self.spin_threshold.setEnabled(current_threshold is not None)
        row.addWidget(self.spin_threshold)
        row.addStretch()
        layout.addLayout(row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_enabled_toggled(self, checked):
        self.spin_threshold.setEnabled(checked)

    def _apply(self):
        self.result_threshold = self.spin_threshold.value() if self.chk_enabled.isChecked() else None
        self.accept()


class PageDigitalInputs(QWidget):
    def __init__(self, tag_manager, access_manager, switching_counters=None, service_notes=None, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.access_manager = access_manager
        # Mechanical-wear counters (Task: liczba przelaczen i czas w
        # stanie zamknietym per aparat) - Qt-free, see
        # epw_os/core/switching_counters.py. May be None in isolated
        # widget tests; every counter-related method below guards
        # against that and simply shows nothing/does nothing.
        self.switching_counters = switching_counters
        # Service history (Task: historia serwisowa przypisana do
        # aparatu) - Qt-free, see epw_os/core/service_notes.py. May be
        # None in isolated widget tests; the Notes button still opens
        # (viewing/adding both simply show nothing/refuse gracefully).
        self.service_notes = service_notes

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.digital_inputs"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        self.table = QTableWidget(64, 10)  # Address, Tag, Description, State, LED, Timestamp, Closes, Opens, Closed Time, Notes
        self.table.setHorizontalHeaderLabels([
            tr("pages.common.col_address"), tr("pages.common.col_tag"),
            tr("pages.common.col_description"), tr("pages.common.col_state"),
            tr("pages.common.col_led"), tr("pages.common.col_timestamp"),
            tr("pages.common.col_closes"), tr("pages.common.col_opens"),
            tr("pages.common.col_closed_time"), tr("pages.common.col_notes"),
        ])
        # Task: podpowiedzi - "naglowki kolumn, zwlaszcza mniej
        # oczywiste". Tag/Description/State are already self-explanatory
        # (Task: "nie dodawaj tam, gdzie etykieta mowi wszystko") - skipped.
        set_header_tooltips(self.table, [
            tr("pages.common.tooltip_col_address"), "", "", "",
            tr("pages.common.tooltip_col_led"), tr("pages.common.tooltip_col_timestamp"),
            tr("pages.common.tooltip_col_closes"), tr("pages.common.tooltip_col_opens"),
            tr("pages.common.tooltip_col_closed_time"), tr("pages.common.tooltip_col_notes"),
        ])

        # Address, Tag, Description, State, LED, Timestamp, Closes, Opens, Closed Time, Notes
        set_resizable_columns(self.table.horizontalHeader(), [85, 75, 300, 75, 45, 160, 60, 60, 110, 70])
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.table.verticalHeader().setVisible(False)
        # Only the Description column is editable (double-click / Enter to
        # rename a channel); everything else stays read-only.
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )

        self.leds = {}
        self.notes_buttons = {}

        for i in range(64):
            di_num = i + 1
            tag_name = f"DI{di_num}"
            addr_item = QTableWidgetItem(f"%IX0.{i}")
            tag_item = QTableWidgetItem(tag_name)
            tag = self.tag_manager.get_tag(tag_name)
            desc_text = tag.description if tag else f"Digital Input Channel {di_num}"
            desc_item = QTableWidgetItem(desc_text)

            state_item = QTableWidgetItem(tr("pages.common.state_off"))
            time_item = QTableWidgetItem("-")
            closes_item = QTableWidgetItem("0")
            opens_item = QTableWidgetItem("0")
            closed_time_item = QTableWidgetItem(format_duration(0))

            for item in (addr_item, tag_item, state_item, time_item, closes_item, opens_item, closed_time_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.table.setItem(i, 0, addr_item)
            self.table.setItem(i, 1, tag_item)
            self.table.setItem(i, 2, desc_item)
            self.table.setItem(i, 3, state_item)
            self.table.setItem(i, 5, time_item)
            self.table.setItem(i, _COL_CLOSES, closes_item)
            self.table.setItem(i, _COL_OPENS, opens_item)
            self.table.setItem(i, _COL_CLOSED_TIME, closed_time_item)

            # Simulated LED widget
            led_container = QWidget()
            led_layout = QVBoxLayout(led_container)
            led_layout.setContentsMargins(2,2,2,2)
            led_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            led = Lamp("green")
            led.setFixedSize(20, 20)
            led.update_state(0)
            self.leds[f"DI{di_num}"] = led
            led_layout.addWidget(led)
            self.table.setCellWidget(i, 4, led_container)

            # Task: "dostep z tabel DI/DO" - viewing is unrestricted
            # (GRANICE), so the button itself is always present/enabled;
            # only adding a note (inside the dialog it opens) is gated.
            #
            # Task (button-look fix): wrapped in a small centering
            # container instead of set directly as the cell widget -
            # unwrapped, Qt stretches a cell widget to fill the entire
            # cell (touching every edge, top-anchored rather than
            # centered) - the "jedne przyklejone do krawedzi, inne nie"
            # symptom.
            notes_container = QWidget()
            style_transparent_cell_container(notes_container)
            notes_layout = QHBoxLayout(notes_container)
            notes_layout.setContentsMargins(2, 2, 2, 2)
            notes_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_notes = QPushButton(tr("pages.common.btn_notes"))
            apply_table_button_style(btn_notes)
            btn_notes.setToolTip(tr("pages.common.notes_tooltip"))
            btn_notes.clicked.connect(lambda checked=False, t=tag_name: self._open_notes(t))
            notes_layout.addWidget(btn_notes)
            self.notes_buttons[tag_name] = btn_notes
            self.table.setCellWidget(i, _COL_NOTES, notes_container)

            self._refresh_counter_row(tag_name)

        layout.addWidget(self.table, stretch=1)
        self.tag_manager.tag_changed.connect(self.on_tag_changed)
        self.table.itemChanged.connect(self.on_item_edited)
        self.access_manager.level_changed.connect(self._refresh_edit_permissions)
        self._refresh_edit_permissions()

        # Task (button-look fix): Notes buttons bake their bevel colors
        # in at construction (apply_table_button_style() above) - without
        # this, they'd freeze at whatever theme was active when the page
        # was built instead of following a live theme switch.
        from epw_os.gui.theme_manager import get_theme_manager
        get_theme_manager().theme_changed.connect(self.refresh_theme)

    def refresh_theme(self, *_):
        for btn in self.notes_buttons.values():
            apply_table_button_style(btn)

        # Add right click simulation context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu_requested)

    def _refresh_edit_permissions(self, *_):
        """Description is Engineer-only (Task: real per-level
        permissions). Toggling ItemIsEditable per row is the visual half;
        on_item_edited() below is the real, execution-time half.

        blockSignals around the loop: QTableWidgetItem.setFlags() can
        itself emit itemChanged (observed directly - not every Qt
        version/build documents this), which would otherwise reach
        on_item_edited() below on every call to this method, including
        the one at construction time - harmless with a real TagManager
        (its get_tag() already matches the displayed text, so
        on_item_edited()'s own "did the text actually change" guard
        catches it first) but not something to rely on."""
        can_edit = self.access_manager.has_access(AccessLevel.ENGINEER)
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 2)
            if item is None:
                continue
            flags = item.flags()
            item.setFlags(flags | Qt.ItemFlag.ItemIsEditable if can_edit
                          else flags & ~Qt.ItemFlag.ItemIsEditable)
        self.table.blockSignals(False)

    def _on_context_menu_requested(self, pos):
        """Dispatches by column: the counter columns get their own
        maintenance menu (Reset/Threshold - Engineer-only, works in any
        mode); everything else keeps the original simulation-only Force
        menu exactly as it was (open_simulation_menu() below is
        untouched, including its own access/mode gating and the
        existing "denial audited" behavior some tests already depend
        on)."""
        col = self.table.columnAt(pos.x())
        if col in _COUNTER_COLUMNS:
            self.open_counter_menu(pos)
        else:
            self.open_simulation_menu(pos)

    def open_simulation_menu(self, pos):
        if self.tag_manager.mode != "SIMULATION MODE":
            return
        # Force-simulating a DI is the same commissioning/testing power
        # as Control Outputs' Force button - Engineer-only there, so
        # Engineer-only here too (Task's permission matrix doesn't call
        # this out by name, but the existing Force feature it mirrors is
        # explicitly Engineer-only).
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Force Digital Input (simulation)")
            return

        row = self.table.rowAt(pos.y())
        if row >= 0:
            di_num = row + 1
            tag_name = f"DI{di_num}"

            from PySide6.QtWidgets import QMenu
            menu = QMenu(self)
            c = current_colors()
            menu.setStyleSheet(f"background: {c['panel_bg']}; border: 2px outset {c['bevel_light']};")

            act_on = menu.addAction(tr("pages.digital_inputs.menu_force_on"))
            act_off = menu.addAction(tr("pages.digital_inputs.menu_force_off"))
            act_toggle = menu.addAction(tr("pages.digital_inputs.menu_toggle"))
            act_pulse = menu.addAction(tr("pages.digital_inputs.menu_pulse"))

            action = menu.exec(self.table.viewport().mapToGlobal(pos))

            if action == act_on:
                self.tag_manager.update_tag(tag_name, 1)
            elif action == act_off:
                self.tag_manager.update_tag(tag_name, 0)
            elif action == act_toggle:
                val = 1 if self.table.item(row, 3).text() == tr("pages.common.state_off") else 0
                self.tag_manager.update_tag(tag_name, val)
            elif action == act_pulse:
                self.tag_manager.update_tag(tag_name, 1)
                from PySide6.QtCore import QTimer
                QTimer.singleShot(500, lambda: self.tag_manager.update_tag(tag_name, 0))

    # --- switching counters: display, reset, threshold (Task) ----------

    def open_counter_menu(self, pos):
        if self.switching_counters is None:
            return
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        tag_name = f"DI{row + 1}"

        # Reset/threshold are maintenance actions, not simulation tools -
        # available in any mode (GRANICE doesn't restrict this to
        # SIMULATION MODE the way Force is; a device is replaced on real,
        # live hardware, not in simulation).
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Switching counter maintenance")
            return

        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        c = current_colors()
        menu.setStyleSheet(f"background: {c['panel_bg']}; border: 2px outset {c['bevel_light']};")
        act_reset = menu.addAction(tr("pages.digital_inputs.menu_reset_counter"))
        act_threshold = menu.addAction(tr("pages.digital_inputs.menu_set_threshold"))

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_reset:
            self._reset_counter(tag_name)
        elif action == act_threshold:
            self._configure_threshold(tag_name)

    def _reset_counter(self, tag_name):
        """Task: "reczne zerowanie licznika... do uzycia po wymianie
        aparatu" - Engineer-only (re-checked here too, in case access
        lapsed between the menu opening and the click - same pattern as
        every other Engineer-gated action in this app), confirmed
        before acting (destructive, not reversible), and recorded to
        the audit log, not just the operational Event Recorder."""
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Reset switching counter")
            return
        reply = QMessageBox.question(
            self, tr("pages.digital_inputs.reset_confirm_title"),
            tr("pages.digital_inputs.reset_confirm_message", tag=tag_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        old = self.switching_counters.reset_counter(tag_name)
        self._refresh_counter_row(tag_name)
        detail = f"{tag_name}: switching counter reset (was {old['closes']} closes, {old['opens']} opens)"
        ui_logger.log("WARNING", "SYSTEM", tag_name, "Switching counter reset", "Engineer", self.tag_manager.mode, "")
        self._audit("COUNTER_RESET", detail)

    def _configure_threshold(self, tag_name):
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Set switching counter threshold")
            return
        current = self.switching_counters.get_snapshot(tag_name).get("warning_threshold")
        dlg = SwitchingThresholdDialog(current, self)
        if not dlg.exec():
            return
        new_threshold = dlg.result_threshold
        if new_threshold == current:
            return
        self.switching_counters.set_warning_threshold(tag_name, new_threshold)
        self._refresh_counter_row(tag_name)
        ui_logger.log(
            "INFO", "SYSTEM", tag_name,
            f"Switching counter warning threshold set to {new_threshold}", "Engineer", self.tag_manager.mode, "",
        )
        self._audit("SETTING_CHANGE", f"{tag_name}: switching counter warning threshold set to {new_threshold}")

    # --- service history (Task) -----------------------------------------

    def _open_notes(self, tag_name):
        """Task: "Zakladka Notatki... oraz dostep z tabel DI/DO" - a
        standalone dialog here (this table has no larger "device
        properties" window of its own the way Main View's synoptic
        devices do). Opening it (viewing) needs no access check at all
        (Task: "podglad: dla kazdego, bez ograniczen") - only adding a
        note inside it is gated, by ServiceNotesWidget itself."""
        idx = int(tag_name[2:]) - 1
        properties = {
            "Tag": tag_name,
            "Description": self.table.item(idx, 2).text() if self.table.item(idx, 2) else "",
        }
        if self.switching_counters is not None:
            snap = self.switching_counters.get_snapshot(tag_name)
            properties["Closes"] = str(snap["closes"])
            properties["Opens"] = str(snap["opens"])
            properties["Closed Time"] = format_duration(snap["closed_seconds"])
        dlg = ServiceNotesDialog(tag_name, self.service_notes, self.access_manager, properties, self)
        dlg.exec()

    def _audit(self, event_type, detail):
        # Best-effort: main_window.audit_logger may not exist in isolated
        # widget tests that construct this page without a real MainWindow -
        # same pattern as page_protection.py's _audit().
        audit_logger = getattr(self.window(), "audit_logger", None)
        if audit_logger is not None:
            audit_logger.record(event_type, "Engineer", detail, success=True)

    def _refresh_counter_row(self, tag_name):
        """(Re)renders one row's Closes/Opens/Closed Time cells from the
        live counter snapshot, and colors the Closes cell with the
        theme's warning color once the (optional) threshold is reached
        (Task 7). Safe to call even with no switching_counters wired up,
        or before the row's items exist yet (construction time)."""
        try:
            idx = int(tag_name[2:]) - 1
        except (ValueError, IndexError):
            # Deliberate, not logged: `tag_name` is expected to be a
            # DIn/DOn-shaped name (callers already filter for that), but
            # this is defensive against anything else reaching here
            # anyway - would fire routinely, not a problem worth
            # surfacing.
            return
        if idx < 0 or idx >= self.table.rowCount():
            return
        closes_item = self.table.item(idx, _COL_CLOSES)
        opens_item = self.table.item(idx, _COL_OPENS)
        closed_time_item = self.table.item(idx, _COL_CLOSED_TIME)
        if closes_item is None or opens_item is None or closed_time_item is None:
            return

        if self.switching_counters is None:
            closes_item.setText("0")
            opens_item.setText("0")
            closed_time_item.setText(format_duration(0))
            return

        snap = self.switching_counters.get_snapshot(tag_name)
        closes_item.setText(str(snap["closes"]))
        opens_item.setText(str(snap["opens"]))
        closed_time_item.setText(format_duration(snap["closed_seconds"]))

        c = current_colors()
        if self.switching_counters.is_over_threshold(tag_name):
            closes_item.setBackground(QColor(c["state_warning"]))
        else:
            closes_item.setBackground(QColor(c["field_bg"]))

    def on_tag_changed(self, tag_name, new_value, quality):
        if tag_name.startswith("DI"):
            try:
                idx = int(tag_name[2:]) - 1
                state_str = tr("pages.common.state_on") if new_value == 1 else tr("pages.common.state_off")
                self.table.item(idx, 3).setText(state_str)
                self.leds[tag_name].update_state(new_value)

                from datetime import datetime
                t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.table.item(idx, 5).setText(t)

                self._refresh_counter_row(tag_name)
            except ValueError:
                # Deliberate, not logged: only a tag literally named
                # "DI<non-numeric>" could reach int() here (the prefix
                # check just above already filters everything else) -
                # harmless no-op, not worth surfacing.
                pass

    def on_item_edited(self, item):
        # Only the Description column (2) is user-editable; State/Timestamp
        # updates from on_tag_changed() also fire itemChanged, so guard here.
        # itemChanged only fires once the cell editor commits (Enter / focus
        # lost), never per keystroke, so this is already the "final value".
        if item.column() != 2:
            return
        di_num = item.row() + 1
        tag_name = f"DI{di_num}"
        new_desc = item.text()

        tag = self.tag_manager.get_tag(tag_name)
        old_desc = tag.description if tag else ""
        if new_desc == old_desc:
            return

        # Execution-time re-check (Task: real per-level permissions) -
        # see PageControlOutputs._on_output_item_edited() for the same
        # pattern and reasoning.
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Edit Digital Input description")
            self.table.blockSignals(True)
            item.setText(old_desc)
            self.table.blockSignals(False)
            return

        self.tag_manager.set_description(tag_name, new_desc)
        ui_logger.log(
            "INFO", "SYSTEM", tag_name,
            f"Description changed from \"{old_desc}\" to \"{new_desc}\"",
            "Operator", self.tag_manager.mode, ""
        )
