"""Extra audit requested alongside Stage 2 ("EPW Studio: jedna szata
graficzna") - "sprawdz, czy ta sama klasa bledu [zalozenie 'jestem
samodzielna aplikacja'] nie dotyczy czegos jeszcze w powloce". This
probes one specific item on that list: Synoptic's MenuBar.tsx/
PropertyInspector.tsx/DeviceFormDialog.tsx etc. guard destructive
actions with plain browser confirm()/prompt() calls - fine in a real
browser tab, but QWebEngineView's default QWebEnginePage does NOT
implement javaScriptConfirm()/javaScriptAlert()/javaScriptPrompt() with
any visible UI at all (Qt's own docs: the base class's default just
does nothing) unless the embedding app overrides them - which
SynopticPanel does not.

Result (see this task's own chat report for the full audit): confirm()
returns immediately with no dialog shown AT ALL - not silently "yes",
not a native OS dialog, just nothing, and an empty/falsy result. Since
every call site here is written as `if (!confirm(...)) return;`, the
practical effect is the SAFE direction (the guarded action always acts
as if the user clicked Cancel) rather than a false "yes" - but it means
New/Open-with-unsaved-changes, Exit, delete-device/location/card, and
the two prompt()-based naming flows (new project name, custom property
key) are all silently non-functional today when Synoptic runs embedded
in Studio. Not fixed here (explicitly out of scope - this task's own
instruction was "list only, do not fix in this branch").
"""
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


def after_load():
    pv.runJavaScript("window.confirm('probe test message')", on_result)
    QTimer.singleShot(800, take_screenshot)


def take_screenshot():
    # Cited in the chat report: a plain, undisturbed canvas - no dialog,
    # no overlay, nothing - confirming confirm() showed the user
    # literally nothing rather than some native OS popup this screenshot
    # wouldn't have captured anyway.
    panel.grab().save(str(OUT_DIR / "js_confirm_probe.png"))
    print("screenshot taken")


def on_result(result):
    print("confirm() returned:", repr(result))


panel.web_view().loadFinished.connect(lambda ok: QTimer.singleShot(1000, after_load))
QTimer.singleShot(5000, app.quit)
app.exec()
