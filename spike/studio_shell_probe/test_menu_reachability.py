"""Stage 1 reconnaissance (EPW Studio UI standard task), question 1.2:
can a Synoptic menu action be invoked from Python via runJavaScript?
Checked empirically, not from reading MenuBar.tsx alone.

Method: MenuBar.tsx renders every dropdown item as a plain
<div class="dropdown-item" onClick=...> - CSS only shows it on
`.menu-item:hover` (index.css), but the DOM node exists unconditionally,
so a plain `.click()` via runJavaScript fires the real onClick handler
regardless of CSS visibility. "Save" itself is deliberately NOT the
action clicked here - ProjectFileService.saveFile() falls through to
saveFileAs() -> window.showSaveFilePicker(), a real native OS file
dialog that would block this automated script waiting for a human.
"Snap to Grid" (View menu) is used instead - same click-a-.dropdown-
item mechanism, but its effect (a checkmark prefix toggling in the
menu's own text) is safely observable without any dialog.

Result written to menu_click_probe_result.json, not printed - Windows
console codepage mangles the Polish check-mark text mid-run in this
environment; the file is unambiguous.
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
from studio.shell.synoptic_panel import SynopticPanel

panel = SynopticPanel()
panel.resize(1200, 800)
panel.show()
pv = panel.web_view().page()
results = {}


def step1_list_items():
    pv.runJavaScript(
        "JSON.stringify(Array.from(document.querySelectorAll('.dropdown-item')).map(e => e.textContent))",
        step2_before_state,
    )


def step2_before_state(items_json):
    results["all_dropdown_items"] = json.loads(items_json) if items_json else None
    pv.runJavaScript(
        "(function(){const t=Array.from(document.querySelectorAll('.dropdown-item'))"
        ".find(e=>e.textContent.includes('Snap to Grid')); return t ? t.textContent : 'NOT_FOUND';})()",
        step3_click,
    )


def step3_click(before_text):
    results["snap_to_grid_before"] = before_text
    pv.runJavaScript(
        "(function(){const t=Array.from(document.querySelectorAll('.dropdown-item'))"
        ".find(e=>e.textContent.includes('Snap to Grid')); t.click(); return 'clicked';})()",
        lambda _: QTimer.singleShot(300, step4_after_state),
    )


def step4_after_state():
    pv.runJavaScript(
        "(function(){const t=Array.from(document.querySelectorAll('.dropdown-item'))"
        ".find(e=>e.textContent.includes('Snap to Grid')); return t.textContent;})()",
        step5_click_again,
    )


def step5_click_again(after_text):
    results["snap_to_grid_after_first_click"] = after_text
    pv.runJavaScript(
        "(function(){const t=Array.from(document.querySelectorAll('.dropdown-item'))"
        ".find(e=>e.textContent.includes('Snap to Grid')); t.click(); return 'clicked again';})()",
        lambda _: QTimer.singleShot(300, step6_after_second),
    )


def step6_after_second():
    pv.runJavaScript(
        "(function(){const t=Array.from(document.querySelectorAll('.dropdown-item'))"
        ".find(e=>e.textContent.includes('Snap to Grid')); return t.textContent;})()",
        step7_check_state_reachability,
    )


def step7_check_state_reachability(after2_text):
    results["snap_to_grid_after_second_click"] = after2_text
    # Question from "uściślenie 2.2": is undo/redo/dirty/clipboard state
    # (needed to correctly enable/disable a shared toolbar button)
    # reachable from outside the page at all?
    pv.runJavaScript(
        "JSON.stringify({useStore: typeof window.useStore, "
        "ProjectFileService: typeof window.ProjectFileService, "
        "pywebview: typeof window.pywebview})",
        finish,
    )


def finish(reachability_json):
    results["window_reachability"] = json.loads(reachability_json)
    with open(OUT_DIR / "menu_click_probe_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    app.quit()


panel.web_view().loadFinished.connect(lambda ok: QTimer.singleShot(800, step1_list_items))
QTimer.singleShot(15000, app.quit)
app.exec()
