"""Who may operate this controller, and with what secret.

The people themselves come from the project (Studio decides who exists,
what level they hold and which zones they may operate). THEIR SECRETS
belong to this controller and are set here, at the cabinet:

  * a KEYPAD CODE, which signs that person in on this panel;
  * a REMOTE TOKEN, which lets their Home Assistant automation command
    this controller over MQTT.

Two separate secrets on purpose: the token lives on another machine, in
an automation file, so if it leaks it must not also open the panel
standing in front of the cabinet. Either can be taken away without
touching the other - revoking the token leaves the person working at the
panel exactly as before.

Neither can ever be read back: only hashes are stored (access_manager.py),
so a generated token is shown ONCE, here, and then exists nowhere on this
machine in a form anyone could copy.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from epw_os.core.access_manager import AccessLevel
from epw_os.i18n import tr

_COLUMNS = ("name", "level", "zones", "code", "token")


class AlarmUsersDialog(QDialog):
    def __init__(self, access_manager, parent=None):
        super().__init__(parent)
        self.access_manager = access_manager
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("users.title"))
        self.setModal(True)
        self.resize(720, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        info = QLabel(tr("users.info"))
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([tr(f"users.col_{c}") for c in _COLUMNS])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # The one field a generated token is ever shown in. Read-only and
        # selectable so it can be copied into Home Assistant, and cleared
        # the moment anything else happens.
        self.token_field = QLineEdit()
        self.token_field.setReadOnly(True)
        self.token_field.setPlaceholderText(tr("users.token_placeholder"))
        layout.addWidget(self.token_field)

        buttons = QHBoxLayout()
        self.btn_set_code = QPushButton(tr("users.btn_set_code"))
        self.btn_set_code.clicked.connect(self._set_code)
        buttons.addWidget(self.btn_set_code)
        self.btn_clear_code = QPushButton(tr("users.btn_clear_code"))
        self.btn_clear_code.clicked.connect(self._clear_code)
        buttons.addWidget(self.btn_clear_code)
        self.btn_issue_token = QPushButton(tr("users.btn_issue_token"))
        self.btn_issue_token.clicked.connect(self._issue_token)
        buttons.addWidget(self.btn_issue_token)
        self.btn_revoke_token = QPushButton(tr("users.btn_revoke_token"))
        self.btn_revoke_token.clicked.connect(self._revoke_token)
        buttons.addWidget(self.btn_revoke_token)
        buttons.addStretch()
        close = QPushButton(tr("common.close"))
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

        self.refresh()

    # --- data ----------------------------------------------------------------

    def refresh(self):
        users = self.access_manager.get_users() if self.access_manager else []
        self.table.setRowCount(len(users))
        for row, user in enumerate(users):
            zones = ", ".join(user["zones"]) if user["zones"] else tr("users.zones_all")
            name = user["name"] if user["enabled"] else tr("users.disabled_name", name=user["name"])
            values = (name, user["level"], zones,
                      tr("users.set") if user["has_pin"] else tr("users.not_set"),
                      tr("users.set") if user["has_remote_token"] else tr("users.not_set"))
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, user["id"])
                self.table.setItem(row, column, item)
        self.setEnabled(True)

    def _selected_user_id(self):
        row = self.table.currentRow()
        if row < 0 or self.table.item(row, 0) is None:
            QMessageBox.information(self, self.windowTitle(), tr("users.select_first"))
            return None
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _require_engineer(self) -> bool:
        """Every secret on this dialog is Engineer-level - the same bar
        as changing a PIN. Re-checked at the click, not just when the
        dialog opened: access can lapse while it is on screen."""
        if self.access_manager is None or not self.access_manager.has_access(AccessLevel.ENGINEER):
            QMessageBox.warning(self, self.windowTitle(), tr("users.engineer_required"))
            return False
        return True

    # --- actions --------------------------------------------------------------

    def _set_code(self):
        self.token_field.clear()
        user_id = self._selected_user_id()
        if user_id is None or not self._require_engineer():
            return
        code = self._ask_code()
        if not code:
            return
        if self.access_manager.set_user_pin(user_id, code, level=AccessLevel.ENGINEER):
            self.refresh()
        else:
            QMessageBox.warning(self, self.windowTitle(), tr("users.code_refused"))

    def _ask_code(self):
        """The keypad code, typed twice. A dialog rather than the
        on-screen keypad flow the level PINs use: this is an Engineer
        configuring somebody ELSE's code, not that person signing in."""
        from PySide6.QtWidgets import QInputDialog
        first, ok = QInputDialog.getText(self, tr("users.code_title"), tr("users.code_prompt"),
                                          QLineEdit.EchoMode.Password)
        if not ok or not first:
            return None
        again, ok = QInputDialog.getText(self, tr("users.code_title"), tr("users.code_repeat"),
                                          QLineEdit.EchoMode.Password)
        if not ok:
            return None
        if first != again:
            QMessageBox.warning(self, self.windowTitle(), tr("users.code_mismatch"))
            return None
        return first

    def _clear_code(self):
        self.token_field.clear()
        user_id = self._selected_user_id()
        if user_id is None or not self._require_engineer():
            return
        self.access_manager.clear_user_pin(user_id, level=AccessLevel.ENGINEER)
        self.refresh()

    def _issue_token(self):
        user_id = self._selected_user_id()
        if user_id is None or not self._require_engineer():
            return
        answer = QMessageBox.question(self, self.windowTitle(), tr("users.token_confirm"),
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        token = self.access_manager.issue_remote_token(user_id, level=AccessLevel.ENGINEER)
        if not token:
            QMessageBox.warning(self, self.windowTitle(), tr("users.token_refused"))
            return
        self.token_field.setText(token)
        self.refresh()
        QMessageBox.information(self, self.windowTitle(), tr("users.token_shown_once"))

    def _revoke_token(self):
        self.token_field.clear()
        user_id = self._selected_user_id()
        if user_id is None or not self._require_engineer():
            return
        self.access_manager.revoke_remote_token(user_id, level=AccessLevel.ENGINEER)
        self.refresh()
