"""Shared fixtures for studio/shell/tests.

Many tests build a real StudioMainWindow and simply let it fall out of
scope. Its 400 ms shared-toolbar timer (_state_timer) and its editor
polls keep firing in whatever test pumps the Qt event loop next; once
the suite holds enough half-collected windows, a timer reaches a
toolbar action whose C++ object is already gone and every later test
that pumps events sees "libshiboken: Internal C++ object (QAction)
already deleted" from the Qt loop - order-dependent and unrelated to the
test that reports it. The autouse fixture below stops the timers of
every window still alive after each test, so a window can only ever
act inside its own test.
"""
import pytest


@pytest.fixture(autouse=True)
def _quiesce_studio_windows():
    yield
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
    except ImportError:  # a test module that never touched Qt
        return
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        if type(widget).__name__ != "StudioMainWindow":
            continue
        try:
            for timer in widget.findChildren(QTimer):
                timer.stop()
            widget.hide()
        except RuntimeError:
            pass  # already deleted on the C++ side - nothing left to stop
    app.processEvents()
