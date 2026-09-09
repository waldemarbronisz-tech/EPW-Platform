import time

from PySide6.QtWidgets import QLabel, QLineEdit, QStackedWidget
from PySide6.QtCore import Qt, Signal, QEvent

from epw_os.gui.theme_manager import get_theme_manager
from epw_os.i18n import tr

class StatusLabel(QLabel):
    """A generic status badge (System Topology, Main View's device
    panel) - colored by the theme's semantic state tokens (Task:
    przelaczane motywy wizualne), never a hardcoded color, and re-derived
    from self.text() on every theme change so it stays correct live,
    with no restart and no page-level wiring needed for THIS widget
    specifically (see __init__ below)."""

    def __init__(self, text="UNKNOWN", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Task: podpowiedzi - "status urzadzenia -> od kiedy w tym
        # stanie". None until update_status() has run for real at least
        # once (below) - _since is only ever advanced on a genuine text
        # change (see the guard in update_status()), never by a
        # theme-only recolor (_on_theme_changed() re-invokes
        # update_status() with the SAME text purely to re-derive colors).
        self._since = None
        get_theme_manager().theme_changed.connect(self._on_theme_changed)
        self.update_status(text)

    def _on_theme_changed(self, _index):
        self.update_status(self.text())

    def update_status(self, status):
        status_str = str(status)
        if self._since is None or status_str != self.text():
            self._since = time.time()
        self.setText(status_str)
        # Cheap (one time.strftime() call, only on an actual text/color
        # refresh - never on a bare mouse move, per GRANICE's "nie licz
        # nic ciezkiego przy kazdym ruchu myszy").
        self.setToolTip(tr("pages.common.tooltip_status_since", time=time.strftime("%H:%M:%S", time.localtime(self._since))))
        status_upper = status_str.upper()
        colors = get_theme_manager().current_colors()

        color = colors["accent_text"]  # default - was "white"
        if "READY" in status_upper or "ONLINE" in status_upper or "OK" in status_upper or "RUNNING" in status_upper or status_upper == "CLOSED":
            color = colors["state_ok"]
        elif "TRIP" in status_upper or "ALARM" in status_upper or "FAULT" in status_upper or "OFFLINE" in status_upper or "LOST" in status_upper or "FAILURE" in status_upper:
            color = colors["state_alarm"]
        elif "STARTING" in status_upper or "PICKUP" in status_upper or "BOOTING" in status_upper:
            color = colors["state_warning"]
        elif "WARNING" in status_upper or "SIMULATION" in status_upper:
            color = colors["state_caution"]
        elif "BLOCKED" in status_upper:
            color = colors["state_info"]
        elif "DISABLED" in status_upper or status_upper == "OPEN" or "TIMEOUT" in status_upper:
            color = colors["state_neutral"]
        elif "UNKNOWN" in status_upper:
            color = colors["state_unknown"]

        self.setStyleSheet(
            f"background-color: {colors['lcd_bg']}; color: {color}; "
            f"border: 2px inset {colors['bevel_shadow']}; font-weight: bold; font-size: 12px; padding: 2px;"
        )


class EditableLabel(QStackedWidget):
    """A QLabel that turns into an inline QLineEdit on double-click - the
    same "double-click a field to rename it" interaction as the Digital
    Inputs Description column, for places (panel headers) that aren't a
    QTableWidget. Commits on Enter/focus-loss, Escape cancels back to the
    prior text. Emits `edited(new_text)` only when the text actually
    changed (no-op edits don't fire a save)."""
    edited = Signal(str)

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._label = QLabel(text)
        self._edit = QLineEdit(text)
        self._edit.installEventFilter(self)
        self.addWidget(self._label)
        self.addWidget(self._edit)
        self.setCurrentWidget(self._label)

        self._label.mouseDoubleClickEvent = self._start_edit
        self._edit.editingFinished.connect(self._commit_edit)

    def text(self):
        return self._label.text()

    def setText(self, text):
        self._label.setText(text)
        self._edit.setText(text)

    def setStyleSheet(self, qss):
        self._label.setStyleSheet(qss)

    def setAlignment(self, alignment):
        self._label.setAlignment(alignment)

    def eventFilter(self, obj, event):
        if obj is self._edit and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self._edit.setText(self._label.text())
            self.setCurrentWidget(self._label)
            return True
        return super().eventFilter(obj, event)

    def _start_edit(self, event=None):
        self._edit.setText(self._label.text())
        self.setCurrentWidget(self._edit)
        self._edit.setFocus()
        self._edit.selectAll()

    def _commit_edit(self):
        if self.currentWidget() is not self._edit:
            return  # already committed/cancelled - editingFinished can re-fire on the focus-out this causes
        new_text = self._edit.text()
        old_text = self._label.text()
        self.setCurrentWidget(self._label)
        if new_text != old_text:
            self._label.setText(new_text)
            self.edited.emit(new_text)
