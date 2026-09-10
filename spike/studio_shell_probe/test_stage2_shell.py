"""Stage 2 smoke test ("EPW Studio: jedna szata graficzna") - drives the
REAL StudioMainWindow (not a mock), clicking through the tree exactly as
a user would, and:
  1. screenshots Studio with Screens active and with Logic active, for
     the DOWOD requirement (one menu, one skin, same position both
     times) - both screenshots opened and looked at before being cited
     anywhere, per this session's own standing rule.
  2. reads back the actual QMenuBar structure in both contexts (menu
     titles + item counts) to confirm one shared menu bar, not two.
  3. exercises the shared toolbar's honesty requirement (uściślenie
     2.2): Undo must be disabled with a fresh Logic project and become
     enabled after a real edit produces a real undo-stack entry.
Results written to stage2_probe_result.json - not printed to stdout,
same Windows-console-codepage reasoning as test_menu_reachability.py.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
OUT_DIR = Path(__file__).resolve().parent

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from studio.shell.logic_panel import _ensure_logic_studio_importable
_ensure_logic_studio_importable()
from logic_studio.app import apply_classic_style
apply_classic_style(app)

from studio.shell.main_window import StudioMainWindow, _TREE_ITEM_LOGIC, _TREE_ITEM_SCREENS

window = StudioMainWindow()
window.resize(1500, 1000)
window.show()

results = {}


def _menu_snapshot():
    mb = window.menuBar()
    return [
        {"title": action.text(), "item_count": len(action.menu().actions()) if action.menu() else 0}
        for action in mb.actions()
    ]


def step1_click_screens():
    item = window._item_screens
    window.tree.setCurrentItem(item)
    QTimer.singleShot(1200, step2_after_screens)  # give the webview time to load + apply skin


def step2_after_screens():
    results["screens_menu"] = _menu_snapshot()
    results["screens_active_value"] = window._active
    window.grab().save(str(OUT_DIR / "stage2_screens_active.png"))
    QTimer.singleShot(600, step3_click_logic)


def step3_click_logic():
    item = window._item_logic
    window.tree.setCurrentItem(item)
    QTimer.singleShot(500, step4_after_logic)


def step4_after_logic():
    results["logic_menu"] = _menu_snapshot()
    results["logic_active_value"] = window._active
    # Fresh project: nothing to undo yet.
    mw = window._logic_panel.main_window()
    results["logic_undo_enabled_before_edit"] = window.act_shared_undo.isEnabled()
    results["logic_undo_stack_len_before"] = len(mw.project.undo_stack)

    # A real edit: add one block via the same path the library panel's
    # own drag-and-drop uses (add_block_from_library), so a real
    # undo-stack entry gets pushed - not a synthetic append, the actual
    # production code path.
    from logic_studio.blocks.registry import BlockRegistry
    category = BlockRegistry.get_categories()[0]
    block_type = BlockRegistry.get_blocks_in_category(category)[0]
    mw.scene.add_block_from_library(block_type, 200, 200)

    QTimer.singleShot(300, step5_after_edit)


def step5_after_edit():
    mw = window._logic_panel.main_window()
    window._refresh_shared_toolbar_state()
    QTimer.singleShot(200, lambda: step6_check_after_edit(mw))


def step6_check_after_edit(mw):
    results["logic_undo_stack_len_after"] = len(mw.project.undo_stack)
    results["logic_undo_enabled_after_edit"] = window.act_shared_undo.isEnabled()
    results["logic_save_enabled_after_edit"] = window.act_shared_save.isEnabled()
    window.grab().save(str(OUT_DIR / "stage2_logic_active.png"))
    QTimer.singleShot(300, step7_back_to_screens_query_bridge)


def step7_back_to_screens_query_bridge():
    window.tree.setCurrentItem(window._item_screens)
    QTimer.singleShot(1200, step8_query_synoptic_bridge)


def step8_query_synoptic_bridge():
    window._synoptic_panel.query_state(step9_finish)


def step9_finish(state):
    results["synoptic_bridge_state_fresh_project"] = state
    with open(OUT_DIR / "stage2_probe_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    app.quit()


QTimer.singleShot(500, step1_click_screens)
QTimer.singleShot(25000, app.quit)
app.exec()
