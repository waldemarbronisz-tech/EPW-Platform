"""EPW Studio's own shell window: a project tree on the left, the
active editor's own view on the right, a status bar at the bottom.

Task 2.2's own instruction is followed literally: the tree has exactly
the two branches that correspond to an editor that actually exists
today (SCREENS -> Synoptic Editor, LOGIC -> Logic Studio). No Cards/
Points/Devices/Alarms branches - the project format that would give
them something to show does not exist yet (still being designed), and
an empty branch is a facade, not a feature.

Task "EPW Studio: jedna szata graficzna" 2.1/2.2 added the one shared
QMenuBar (studio/shell/menus.py, rebuilt every time the tree selection
changes) and the fixed left toolbar zone (New/Open/Save/Undo/Redo - the
"variable right zone" from that task's 2.2 is simply whatever tool row
the ACTIVE embedded editor already draws itself, right under this one;
neither editor's ~20 drawing/simulation-specific tools are reimplemented
here, only the five actions both editors already have an equivalent of
are unified into one place - see STUDIO_UI_STANDARD.md and this task's
own Stage 2 report for why: rebuilding either editor's own tool row was
explicitly out of scope, same reasoning as Stage 1's overlay-not-rebuild
finding for Synoptic's skin).
"""
from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QMenuBar, QSplitter, QStyle, QStyledItemDelegate, QToolBar,
    QTreeWidget, QTreeWidgetItem, QStackedWidget, QLabel, QWidget, QVBoxLayout,
)

from studio.shell.i18n import tr
from studio.shell.menus import build_logic_menu, build_neutral_menu, build_synoptic_menu

_TREE_ITEM_SCREENS = "screens"
_TREE_ITEM_LOGIC = "logic"

# STUDIO_UI_STANDARD.md section 6 (tree): 24px rows, sourced from
# runtime/epw_os/gui/widgets/nav_tree.py's own ROW_HEIGHT - repeated
# here as a literal, not imported, since runtime/ is read-only for this
# task and studio/ is a separate deployable unit with no dependency on
# it (same reasoning as studio/shell/i18n.py's own module docstring).
_TREE_ROW_HEIGHT = 24


class _TreeRowHeightDelegate(QStyledItemDelegate):
    """Task 2.4 - "węższe/gęstsze [drzewo] z ikonami": the only way to
    force a QTreeWidget's row height below/above its natural
    font-metrics height is a delegate overriding sizeHint(), same
    technique runtime/epw_os/gui/widgets/nav_tree.py uses for its own
    24px rows (its version also custom-paints; this one only needs the
    height - two items, plain text-and-icon, don't need custom paint)."""

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(_TREE_ROW_HEIGHT)
        return size


class StudioMainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.setWindowTitle(tr("app.title"))
        self.resize(1400, 900)

        # Injectable so tests (and any headless/CI construction) don't
        # write splitter-width state into the real user registry - same
        # "settings=None defaults to the real QSettings" pattern
        # logic_studio.ui.main_window.MainWindow already uses (see
        # [[logic-studio-tests-must-inject-qsettings]]).
        self.settings = settings if settings is not None else QSettings("BroniszLabs", "EPW Studio")

        self._synoptic_panel = None
        self._logic_panel = None
        self._active = None  # None | _TREE_ITEM_SCREENS | _TREE_ITEM_LOGIC

        self._build_ui()
        self._restore_splitter_state()
        self._rebuild_menu()

        # Uściślenie 2.2's own requirement: the shared Save/Undo/Redo
        # buttons must reflect the ACTIVE editor's real state, not just
        # be permanently clickable. Neither editor exposes a Qt signal
        # for "dirty flag changed"/"undo stack changed" (Logic Studio's
        # is a plain bool + plain list; Synoptic's is read across the
        # JS bridge, inherently a poll, not a push) - so this polls both
        # uniformly on one short timer rather than inventing a push
        # mechanism for one side only.
        self._state_timer = QTimer(self)
        self._state_timer.setInterval(400)
        self._state_timer.timeout.connect(self._refresh_shared_toolbar_state)
        self._state_timer.start()

    def _build_ui(self):
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(12)
        self.tree.setItemDelegate(_TreeRowHeightDelegate(self.tree))

        style = self.style()
        icon_screens = style.standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)
        icon_logic = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)

        self._item_screens = QTreeWidgetItem([tr("tree.screens")])
        self._item_screens.setIcon(0, icon_screens)
        self._item_screens.setData(0, Qt.ItemDataRole.UserRole, _TREE_ITEM_SCREENS)
        self.tree.addTopLevelItem(self._item_screens)

        self._item_logic = QTreeWidgetItem([tr("tree.logic")])
        self._item_logic.setIcon(0, icon_logic)
        self._item_logic.setData(0, Qt.ItemDataRole.UserRole, _TREE_ITEM_LOGIC)
        self.tree.addTopLevelItem(self._item_logic)

        self.tree.currentItemChanged.connect(self._on_tree_selection_changed)

        self.stack = QStackedWidget()
        self._empty_placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self._empty_placeholder)
        placeholder_layout.addStretch(1)
        self.stack.addWidget(self._empty_placeholder)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.setCentralWidget(self.splitter)

        self._build_shared_toolbar()

        # Status bar (Task 2.5): project name (always "none" today - no
        # shared project format exists yet to open one from, GRANICE)
        # and which editor is active. Nothing else - no controller
        # connection indicator, that doesn't exist yet either.
        self._status_project = QLabel(tr("statusbar.no_project"))
        self._status_editor = QLabel(tr("statusbar.no_editor"))
        status_bar = self.statusBar()
        status_bar.addWidget(self._status_project)
        status_bar.addPermanentWidget(self._status_editor)

    def _build_shared_toolbar(self):
        """The fixed left zone of task 2.2's two-zone toolbar - New,
        Open, Save, Undo, Redo, always in the same place regardless of
        which editor is active. Each one's triggered handler dispatches
        to whichever editor is currently active's own mechanism (never
        a Studio-level implementation of its own - see
        _shared_new/_shared_save/etc. below); Save/Undo/Redo's enabled
        state is kept honest by _refresh_shared_toolbar_state(), polled
        on a timer (see __init__)."""
        style = self.style()
        tb = QToolBar(tr("app.title"), self)
        tb.setObjectName("SharedToolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        self.addToolBar(tb)

        def _make(text_key, icon: QIcon, handler):
            action = tb.addAction(icon, tr(text_key))
            action.triggered.connect(handler)
            return action

        self.act_shared_new = _make(
            "toolbar.new", style.standardIcon(QStyle.StandardPixmap.SP_FileIcon), self._shared_new
        )
        self.act_shared_open = _make(
            "toolbar.open", style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), self._shared_open
        )
        self.act_shared_save = _make(
            "toolbar.save", style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), self._shared_save
        )
        tb.addSeparator()
        self.act_shared_undo = _make(
            "toolbar.undo", style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack), self._shared_undo
        )
        self.act_shared_redo = _make(
            "toolbar.redo", style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward), self._shared_redo
        )
        self._set_shared_toolbar_enabled(False, False, False)

    def _set_shared_toolbar_enabled(self, can_save, can_undo, can_redo):
        has_editor = self._active is not None
        self.act_shared_new.setEnabled(has_editor)
        self.act_shared_open.setEnabled(has_editor)
        self.act_shared_save.setEnabled(has_editor and can_save)
        self.act_shared_undo.setEnabled(has_editor and can_undo)
        self.act_shared_redo.setEnabled(has_editor and can_redo)

    def _shared_new(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_new.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("New", exact=True)

    def _shared_open(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_open.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Open")

    def _shared_save(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_save.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Save", exact=True)

    def _shared_undo(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_undo.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Undo")

    def _shared_redo(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_redo.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Redo")

    def _refresh_shared_toolbar_state(self):
        if self._active == _TREE_ITEM_LOGIC and self._logic_panel is not None:
            mw = self._logic_panel.main_window()
            self._set_shared_toolbar_enabled(
                mw.is_dirty, len(mw.project.undo_stack) > 0, len(mw.project.redo_stack) > 0
            )
        elif self._active == _TREE_ITEM_SCREENS and self._synoptic_panel is not None:
            self._synoptic_panel.query_state(self._apply_synoptic_toolbar_state)
        else:
            self._set_shared_toolbar_enabled(False, False, False)

    def _apply_synoptic_toolbar_state(self, state):
        # Guards against a reply arriving after the user has already
        # switched away from Screens (runJavaScript's callback is async -
        # see synoptic_panel.py's query_state()) and against an old,
        # un-rebuilt dist/ that doesn't expose the bridge at all (state
        # is None then) - treated as "unknown", i.e. disabled, never as
        # a silent "everything's fine".
        if self._active != _TREE_ITEM_SCREENS:
            return
        if state is None:
            self._set_shared_toolbar_enabled(False, False, False)
            return
        self._set_shared_toolbar_enabled(
            bool(state.get("isDirty")), bool(state.get("canUndo")), bool(state.get("canRedo"))
        )

    def _rebuild_menu(self):
        """Task 2.1 - one shared menu, content varies by context. Both
        editors' own menu bars are already hidden for good (see
        logic_panel.py / synoptic_panel.py) - this is the only menu bar
        Studio ever shows.

        A brand new QMenuBar every time, via setMenuBar() - not
        menuBar().clear() - on purpose: every QAction menus.py builds is
        parented to the QMenu it lives in (see that module's own
        docstring), so replacing the whole bar is what actually lets Qt
        delete the previous context's menus/actions (and, with them,
        their `source_action.changed` connections) instead of merely
        hiding them while they pile up across repeated tree clicks."""
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        if self._active == _TREE_ITEM_LOGIC and self._logic_panel is not None:
            build_logic_menu(menubar, self._logic_panel, self)
        elif self._active == _TREE_ITEM_SCREENS and self._synoptic_panel is not None:
            build_synoptic_menu(menubar, self._synoptic_panel, self)
        else:
            build_neutral_menu(menubar, self)

    def _on_tree_selection_changed(self, current, _previous):
        if current is None:
            return
        which = current.data(0, Qt.ItemDataRole.UserRole)
        if which == _TREE_ITEM_SCREENS:
            self._open_screens()
        elif which == _TREE_ITEM_LOGIC:
            self._open_logic()

    def _open_screens(self):
        if self._synoptic_panel is None:
            from studio.shell.synoptic_panel import SynopticPanel
            self._synoptic_panel = SynopticPanel()
            self.stack.addWidget(self._synoptic_panel)
        self.stack.setCurrentWidget(self._synoptic_panel)
        self._status_editor.setText(tr("statusbar.active_editor", name=tr("editor.synoptic_name")))
        self._active = _TREE_ITEM_SCREENS
        self._rebuild_menu()
        self._refresh_shared_toolbar_state()

    def _open_logic(self):
        if self._logic_panel is None:
            from studio.shell.logic_panel import LogicPanel
            self._logic_panel = LogicPanel()
            self.stack.addWidget(self._logic_panel)
        self.stack.setCurrentWidget(self._logic_panel)
        self._status_editor.setText(tr("statusbar.active_editor", name=tr("editor.logic_name")))
        self._active = _TREE_ITEM_LOGIC
        self._rebuild_menu()
        self._refresh_shared_toolbar_state()

    def _restore_splitter_state(self):
        state = self.settings.value("shell/splitter_state")
        if state is not None:
            self.splitter.restoreState(state)
        else:
            # Task 2.4 - "węższe [drzewo]": two short items, no reason
            # for today's ~250px default. Still a real QSplitter handle,
            # not a fixed width - the user can still drag it wider.
            self.splitter.setSizes([170, 1230])

    def closeEvent(self, event):
        self.settings.setValue("shell/splitter_state", self.splitter.saveState())
        super().closeEvent(event)
