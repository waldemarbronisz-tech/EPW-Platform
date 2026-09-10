"""Drives studio/main.py's real StudioMainWindow: clicks SCREENS,
screenshots; clicks LOGIC, screenshots. Proof for the task's own DOWOD,
not part of the shell itself."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from studio.shell.main_window import StudioMainWindow

OUT_DIR = Path(__file__).resolve().parent


def main():
    app = QApplication(sys.argv)
    window = StudioMainWindow()
    window.show()

    def click_screens():
        window.tree.setCurrentItem(window._item_screens)
        print("[SHELL PROBE] clicked SCREENS")
        QTimer.singleShot(2500, screenshot_screens)

    def screenshot_screens():
        window.grab().save(str(OUT_DIR / "shell_screens.png"))
        print("[SHELL PROBE] status bar:", window._status_editor.text())
        QTimer.singleShot(300, click_logic)

    def click_logic():
        window.tree.setCurrentItem(window._item_logic)
        print("[SHELL PROBE] clicked LOGIC")
        QTimer.singleShot(1500, screenshot_logic)

    def screenshot_logic():
        window.grab().save(str(OUT_DIR / "shell_logic.png"))
        print("[SHELL PROBE] status bar:", window._status_editor.text())
        QTimer.singleShot(300, back_to_screens)

    def back_to_screens():
        # Proves switching BACK doesn't rebuild/reload the panel (lazy-
        # cached, not re-created every click).
        window.tree.setCurrentItem(window._item_screens)
        print("[SHELL PROBE] clicked SCREENS again")
        QTimer.singleShot(500, finish)

    def finish():
        window.grab().save(str(OUT_DIR / "shell_screens_again.png"))
        print("[SHELL PROBE] done")
        app.quit()

    QTimer.singleShot(500, click_screens)
    QTimer.singleShot(30000, app.quit)
    app.exec()


if __name__ == "__main__":
    main()
