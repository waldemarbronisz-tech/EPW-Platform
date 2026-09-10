"""EPW Studio's own shell window.

Task "EPW Studio: przebudowa nawigacji wg wzorca e²TANGO" - the
diagnosis this task starts from: the old shell treated EKRANY/LOGIKA
as two application MODES (a whole menu bar rebuilt on every click), so
it looked like two programs stitched together because structurally it
was. This rebuild follows e²TANGO-Studio's own four-part pattern:

  1. The APP menu (Plik/Widok/Ustawienia/Pomoc) is built exactly ONCE,
     here in __init__ (build_fixed_menu()) - it never changes shape
     again. Only individual items' enabled state moves, the same way
     Cofnij/Ponów already did in the previous stage.
  2. The top toolbar (Nowy/Otwórz/Zapisz/Zapisz jako/Cofnij/Ponów/
     Pomoc) is equally fixed - project-level operations, routed to
     whichever aspect is active via the SAME dispatch methods as
     before (_shared_new/_shared_save/etc.) - that routing mechanism
     is unchanged, per this task's own GRANICE.
  3. Each aspect's own tools live in a CONTEXTUAL toolbar INSIDE the
     document area (_AspectContainer, below), under a breadcrumb
     header - a separate visual zone (own panel_bg background + raised
     border, STUDIO_UI_STANDARD.md) from the fixed top chrome, not a
     second half of the same bar.
  4. The tree is navigation by PROJECT STRUCTURE (shared/docs/
     SPEC_FORMAT_EPW.md's own section names), not by which program
     happens to implement which part - EKRANY/LOGIKA become two leaves
     among many, most still unbuilt and shown, honestly, as such.
"""
from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QMenuBar, QMessageBox, QSplitter, QStyle, QStyledItemDelegate,
    QToolBar, QTreeWidget, QTreeWidgetItem, QStackedWidget, QLabel, QWidget,
    QVBoxLayout,
)

from studio.shell.i18n import get_language, set_language, tr
from studio.shell.menus import build_fixed_menu, build_logic_context_toolbar, build_synoptic_context_toolbar

_TREE_ITEM_SCREENS = "screens"
_TREE_ITEM_LOGIC = "logic"

# The 10 project-structure branches shared/docs/SPEC_FORMAT_EPW.md
# describes but nothing in this platform builds yet (task 1.4) - each
# tuple is (key, tree label tr() key). GRANICE for this task: build
# NONE of these as real panels - a click shows one explanatory sentence
# (placeholder.<key> in locales/*.json), never an empty or fake form.
_INACTIVE_INFO = ("info", "tree.info")
_INACTIVE_CONFIG_CHILDREN = [
    ("devices", "tree.devices"),
    ("io_cards", "tree.io_cards"),
    ("locations", "tree.locations"),
    ("point_registry", "tree.point_registry"),
    ("apparatus_registry", "tree.apparatus_registry"),
]
_INACTIVE_ALARM_CHILDREN = [
    ("security_zones", "tree.security_zones"),
    ("security_lines", "tree.security_lines"),
]
_INACTIVE_PROTECTION_CHILDREN = [("protection_settings", "tree.protection_settings")]
_INACTIVE_CONTROLLER_CHILDREN = [("controller_connection", "tree.controller_connection")]

_BREADCRUMB_KEYS = {
    _TREE_ITEM_SCREENS: "breadcrumb.screens",
    _TREE_ITEM_LOGIC: "breadcrumb.logic",
}

# STUDIO_UI_STANDARD.md section 1/3: panel_bg + a raised 2px bevel
# (light top/left, shadow bottom/right) - the one visual device that
# actually separates the contextual zone from the fixed top chrome
# (task 1.3's own point: today both sit on the same background and
# read as one bar split in two; a real background+border boundary is
# what a label alone cannot fix).
_DOCUMENT_HEADER_QSS = """
QLabel#DocumentHeader {
    background: #D4D0C8;
    color: #000000;
    border-style: outset;
    border-width: 2px;
    border-color: #FFFFFF #808080 #808080 #FFFFFF;
    padding: 4px 6px;
    font-weight: bold;
}
"""
_CONTEXT_TOOLBAR_QSS = """
QToolBar#ContextToolbar {
    background: #D4D0C8;
    border-style: outset;
    border-width: 2px;
    border-color: #FFFFFF #808080 #808080 #FFFFFF;
    spacing: 2px;
    padding: 2px;
}
"""
_PLACEHOLDER_MESSAGE_QSS = "color: #808080; font-style: italic; padding: 24px;"

