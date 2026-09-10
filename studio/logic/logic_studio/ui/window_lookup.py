"""logic_main_window(widget) - the ONE explicit replacement for every
`<some_widget>.window()` call this codebase used to make to find its
owning logic_studio.ui.main_window.MainWindow.

Why this exists (Task "EPW Studio: jedna szata graficzna", Stage 2):
Qt's own QWidget.window() returns the nearest ancestor for which
isWindow() is true - normally MainWindow itself, since a real top-level
window always answers isWindow() with True. But studio/shell/logic_panel.py
embeds MainWindow as a plain CHILD widget inside EPW Studio's own
QStackedWidget (via layout.addWidget(main_window) - the same technique
this whole file's docstring history shows Logic Studio embedding its own
child widgets with everywhere else), and a widget with a real parent is,
by Qt's own definition, no longer a window (isWindow() becomes False).
window() then keeps climbing PAST MainWindow to whatever real top-level
window happens to contain it - EPW Studio's own StudioMainWindow, which
has no `.project`, no `.engine`, no `.scene`/`.view`, no `.set_dirty()` -
so every one of the 32 real call sites this replaced (verified by an
exhaustive, unfiltered `grep -rn ".window()" studio/logic/logic_studio/`
- see this task's own Stage 2 report for the full list) either silently
did nothing (getattr(..., None) / hasattr() guards swallowing the miss)
or, in a few places, misdirected a status-bar message into Studio's own
status bar instead of Logic Studio's.

Deliberately NOT fixed by overriding QWidget.window() anywhere (the
user's own explicit decision on this task, and the right one - Qt uses
window() internally for dialog parenting/modality/tooltip placement;
making it lie about what is and isn't a real top-level window is a
correctness trap for code nobody would think to connect to this change).
This is a plain, explicit helper instead: it walks `widget.parentWidget()`
by hand - never touching Qt's own notion of "window" - looking for the
nearest ancestor that IS a real logic_studio MainWindow. In standalone
use (python studio/logic/main.py) this finds exactly the same object
window() already did, since MainWindow's own top-level instance is also
the nearest such ancestor - behavior there is unchanged.
"""


def logic_main_window(widget):
    """Returns the nearest logic_studio.ui.main_window.MainWindow
    ancestor of `widget` (a QWidget - callers reaching this from a
    QGraphicsItem pass their view, e.g. self.scene().views()[0], exactly
    as they passed it to .window() before), or None if there isn't one
    yet (mid-construction, or a widget/test that was never added under a
    real MainWindow - the same cases every one of the old `.window()`
    call sites already had to guard against with getattr/hasattr)."""
    from logic_studio.ui.main_window import MainWindow

    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, MainWindow):
            return parent
        parent = parent.parentWidget()
    return None
