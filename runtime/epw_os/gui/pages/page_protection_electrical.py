from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
                             QLabel, QCheckBox, QComboBox,
                             QDoubleSpinBox, QSpinBox, QHBoxLayout, QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from datetime import datetime
from epw_os.gui.logger import ui_logger
from epw_os.gui.widgets.popups import SettingChangePopup
from epw_os.gui.table_helpers import set_resizable_columns
from epw_os.core.protection_manager import ProtectionManager
from epw_os.core.access_manager import AccessLevel
from epw_os.gui.theme_manager import get_theme_manager, neutral_text_style
from epw_os.i18n import tr

class PageProtectionElectrical(QWidget):
    """Task (page-split): ZABEZPIECZENIA > Elektryczne - the exact
    successor of the old, single "Nastawy zabezpieczen" page, unchanged
    in every behavior. ONLY the non-electrical categories that used to
    also live here (Environmental/Communication/System) are gone - they
    were pure UI facades with no live tag binding at all, deleted per
    this task's own analysis rather than kept or relocated (see
    protection_manager.py's own comment, and SESSION_REPORT.md for the
    itemized list). Still reuses the "protection_settings" feature id
    (see feature_config.py's own comment on why) and still owns the one
    ProtectionManager instance Engineer Mode's verification page also
    depends on (main_window.py)."""

    def __init__(self, tag_manager, access_manager, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.access_manager = access_manager
        self.protection_manager = ProtectionManager()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.protection_electrical"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_reset_stats = QPushButton(tr("pages.protection.btn_reset_stats"))
        self.btn_reset_stats.setToolTip(tr("pages.protection.tooltip_btn_reset_stats"))
        self.btn_reset_stats.clicked.connect(self.reset_all_statistics)
        toolbar.addWidget(self.btn_reset_stats)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(11)
        # Columns are addressed by index everywhere in this file (never by
        # header text), so translating these labels is safe.
        self.tree.setHeaderLabels([
            tr("pages.protection.col_enabled"), tr("pages.protection.col_protection_stage"),
            tr("pages.protection.col_source"), tr("pages.protection.col_setting"),
            tr("pages.protection.col_hysteresis"), tr("pages.protection.col_delay"),
            tr("pages.protection.col_action"), tr("pages.protection.col_status"),
            tr("pages.protection.col_actual_value"), tr("pages.protection.col_statistics"),
            tr("pages.protection.col_logic"),
        ])
        # Task: podpowiedzi - "naglowki kolumn, zwlaszcza mniej
        # oczywiste". Enabled/Protection-Stage/Source/Setting/Action/Status
        # are already self-explanatory - skipped.
        header_tooltips = {
            4: tr("pages.protection.tooltip_col_hysteresis"),
            5: tr("pages.protection.tooltip_col_delay"),
            8: tr("pages.protection.tooltip_col_actual_value"),
            9: tr("pages.protection.tooltip_col_statistics"),
            10: tr("pages.protection.tooltip_col_logic"),
        }
        header_item = self.tree.headerItem()
        for col, text in header_tooltips.items():
            header_item.setToolTip(col, text)

        # Enabled, Protection/Stage, Source, Setting, Hysteresis, Delay,
        # Action, Status, Actual Value, Statistics, Logic - all draggable.
        set_resizable_columns(self.tree.header(),
                              [70, 220, 90, 90, 90, 90, 110, 90, 110, 110, 90])
        # Ensure horizontal scrollbar appears when wide instead of truncating
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        layout.addWidget(self.tree, stretch=1)

        self.populate_tree()
        self.update_mode()
        self.tag_manager.tag_changed.connect(self.on_tag_changed)
        self.access_manager.level_changed.connect(self.update_mode)
        self.access_manager.level_changed.connect(self._refresh_reset_button)
        self._refresh_reset_button()
        get_theme_manager().theme_changed.connect(self.refresh_theme)

    def refresh_theme(self, *_):
        """Status/grouping colors are baked into QTreeWidgetItems at
        populate time (get_status_color(), the group/item backgrounds
        above) rather than read live at paint time - a full rebuild
        (already the existing pattern for Reset Statistics) is the
        simplest correct way to re-apply them under a new theme."""
        self.populate_tree()
        self.update_mode()
        
    def get_status_color(self, status):
        theme_colors = get_theme_manager().current_colors()
        colors = {
            "READY": QColor(theme_colors["state_ok"]),
            "PICKUP": QColor(theme_colors["state_warning"]),
            "TRIP": QColor(theme_colors["state_alarm"]),
            "BLOCKED": QColor(theme_colors["state_info"]),
            "DISABLED": QColor(theme_colors["state_neutral"]),
            "UNKNOWN": QColor(theme_colors["state_unknown"]),
        }
        return colors.get(status.upper(), QColor(theme_colors["state_unknown"]))

    def populate_tree(self):
        self.tree.clear()
        
        # Group by category
        categories = {}
        for prot_id, prot_func in self.protection_manager.protections.items():
            cat = prot_func.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((prot_id, prot_func))
            
        theme_colors = get_theme_manager().current_colors()
        group_bg = QColor(theme_colors["tree_group_bg"])
        item_bg = QColor(theme_colors["tree_item_bg"])

        for cat, prots in categories.items():
            cat_item = QTreeWidgetItem(self.tree)
            cat_item.setText(1, cat.upper())
            cat_item.setBackground(0, group_bg)
            for col in range(1, 11):
                cat_item.setBackground(col, group_bg)

            for prot_id, prot_func in prots:
                root_item = QTreeWidgetItem(cat_item)
                root_item.setText(1, prot_id)
                root_item.setText(2, prot_func.source)
                root_item.setBackground(0, item_bg)
                for col in range(1, 11):
                    root_item.setBackground(col, item_bg)
                    
                for stage in prot_func.stages:
                    child_item = QTreeWidgetItem(root_item)
                    child_item.setText(1, stage.name)
                    
                    # Checkbox
                    chk_enabled = QCheckBox()
                    chk_enabled.setChecked(stage.enabled)
                    chk_enabled.stateChanged.connect(
                        lambda state, p=prot_id, s=stage, w=chk_enabled: self.on_stage_enabled_changed(p, s, state, w))
                    self.tree.setItemWidget(child_item, 0, chk_enabled)
                    
                    # Setting
                    spn_setting = QDoubleSpinBox()
                    spn_setting.setMinimumWidth(80)
                    spn_setting.setRange(-9999, 9999)
                    spn_setting.setDecimals(1)
                    spn_setting.setValue(stage.setting)
                    spn_setting.editingFinished.connect(
                        lambda p=prot_id, s=stage, w=spn_setting: self.on_setting_edit_finished(p, s, "Setting", "setting", w))
                    self.tree.setItemWidget(child_item, 3, spn_setting)

                    # Hysteresis
                    if stage.hysteresis is not None:
                        spn_hyst = QDoubleSpinBox()
                        spn_hyst.setMinimumWidth(80)
                        spn_hyst.setRange(0, 9999)
                        spn_hyst.setDecimals(1)
                        spn_hyst.setValue(stage.hysteresis)
                        spn_hyst.editingFinished.connect(
                            lambda p=prot_id, s=stage, w=spn_hyst: self.on_setting_edit_finished(p, s, "Hysteresis", "hysteresis", w))
                        self.tree.setItemWidget(child_item, 4, spn_hyst)
                    else:
                        child_item.setText(4, "N/A")

                    # Delay
                    spn_delay = QSpinBox()
                    spn_delay.setMinimumWidth(80)
                    spn_delay.setRange(0, 60000)
                    spn_delay.setValue(stage.delay_ms)
                    spn_delay.editingFinished.connect(
                        lambda p=prot_id, s=stage, w=spn_delay: self.on_setting_edit_finished(p, s, "Delay", "delay_ms", w))
                    self.tree.setItemWidget(child_item, 5, spn_delay)
                    
                    # Action
                    cmb_action = QComboBox()
                    cmb_action.setMinimumWidth(100)
                    # Deliberately NOT translated - setCurrentText(stage.action)
                    # below and on_action_changed() both match/store this
                    # combo's visible text directly against stage.action (a
                    # ProtectionManager core data field, protection/safety
                    # adjacent). Translating the items would either break
                    # setCurrentText's match (blank selection) or start
                    # persisting Polish text into stage.action - out of
                    # scope per GRANICE ("nie zmieniaj logiki"). Flagged in
                    # SESSION_REPORT.md.
                    cmb_action.addItems(["Disabled", "Information", "Warning", "Trip", "Custom Logic"])
                    cmb_action.setCurrentText(stage.action)
                    cmb_action.currentTextChanged.connect(
                        lambda text, p=prot_id, s=stage, w=cmb_action: self.on_action_changed(p, s, text, w))
                    self.tree.setItemWidget(child_item, 6, cmb_action)
                    
                    # Status - deliberately NOT translated: stage.status is
                    # matched literally against get_status_color()'s keys
                    # (READY/PICKUP/TRIP/.../UNKNOWN) and is core
                    # ProtectionManager state, protection/safety-adjacent
                    # data - out of scope to touch. See SESSION_REPORT.md.
                    child_item.setText(7, stage.status)
                    child_item.setBackground(7, self.get_status_color(stage.status))

                    # Actual Value
                    val_str = "--- " + prot_func.unit
                    child_item.setText(8, val_str)

                    # Statistics
                    stats = tr("pages.protection.stats_template", pickups=stage.pickups, trips=stage.trips,
                               optime=stage.operating_time, lp=stage.last_pickup, lt=stage.last_trip)
                    child_item.setText(9, stats)

                    # Logic Link
                    # Removed integrated Logic Studio coupling.
                    lbl_logic = QLabel(tr("pages.protection.logic_linked", id=f"{prot_id}_{stage.name}"))
                    lbl_logic.setStyleSheet(neutral_text_style("font-size: 10px;"))
                    self.tree.setItemWidget(child_item, 10, lbl_logic)

                root_item.setExpanded(True)
            cat_item.setExpanded(True)
            
        # Let ResizeToContents do the work for all columns to prevent truncation
        for col in range(self.tree.columnCount()):
            self.tree.resizeColumnToContents(col)

    def _audit(self, detail):
        # Best-effort: main_window.audit_logger may not exist in isolated
        # widget tests that construct this page without a real MainWindow.
        main_window = self.window()
        audit_logger = getattr(main_window, "audit_logger", None)
        if audit_logger is not None:
            audit_logger.record("SETTING_CHANGE", "Engineer", detail, success=True)

    def _deny_and_revert_checkbox(self, checkbox, old_checked):
        self.window().deny_access(AccessLevel.ENGINEER, "Edit Protection Settings (stage enable)")
        checkbox.blockSignals(True)
        checkbox.setChecked(old_checked)
        checkbox.blockSignals(False)

    def on_stage_enabled_changed(self, prot_id, stage, state, checkbox):
        enabled = state == 2
        # Execution-time re-check (Task: real per-level permissions) -
        # update_mode() already disables this checkbox for non-Engineer,
        # but this is the actual save path, checked independently too.
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self._deny_and_revert_checkbox(checkbox, stage.enabled)
            return
        stage.enabled = enabled
        action = "Enabled" if enabled else "Disabled"
        ui_logger.log("WARNING", "PROTECTION", f"{prot_id} {stage.name}", f"Stage {action}", "Engineer", self.tag_manager.mode, "")
        self._audit(f"{prot_id} {stage.name} stage {action.lower()}")

    def on_setting_edit_finished(self, prot_id, stage, field, attr, spinbox):
        old_val = getattr(stage, attr)
        new_val = spinbox.value()
        if new_val == old_val:
            # editingFinished also fires on plain focus-loss with no change
            # (e.g. tabbing through fields) - nothing to confirm or log.
            return

        # Execution-time re-check, same reasoning as on_stage_enabled_changed
        # above - checked before even offering the confirmation popup.
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Edit Protection Settings (setting value)")
            spinbox.blockSignals(True)
            spinbox.setValue(old_val)
            spinbox.blockSignals(False)
            return

        popup = SettingChangePopup(f"{prot_id} {stage.name}", field, old_val, new_val, "Engineer", self)
        popup.move(spinbox.mapToGlobal(spinbox.rect().bottomLeft()))
        if popup.exec():
            setattr(stage, attr, new_val)
            ui_logger.log("WARNING", "PROTECTION", f"{prot_id} {stage.name}", f"{field} changed from {old_val} to {new_val}", "Engineer", self.tag_manager.mode, "")
            self._audit(f"{prot_id} {stage.name} {field} changed from {old_val} to {new_val}")
        else:
            spinbox.blockSignals(True)
            spinbox.setValue(old_val)
            spinbox.blockSignals(False)

    def on_action_changed(self, prot_id, stage, text, combo):
        # Execution-time re-check, same reasoning as above.
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Edit Protection Settings (action)")
            combo.blockSignals(True)
            combo.setCurrentText(stage.action)
            combo.blockSignals(False)
            return
        stage.action = text
        ui_logger.log("WARNING", "PROTECTION", f"{prot_id} {stage.name}", f"Action changed to {text}", "Engineer", self.tag_manager.mode, "")
        self._audit(f"{prot_id} {stage.name} action changed to {text}")

    def _refresh_reset_button(self, *_):
        self.btn_reset_stats.setEnabled(self.access_manager.has_access(AccessLevel.ENGINEER))

    def reset_all_statistics(self):
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Reset Protection Statistics")
            return
        reply = QMessageBox.question(
            self, tr("pages.protection.reset_confirm_title"), tr("pages.protection.reset_confirm_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for prot_func in self.protection_manager.protections.values():
                for stage in prot_func.stages:
                    stage.pickups = 0
                    stage.trips = 0
                    stage.last_pickup = "N/A"
                    stage.last_trip = "N/A"
                    stage.operating_time = "0 ms"
            self.populate_tree()
            self.update_mode()
            ui_logger.log("WARNING", "PROTECTION", "ALL", "Statistics Reset", "Engineer", self.tag_manager.mode, "")

    def update_mode(self, *_):
        # access_manager.level_changed passes the new level as an arg (when
        # connected directly to the signal); *_ absorbs that so the
        # zero-arg call sites (populate, on_tag_changed) keep working too.
        #
        # The previous version of this method also enabled editing for
        # everyone in SIMULATION MODE, regardless of access level ("an
        # unrelated axis - simulated vs. real I/O - kept for test/dev
        # convenience"). Removed for this task: the new permission matrix
        # requires Protection Settings to be Engineer-only with no stated
        # exception, and User must be genuinely view-only - a real,
        # enforced restriction, not one a dev-convenience mode used to
        # bypass. Flagged here (not silently dropped) since it was a
        # deliberate, documented earlier decision this task's explicit
        # matrix now overrides.
        is_engineer = self.access_manager.has_access(AccessLevel.ENGINEER)

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            prot_item = root.child(i)
            for j in range(prot_item.childCount()):
                stage_item = prot_item.child(j)
                for col in [0, 3, 4, 5, 6]:
                    widget = self.tree.itemWidget(stage_item, col)
                    if widget:
                        widget.setEnabled(is_engineer)

    def open_in_logic_studio(self, prot_id, stage_name):
        from epw_os.gui.main_window import MainWindow
        # Find main window to trigger navigation
        parent = self.parent()
        while parent and not isinstance(parent, MainWindow):
            parent = parent.parent()
            
        if parent:
            parent.nav_btns["LOGIC STUDIO"].click()
            parent.page_logic_studio.open_protection_block(prot_id, stage_name)

    def on_tag_changed(self, tag_name, new_value, quality):
        if tag_name == "System.Mode":
            self.update_mode()
        # In a real system, we would map tag_name to the source and update Actual Value column.
