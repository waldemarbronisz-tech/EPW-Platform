"""Settings > Data Retention... (Task: feature/retention-and-test-fix,
B3+B4). Engineer-only - same hidden+disabled belt-and-suspenders gate as
Feature Configuration/MQTT/Training Mode's own menu entries (see
main_window.py), and re-checked again at Save time inside
Historian.configure_retention()/AuditLogger.configure_retention()
themselves (defense in depth, same pattern every other Engineer-gated
core method in this codebase already follows).

Two clearly separate sections (B4: "Osobne ustawienia dla Historiana i
dla dziennika - dwie rozne sprawy i nie moga dzielic jednego
przelacznika") - Historian and Audit Log each have their own
independent max-days/max-rows fields, matching the existing
HistoryRetentionDialog (page_intrusion.py) convention of 0 = "Unlimited"
via setSpecialValueText rather than a redundant separate on/off
checkbox. A third, standalone section covers the overall database size
warning threshold (B3) - deliberately not part of either retention
section, since it's about the whole database file, not a per-table
limit.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel, QLineEdit,
    QCheckBox, QSpinBox, QPushButton, QDialogButtonBox, QFileDialog, QMessageBox,
)

from epw_os.gui.theme_manager import neutral_text_style
from epw_os.i18n import tr


def _format_bytes(n: int) -> str:
    """MB, one decimal - the unit every field/label in this dialog uses
    (matches the "threshold_mb" project.json field), so the live stats
    line reads in the same unit the user is about to configure."""
    return f"{n / (1024 * 1024):.1f} MB"


class DataRetentionDialog(QDialog):
    def __init__(self, historian, audit_logger, access_manager, parent=None):
        super().__init__(parent)
        self.historian = historian
        self.audit_logger = audit_logger
        self.access_manager = access_manager
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("retention.title"))
        self.setModal(True)
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        hint = QLabel(tr("retention.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # --- B3: current size / row counts, so an Engineer can judge
        # whether retention is actually needed before configuring it. ---
        self.lbl_stats = QLabel("")
        self.lbl_stats.setWordWrap(True)
        self.lbl_stats.setStyleSheet(neutral_text_style("font-size: 10px;"))
        layout.addWidget(self.lbl_stats)
        self._refresh_stats()

        # --- Historian section ------------------------------------------
        hist_box = QGroupBox(tr("retention.historian_section"))
        hist_form = QFormLayout(hist_box)
        hist_cfg = self.historian.get_retention_config() if self.historian is not None else {}

        self.spin_hist_days = QSpinBox()
        self.spin_hist_days.setRange(0, 3650)
        self.spin_hist_days.setSpecialValueText(tr("retention.unlimited"))
        self.spin_hist_days.setToolTip(tr("retention.tooltip_max_days"))
        self.spin_hist_days.setValue(int(hist_cfg.get("max_days", 0) or 0))
        hist_form.addRow(tr("retention.lbl_max_days"), self.spin_hist_days)

        self.spin_hist_rows = QSpinBox()
        self.spin_hist_rows.setRange(0, 10_000_000)
        self.spin_hist_rows.setSpecialValueText(tr("retention.unlimited"))
        self.spin_hist_rows.setToolTip(tr("retention.tooltip_max_rows"))
        self.spin_hist_rows.setValue(int(hist_cfg.get("max_rows", 0) or 0))
        hist_form.addRow(tr("retention.lbl_max_rows"), self.spin_hist_rows)
        layout.addWidget(hist_box)

        # --- Audit Log section (archival, never a plain delete) ---------
        audit_box = QGroupBox(tr("retention.audit_section"))
        audit_form = QFormLayout(audit_box)
        audit_cfg = self.audit_logger.get_retention_config() if self.audit_logger is not None else {}

        audit_note = QLabel(tr("retention.audit_archive_note"))
        audit_note.setWordWrap(True)
        audit_note.setStyleSheet(neutral_text_style("font-size: 10px;"))
        audit_form.addRow(audit_note)

        self.spin_audit_days = QSpinBox()
        self.spin_audit_days.setRange(0, 3650)
        self.spin_audit_days.setSpecialValueText(tr("retention.unlimited"))
        self.spin_audit_days.setToolTip(tr("retention.tooltip_max_days"))
        self.spin_audit_days.setValue(int(audit_cfg.get("max_days", 0) or 0))
        audit_form.addRow(tr("retention.lbl_max_days"), self.spin_audit_days)

        self.spin_audit_rows = QSpinBox()
        self.spin_audit_rows.setRange(0, 10_000_000)
        self.spin_audit_rows.setSpecialValueText(tr("retention.unlimited"))
        self.spin_audit_rows.setToolTip(tr("retention.tooltip_max_rows"))
        self.spin_audit_rows.setValue(int(audit_cfg.get("max_rows", 0) or 0))
        audit_form.addRow(tr("retention.lbl_max_rows"), self.spin_audit_rows)

        archive_row = QHBoxLayout()
        self.edit_archive_dir = QLineEdit(audit_cfg.get("archive_dir", ""))
        self.edit_archive_dir.setToolTip(tr("retention.tooltip_archive_dir"))
        archive_row.addWidget(self.edit_archive_dir)
        btn_browse = QPushButton(tr("retention.btn_browse"))
        btn_browse.clicked.connect(self._browse_archive_dir)
        archive_row.addWidget(btn_browse)
        audit_form.addRow(tr("retention.lbl_archive_dir"), archive_row)
        layout.addWidget(audit_box)

        # --- B3: overall database size warning ---------------------------
        size_box = QGroupBox(tr("retention.size_warning_section"))
        size_form = QFormLayout(size_box)
        _pm = getattr(parent, "project_manager", None) if parent is not None else None
        size_cfg = _pm.get_db_size_warning_config() if _pm is not None else {"enabled": False, "threshold_mb": 500}

        self.chk_size_warning = QCheckBox(tr("retention.chk_enable_size_warning"))
        self.chk_size_warning.setChecked(bool(size_cfg.get("enabled", False)))
        size_form.addRow(self.chk_size_warning)

        self.spin_size_threshold = QSpinBox()
        self.spin_size_threshold.setRange(1, 1_000_000)
        self.spin_size_threshold.setSuffix(" MB")
        self.spin_size_threshold.setValue(int(size_cfg.get("threshold_mb", 500) or 500))
        size_form.addRow(tr("retention.lbl_size_threshold"), self.spin_size_threshold)
        layout.addWidget(size_box)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh_stats(self):
        from epw_os.db.database import get_db_stats
        try:
            stats = get_db_stats()
        except Exception:
            self.lbl_stats.setText(tr("retention.stats_unavailable"))
            return
        counts = stats["row_counts"]
        self.lbl_stats.setText(tr(
            "retention.stats_line",
            size=_format_bytes(stats["file_size_bytes"]),
            tag_history=counts.get("tag_history", 0), audit_log=counts.get("audit_log", 0),
            alarm_history=counts.get("alarm_history", 0),
            intrusion_alarm_history=counts.get("intrusion_alarm_history", 0),
        ))

    def _browse_archive_dir(self):
        chosen = QFileDialog.getExistingDirectory(self, tr("retention.btn_browse"), self.edit_archive_dir.text())
        if chosen:
            self.edit_archive_dir.setText(chosen)

    def _save(self):
        level = self.access_manager.level
        if self.historian is not None:
            ok = self.historian.configure_retention(
                max_days=self.spin_hist_days.value(), max_rows=self.spin_hist_rows.value(), level=level)
            if not ok:
                QMessageBox.warning(self, tr("retention.title"), tr("retention.denied"))
                return
        if self.audit_logger is not None:
            archive_dir = self.edit_archive_dir.text().strip() or None
            ok = self.audit_logger.configure_retention(
                max_days=self.spin_audit_days.value(), max_rows=self.spin_audit_rows.value(),
                archive_dir=archive_dir, level=level)
            if not ok:
                QMessageBox.warning(self, tr("retention.title"), tr("retention.denied"))
                return
        # Persistence (survives a restart) lives here, at the GUI layer -
        # unlike IntrusionAlarmHistoryLogger, neither Historian nor
        # AuditLogger holds its own project_manager reference (see their
        # own __init__ docstrings), so this dialog is the one place that
        # has both the just-applied live config AND project_manager.
        pm = self.parent().project_manager if self.parent() is not None else None
        if pm is not None:
            pm.set_historian_retention_config(
                max_days=self.spin_hist_days.value(), max_rows=self.spin_hist_rows.value())
            pm.set_audit_retention_config(
                max_days=self.spin_audit_days.value(), max_rows=self.spin_audit_rows.value(),
                archive_dir=self.edit_archive_dir.text().strip())
            pm.set_db_size_warning_config(
                enabled=self.chk_size_warning.isChecked(), threshold_mb=self.spin_size_threshold.value())
            pm.save_project()
        self.accept()
