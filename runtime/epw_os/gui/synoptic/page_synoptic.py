"""The "Synoptic" page: the screen Studio embedded in projekt.epw, live
(punkt 2 / luka 5). Same nav-level place as Main View; shows why when
there is nothing to draw (no screens in the project, a refused document,
the symbol geometry file missing) instead of a blank canvas.

A click on a symbol bound to a SWITCHED apparatus goes the same way as
on the Main View (page_entry_gate.py): Operator access, a confirmation
popup, then CommandManager.request_command(<apparatus id>, CLOSE|OPEN)
- the apparatus's own command definitions (apparatus.py's
apparatus_command_definitions()) decide what that does on the outputs.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from epw_os.core.access_manager import AccessLevel
from epw_os.core.logging import log
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
        title = QLabel(tr("nav.synoptic"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

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
        """Re-reads the embedded screen and the analog units from the
        project manager - call after a project (re)load."""
        screens = {}
        analog_units = {}
        if self.project_manager is not None:
            getter = getattr(self.project_manager, "get_embedded_screens", None)
            screens = getter() if callable(getter) else {}
            points = getattr(self.project_manager, "get_analog_points", None)
            for point in (points() if callable(points) else []) or []:
                if isinstance(point, dict) and point.get("tag"):
                    analog_units[point["tag"]] = point.get("unit") or ""
        self.screen.set_sources(self.tag_manager, self.apparatus_registry, analog_units)
        self.screen.set_screen(screens)
        self._update_status(bool(screens))

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
            QMessageBox.warning(self, tr("pages.entry_gate.command_rejected_title"),
                                tr("pages.entry_gate.command_rejected_text", reason=(reasons or ["?"])[0]))
        return bool(permitted)
