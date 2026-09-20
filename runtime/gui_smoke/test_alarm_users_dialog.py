"""Setting a person's secrets at the cabinet.

The people come from the project; their keypad code and their remote
(MQTT) token are set here. Without this dialog the whole remote-command
channel is unusable - there would be no way to hand anybody a token - so
what matters is that it really writes through AccessManager, that a
generated token is shown once and only once, and that none of it is
possible below Engineer.
"""
import pytest
from PySide6.QtWidgets import QMessageBox

from epw_os.core.access_manager import AccessLevel, AccessManager
from epw_os.core.events import EventBus
from epw_os.gui.widgets.alarm_users_dialog import AlarmUsersDialog

USERS = [
    {"id": "U1", "name": "Kowalski", "level": "Operator", "zones": ["Z1"]},
    {"id": "U2", "name": "Nowak", "level": "Engineer", "zones": []},
]


@pytest.fixture
def access(tmp_path):
    manager = AccessManager(EventBus(), config_path=str(tmp_path / "access.local.json"))
    manager.set_users(USERS)
    manager.level = AccessLevel.ENGINEER
    return manager


@pytest.fixture
def dialog(qapp, access):
    widget = AlarmUsersDialog(access)
    yield widget
    widget.deleteLater()


def _select(dialog, row):
    dialog.table.setCurrentCell(row, 0)


def test_it_lists_the_people_from_the_project(dialog):
    assert dialog.table.rowCount() == 2
    assert dialog.table.item(0, 0).text() == "Kowalski"
    assert dialog.table.item(0, 2).text() == "Z1"
    assert dialog.table.item(1, 2).text() == "(every zone)", "no zones listed means every zone"
    # Neither secret is set yet, and the table says so rather than
    # showing anything about them.
    assert dialog.table.item(0, 3).text() == "-" and dialog.table.item(0, 4).text() == "-"


def test_issuing_a_token_shows_it_once_and_stores_only_its_hash(dialog, access, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    _select(dialog, 0)

    dialog._issue_token()

    token = dialog.token_field.text()
    assert token, "the token has to be shown - it can never be read back"
    assert access.resolve_remote_token(token)["name"] == "Kowalski"
    assert dialog.table.item(0, 4).text() == "set"
    # Stored one-way: the token itself is nowhere in the listing.
    assert all(token not in str(user) for user in access.get_users())


def test_issuing_again_replaces_the_previous_token(dialog, access, monkeypatch):
    """How a leaked token is revoked: the old one stops working the
    moment a new one is generated."""
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    _select(dialog, 0)

    dialog._issue_token()
    first = dialog.token_field.text()
    dialog._issue_token()
    second = dialog.token_field.text()

    assert first != second
    assert access.resolve_remote_token(first) is None
    assert access.resolve_remote_token(second) is not None


def test_revoking_leaves_the_keypad_code_alone(dialog, access, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    access.set_user_pin("U1", "4711", level=AccessLevel.ENGINEER)
    _select(dialog, 0)
    dialog._issue_token()
    token = dialog.token_field.text()

    dialog._revoke_token()

    assert access.resolve_remote_token(token) is None
    assert access.attempt_user_login("4711") is not None, "the person still works at the panel"
    assert dialog.token_field.text() == ""


def test_nothing_can_be_changed_below_engineer(dialog, access, monkeypatch):
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text, *a, **k: warned.append(text))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    access.level = AccessLevel.OPERATOR
    _select(dialog, 0)

    dialog._issue_token()
    dialog._revoke_token()
    dialog._clear_code()

    assert dialog.token_field.text() == ""
    assert access.get_users()[0]["has_remote_token"] is False
    assert len(warned) == 3, "each attempt says why, rather than doing nothing silently"


def test_setting_a_code_needs_it_typed_twice(dialog, access, monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    answers = iter([("4711", True), ("4712", True)])
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: next(answers))
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text, *a, **k: warned.append(text))
    _select(dialog, 0)

    dialog._set_code()

    assert warned and "not the same" in warned[0]
    assert access.get_users()[0]["has_pin"] is False