# STUDIO_UI_STANDARD.md section 6: 24px tree rows, sourced from
# runtime/epw_os/gui/widgets/nav_tree.py's own ROW_HEIGHT - repeated
# here as a literal (studio/ has no dependency on runtime/, GRANICE).
_TREE_ROW_HEIGHT = 24


class _TreeRowHeightDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(_TREE_ROW_HEIGHT)
        return size


class _AspectContainer(QWidget):
    """Task 1.3/1.5: a breadcrumb header over a contextual toolbar,
    over the aspect's own real editor widget - the whole reason the
    old shell "looked like a zlepek dwóch programów" was that these
    lived at the top, beside the app-level chrome; here they are a
    visually distinct zone INSIDE the document area instead."""

    def __init__(self, breadcrumb_text, editor_widget, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QLabel(breadcrumb_text)
        self.header.setObjectName("DocumentHeader")
        self.header.setStyleSheet(_DOCUMENT_HEADER_QSS)
        layout.addWidget(self.header)

        self.context_toolbar = QToolBar()
        self.context_toolbar.setObjectName("ContextToolbar")
        self.context_toolbar.setMovable(False)
        self.context_toolbar.setStyleSheet(_CONTEXT_TOOLBAR_QSS)
        layout.addWidget(self.context_toolbar)

        layout.addWidget(editor_widget, 1)


class _InactivePlaceholder(QWidget):
    """Task 1.4's own boundary between a table of contents and a
    facade: a real header (so "gdzie jestem" still holds, task 1.5),
    one plain explanatory sentence, and NOTHING ELSE - no empty panel,
    no disabled form, no control that looks live but isn't. One
    instance, reused and re-filled for every inactive branch clicked."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QLabel()
        self.header.setObjectName("DocumentHeader")
        self.header.setStyleSheet(_DOCUMENT_HEADER_QSS)
        layout.addWidget(self.header)

        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setStyleSheet(_PLACEHOLDER_MESSAGE_QSS)
        layout.addStretch(1)
        layout.addWidget(self.message)
        layout.addStretch(2)

    def set_content(self, breadcrumb_text, message_text):
        self.header.setText(breadcrumb_text)
        self.message.setText(message_text)


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
        self._aspect_containers = {}  # key -> _AspectContainer, rebuilt on every visit
        self._tree_label_refs = []  # [(QTreeWidgetItem, tr key), ...] for language switches

        self._build_ui()
        self._restore_splitter_state()

        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        build_fixed_menu(menubar, self)
        self._refresh_fixed_menu_state()

        # Uściślenie 2.2's own requirement, unchanged from the previous
        # stage: the shared Save/Undo/Redo buttons must reflect the
        # ACTIVE aspect's real state, not just be permanently
        # clickable. Neither aspect exposes a push signal for this
        # (Logic Studio's is a plain bool + plain list; Synoptic's is
        # read across the JS bridge, inherently a poll) - polled
        # uniformly on one short timer.
        self._state_timer = QTimer(self)
        self._state_timer.setInterval(400)
        self._state_timer.timeout.connect(self._refresh_shared_toolbar_state)
        self._state_timer.start()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.tree = self._build_tree()

        self.stack = QStackedWidget()
        self._empty_placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self._empty_placeholder)
        placeholder_layout.addStretch(1)
        self.stack.addWidget(self._empty_placeholder)

        self._inactive_placeholder = _InactivePlaceholder()
        self.stack.addWidget(self._inactive_placeholder)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.setCentralWidget(self.splitter)

        self._build_shared_toolbar()

        # Status bar (Task 1.5's counterpart at the bottom): project
        # name (always "none" today - no shared project format exists
        # yet to open one from, GRANICE) and which aspect is active.
        self._status_project = QLabel(tr("statusbar.no_project"))
        self._status_editor = QLabel(tr("statusbar.no_editor"))
        status_bar = self.statusBar()
        status_bar.addWidget(self._status_project)
        status_bar.addPermanentWidget(self._status_editor)

    def _build_tree(self):
        """Task 1.4 - the WHOLE project structure, not just what's
        implemented. shared/docs/SPEC_FORMAT_EPW.md's own section names
        (project/, io/, screens/, logic/, security/, protection/)
        supply every branch label - the tree mirrors the project FILE
        FORMAT's structure, not a list of programs."""
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setIndentation(12)
        tree.setItemDelegate(_TreeRowHeightDelegate(tree))

        style = self.style()
        icon_screens = style.standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)
        icon_logic = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        icon_inactive = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)

        def add_group(parent_item, label_key):
            item = QTreeWidgetItem([tr(label_key)])
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            f = item.font(0)
            f.setBold(True)
            item.setFont(0, f)
            parent_item.addChild(item)
            self._tree_label_refs.append((item, label_key))
            return item

        def add_inactive_leaf(parent_item, key, label_key):
            item = QTreeWidgetItem([tr(label_key)])
            item.setData(0, Qt.ItemDataRole.UserRole, ("inactive", key))
            item.setIcon(0, icon_inactive)
            item.setForeground(0, QColor("#808080"))
            f = item.font(0)
            f.setItalic(True)
            item.setFont(0, f)
            parent_item.addChild(item)
            self._tree_label_refs.append((item, label_key))

        root = QTreeWidgetItem([tr("tree.root")])
        root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        f = root.font(0)
        f.setBold(True)
        root.setFont(0, f)
        tree.addTopLevelItem(root)
        self._tree_label_refs.append((root, "tree.root"))

        add_inactive_leaf(root, *_INACTIVE_INFO)

        config = add_group(root, "tree.group_config")
        for key, label_key in _INACTIVE_CONFIG_CHILDREN:
            add_inactive_leaf(config, key, label_key)

        self._item_screens = QTreeWidgetItem([tr("tree.screens")])
        self._item_screens.setIcon(0, icon_screens)
        self._item_screens.setData(0, Qt.ItemDataRole.UserRole, ("active", _TREE_ITEM_SCREENS))
        config.addChild(self._item_screens)
        self._tree_label_refs.append((self._item_screens, "tree.screens"))

        self._item_logic = QTreeWidgetItem([tr("tree.logic")])
        self._item_logic.setIcon(0, icon_logic)
        self._item_logic.setData(0, Qt.ItemDataRole.UserRole, ("active", _TREE_ITEM_LOGIC))
        config.addChild(self._item_logic)
        self._tree_label_refs.append((self._item_logic, "tree.logic"))

        alarm = add_group(root, "tree.group_alarm")
        for key, label_key in _INACTIVE_ALARM_CHILDREN:
            add_inactive_leaf(alarm, key, label_key)

        protection = add_group(root, "tree.group_protection")
        for key, label_key in _INACTIVE_PROTECTION_CHILDREN:
            add_inactive_leaf(protection, key, label_key)

        controller = add_group(root, "tree.group_controller")
        for key, label_key in _INACTIVE_CONTROLLER_CHILDREN:
            add_inactive_leaf(controller, key, label_key)

        tree.expandAll()
        tree.currentItemChanged.connect(self._on_tree_selection_changed)
        return tree

    def _build_shared_toolbar(self):
        """Task 1.2 - the fixed top toolbar: Nowy/Otwórz/Zapisz/Zapisz
        jako/Cofnij/Ponów/Pomoc, always the same regardless of the
        active aspect. Each handler dispatches to whichever aspect is
        currently active's own mechanism (never a Studio-level
        implementation of its own); Save/Undo/Redo's enabled state is
        kept honest by _refresh_shared_toolbar_state() (unchanged from
        the previous stage - GRANICE: "nie ruszaj mostu stanu")."""
        style = self.style()
        tb = QToolBar(tr("app.title"), self)
        tb.setObjectName("SharedToolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        self.addToolBar(tb)
        self._shared_toolbar = tb

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
        self.act_shared_save_as = _make(
            "toolbar.save_as", style.standardIcon(QStyle.StandardPixmap.SP_DriveFDIcon), self._shared_save_as
        )
        tb.addSeparator()
        self.act_shared_undo = _make(
            "toolbar.undo", style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack), self._shared_undo
        )
        self.act_shared_redo = _make(
            "toolbar.redo", style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward), self._shared_redo
        )
        tb.addSeparator()
        self.act_shared_help = _make(
            "toolbar.help", style.standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton), self._help_topics
        )
        self._set_shared_toolbar_enabled(False, False, False)

    # ------------------------------------------------------------------
    # Shared (fixed) toolbar - state
    # ------------------------------------------------------------------

    def _set_shared_toolbar_enabled(self, can_save, can_undo, can_redo):
        has_editor = self._active is not None
        self.act_shared_new.setEnabled(has_editor)
        self.act_shared_open.setEnabled(has_editor)
        self.act_shared_save.setEnabled(has_editor and can_save)
        self.act_shared_save_as.setEnabled(has_editor)
        self.act_shared_undo.setEnabled(has_editor and can_undo)
        self.act_shared_redo.setEnabled(has_editor and can_redo)
        self.act_shared_help.setEnabled(has_editor)

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

    def _shared_save_as(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_save_as.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Save As")

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
        # switched away from Screens (runJavaScript's callback is
        # async) and against an old, un-rebuilt dist/ that doesn't
        # expose the bridge at all (state is None then) - treated as
        # "unknown", i.e. disabled, never as a silent "everything's
        # fine".
        if self._active != _TREE_ITEM_SCREENS:
            return
        if state is None:
            self._set_shared_toolbar_enabled(False, False, False)
            return
        self._set_shared_toolbar_enabled(
            bool(state.get("isDirty")), bool(state.get("canUndo")), bool(state.get("canRedo"))
        )

    # ------------------------------------------------------------------
    # Fixed menu - state and routed actions (Widok/Pomoc)
    # ------------------------------------------------------------------

    def _refresh_fixed_menu_state(self):
        is_logic = self._active == _TREE_ITEM_LOGIC
        is_any = self._active in (_TREE_ITEM_LOGIC, _TREE_ITEM_SCREENS)
        self.act_menu_new.setEnabled(is_any)
        self.act_menu_open.setEnabled(is_any)
        self.act_menu_save.setEnabled(is_any)
        self.act_menu_save_as.setEnabled(is_any)
        # Zoom/Grid have no Synoptic menu equivalent (Stage 1
        # reconnaissance - Synoptic's own View menu only ever had Snap
        # to Grid/SCADA Preview) - honestly disabled rather than wired
        # to nothing, not a facade with a false "supported" look.
        self.act_view_zoom_in.setEnabled(is_logic)
        self.act_view_zoom_out.setEnabled(is_logic)
        self.act_view_reset_zoom.setEnabled(is_logic)
        self.act_view_grid.setEnabled(is_logic)
        self.act_view_snap.setEnabled(is_any)
        self.act_menu_help_topics.setEnabled(is_any)

    def _view_zoom_in(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_zoom_in.trigger()

    def _view_zoom_out(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_zoom_out.trigger()

    def _view_reset_zoom(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_reset_zoom.trigger()

    def _view_toggle_grid(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_grid.trigger()

    def _view_toggle_snap(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_snap.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Snap to Grid")

    def _help_topics(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_help.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Help Topics")

    def _show_about_studio(self):
        QMessageBox.about(self, tr("menu.help.about_studio"), tr("about.studio_text"))

    def _set_language(self, code):
        set_language(code)
        self._retranslate()

    def _retranslate(self):
        self.setWindowTitle(tr("app.title"))
        for item, key in self._tree_label_refs:
            item.setText(0, tr(key))

        old_toolbar = self._shared_toolbar
        self.removeToolBar(old_toolbar)
        old_toolbar.deleteLater()
        self._build_shared_toolbar()

        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        build_fixed_menu(menubar, self)

        self._status_project.setText(tr("statusbar.no_project"))
        current_item = self.tree.currentItem()
        if current_item is None:
            self._status_editor.setText(tr("statusbar.no_editor"))
            self._refresh_fixed_menu_state()
            self._refresh_shared_toolbar_state()
        else:
            # Re-runs whichever _open_*/_open_inactive the current
            # selection maps to - rebuilds that aspect's breadcrumb +
            # contextual toolbar in the new language too, and refreshes
            # both chrome states as a side effect.
            self._on_tree_selection_changed(current_item, None)

    # ------------------------------------------------------------------
    # Tree navigation
    # ------------------------------------------------------------------

    def _on_tree_selection_changed(self, current, _previous):
        if current is None:
            return
        data = current.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return  # PROJEKT root / a group header - not selectable, defensive no-op
        kind, key = data
        if kind == "active":
            if key == _TREE_ITEM_SCREENS:
                self._open_screens()
            elif key == _TREE_ITEM_LOGIC:
                self._open_logic()
        elif kind == "inactive":
            self._open_inactive(key)

    def _open_screens(self):
        if self._synoptic_panel is None:
            from studio.shell.synoptic_panel import SynopticPanel
            self._synoptic_panel = SynopticPanel()
        self._show_aspect_container(
            _TREE_ITEM_SCREENS, self._synoptic_panel, build_synoptic_context_toolbar, self._synoptic_panel
        )
        self._status_editor.setText(tr("statusbar.active_editor", name=tr("editor.synoptic_name")))
        self._active = _TREE_ITEM_SCREENS
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_logic(self):
        if self._logic_panel is None:
            from studio.shell.logic_panel import LogicPanel
            self._logic_panel = LogicPanel()
        self._show_aspect_container(
            _TREE_ITEM_LOGIC, self._logic_panel, build_logic_context_toolbar, self._logic_panel
        )
        self._status_editor.setText(tr("statusbar.active_editor", name=tr("editor.logic_name")))
        self._active = _TREE_ITEM_LOGIC
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _show_aspect_container(self, key, editor_widget, toolbar_builder, panel_for_builder):
        """Wraps `editor_widget` in a fresh _AspectContainer (breadcrumb
        + contextual toolbar) and swaps it into the stack. Fresh every
        time, same reasoning as menus.py's own docstring for the old
        per-context QMenuBar: every QAction toolbar_builder creates is
        parented to the toolbar it lives in, so replacing the whole
        container is what lets Qt actually delete the previous one's
        actions/connections instead of piling them up across repeated
        tree clicks. `editor_widget` itself is NOT rebuilt - reparenting
        an existing widget into a new layout is a normal, cheap Qt
        operation, unlike reconstructing SynopticPanel/LogicPanel."""
        old = self._aspect_containers.get(key)
        container = _AspectContainer(tr(_BREADCRUMB_KEYS[key]), editor_widget)
        toolbar_builder(container.context_toolbar, panel_for_builder, self)
        self.stack.addWidget(container)
        self.stack.setCurrentWidget(container)
        self._aspect_containers[key] = container
        if old is not None and old is not container:
            self.stack.removeWidget(old)
            old.deleteLater()

    def _open_inactive(self, key):
        self._inactive_placeholder.set_content(tr(_placeholder_breadcrumb_key(key)), tr(f"placeholder.{key}"))
        self.stack.setCurrentWidget(self._inactive_placeholder)
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = None
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    # ------------------------------------------------------------------

    def _restore_splitter_state(self):
        state = self.settings.value("shell/splitter_state")
        if state is not None:
            self.splitter.restoreState(state)
        else:
            # Task 1.4's fuller tree (nested groups) needs a bit more
            # room than the old two-flat-item tree's 170px default.
            self.splitter.setSizes([230, 1170])

    def closeEvent(self, event):
        self.settings.setValue("shell/splitter_state", self.splitter.saveState())
        super().closeEvent(event)


def _placeholder_breadcrumb_key(key):
    return f"breadcrumb.{key}"
