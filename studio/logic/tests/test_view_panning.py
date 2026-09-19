"""User, 2026-09-18: "ruch po kanwasie poprzez kliknięcie i przytrzymanie
scrolla" - the middle button pans the Logic canvas (LogicView). Checked
with real mouse events through QTest, on a scene large enough to scroll."""
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from shared.logic.blocks import register_builtin_blocks

register_builtin_blocks()


def _app():
    return QApplication.instance() or QApplication([])


def test_middle_button_drag_pans_the_view_and_releases_cleanly(qsettings):
    _app()
    from logic_studio.ui.main_window import MainWindow
    window = MainWindow(settings=qsettings)
    try:
        window.scene.clear()
        window.scene.setSceneRect(-5000, -5000, 10000, 10000)
        view = window.view
        window.resize(800, 600)
        window.show()
        QTest.qWaitForWindowExposed(window)
        before = view.mapToScene(QPoint(0, 0))
        start, end = QPoint(300, 300), QPoint(180, 240)
        QTest.mousePress(view.viewport(), Qt.MiddleButton, Qt.NoModifier, start)
        assert view._is_panning
        QTest.mouseMove(view.viewport(), end)
        QTest.mouseRelease(view.viewport(), Qt.MiddleButton, Qt.NoModifier, end)
        assert not view._is_panning
        after = view.mapToScene(QPoint(0, 0))
        scale = view.current_zoom()
        assert round((after.x() - before.x()) * scale) == 120     # the scene moved with the pointer
        assert round((after.y() - before.y()) * scale) == 60
        assert view.cursor().shape() == Qt.ArrowCursor
        assert not window.scene.selectedItems()                   # no marquee, nothing selected
    finally:
        window.is_dirty = False
        window.close()
