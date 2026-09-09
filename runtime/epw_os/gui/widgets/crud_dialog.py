"""A minimal Add/Edit/Remove list dialog shell, reused across every
page in this app that just needs "manage a small named collection" -
zones/lines (page_intrusion.py's PageIntrusionConfiguration) and
process protections (page_protection_process.py). Originally a private
method on the old single PageIntrusion class; factored out here (page-
split task) so a second, near-identical ~70-line copy wasn't needed for
Process Protections - same "don't duplicate, extract and reuse" stance
this codebase's own other shared dialog helpers already follow
(table_helpers.py's ItemBackgroundDelegate/apply_table_button_style)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
                             QListWidget, QListWidgetItem)

from epw_os.i18n import tr


def run_crud_dialog(parent, title, get_items, item_label, open_add_dialog, open_edit_dialog,
                     on_add, on_edit, on_remove, remove_refused_message):
    """`get_items()` returns the current list; `item_label(item)` is the
    list row's display text; `open_add_dialog()`/`open_edit_dialog(item)`
    return a QDialog whose `.exec()` return value gates whether `on_add
    (dialog)`/`on_edit(item, dialog)` actually runs; `on_remove(item)`
    returns whether the removal succeeded (False shows
    `remove_refused_message`, if given). Uses the same i18n keys every
    caller of this shell already shared (pages.intrusion.btn_add/
    btn_edit/btn_remove/btn_close) - generic list-management wording,
    not specific to any one domain."""
    dialog = QDialog(parent)
    dialog.setObjectName("IndustrialDialog")
    dialog.setWindowTitle(title)
    dialog.setModal(True)
    dialog.setMinimumSize(360, 320)
    layout = QVBoxLayout(dialog)

    list_widget = QListWidget()

    def _reload_list():
        list_widget.clear()
        for item in get_items():
            entry = QListWidgetItem(item_label(item))
            entry.setData(Qt.ItemDataRole.UserRole, item)
            list_widget.addItem(entry)

    _reload_list()
    layout.addWidget(list_widget)

    btn_row = QHBoxLayout()
    btn_add = QPushButton(tr("pages.intrusion.btn_add"))
    btn_edit = QPushButton(tr("pages.intrusion.btn_edit"))
    btn_remove = QPushButton(tr("pages.intrusion.btn_remove"))
    btn_row.addWidget(btn_add)
    btn_row.addWidget(btn_edit)
    btn_row.addWidget(btn_remove)
    layout.addLayout(btn_row)

    btn_close = QPushButton(tr("pages.intrusion.btn_close"))
    btn_close.clicked.connect(dialog.accept)
    layout.addWidget(btn_close)

    def _add():
        add_dlg = open_add_dialog()
        if add_dlg.exec():
            on_add(add_dlg)
            _reload_list()

    def _edit():
        current = list_widget.currentItem()
        if current is None:
            return
        item = current.data(Qt.ItemDataRole.UserRole)
        edit_dlg = open_edit_dialog(item)
        if edit_dlg.exec():
            on_edit(item, edit_dlg)
            _reload_list()

    def _remove():
        current = list_widget.currentItem()
        if current is None:
            return
        item = current.data(Qt.ItemDataRole.UserRole)
        if not on_remove(item):
            if remove_refused_message:
                QMessageBox.warning(dialog, title, remove_refused_message)
        else:
            _reload_list()

    btn_add.clicked.connect(_add)
    btn_edit.clicked.connect(_edit)
    btn_remove.clicked.connect(_remove)

    dialog.exec()
