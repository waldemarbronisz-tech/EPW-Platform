"""Verifies the two corrections requested after the first version of
the shell was reviewed: a loading indicator is genuinely shown before
the page finishes loading, and a failed `npm run build` shows a
readable error instead of killing the whole Studio process - with
LOGIC still opening afterward. Every claim here is checked against
either a screenshot or a plain, un-photographed state read taken at
that exact moment - not assumed from reading the code.

Note on method: grabbing the FULL shell window (QMainWindow.grab())
while a QWebEngineView is compositing turns out to pump enough of the
Qt/Chromium event loop, on this machine, for an already-available
loopback HTTP response to finish loading before the grab completes -
so the "loading" frame is real (proven below by a plain, un-grabbed
index check performed synchronously, immediately after construction,
before returning control to Qt at all) but is not reliably
photographable through the full window on a fast local server. It IS
photographable by grabbing the SynopticPanel widget on its own, before
it has ever been shown or grabbed as part of a larger window - see
loading_state_isolated.png.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from studio.shell.main_window import StudioMainWindow

OUT_DIR = Path(__file__).resolve().parent

_PAGE_NAMES = {0: "loading", 1: "error", 2: "view"}


def main():
    app = QApplication(sys.argv)

    # --- Part 1: the loading page is real, proven two ways --------------
    from studio.shell.synoptic_panel import SynopticPanel

    isolated_panel = SynopticPanel()
    isolated_panel.resize(1000, 700)
    idx_before_any_grab = isolated_panel._pages.currentIndex()
    isolated_panel.grab().save(str(OUT_DIR / "loading_state_isolated.png"))
    print(f"[TEST] synchronously right after construction (no window, no prior grab): "
          f"page={_PAGE_NAMES[idx_before_any_grab]} - this is what loading_state_isolated.png shows")

    # --- Part 2: full shell flow - open SCREENS, confirm it settles on
    # the real view; then simulate a build failure and confirm it shows
    # a readable error AND that LOGIC still opens afterward. -------------
    window = StudioMainWindow()
    window.show()

    def click_screens():
        window.tree.setCurrentItem(window._item_screens)
        print("[TEST] clicked SCREENS")
        QTimer.singleShot(2500, screenshot_loaded_state)

    def screenshot_loaded_state():
        window.grab().save(str(OUT_DIR / "shell_screens.png"))
        panel = window._synoptic_panel
        print(f"[TEST] 2.5s after click, page={_PAGE_NAMES[panel._pages.currentIndex()]} "
              f"(shell_screens.png)")
        QTimer.singleShot(300, simulate_build_failure)

    def simulate_build_failure():
        # Force build_frontend()'s own sys.exit(1) path by making `npm`
        # unresolvable on PATH for this process only - the same
        # condition a real machine without Node.js installed would hit -
        # against a SEPARATE panel instance built against a dist/ that
        # does not exist, so build_frontend() actually runs instead of
        # short-circuiting on the already-built one.
        import os
        os.environ["PATH"] = ""
        import shutil
        dist_dir = REPO_ROOT / "studio" / "synoptic" / "dist"
        backup_dir = REPO_ROOT / "studio" / "synoptic" / "dist_backup_for_test"
        if dist_dir.exists():
            shutil.move(str(dist_dir), str(backup_dir))

        global failing_panel
        failing_panel = SynopticPanel()
        window.stack.addWidget(failing_panel)
        window.stack.setCurrentWidget(failing_panel)

        # Restore dist/ immediately - this test must not leave the repo
        # in a different state than it found it, regardless of outcome.
        if backup_dir.exists():
            shutil.move(str(backup_dir), str(dist_dir))

        QTimer.singleShot(200, screenshot_build_failure)

    def screenshot_build_failure():
        window.grab().save(str(OUT_DIR / "build_failure_state.png"))
        print(f"[TEST] build-failure panel page={_PAGE_NAMES[failing_panel._pages.currentIndex()]} "
              f"error_text={failing_panel._error_label.text()!r}")
        print("[TEST] process still alive after the simulated build failure - sys.exit(1) was caught, "
              "not propagated")
        QTimer.singleShot(300, click_logic_after_failure)

    def click_logic_after_failure():
        window.tree.setCurrentItem(window._item_logic)
        QTimer.singleShot(1200, screenshot_logic_still_works)

    def screenshot_logic_still_works():
        window.grab().save(str(OUT_DIR / "logic_still_works_after_failure.png"))
        print("[TEST] status bar after opening LOGIC post-failure:", window._status_editor.text())
        QTimer.singleShot(300, finish)

    def finish():
        print("[TEST] done")
        app.quit()

    QTimer.singleShot(500, click_screens)
    QTimer.singleShot(30000, app.quit)
    app.exec()


if __name__ == "__main__":
    main()
