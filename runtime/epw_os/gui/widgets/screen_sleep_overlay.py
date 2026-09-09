from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QKeyEvent


class ScreenSleepOverlay(QWidget):
    """Solid black widget covering the whole MainWindow when idle - a
    screen-blank/kiosk mode, distinct from the existing 5-minute
    access-level auto-logout (that one changes *permissions*; this one
    only changes what's on screen, nobody gets logged out).

    Parented directly to MainWindow (not just its central widget) and
    manually raised/resized to MainWindow's full rect, so it covers the
    menu bar and status bar too, not just the page area.

    Woken by literally anything - a real touchscreen has no hover state,
    so waiting for a specific gesture would be wrong; any mouse press,
    mouse move, or key press wakes it, matching MainWindow's existing
    eventFilter which already tracks the same three event types
    app-wide for the access-timeout timer."""

    woken = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: black;")
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.hide()

    def show_asleep(self):
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self.show()
        self.raise_()
        self.setFocus()

    def mousePressEvent(self, event: QMouseEvent):
        self.woken.emit()

    def mouseMoveEvent(self, event: QMouseEvent):
        self.woken.emit()

    def keyPressEvent(self, event: QKeyEvent):
        self.woken.emit()
