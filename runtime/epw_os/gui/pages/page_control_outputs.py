from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTableWidget, QTableWidgetItem)
from PySide6.QtCore import Qt
from epw_os.gui.widgets.synoptic_objects import Lamp
from epw_os.gui.widgets.popups import ForceOutputConfirmPopup
from epw_os.gui.widgets.service_notes_widget import ServiceNotesDialog
from epw_os.gui.logger import ui_logger
from epw_os.gui.table_helpers import (
    set_resizable_columns, set_header_tooltips,
    apply_table_button_style, style_transparent_cell_container,
)
from epw_os.core.access_manager import AccessLevel
from epw_os.core.addressing import is_address, parse_address
from epw_os.gui.theme_manager import get_theme_manager, current_colors
from epw_os.i18n import tr
from datetime import datetime


class SwitchingDeviceRow:
    """Owns one row of the Switching Devices table (Address/Tag/Description/
    State/LED/Timestamp/Force) - the table-cell equivalent of what
    SwitchingDevicePanel used to own as a QFrame. Feedback state comes live
    from tag_manager (di_tag); the Force button only exists for
    is_controllable rows and only while Engineer access is active."""

    def __init__(self, table, row, do_tag, designation, default_description, di_tag,
                 tag_manager, access_manager, is_controllable=True, service_notes=None):
        self.table = table
        self.row = row
        self.do_tag = do_tag
        self.designation = designation
        self.di_tag = di_tag
        self.tag_manager = tag_manager
        self.access_manager = access_manager
        self.is_controllable = is_controllable
        self.service_notes = service_notes

        addr_item = QTableWidgetItem(f"%QX0.{row}")
        tag_item = QTableWidgetItem(do_tag)

        # Description persistence is keyed by the visible DO tag (do_tag),
        # not the internal designation - matches Digital Inputs, which
        # keys by the visible Tag column text too.
        self.description = tag_manager.get_output_description(do_tag, default_description)
        self.desc_item = QTableWidgetItem(self.description)
        self._apply_edit_permission()

        state_item = QTableWidgetItem(tr("pages.common.state_open"))
        time_item = QTableWidgetItem("-")

        for item in (addr_item, tag_item, state_item, time_item):
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        table.setItem(row, 0, addr_item)
        table.setItem(row, 1, tag_item)
        table.setItem(row, 2, self.desc_item)
        table.setItem(row, 3, state_item)
        table.setItem(row, 5, time_item)

        led_container = QWidget()
        led_layout = QVBoxLayout(led_container)
        led_layout.setContentsMargins(2, 2, 2, 2)
        led_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.led = Lamp("green")
        self.led.setFixedSize(20, 20)
        self.led.update_state(0)
        led_layout.addWidget(self.led)
        table.setCellWidget(row, 4, led_container)

        # Task: historia serwisowa - "dostep z tabel DI/DO". Always
        # present/enabled (viewing is unrestricted); only adding a note
        # inside the dialog it opens is Operator-gated.
        #
        # Task (button-look fix): wrapped in a small centering container
        # like Force below, rather than set directly as the cell widget -
        # unwrapped, Qt stretches a cell widget to fill the ENTIRE cell
        # (touching every edge, no breathing room, and top-anchored
        # rather than centered) - the "jedne przyklejone do krawedzi,
        # inne nie" symptom. Built BEFORE refresh_force_button() below,
        # since that call re-styles self.btn_notes too (see its
        # docstring) and needs it to already exist.
        self.notes_container = QWidget()
        style_transparent_cell_container(self.notes_container)
        notes_layout = QHBoxLayout(self.notes_container)
        notes_layout.setContentsMargins(2, 2, 2, 2)
        notes_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_notes = QPushButton(tr("pages.common.btn_notes"))
        apply_table_button_style(self.btn_notes)
        self.btn_notes.setToolTip(tr("pages.common.notes_tooltip"))
        self.btn_notes.clicked.connect(self._open_notes)
        notes_layout.addWidget(self.btn_notes)
        table.setCellWidget(row, 7, self.notes_container)

        self.force_container = QWidget()
        style_transparent_cell_container(self.force_container)
        self.force_layout = QHBoxLayout(self.force_container)
        self.force_layout.setContentsMargins(2, 2, 2, 2)
        self.force_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_force = None
        table.setCellWidget(row, 6, self.force_container)
        self.refresh_force_button()

    def _apply_edit_permission(self):
        """Description is Engineer-only (Task: real per-level
        permissions). Toggling ItemIsEditable is the visual half - a
        read-only cell shows its content but the in-place editor never
        opens; PageControlOutputs._on_output_item_edited() below is the
        real, execution-time half, re-checking access independently of
        this flag (defense in depth, not "trust the widget state").

        blockSignals: QTableWidgetItem.setFlags() can itself emit
        itemChanged (observed directly) - harmless with a real
        TagManager (_on_output_item_edited()'s own "did the text
        actually change" guard catches it first) but not something to
        rely on, especially the very first call here at construction
        time, before self.description is even meaningfully comparable."""
        can_edit = self.access_manager.has_access(AccessLevel.ENGINEER)
        self.table.blockSignals(True)
        flags = self.desc_item.flags()
        self.desc_item.setFlags(flags | Qt.ItemFlag.ItemIsEditable if can_edit
                                 else flags & ~Qt.ItemFlag.ItemIsEditable)
        self.table.blockSignals(False)

    def refresh_force_button(self, *_):
        """Called at construction and on every access_level_changed, so the
        Force button appears/disappears live without needing to leave and
        re-enter the page. Also refreshes the Description column's
        edit-permission flag (same trigger, same reason).

        Also called on every theme_changed (via PageControlOutputs.
        refresh_theme() below) - re-applying apply_table_button_style()
        to the always-present Notes button here too (not just Force,
        which gets rebuilt from scratch anyway) is what keeps its bevel
        colors current instead of freezing at whatever theme was active
        when the row was first built."""
        apply_table_button_style(self.btn_notes)
        self._apply_edit_permission()
        if self.btn_force is not None:
            self.force_layout.removeWidget(self.btn_force)
            self.btn_force.deleteLater()
            self.btn_force = None
        if self.is_controllable and self.access_manager.has_access(AccessLevel.ENGINEER):
            self.btn_force = QPushButton(tr("pages.common.btn_force"))
            self.btn_force.setToolTip(tr("pages.common.force_tooltip"))
            # Task (button-look fix): apply_table_button_style() redraws
            # the full Win98 bevel every time (a partial local
            # setStyleSheet - just the color, as this used to be - loses
            # the inherited border entirely, which was the actual cause
            # of Force looking flat) - `extra_css` adds just the red text
            # on top, same as before.
            apply_table_button_style(
                self.btn_force,
                extra_css=f"QPushButton {{ color: {current_colors()['action_danger']}; }}",
            )
            self.btn_force.clicked.connect(self.attempt_force)
            self.force_layout.addWidget(self.btn_force)

    def attempt_force(self):
        current_val = self.tag_manager.get_value(self.di_tag)
        current_state = tr("pages.common.state_closed") if current_val == 1 else tr("pages.common.state_open")
        # target_command is a CommandManager protocol keyword (matched
        # against command definitions in epw_core.py), not display text -
        # must stay "OPEN"/"CLOSE" regardless of UI language.
        target_command = "OPEN" if current_val == 1 else "CLOSE"

        popup = ForceOutputConfirmPopup(self.designation, current_state, target_command, tr("access.engineer"), self.table)
        popup.move(self.table.mapToGlobal(self.table.rect().center()))
        if not popup.exec():
            ui_logger.log("INFO", "OPERATION", self.designation, "Manual force cancelled by operator", "Engineer", self.tag_manager.mode, "")
            return

        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            # Engineer access could have timed out in the seconds the
            # confirmation dialog was open - re-check right before dispatch,
            # not just when the button was first shown.
            ui_logger.log("WARNING", "OPERATION", self.designation, "Manual force rejected: Engineer access expired", "Operator", self.tag_manager.mode, "")
            self.refresh_force_button()
            return

        main_window = self.table.window()
        record = main_window.command_manager.request_command_ex(
            self.designation, target_command, user="Engineer", source="GUI-Manual-Force"
        )
        if record.state in ("BLOCKED", "FAILED"):
            ui_logger.log("WARNING", "OPERATION", self.designation, "Manual force rejected", "Engineer", self.tag_manager.mode, record.reason)
            return

        ui_logger.log("INFO", "OPERATION", self.designation, f"Manual FORCE {target_command} dispatched via CommandManager ({record.state})", "Engineer", self.tag_manager.mode, "")

    def on_tag_changed(self, tag_name, new_value, quality):
        if tag_name != self.di_tag:
            return
        state_str = tr("pages.common.state_closed") if new_value == 1 else tr("pages.common.state_open")
        self.table.item(self.row, 3).setText(state_str)
        self.led.update_state(1 if new_value == 1 else 0)
        t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.table.item(self.row, 5).setText(t)

    def _open_notes(self):
        # Task: historia serwisowa - keyed by this row's own DO tag
        # (do_tag) - a device viewed from Control Outputs is identified
        # by its command/routing tag here, same as its Description
        # (output_description) already is; Digital Inputs' own DI rows
        # (and Main View, via counter_tag) key by the DI tag instead -
        # same split this app's descriptions already have for DO01-04
        # (see set_output_description()'s docstring in project_manager.py).
        properties = {"Tag": self.do_tag, "Description": self.description}
        dlg = ServiceNotesDialog(self.do_tag, self.service_notes, self.access_manager, properties, self.table)
        dlg.exec()


