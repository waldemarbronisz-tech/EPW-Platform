"""Settings > Feature Configuration (Task: "okno konfiguracji, w ktorym
wlacza i wylacza sie poszczegolne funkcje sterownika"). Engineer-only -
see main_window.py's own Engineer-gated Settings entries
(Training Mode/Kiosk Mode) for the identical visibility pattern this
one's own menu action follows.

Each row is a plain QCheckBox, applied IMMEDIATELY on toggle (same
"no OK/Cancel batching" stance Kiosk Mode/Training Mode's own toggle
actions already have elsewhere in this app) rather than staged behind
an OK button - Task: "zmiana ma dzialac BEZ RESTARTU", and a toggle
that only takes effect after closing a dialog would make it easy to
forget whether it "took" at all. Disabling something ALWAYS goes
through _confirm_and_apply() first, which shows the Task's own two
required warnings (logic uses this feature's tags / this feature
produces data that will stop) before the actual change, and lets the
operator cancel out of the checkbox itself if they change their mind.
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QMessageBox, QScrollArea, QWidget
from PySide6.QtCore import Qt

from epw_os.core.access_manager import AccessLevel
from epw_os.core.feature_config import TOGGLABLE_FEATURES
from epw_os.core.nav_model import engineer_mode_available, intrusion_subpage_available
from epw_os.gui.theme_manager import neutral_text_style
from epw_os.i18n import tr

# Display order + label key - reuses the SAME nav.* keys the tree/old
# flat menu already show for every feature that IS a page, so the
# dialog never invents a second name for something the operator already
# knows by its nav label. switching_counters/service_notes are the only
# two with no page of their own (Task: they're capabilities woven into
# Digital/Control Outputs, not separate pages) - their own
# feature_config.* keys.
_FEATURE_LABELS = [
    ("intrusion", "nav.intrusion"),
    ("intrusion_history", "nav.intrusion_history"),
    ("intrusion_config", "nav.intrusion_config"),
    ("analog_inputs", "nav.analog_inputs"),
    ("power_quality", "nav.power_quality"),
    ("trends", "nav.trends"),
    ("protection_settings", "nav.protection_electrical"),
    ("protection_process", "nav.protection_process"),
    ("system_topology", "nav.system_topology"),
    ("bus_diagnostics", "nav.bus_diagnostics"),
    ("engineer_mode", "nav.engineer_mode"),
    ("switching_counters", "feature_config.lbl_switching_counters"),
    ("service_notes", "feature_config.lbl_service_notes"),
]
assert {f for f, _ in _FEATURE_LABELS} == set(TOGGLABLE_FEATURES)  # keep this list honest if the core one ever grows

# Task: "jesli funkcja zapisuje dane, ktore przestana powstawac" - a
# short, per-feature note shown under its checkbox, informational only
# (no tag names removed = no note here; see FeatureConfigDialog's own
# tag-reference warning for that half separately). None = nothing lost.
_DATA_NOTE_KEYS = {
    "intrusion": "feature_config.note_data_intrusion",
    "analog_inputs": "feature_config.note_data_analog_inputs",
    "trends": "feature_config.note_data_trends",
    "switching_counters": "feature_config.note_data_switching_counters",
    "service_notes": "feature_config.note_data_service_notes",
}


class FeatureConfigDialog(QDialog):
    def __init__(self, feature_config, access_manager, parent=None):
        """`feature_config`: the GUIFeatureConfigAdapter main.py builds
        around EPWCore - get_enabled_features()/set_feature_enabled()/
        feature_referenced_by_logic()/get_feature_tag_names()."""
        super().__init__(parent)
        self.feature_config = feature_config
        self.access_manager = access_manager
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("feature_config.title"))
        self.setModal(True)
        self.setMinimumSize(440, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        intro = QLabel(tr("feature_config.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        self._checkboxes = {}
        enabled = self.feature_config.get_enabled_features()
        for feature, label_key in _FEATURE_LABELS:
            row = QVBoxLayout()
            cb = QCheckBox(tr(label_key))
            cb.setChecked(bool(enabled.get(feature, True)))
            cb.toggled.connect(lambda checked, f=feature, box=cb: self._on_toggled(f, checked, box))
            row.addWidget(cb)
            note_key = _DATA_NOTE_KEYS.get(feature)
            if note_key:
                note = QLabel(tr(note_key))
                note.setWordWrap(True)
                note.setStyleSheet(neutral_text_style("font-size: 10px; margin-left: 20px;"))
                row.addWidget(note)
            inner_layout.addLayout(row)
            self._checkboxes[feature] = cb
        inner_layout.addStretch()

        btn_close = QPushButton(tr("pages.intrusion.btn_close"))
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self._refresh_engineer_mode_dependency()
        self._refresh_intrusion_subpage_dependency()

    # --- Engineer Mode <-> Protection Settings (see nav_model.py's own
    # engineer_mode_available() docstring for the full reasoning) ------

    def _refresh_engineer_mode_dependency(self):
        cb = self._checkboxes.get("engineer_mode")
        if cb is None:
            return
        enabled = self.feature_config.get_enabled_features()
        available = engineer_mode_available(enabled)
        cb.setEnabled(available)
        cb.setToolTip(tr("feature_config.tooltip_engineer_mode_needs_protection") if not available else "")

    # --- Historia zdarzen / Konfiguracja <-> whole intrusion module
    # (page-split task; same dependency shape as Engineer Mode above -
    # see nav_model.intrusion_subpage_available()) -----------------

    def _refresh_intrusion_subpage_dependency(self):
        enabled = self.feature_config.get_enabled_features()
        available = intrusion_subpage_available(enabled)
        for feature in ("intrusion_history", "intrusion_config"):
            cb = self._checkboxes.get(feature)
            if cb is None:
                continue
            cb.setEnabled(available)
            cb.setToolTip(tr("feature_config.tooltip_intrusion_subpage_needs_intrusion") if not available else "")

    # --- apply ------------------------------------------------------------

    def _on_toggled(self, feature: str, checked: bool, checkbox: QCheckBox):
        if checked:
            self._apply(feature, True)
            self._refresh_engineer_mode_dependency()
            self._refresh_intrusion_subpage_dependency()
            return
        if not self._confirm_disable(feature):
            # Put the checkbox back without re-entering this handler.
            checkbox.blockSignals(True)
            checkbox.setChecked(True)
            checkbox.blockSignals(False)
            return
        self._apply(feature, False)
        # Both dependencies are cheap to recompute unconditionally - no
        # need to special-case which specific feature was just toggled
        # (protection_settings/intrusion are the only two anything below
        # depends on, but a blanket refresh is simpler and just as
        # correct as tracking that explicitly here).
        self._refresh_engineer_mode_dependency()
        self._refresh_intrusion_subpage_dependency()

    def _confirm_disable(self, feature: str) -> bool:
        """Task's own two required warnings. Returns True if the
        operator should proceed (either nothing to warn about, or they
        explicitly confirmed anyway)."""
        warnings = []
        if self.feature_config.feature_referenced_by_logic(feature):
            warnings.append(tr("feature_config.warn_logic_uses_tags"))
        if feature in _DATA_NOTE_KEYS:
            warnings.append(tr(_DATA_NOTE_KEYS[feature]))
        if not warnings:
            return True
        message = tr("feature_config.confirm_disable_intro") + "\n\n" + "\n".join(f"- {w}" for w in warnings)
        result = QMessageBox.warning(
            self, tr("feature_config.title"), message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def _apply(self, feature: str, enabled: bool):
        result = self.feature_config.set_feature_enabled(feature, enabled, actor=self.access_manager.level,
                                                           level=self.access_manager.level)
        if not result.get("success"):
            QMessageBox.warning(self, tr("feature_config.title"), result.get("reason", ""))
            cb = self._checkboxes.get(feature)
            if cb is not None:
                cb.blockSignals(True)
                cb.setChecked(not enabled)
                cb.blockSignals(False)
