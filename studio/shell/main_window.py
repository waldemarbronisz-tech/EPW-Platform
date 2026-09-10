"""EPW Studio's own shell window: a project tree on the left, the
active editor's own view on the right, a status bar at the bottom.

Task 2.2's own instruction is followed literally: the tree has exactly
the two branches that correspond to an editor that actually exists
today (SCREENS -> Synoptic Editor, LOGIC -> Logic Studio). No Cards/
Points/Devices/Alarms branches - the project format that would give
them something to show does not exist yet (still being designed), and
an empty branch is a facade, not a feature.
"""
from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QTreeWidget, QTreeWidgetItem, QStackedWidget,
    QLabel, QWidget, QVBoxLayout,
)

from studio.shell.i18n import tr

_TREE_ITEM_SCREENS = "screens"
_TREE_ITEM_LOGIC = "logic"


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

        self._build_ui()
        self._restore_splitter_state()

    def _build_ui(self):
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)

        self._item_screens = QTreeWidgetItem([tr("tree.screens")])
        self._item_screens.setData(0, Qt.ItemDataRole.UserRole, _TREE_ITEM_SCREENS)
        self.tree.addTopLevelItem(self._item_screens)

        self._item_logic = QTreeWidgetItem([tr("tree.logic")])
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

        # Status bar (Task 2.5): project name (always "none" today - no
        # shared project format exists yet to open one from, GRANICE)
        # and which editor is active. Nothing else - no controller
        # connection indicator, that doesn't exist yet either.
        self._status_project = QLabel(tr("statusbar.no_project"))
        self._status_editor = QLabel(tr("statusbar.no_editor"))
        status_bar = self.statusBar()
        status_bar.addWidget(self._status_project)
        status_bar.addPermanentWidget(self._status_editor)

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

    def _open_logic(self):
        if self._logic_panel is None:
            from studio.shell.logic_panel import LogicPanel
            self._logic_panel = LogicPanel()
            self.stack.addWidget(self._logic_panel)
        self.stack.setCurrentWidget(self._logic_panel)
        self._status_editor.setText(tr("statusbar.active_editor", name=tr("editor.logic_name")))

    def _restore_splitter_state(self):
        state = self.settings.value("shell/splitter_state")
        if state is not None:
            self.splitter.restoreState(state)
        else:
            self.splitter.setSizes([220, 1180])

    def closeEvent(self, event):
        self.settings.setValue("shell/splitter_state", self.splitter.saveState())
        super().closeEvent(event)
