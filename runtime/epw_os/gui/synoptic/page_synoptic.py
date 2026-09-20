"""THE Main View: the screen Studio embedded in projekt.epw, live.

This page used to sit next to a second one - a hand-built drawing of one
particular entry gate, with a measurement panel whose voltages, currents
and power were invented by a 250 ms timer and a device-feedback path that
succeeded 95% of the time by random(). That page is gone (owner's
instruction: "main view ma mieć tylko obraz z synoptic - tam umieszczamy
wizualizację pomiarów"), and this is what the operator sees instead. A
real measurement reaches them the way every other value does: drawn on
the screen in the Synoptic editor, bound to a real point.

Shows why when there is nothing to draw (no screens in the project, a
refused document, the symbol geometry file missing) instead of a blank
canvas, and offers a selector when the project carries several screens.

A click on a symbol bound to a SWITCHED apparatus takes the ordinary
command path: Operator access, a confirmation popup, then
CommandManager.request_command(<apparatus id>, CLOSE|OPEN) - the
apparatus's own command definitions (apparatus.py's
apparatus_command_definitions()) decide what that does on the outputs.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from epw_os.core.access_manager import AccessLevel
from epw_os.core.logging import log
from epw_os.core.screen_set import active_screen_id, has_screen, screen_document, screen_list
from epw_os.gui.synoptic.screen_state import command_for_toggle
from epw_os.gui.synoptic.screen_widget import SynopticScreenWidget
from epw_os.i18n import tr


class PageSynoptic(QWidget):
    def __init__(self, tag_manager, project_manager=None, apparatus_registry=None, access_manager=None,
                 command_manager=None, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.project_manager = project_manager
        self.apparatus_registry = apparatus_registry
        self.access_manager = access_manager
        self.command_manager = command_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        title = QLabel(tr("nav.main_diagram"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        # One project can carry several screens (SPEC: "screens: name,
        # kolejność przełączania"); the row appears only when there is
        # more than one to switch between.
        self.screen_row = QWidget(self)
        row_layout = QHBoxLayout(self.screen_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(QLabel(tr("pages.synoptic.screen_label")))
        self.screen_selector = QComboBox()
        self.screen_selector.setMinimumWidth(220)
        self.screen_selector.currentIndexChanged.connect(self._on_screen_selected)
        row_layout.addWidget(self.screen_selector)
        row_layout.addStretch()
        layout.addWidget(self.screen_row)
        self.screen_row.setVisible(False)
        self._document = {}

        self.status_label = QLabel("")
        self.status_label.setObjectName("SynopticStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.screen = SynopticScreenWidget(self)
        self.screen.object_clicked.connect(self._on_object_clicked)
        layout.addWidget(self.screen, stretch=1)

        self.reload()

    # -- data -------------------------------------------------------------------------

    def reload(self):
        """Re-reads the embedded screens and the analog units from the
        project manager - call after a project (re)load. Opens the screen
        the panel had open before the restart when the project still has
        it, otherwise the one the editor left active."""
        screens = {}
        analog_units = {}
        if self.project_manager is not None:
            getter = getattr(self.project_manager, "get_embedded_screens", None)
            screens = getter() if callable(getter) else {}
            points = getattr(self.project_manager, "get_analog_points", None)
            for point in (points() if callable(points) else []) or []:
                if isinstance(point, dict) and point.get("tag"):
                    analog_units[point["tag"]] = point.get("unit") or ""
        self._document = screens or {}
        self.screen.set_sources(self.tag_manager, self.apparatus_registry, analog_units)

        entries = screen_list(self._document) if self._document else []
        remembered = None
        if self.project_manager is not None:
            getter = getattr(self.project_manager, "get_last_synoptic_screen", None)
            remembered = getter() if callable(getter) else None
        chosen = remembered if (remembered and has_screen(self._document, remembered))             else active_screen_id(self._document)

        self.screen_selector.blockSignals(True)
        self.screen_selector.clear()
        for entry in entries:
            self.screen_selector.addItem(entry["name"] or entry["id"], entry["id"])
        index = self.screen_selector.findData(chosen)
        if index >= 0:
            self.screen_selector.setCurrentIndex(index)
        self.screen_selector.blockSignals(False)
        self.screen_row.setVisible(len(entries) > 1)

        self._show_screen(chosen, remember=False)

    def _on_screen_selected(self, index: int):
        screen_id = self.screen_selector.itemData(index)
        if screen_id is not None:
            self._show_screen(screen_id)

    def _show_screen(self, screen_id, remember: bool = True):
        """Draws one screen of the document and (unless this is the
        restore at load) remembers it in runtime_state.json."""
        self.screen.set_screen(screen_document(self._document, screen_id) if self._document else {})
        if remember and self.project_manager is not None:
            setter = getattr(self.project_manager, "set_last_synoptic_screen", None)
            if callable(setter):
                setter(screen_id)
        self._update_status(bool(self._document))

    def _update_status(self, has_section: bool):
        messages = []
        if not has_section:
            messages.append(tr("pages.synoptic.no_screens"))
        elif self.screen.load_error:
            messages.append(tr("pages.synoptic.screen_refused", reason=self.screen.load_error))
        if self.screen.geometry_problem:
            messages.append(tr("pages.synoptic.geometry_missing", reason=self.screen.geometry_problem))
        elif self.screen.document is not None and self.screen.document.warnings:
            messages.append(tr("pages.synoptic.screen_warnings", count=len(self.screen.document.warnings)))
        self.status_label.setText("\n".join(messages))
        self.status_label.setVisible(bool(messages))

    def shutdown(self):
        self.screen.shutdown()

    # -- commands ----------------------------------------------------------------------

    def _on_object_clicked(self, obj, presentation, global_pos):
        if presentation is None or not presentation.commandable:
            return
        apparatus = presentation.apparatus
        main_window = self.window()
        access = self.access_manager or getattr(main_window, "access_manager", None)
        if access is not None and not access.has_access(AccessLevel.OPERATOR):
            deny = getattr(main_window, "deny_access", None)
            if callable(deny):
                deny(AccessLevel.OPERATOR, "Device control from the Synoptic screen")
            return
        action = command_for_toggle(apparatus, self.screen._tag_reader)
        if action is None:
            QMessageBox.information(self, tr("pages.synoptic.state_unknown_title"),
                                    tr("pages.synoptic.state_unknown", device=apparatus.id))
            return
        if not self.confirm_command(apparatus, action, global_pos):
            return
        self.send_command(apparatus.id, action)

    def confirm_command(self, apparatus, action: str, global_pos=None) -> bool:
        """The same ConfirmationPopup the Main View uses; a subclass or a
        test can replace it."""
        from epw_os.gui.widgets.popups import ConfirmationPopup
        current = tr("pages.common.state_open") if action == "CLOSE" else tr("pages.common.state_closed")
        popup = ConfirmationPopup(apparatus.id, current, action, tr("access.operator"), self)
        if global_pos is not None:
            popup.move(global_pos)
        return bool(popup.exec())

    def send_command(self, apparatus_id: str, action: str) -> bool:
        command_manager = self.command_manager or getattr(self.window(), "command_manager", None)
        if command_manager is None:
            log.error("Synoptic page: no command manager - command not sent.")
            return False
        permitted, reasons = command_manager.request_command(apparatus_id, action)
        if not permitted:
            QMessageBox.warning(self, tr("pages.synoptic.command_rejected_title"),
                                tr("pages.synoptic.command_rejected_text", reason=(reasons or ["?"])[0]))
        return bool(permitted)
