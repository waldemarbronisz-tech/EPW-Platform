"""Task "Studio: wyostrzenie stylu i układu do poziomu narzędzia
profesjonalnego" - DOWOD script. Drives the REAL StudioMainWindow:
  - clicks Schemat synoptyczny, screenshots the full window and a
    close-up crop of the chrome (menu/shared toolbar/contextual
    toolbar) for bevel/separator inspection.
  - clicks Logika, same two screenshots - Problem 1's own proof is that
    the chrome above the document area is THREE bars both times, not
    five, and reads as the same skin.
  - reads back both editors' own hidden bars' visibility (menuBar()/
    toolbar for Logic, DOM query for Synoptic) to confirm they are
    actually hidden, not just visually behind something.
All screenshots re-opened and looked at before being cited anywhere,
per this session's own standing rule. Results written to
studio_polish_probe_result.json, not printed (Windows console codepage
issue with Polish text, same as every other probe script this session).
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
OUT_DIR = Path(__file__).resolve().parent

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from studio.shell.logic_panel import _ensure_logic_studio_importable
_ensure_logic_studio_importable()
from logic_studio.app import apply_classic_style
apply_classic_style(app)

from studio.shell.main_window import StudioMainWindow

window = StudioMainWindow()
window.resize(1500, 1000)
window.show()

results = {}


def _crop_chrome(pixmap):
    # Top ~230px covers menu bar + shared toolbar + contextual toolbar
    # with a little of the document area below, at this window size.
    return pixmap.copy(0, 0, 1500, 230)


def step1_click_screens():
    window.tree.setCurrentItem(window._item_screens)
    QTimer.singleShot(1200, step2_after_screens)


def step2_after_screens():
    results["logic_toolbar_visible_before_check"] = "n/a (screens active)"
    pm = window.grab()
    pm.save(str(OUT_DIR / "polish_screens_full.png"))
    _crop_chrome(pm).save(str(OUT_DIR / "polish_screens_chrome.png"))

    def _check_dom(has_menu, has_toolbar):
        results["synoptic_menu_bar_hidden"] = not bool(has_menu)
        results["synoptic_toolbar_hidden"] = not bool(has_toolbar)

    pv = window._synoptic_panel.web_view().page()
    pv.runJavaScript(
        "(function(){const m=document.querySelector('.menu-bar');"
        "return m ? getComputedStyle(m).display !== 'none' : false;})()",
        lambda has_menu: pv.runJavaScript(
            "(function(){const t=document.querySelector('.toolbar');"
            "return t ? getComputedStyle(t).display !== 'none' : false;})()",
            lambda has_toolbar: _check_dom(has_menu, has_toolbar),
        ),
    )
    QTimer.singleShot(500, step3_click_logic)


def step3_click_logic():
    window.tree.setCurrentItem(window._item_logic)
    QTimer.singleShot(500, step4_after_logic)


def step4_after_logic():
    results["logic_own_menu_bar_visible"] = window._logic_panel.main_window().menuBar().isVisible()
    results["logic_own_toolbar_visible"] = window._logic_panel.main_window().toolbar.isVisible()
    pm = window.grab()
    pm.save(str(OUT_DIR / "polish_logic_full.png"))
    _crop_chrome(pm).save(str(OUT_DIR / "polish_logic_chrome.png"))
    QTimer.singleShot(300, step5_logic_color_picker)


def step5_logic_color_picker():
    # Opens the REAL StudioColorDialog (not a mock), picks a distinct
    # color programmatically (no human to click the wheel), accepts,
    # and lets it apply through the real set_canvas_background() path.
    from studio.shell.color_picker import StudioColorDialog
    from PySide6.QtGui import QColor

    results["logic_canvas_background_before"] = window._logic_panel.canvas_background()

    def _open_and_accept():
        dlg = StudioColorDialog(QColor("#FFFFFF"), window)
        dlg._set_color(QColor("#FFD9A0"), update_wheel=True)
        results["dialog_new_swatch_color"] = dlg._new_swatch.color().name()
        dlg.grab().save(str(OUT_DIR / "polish_color_picker.png"))
        dlg.accept()
        window._logic_panel.set_canvas_background(dlg.selected_color().name())

    QTimer.singleShot(0, _open_and_accept)
    QTimer.singleShot(300, step6_after_logic_color)


def step6_after_logic_color():
    results["logic_canvas_background_after"] = window._logic_panel.canvas_background()
    window.grab().save(str(OUT_DIR / "polish_logic_canvas_colored.png"))
    QTimer.singleShot(300, step7_screens_color)


def step7_screens_color():
    window.tree.setCurrentItem(window._item_screens)
    QTimer.singleShot(1000, step8_apply_screens_color)


def step8_apply_screens_color():
    def _got_before(color):
        results["synoptic_canvas_background_before"] = color
        window._synoptic_panel.set_canvas_background("#C9E8FF")
        QTimer.singleShot(400, step9_after_screens_color)

    window._synoptic_panel.query_canvas_background(_got_before)


def step9_after_screens_color():
    def _got_after(color):
        results["synoptic_canvas_background_after"] = color
        window.grab().save(str(OUT_DIR / "polish_screens_canvas_colored.png"))
        QTimer.singleShot(200, finish)

    window._synoptic_panel.query_canvas_background(_got_after)


def finish():
    with open(OUT_DIR / "studio_polish_probe_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    app.quit()


QTimer.singleShot(500, step1_click_screens)
QTimer.singleShot(25000, app.quit)
app.exec()
