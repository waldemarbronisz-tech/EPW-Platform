"""Task "jedno źródło listy kart", etap 4: switching to Logika (any
aspect, but Logika is the one that embeds a full Logic Studio MainWindow
and is where the jank was actually reported/measured) used to rebuild a
fresh _AspectContainer - and so re-parent the cached editor widget into
a new layout - on EVERY visit. Measured ~135ms per cached re-visit
(spike/addressing_migration/... in the chat report); the fix reuses one
container per aspect and only rebuilds its own contextual toolbar.
"""
import os
import tempfile
import time

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Card
from studio.shell.project_panels import sync_points_for_card


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


def test_the_same_container_is_reused_across_visits(tmp_path):
    _app()
    win = _window(tmp_path)
    win.show()
    _app().processEvents()

    win._open_io_cards()
    first = win._aspect_containers["io_cards"]
    win._open_point_registry()
    win._open_io_cards()
    second = win._aspect_containers["io_cards"]

    assert first is second


def test_toolbar_actions_do_not_accumulate_across_repeated_visits(tmp_path):
    _app()
    win = _window(tmp_path)
    win.show()
    _app().processEvents()

    win._open_io_cards()
    container = win._aspect_containers["io_cards"]
    count_after_first_visit = len(container.context_toolbar.actions())

    win._open_point_registry()
    win._open_io_cards()
    win._open_point_registry()
    win._open_io_cards()

    assert len(container.context_toolbar.actions()) == count_after_first_visit


def test_the_editor_widget_is_never_reparented_on_a_revisit(tmp_path):
    """The actual fix, not just its side effect: the cached editor
    widget's own parent (the _AspectContainer) is the SAME object
    across visits - it is genuinely never re-added to a layout."""
    _app()
    win = _window(tmp_path)
    win.show()
    _app().processEvents()

    win._open_io_cards()
    cards_panel = win._cards_panel
    original_parent = cards_panel.parentWidget()

    win._open_point_registry()
    win._open_io_cards()

    assert cards_panel.parentWidget() is original_parent


def test_revisiting_logika_is_fast_once_the_panel_is_cached(tmp_path):
    """The reported symptom itself, measured directly - a generous
    threshold (the old behavior measured ~135ms; the fix, ~20-25ms) so
    this catches a real regression without being flaky on slower CI
    hardware."""
    _app()
    win = _window(tmp_path)
    for i in range(1, 3):
        card = Card(id=f"ELA{i}", model="ELA01", kind="DI", channels=32)
        win._project.cards.append(card)
        sync_points_for_card(win._project, card)
    win.show()
    _app().processEvents()

    win._open_logic()  # first visit - real construction, not timed
    _app().processEvents()
    win._open_io_cards()
    _app().processEvents()

    t0 = time.perf_counter()
    win._open_logic()
    _app().processEvents()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 80, f"revisiting Logika took {elapsed_ms:.1f}ms - expected the cached-panel fast path"
