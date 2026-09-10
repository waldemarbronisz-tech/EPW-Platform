"""Task "Studio: wyostrzenie stylu — wspólny rdzeń" - DOWOD script.
Window fixed at 1366px width (task's own requirement). Drives the REAL
StudioMainWindow, clicks Schemat synoptyczny then Logika, and for each:
  - screenshots the full window
  - screenshots a close-up crop of JUST the contextual toolbar row
    (same y-range both times, so the two crops can be overlaid pixel
    for pixel to check the core group's position)
  - reads back the core actions' own x-position within the toolbar
    (widgetForAction().geometry()) for a numeric check, not just visual
Also counts: total actions in each editor's context toolbar, how many
are the shared core, how many are that editor's own, and whether a
second row exists/was needed.
All screenshots re-opened and looked at before being cited anywhere.
Results in toolbar_core_probe_result.json.
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
window.resize(1366, 900)
window.move(0, 0)
window.show()

results = {}


def _toolbar_crop(pixmap):
    return pixmap.copy(0, 60, 1366, 50)


def _core_geometry(toolbar):
    geoms = {}
    for name in ("act_core_copy", "act_core_paste", "act_core_delete", "act_core_snap"):
        action = getattr(window, name)
        w = toolbar.widgetForAction(action)
        if w is not None:
            geoms[name] = [w.x(), w.y(), w.width(), w.height()]
    return geoms


def step1_click_screens():
    window.tree.setCurrentItem(window._item_screens)
    QTimer.singleShot(1200, step2_after_screens)


def _classify(toolbar):
    separators = 0
    widgets = 0
    real = 0
    for a in toolbar.actions():
        if a.isSeparator():
            separators += 1
        elif toolbar.widgetForAction(a) is not None and a not in (
            window.act_core_copy, window.act_core_paste, window.act_core_delete, window.act_core_snap
        ) and not a.text():
            widgets += 1
        else:
            real += 1
    return {"separators": separators, "breadcrumb_widgets": widgets, "real_buttons": real, "total": len(toolbar.actions())}


def step2_after_screens():
    container = window._aspect_containers[window._active]
    toolbar = container.context_toolbar
    results["screens_action_count"] = len(toolbar.actions())
    results["screens_breakdown"] = _classify(toolbar)
    results["screens_core_geometry"] = _core_geometry(toolbar)
    results["screens_toolbar_button_style"] = int(toolbar.toolButtonStyle().value)
    results["screens_second_row_exists"] = hasattr(container, "context_toolbar_row2")
    pm = window.grab()
    pm.save(str(OUT_DIR / "core_screens_full.png"))
    _toolbar_crop(pm).save(str(OUT_DIR / "core_screens_toolbar.png"))
    QTimer.singleShot(400, step3_click_logic)


def step3_click_logic():
    window.tree.setCurrentItem(window._item_logic)
    QTimer.singleShot(500, step4_after_logic)


def step4_after_logic():
    container = window._aspect_containers[window._active]
    toolbar = container.context_toolbar
    results["logic_action_count"] = len(toolbar.actions())
    results["logic_breakdown"] = _classify(toolbar)
    results["logic_core_geometry"] = _core_geometry(toolbar)
    results["logic_second_row_exists"] = hasattr(container, "context_toolbar_row2")
    pm = window.grab()
    pm.save(str(OUT_DIR / "core_logic_full.png"))
    _toolbar_crop(pm).save(str(OUT_DIR / "core_logic_toolbar.png"))
    QTimer.singleShot(300, finish)


def finish():
    with open(OUT_DIR / "toolbar_core_probe_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    app.quit()


QTimer.singleShot(500, step1_click_screens)
QTimer.singleShot(25000, app.quit)
app.exec()
