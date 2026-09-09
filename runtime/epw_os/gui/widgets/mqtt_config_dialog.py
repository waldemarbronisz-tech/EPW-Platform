"""Settings > MQTT... (Task: "integracja MQTT", CZESC A3). Engineer-only
- same hidden+disabled belt-and-suspenders gate as Feature Configuration/
Training Mode/Kiosk Mode's own menu entries (see main_window.py), and
re-checked again at Save time inside MqttManager.configure() itself
(defense in depth - the same pattern every other Engineer-gated core
method in this codebase already follows).

Applied immediately on Save (no separate "restart program" step) via
MqttManager.configure()/restart() - matches Feature Configuration's own
"zmiana ma dzialac BEZ RESTARTU" stance for a conceptually similar
Settings entry.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QCheckBox,
    QSpinBox, QDoubleSpinBox, QComboBox, QPushButton, QDialogButtonBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QScrollArea, QWidget,
)
from PySide6.QtCore import Qt

from epw_os.core.logging import log
from epw_os.core.mqtt_manager import MqttConnectionState, MQTT_LIB_AVAILABLE
from epw_os.gui.widgets.industrial_labels import StatusLabel
from epw_os.gui.theme_manager import neutral_text_style
from epw_os.i18n import tr

# StatusLabel (industrial_labels.py) colors by matching substrings
# against an existing, generic keyword vocabulary (READY/ONLINE/OK/...
# = green, FAULT/OFFLINE/LOST/... = red, etc.) shared by every other
# status badge in this app - reusing it here (rather than inventing a
# second, dialog-only coloring scheme) just needs each connection state
# mapped to text that vocabulary already recognizes.
_STATE_DISPLAY_TEXT = {
    MqttConnectionState.UNAVAILABLE: "DISABLED",
    MqttConnectionState.DISABLED: "DISABLED",
    MqttConnectionState.CONNECTING: "STARTING",
    MqttConnectionState.CONNECTED: "ONLINE",
    MqttConnectionState.DISCONNECTED: "OFFLINE",
    MqttConnectionState.AUTH_ERROR: "FAULT (AUTH)",
    MqttConnectionState.ERROR: "FAULT",
}

_TYPE_CHOICES = ["BOOL", "REAL", "INT", "DINT", "STRING"]


class MqttConfigDialog(QDialog):
    def __init__(self, mqtt_manager, access_manager, status_changed_signal=None, parent=None):
        """`mqtt_manager`: the GUIMqttAdapter main.py builds around
        EPWCore.mqtt_manager - get_config()/configure()/get_state()/
        get_stats(). `status_changed_signal`: a Qt signal(str) bridging
        the core's "mqtt_status_changed" event, so the status line here
        updates live instead of only reflecting whatever it was when the
        dialog opened."""
        super().__init__(parent)
        self.mqtt_manager = mqtt_manager
        self.access_manager = access_manager
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("mqtt.title"))
        self.setModal(True)
        self.setMinimumSize(520, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        if not MQTT_LIB_AVAILABLE:
            warn = QLabel(tr("mqtt.library_missing_warning"))
            warn.setWordWrap(True)
            warn.setStyleSheet("font-weight: bold;")
            layout.addWidget(warn)

        hint = QLabel(tr("mqtt.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel(tr("mqtt.lbl_status")))
        self.lbl_status = StatusLabel(_STATE_DISPLAY_TEXT.get(self.mqtt_manager.get_state(), "UNKNOWN"))
        status_row.addWidget(self.lbl_status)
        status_row.addStretch()
        layout.addLayout(status_row)

        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet(neutral_text_style("font-size: 10px;"))
        layout.addWidget(self.lbl_stats)
        self._refresh_stats()

        if status_changed_signal is not None:
            status_changed_signal.connect(self._on_status_changed)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        cfg = self.mqtt_manager.get_config()

        self.chk_enabled = QCheckBox(tr("mqtt.enable"))
        self.chk_enabled.setChecked(bool(cfg.get("enabled")))
        form.addRow(self.chk_enabled)

        self.edit_host = QLineEdit(cfg.get("host", ""))
        form.addRow(tr("mqtt.lbl_host"), self.edit_host)

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(int(cfg.get("port", 1883)))
        form.addRow(tr("mqtt.lbl_port"), self.spin_port)

        self.edit_username = QLineEdit(cfg.get("username", ""))
        form.addRow(tr("mqtt.lbl_username"), self.edit_username)

        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_password.setPlaceholderText(tr("mqtt.password_placeholder"))
        form.addRow(tr("mqtt.lbl_password"), self.edit_password)

        self.chk_tls = QCheckBox(tr("mqtt.enable_tls"))
        self.chk_tls.setChecked(bool(cfg.get("tls")))
        form.addRow(self.chk_tls)

        self.edit_client_id = QLineEdit(cfg.get("client_id", ""))
        self.edit_client_id.setPlaceholderText(tr("mqtt.client_id_placeholder"))
        form.addRow(tr("mqtt.lbl_client_id"), self.edit_client_id)

        self.edit_prefix = QLineEdit(cfg.get("topic_prefix", ""))
        self.edit_prefix.setPlaceholderText(tr("mqtt.topic_prefix_placeholder"))
        form.addRow(tr("mqtt.lbl_topic_prefix"), self.edit_prefix)

        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(0.0, 3600.0)
        self.spin_interval.setSuffix(" s")
        self.spin_interval.setValue(float(cfg.get("publish_interval_s", 2.0)))
        form.addRow(tr("mqtt.lbl_publish_interval"), self.spin_interval)

        self.spin_deadband = QDoubleSpinBox()
        self.spin_deadband.setRange(0.0, 1_000_000.0)
        self.spin_deadband.setDecimals(3)
        self.spin_deadband.setValue(float(cfg.get("default_deadband", 0.0)))
        form.addRow(tr("mqtt.lbl_deadband"), self.spin_deadband)

        self.spin_queue = QSpinBox()
        self.spin_queue.setRange(10, 100000)
        self.spin_queue.setValue(int(cfg.get("queue_max", 1000)))
        form.addRow(tr("mqtt.lbl_queue_max"), self.spin_queue)

        link_header = QLabel(tr("mqtt.link_in_header"))
        link_header.setObjectName("SectionHeader")
        form.addRow(link_header)
        link_hint = QLabel(tr("mqtt.link_in_hint"))
        link_hint.setWordWrap(True)
        form.addRow(link_hint)

        self.table_links = QTableWidget(0, 4)
        self.table_links.setHorizontalHeaderLabels([
            tr("mqtt.col_topic"), tr("mqtt.col_tag"), tr("mqtt.col_type"), tr("mqtt.col_stale_after"),
        ])
        self.table_links.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_links.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for entry in cfg.get("link_in", []):
            self._add_link_row(entry)
        form.addRow(self.table_links)

        link_buttons = QHBoxLayout()
        btn_add = QPushButton(tr("mqtt.btn_add_mapping"))
        btn_add.clicked.connect(lambda: self._add_link_row({}))
        btn_remove = QPushButton(tr("mqtt.btn_remove_mapping"))
        btn_remove.clicked.connect(self._remove_selected_link_row)
        link_buttons.addWidget(btn_add)
        link_buttons.addWidget(btn_remove)
        link_buttons.addStretch()
        form.addRow(link_buttons)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # --- live status ------------------------------------------------------

    def _on_status_changed(self, state: str):
        self.lbl_status.update_status(_STATE_DISPLAY_TEXT.get(state, "UNKNOWN"))
        self._refresh_stats()

    def _refresh_stats(self):
        stats = self.mqtt_manager.get_stats()
        last_connect = "-"
        if stats.get("last_connect_time"):
            import time as _time
            last_connect = _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(stats["last_connect_time"]))
        self.lbl_stats.setText(
            tr("mqtt.stats_line", sent=stats.get("sent", 0), received=stats.get("received", 0),
               errors=stats.get("errors", 0), dropped=stats.get("dropped", 0), last_connect=last_connect)
        )

    # --- Link.* mapping table ----------------------------------------

    def _add_link_row(self, entry: dict):
        row = self.table_links.rowCount()
        self.table_links.insertRow(row)
        self.table_links.setItem(row, 0, QTableWidgetItem(entry.get("topic", "")))
        self.table_links.setItem(row, 1, QTableWidgetItem(entry.get("tag", "")))
        combo = QComboBox()
        combo.addItems(_TYPE_CHOICES)
        idx = combo.findText(entry.get("type", "BOOL"))
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.table_links.setCellWidget(row, 2, combo)
        self.table_links.setItem(row, 3, QTableWidgetItem(str(entry.get("stale_after_s", 30))))

    def _remove_selected_link_row(self):
        rows = sorted({idx.row() for idx in self.table_links.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table_links.removeRow(row)

    def _collect_link_mappings(self) -> list:
        mappings = []
        for row in range(self.table_links.rowCount()):
            topic_item = self.table_links.item(row, 0)
            tag_item = self.table_links.item(row, 1)
            topic = (topic_item.text().strip() if topic_item else "")
            tag = (tag_item.text().strip() if tag_item else "")
            if not topic and not tag:
                continue  # a blank row added then left empty - not an error, just skipped
            combo = self.table_links.cellWidget(row, 2)
            type_name = combo.currentText() if combo is not None else "BOOL"
            stale_item = self.table_links.item(row, 3)
            try:
                stale_after_s = float(stale_item.text()) if stale_item else 30.0
            except ValueError:
                # An operator typed something non-numeric into the Stale
                # After column - silently reverting to 30s with no
                # indication is exactly the "polykane wyjatki" pattern
                # System.Mode had (kept unchanged: still reverts to 30s,
                # this table has no per-cell validation UI of its own -
                # only now it's at least visible in the log).
                log.warning(f"Invalid 'stale after' value {stale_item.text()!r} for topic {topic!r} "
                            f"- using 30s.")
                stale_after_s = 30.0
            mappings.append({"topic": topic, "tag": tag, "type": type_name, "stale_after_s": stale_after_s})
        return mappings

    # --- save --------------------------------------------------------------

    def _save(self):
        # Validate every non-blank row looks like a real Link.<id>.In*
        # mapping BEFORE saving anything - a typo here should not
        # silently produce a mapping mqtt_manager.py will just skip at
        # start() with only a log line nobody watching the dialog would see.
        import re
        link_tag_re = re.compile(r"^Link\.[^.]+\.In.+$")
        mappings = self._collect_link_mappings()
        for m in mappings:
            if not m["topic"] or not link_tag_re.match(m["tag"]):
                QMessageBox.warning(self, tr("mqtt.title"),
                                     tr("mqtt.invalid_mapping", topic=m["topic"], tag=m["tag"]))
                return

        config = {
            "enabled": self.chk_enabled.isChecked(),
            "host": self.edit_host.text().strip(),
            "port": self.spin_port.value(),
            "username": self.edit_username.text().strip(),
            "tls": self.chk_tls.isChecked(),
            "client_id": self.edit_client_id.text().strip(),
            "topic_prefix": self.edit_prefix.text().strip(),
            "publish_interval_s": self.spin_interval.value(),
            "default_deadband": self.spin_deadband.value(),
            "queue_max": self.spin_queue.value(),
            "link_in": mappings,
        }
        password = self.edit_password.text() if self.edit_password.text() else None
        result = self.mqtt_manager.configure(config, password=password, actor=self.access_manager.level,
                                              level=self.access_manager.level)
        if not result.get("success"):
            QMessageBox.warning(self, tr("mqtt.title"), result.get("reason", ""))
            return
        self.accept()