class PageControlOutputs(QWidget):
    def __init__(self, tag_manager, access_manager, service_notes=None, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.access_manager = access_manager
        self.service_notes = service_notes

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("pages.control_outputs.title"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        # Switching Devices - table view, same layout family as Digital
        # Inputs (Address/Tag/Description/State/LED/Timestamp), plus a
        # Force column that only ever shows content for Engineer access.
        # In Operator/User mode this is a pure read-only table - no
        # buttons at all.
        #
        # The former Heating/Ventilation/Lighting/Alarm Test panels (and
        # the "Water System" placeholder) were removed - they were never
        # wired to tag_manager (simulated locally, one had a NameError bug
        # on an undefined `delay` variable) and duplicate functionality
        # that belongs to the future Synoptic Editor as drawn process
        # objects on synoptic screens, not standalone OS panels. The
        # "SECTION 1 - SWITCHING DEVICES" header is gone too - there is
        # only one section left, so it labelled nothing.

        # (do_tag, designation, default_description, feedback_tag, is_controllable)
        # Task "migracja adresacji": was a fixed 4 hardcoded DO01-DO04 ->
        # DI1-DI4 pairs (real feedback, a flat-scheme artifact tied to
        # specific reserved slot numbers 1-4 - there is no such thing as
        # a project-wide "slot number" left to be special about) plus
        # `range(5, 65)` for the rest. Every real DO channel configure()
        # produced is now self-contained - own tag is both the command
        # output and its own feedback - the SAME pattern the old flat
        # scheme already used for its own majority case (DO05-DO64); see
        # epw_core.py's own default command definitions for the mirrored
        # decision on the command-routing side. Sorted by (card, channel)
        # for a stable, predictable row order across restarts. The
        # designation (command-routing key) is just the DO tag itself, no
        # project-specific device name lives in this code - which real
        # device each channel is on a given site is entirely a matter of
        # the operator-editable Description column below, persisted per
        # DO tag in project.json's output_descriptions.
        do_tags = sorted(
            (t.name for t in self.tag_manager.list_tags() if is_address(t.name, "DO")),
            key=lambda name: (parse_address(name)[0], parse_address(name)[2]),
        )
        device_defs = [(do_tag, do_tag, do_tag, do_tag, True) for do_tag in do_tags]

        self.table = QTableWidget(len(device_defs), 8)
        self.table.setHorizontalHeaderLabels([
            tr("pages.common.col_address"), tr("pages.common.col_tag"),
            tr("pages.common.col_description"), tr("pages.common.col_state"),
            tr("pages.common.col_led"), tr("pages.common.col_timestamp"),
            tr("pages.common.col_force"), tr("pages.common.col_notes"),
        ])
        set_header_tooltips(self.table, [
            tr("pages.common.tooltip_col_address"), "", "", "",
            tr("pages.common.tooltip_col_led"), tr("pages.common.tooltip_col_timestamp"),
            "", tr("pages.common.tooltip_col_notes"),
        ])
        # Address, Tag, Description, State, LED, Timestamp, Force, Notes
        set_resizable_columns(self.table.horizontalHeader(), [85, 75, 300, 75, 45, 160, 70, 70])
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )

        self.device_rows = []
        for i, (do_tag, designation, default_desc, di_tag, controllable) in enumerate(device_defs):
            self.device_rows.append(
                SwitchingDeviceRow(self.table, i, do_tag, designation, default_desc, di_tag,
                                    self.tag_manager, self.access_manager, is_controllable=controllable,
                                    service_notes=self.service_notes)
            )

        layout.addWidget(self.table, stretch=1)

        self.table.itemChanged.connect(self._on_output_item_edited)
        self.tag_manager.tag_changed.connect(self._on_switching_device_tag_changed)
        self.access_manager.level_changed.connect(self._on_access_level_changed)
        get_theme_manager().theme_changed.connect(self.refresh_theme)

    def refresh_theme(self, *_):
        """The Force button's color is baked in at creation time
        (refresh_force_button() above), so re-running that same,
        already-idempotent method is enough to re-color it under the new
        theme."""
        for row_obj in self.device_rows:
            row_obj.refresh_force_button()

    def _on_output_item_edited(self, item):
        # Only the Description column (2) is user-editable; State/Timestamp
        # updates from _on_switching_device_tag_changed() also fire
        # itemChanged, so guard here - same pattern as Digital Inputs.
        if item.column() != 2:
            return
        row_obj = self.device_rows[item.row()]
        new_desc = item.text()
        old_desc = row_obj.description
        if new_desc == old_desc:
            return
        # Execution-time re-check (Task: real per-level permissions) -
        # the ItemIsEditable flag already stops the in-place editor from
        # opening for non-Engineer, but this is the actual save path, so
        # it's checked independently too, not just trusted. Reverts the
        # cell text rather than leaving the edited-but-rejected value
        # visible.
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Edit Control Outputs description")
            self.table.blockSignals(True)
            item.setText(old_desc)
            self.table.blockSignals(False)
            return
        row_obj.description = new_desc
        self.tag_manager.set_output_description(row_obj.do_tag, new_desc)
        ui_logger.log(
            "INFO", "SYSTEM", row_obj.do_tag,
            f"Description changed from \"{old_desc}\" to \"{new_desc}\"",
            "Operator", self.tag_manager.mode, ""
        )

    def _on_switching_device_tag_changed(self, tag_name, new_value, quality):
        for row_obj in self.device_rows:
            row_obj.on_tag_changed(tag_name, new_value, quality)

    def _on_access_level_changed(self, *_):
        for row_obj in self.device_rows:
            row_obj.refresh_force_button()
