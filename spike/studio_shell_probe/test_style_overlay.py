"""Stage 1 reconnaissance (EPW Studio UI standard task), question 1.3:
can Synoptic's chrome be retinted to the Win98 standard by an
overlay (CSS custom properties set from Python), without touching
studio/synoptic/src/? Checked empirically - three screenshots, each
opened and visually confirmed before being cited anywhere.

Also confirms question 1.2's "is the menu hideable without breaking
the rest of the layout" - the same run hides .menu-bar via injected
CSS afterward and screenshots the result.

style_before_overlay.png   - Synoptic's own current theme, unmodified.
style_after_overlay.png    - after setting the CSS variables this
                              task's STUDIO_UI_STANDARD.md section 9
                              calls for (Win98 panel/bevel/outline/
                              highlight colors) - note the Object
                              Library/Properties/Messages panel HEADERS
                              turn navy (#000080), the one dramatic,
                              easy-to-verify-by-eye change confirming
                              live re-cascade with no reload.
style_menu_hidden.png      - .menu-bar set to display:none on top of
                              the retinted page - the toolbar/tree/
                              canvas/panels reflow to fill the space
                              cleanly, no gap, no broken layout.
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
panel.resize(1500, 1000)
panel.show()
pv = panel.web_view().page()

# The chrome-only variable set from STUDIO_UI_STANDARD.md section 9 -
# domain colors (--scada-energized/--scada-water/--scada-alarm/etc.)
# are deliberately never touched here, matching that document exactly.
OVERLAY_JS = """
(function(){
    const root = document.documentElement;
    root.style.setProperty('--scada-panel', '#D4D0C8');
    root.style.setProperty('--scada-bevel-light', '#FFFFFF');
    root.style.setProperty('--scada-bevel-dark', '#808080');
    root.style.setProperty('--scada-outline', '#000000');
    root.style.setProperty('--scada-value-field', '#FFFFFF');
    root.style.setProperty('--scada-font-ui', 'Tahoma, "MS Sans Serif", sans-serif');
    root.style.setProperty('--scada-font-size-small', '11px');
    // --sys-highlight has no --scada-* source (index.css aliases it to
    // --scada-outline = black today) - this is the one correction, not
    // just a retint, the standard makes to Synoptic's current look.
    root.style.setProperty('--sys-highlight', '#000080');
    root.style.setProperty('--sys-highlight-text', '#FFFFFF');
    return 'overlay applied';
})();
"""


def after_load():
    panel.grab().save(str(OUT_DIR / "style_before_overlay.png"))
    pv.runJavaScript(OVERLAY_JS, after_overlay)


def after_overlay(result):
    print("overlay result:", result)
    QTimer.singleShot(300, screenshot_after)


def screenshot_after():
    panel.grab().save(str(OUT_DIR / "style_after_overlay.png"))
    hide_js = "document.querySelector('.menu-bar').style.display = 'none'; 'hidden';"
    pv.runJavaScript(hide_js, after_hide)


def after_hide(result):
    print("hide result:", result)
    QTimer.singleShot(300, screenshot_hidden)


def screenshot_hidden():
    panel.grab().save(str(OUT_DIR / "style_menu_hidden.png"))
    app.quit()


panel.web_view().loadFinished.connect(lambda ok: QTimer.singleShot(600, after_load))
QTimer.singleShot(15000, app.quit)
app.exec()
