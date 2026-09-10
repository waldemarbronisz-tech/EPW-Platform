"""Task "EPW Studio: przebudowa nawigacji wg wzorca e2TANGO" - Stage 1
DOWOD script. Drives the REAL StudioMainWindow (not a mock):
  - clicks Schemat synoptyczny, reads back the top QMenuBar's titles.
  - clicks Logika, reads back the top QMenuBar's titles again - the
    PRIMARY proof this task asks for is that these two lists are
    IDENTICAL (same count, same text, same order).
  - clicks one inactive branch (Karty wejsc/wyjsc) and reads back the
    placeholder's header/message text and the tree item's own grey/
    italic styling.
Screenshots for each state, saved to disk - all re-opened and looked at
before being cited anywhere, per this session's own standing rule.
Results (menu snapshots, placeholder text) written to
navigation_probe_result.json, not printed - Windows console codepage
mangles Polish text mid-run in this environment.
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


def _menu_snapshot():
    mb = window.menuBar()
    return [action.text() for action in mb.actions()]


def step1_click_screens():
    window.tree.setCurrentItem(window._item_screens)
    QTimer.singleShot(1200, step2_after_screens)  # let the webview load + skin apply


def step2_after_screens():
    results["screens_menu"] = _menu_snapshot()
    window.grab().save(str(OUT_DIR / "nav_screens_active.png"))
    QTimer.singleShot(500, step3_click_logic)


def step3_click_logic():
    window.tree.setCurrentItem(window._item_logic)
    QTimer.singleShot(500, step4_after_logic)


def step4_after_logic():
    results["logic_menu"] = _menu_snapshot()
    results["menus_identical"] = results["screens_menu"] == results["logic_menu"]
    window.grab().save(str(OUT_DIR / "nav_logic_active.png"))
    QTimer.singleShot(300, step5_click_inactive)


def step5_click_inactive():
    # "Karty wejsc/wyjsc" - the second child of KONFIGURACJA.
    config_group = window._item_screens.parent()
    io_cards_item = None
    for i in range(config_group.childCount()):
        child = config_group.child(i)
        data = child.data(0, 0x0100)  # Qt.ItemDataRole.UserRole
        if data and data[0] == "inactive" and data[1] == "io_cards":
            io_cards_item = child
            break
    assert io_cards_item is not None, "could not find the Karty wejsc/wyjsc tree item"
    window._io_cards_item_for_probe = io_cards_item
    window.tree.setCurrentItem(io_cards_item)
    QTimer.singleShot(400, step6_after_inactive)


def step6_after_inactive():
    item = window._io_cards_item_for_probe
    results["inactive_item_text"] = item.text(0)
    results["inactive_item_grey"] = item.foreground(0).color().name()
    results["inactive_item_italic"] = item.font(0).italic()
    results["placeholder_header"] = window._inactive_placeholder.header.text()
    results["placeholder_message"] = window._inactive_placeholder.message.text()
    results["active_after_inactive_click"] = window._active
    window.grab().save(str(OUT_DIR / "nav_inactive_branch.png"))
    QTimer.singleShot(300, step7_switch_to_english)


def step7_switch_to_english():
    # Exercises Ustawienia -> Jezyk -> English directly (the same
    # method the act_lang_en QAction's own triggered signal calls) -
    # simpler and just as faithful as clicking through the real menu,
    # and avoids fighting Qt's own menu-popup event loop from a script.
    window._set_language("en")
    QTimer.singleShot(300, step8_after_language_switch)


def step8_after_language_switch():
    results["menu_after_english"] = _menu_snapshot()
    results["tree_root_after_english"] = window.tree.topLevelItem(0).text(0)
    results["breadcrumb_after_english"] = window._inactive_placeholder.header.text()
    results["placeholder_after_english"] = window._inactive_placeholder.message.text()
    window.grab().save(str(OUT_DIR / "nav_after_language_switch.png"))
    QTimer.singleShot(200, finish)


def finish():
    with open(OUT_DIR / "navigation_probe_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    app.quit()


QTimer.singleShot(500, step1_click_screens)
QTimer.singleShot(25000, app.quit)
app.exec()
