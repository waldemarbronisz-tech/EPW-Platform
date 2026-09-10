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
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QMainWindow, QMenuBar, QMessageBox, QSplitter, QStyle, QStyledItemDelegate,
    QToolBar, QTreeWidget, QTreeWidgetItem, QStackedWidget, QLabel, QWidget,
    QVBoxLayout,
)

from studio.shell import icons
from studio.shell.i18n import get_language, set_language, tr
from studio.shell.menus import (
    build_cards_toolbar, build_devices_toolbar, build_electrical_protection_toolbar,
    build_fixed_menu, build_lines_toolbar, build_locations_toolbar, build_logic_context_toolbar,
    build_point_registry_toolbar, build_process_protection_toolbar, build_project_info_toolbar,
    build_synoptic_context_toolbar, build_zones_toolbar,
)
from studio.shell.project_format import ProjectFormatError, load_project, new_project, save_project
from studio.shell.style import STUDIO_CHROME_QSS

_TREE_ITEM_SCREENS = "screens"
_TREE_ITEM_LOGIC = "logic"
# Task "edytor DI/DO/AI" - SPEC_PROJEKT_EPW.md's own "Kolejność
# wdrożenia" step 2 ("Rejestr punktów w Studio — karty rodzą punkty,
# opisy"), built on step 1 (project_format.py). Promoted out of
# _INACTIVE_CONFIG_CHILDREN below, same "active" leaf pattern as
# Screens/Logic above - real panels, not another placeholder sentence.
_TREE_ITEM_INFO = "info"
# Task "ostatnie dwa działy" - "io_cards" now surfaces under the
# "devices"/"Skład urządzenia" label (see _BREADCRUMB_KEYS below): the
# user's own description of what belongs there - "ustawianie adresów
# ELA/ADA, opisywanie ich, określanie wejść/wyjść" - IS CardsPanel's own
# id/model/kind/channels, not a second, separate registry. The internal
# key stays "io_cards" (no behavior tied to the string itself), only the
# LABEL changes - this decision is flagged, not silently made: SPEC's
# OWN "Skład urządzenia" meaning ("modules: lista nazw modułów... NIE
# JEST lista przełączników") is a different, narrower concept (which
# functional subsystems this controller has) that this does NOT build -
# still open, unrelated to the ELA/ADA registry now living at this leaf.
_TREE_ITEM_IO_CARDS = "io_cards"
_TREE_ITEM_LOCATIONS = "locations"
_TREE_ITEM_POINT_REGISTRY = "point_registry"
# "Co jeszcze możemy dorobić" follow-up - SPEC's next section, Aparaty
# (a device's feedback/command point lists), same "active" leaf pattern.
_TREE_ITEM_DEVICES = "apparatus_registry"

# Every branch that used to live under KONFIGURACJA as a placeholder
# (task 1.4's own "a click shows one explanatory sentence" GRANICE) is
# now active - "devices"/"locations" promoted just above, "io_cards"/
# "point_registry"/"apparatus_registry" in earlier tasks. Nothing left
# in this group's own inactive-children list.
# "Alarmówka: na maksa dużo opcji" - SPEC's next section, promoted the
# same way io_cards/point_registry/apparatus_registry already were.
_TREE_ITEM_ZONES = "security_zones"
_TREE_ITEM_LINES = "security_lines"
# "Zabezpieczenia: podział elektryczne/procesowe" - promoted the same
# way, replacing the single "Nastawy" placeholder with the two real
# domains runtime itself keeps separate (protection_manager.py vs
# process_protection_manager.py).
_TREE_ITEM_ELECTRICAL_PROTECTION = "protection_electrical"
_TREE_ITEM_PROCESS_PROTECTION = "protection_process"
_INACTIVE_CONTROLLER_CHILDREN = [("controller_connection", "tree.controller_connection")]

_BREADCRUMB_KEYS = {
    _TREE_ITEM_SCREENS: "breadcrumb.screens",
    _TREE_ITEM_LOGIC: "breadcrumb.logic",
    _TREE_ITEM_INFO: "breadcrumb.info",
    _TREE_ITEM_IO_CARDS: "breadcrumb.devices",
    _TREE_ITEM_LOCATIONS: "breadcrumb.locations",
    _TREE_ITEM_POINT_REGISTRY: "breadcrumb.point_registry",
    _TREE_ITEM_DEVICES: "breadcrumb.apparatus_registry",
    _TREE_ITEM_ZONES: "breadcrumb.security_zones",
    _TREE_ITEM_LINES: "breadcrumb.security_lines",
    _TREE_ITEM_ELECTRICAL_PROTECTION: "breadcrumb.protection_electrical",
    _TREE_ITEM_PROCESS_PROTECTION: "breadcrumb.protection_process",
}

# STUDIO_UI_STANDARD.md section 1/3: panel_bg + a raised 2px bevel
# (light top/left, shadow bottom/right) - the one visual device that
# actually separates the contextual zone from the fixed top chrome
# (task 1.3's own point: today both sit on the same background and
# read as one bar split in two; a real background+border boundary is
# what a label alone cannot fix).
#
# Task "Studio: wyostrzenie stylu" Problem 1 - the breadcrumb used to be
# its own QLabel bar, stacked ABOVE this toolbar: menu + shared toolbar
# + breadcrumb + contextual toolbar + the editor's own toolbar was five
# bars before a stroke of canvas. The breadcrumb is now the FIRST widget
# INSIDE this same toolbar (BreadcrumbLabel, addWidget()'d below,
# followed by a real QToolBar::separator) - one fewer bar, and the
# editor's own toolbar is gone entirely (its tools mirrored in here too,
# see menus.py's build_*_context_toolbar) - three bars, not five.
_CONTEXT_TOOLBAR_QSS = """
QToolBar#ContextToolbar {
    background: #D4D0C8;
    border-style: outset;
    border-width: 2px;
    border-color: #FFFFFF #808080 #808080 #FFFFFF;
    spacing: 2px;
    padding: 2px;
}
QLabel#BreadcrumbLabel {
    color: #000000;
    font-weight: bold;
    padding: 0 8px 0 2px;
}
"""
_PLACEHOLDER_MESSAGE_QSS = "color: #808080; font-style: italic; padding: 24px;"

# Task "Studio: wyostrzenie stylu" Problem 3 - "drzewo projektu NIE MA
# nagłówka, a Object Library i Properties mają granatowe". accent_bg/
# accent_text (STUDIO_UI_STANDARD.md section 1) - the identical navy the
# tree's own SELECTED row already uses, so the header reads as "this bar
# and the tree below it are one panel", not a color picked separately.
_TREE_HEADER_QSS = """
QLabel#TreeHeader {
    background: #000080;
    color: #FFFFFF;
    padding: 4px 6px;
    font-weight: bold;
}
"""

# STUDIO_UI_STANDARD.md section 6: 24px tree rows, sourced from
# runtime/epw_os/gui/widgets/nav_tree.py's own ROW_HEIGHT - repeated
# here as a literal (studio/ has no dependency on runtime/, GRANICE).
_TREE_ROW_HEIGHT = 24


_BREADCRUMB_FIXED_WIDTH = 280


def _make_breadcrumb_label(text=""):
    """Task "Studio: wyostrzenie stylu — wspólny rdzeń": the breadcrumb
    used to be a plain QLabel sized to its own text - "Projekt →
    Konfiguracja → Schemat synoptyczny" and "Projekt → Konfiguracja →
    Logika" are different lengths, so the shared core group built right
    after it in the SAME toolbar landed at a different x position in
    each context (measured empirically: a 90px shift, not assumed) -
    exactly the "ręka ma trafiać w Kopiuj bez patrzenia" problem this
    correction exists to fix. A FIXED width closes it: every breadcrumb
    occupies identical horizontal space regardless of its own text
    length, elided with "..." if it doesn't fit (QFontMetrics), full
    text always available as the tooltip."""
    label = QLabel()
    label.setObjectName("BreadcrumbLabel")
    label.setFixedWidth(_BREADCRUMB_FIXED_WIDTH)
    if text:
        _set_breadcrumb_text(label, text)
    return label


def _set_breadcrumb_text(label, text):
    metrics = label.fontMetrics()
    elided = metrics.elidedText(text, Qt.TextElideMode.ElideRight, _BREADCRUMB_FIXED_WIDTH - 12)
    label.setText(elided)
    label.setToolTip(text)


class _TreeRowHeightDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(_TREE_ROW_HEIGHT)
        return size


def _dimmed_icon(icon: QIcon, size: int = 16) -> QIcon:
    """Task "Studio: wyostrzenie stylu" Problem 3 - "gałęzie [...]
    nieaktywne mają dziś sam szary tekst kursywą. Dodaj im wyszarzone
    ikony". The SAME glyph as an active branch's own icon, faded rather
    than swapped for a different shape - a dimmed icon still reads as
    "this is a real, specific thing", just not one you can open yet;
    a generic placeholder glyph would read as "this is a filler", which
    is the opposite of what task 1.4's own zero-fasad tree wants. Uses
    QPainter's own opacity compositing on the icon's real pixmap rather
    than Qt's built-in QIcon.Mode.Disabled rendering - that path is
    meant for buttons and reads as near-invisible at a 16px tree-row
    size in a quick visual check, so a plain alpha fade is used
    instead."""
    pixmap = icon.pixmap(size, size)
    dimmed = QPixmap(pixmap.size())
    dimmed.fill(Qt.GlobalColor.transparent)
    painter = QPainter(dimmed)
    painter.setOpacity(0.38)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return QIcon(dimmed)


class _AspectContainer(QWidget):
    """Task 1.3/1.5, tightened by "Studio: wyostrzenie stylu" Problem 1:
    ONE contextual toolbar - the breadcrumb path as its own left-most
    label (BreadcrumbLabel), a separator, then the active aspect's own
    tools - over the aspect's own real editor widget. The whole reason
    the old shell "looked like a zlepek dwóch programów" was chrome
    stacked at the top beside the app-level bars; this is a single,
    visually distinct zone INSIDE the document area instead."""

    def __init__(self, breadcrumb_text, editor_widget, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.context_toolbar = QToolBar()
        self.context_toolbar.setObjectName("ContextToolbar")
        self.context_toolbar.setMovable(False)
        self.context_toolbar.setStyleSheet(_CONTEXT_TOOLBAR_QSS)
        # Task "zestaw ikon Studio" art is drawn at true 16x16 - without
        # this, Qt's default toolbar icon size (24px+) upscales it with
        # no smoothing, which is what made the first pass look "too
        # pixelarty" blown up in the actual button instead of crisp at
        # its native size the way real Win98 toolbar icons sat.
        self.context_toolbar.setIconSize(QSize(16, 16))

        self.breadcrumb_label = _make_breadcrumb_label(breadcrumb_text)
        self.context_toolbar.addWidget(self.breadcrumb_label)
        self.context_toolbar.addSeparator()
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

        self.context_toolbar = QToolBar()
        self.context_toolbar.setObjectName("ContextToolbar")
        self.context_toolbar.setMovable(False)
        self.context_toolbar.setStyleSheet(_CONTEXT_TOOLBAR_QSS)
        self.breadcrumb_label = _make_breadcrumb_label()
        self.context_toolbar.addWidget(self.breadcrumb_label)
        layout.addWidget(self.context_toolbar)

        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setStyleSheet(_PLACEHOLDER_MESSAGE_QSS)
        layout.addStretch(1)
        layout.addWidget(self.message)
        layout.addStretch(2)

    def set_content(self, breadcrumb_text, message_text):
        _set_breadcrumb_text(self.breadcrumb_label, breadcrumb_text)
        self.message.setText(message_text)


class StudioMainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.setObjectName("StudioMainWindow")
        self.setStyleSheet(STUDIO_CHROME_QSS)
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
        self._project_info_panel = None
        self._cards_panel = None
        self._locations_panel = None
        self._point_registry_panel = None
        self._devices_panel = None
        self._zones_panel = None
        self._lines_panel = None
        self._electrical_protection_panel = None
        self._process_protection_panel = None
        self._active = None  # None | _TREE_ITEM_SCREENS | _TREE_ITEM_LOGIC | ...
        self._aspect_containers = {}  # key -> _AspectContainer, rebuilt on every visit
        self._tree_label_refs = []  # [(QTreeWidgetItem, tr key), ...] for language switches

        # Task "edytor DI/DO/AI" - SPEC_PROJEKT_EPW.md step 1
        # (project_format.py) finally has somewhere to live: a real,
        # in-memory Project, present from the moment the window opens
        # (an unsaved new project IS unsaved work - new_project()'s own
        # docstring). This is intentionally SEPARATE from the fixed
        # toolbar's Nowy/Otwórz/Zapisz (still "the active aspect's own
        # document", unchanged) - see project_panels.py's module
        # docstring for why redefining those would have been a silent
        # regression, not a fix.
        self._project = new_project(tr("project_info.default_name"))
        self._project_path = None

        self._build_ui()
        self._restore_splitter_state()
        self._on_project_changed()

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

        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)
        self._tree_header = QLabel(tr("tree.root"))
        self._tree_header.setObjectName("TreeHeader")
        self._tree_header.setStyleSheet(_TREE_HEADER_QSS)
        tree_layout.addWidget(self._tree_header)
        tree_layout.addWidget(self.tree, 1)

        self.stack = QStackedWidget()
        self._empty_placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self._empty_placeholder)
        placeholder_layout.addStretch(1)
        self.stack.addWidget(self._empty_placeholder)

        self._inactive_placeholder = _InactivePlaceholder()
        self.stack.addWidget(self._inactive_placeholder)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(tree_container)
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
        # Problem 2's own status-bar bullet: "uchwyt rozmiaru w rogu" -
        # QStatusBar draws one natively once told to; Qt just doesn't
        # enable it by default.
        status_bar.setSizeGripEnabled(True)

    def _build_tree(self):
        """Task 1.4 - the WHOLE project structure, not just what's
        implemented. shared/docs/SPEC_FORMAT_EPW.md's own section names
        (project/, io/, screens/, logic/, security/, protection/)
        supply every branch label - the tree mirrors the project FILE
        FORMAT's structure, not a list of programs."""
        tree = QTreeWidget()
        tree.setObjectName("ProjectTree")
        tree.setHeaderHidden(True)
        tree.setIndentation(12)
        tree.setItemDelegate(_TreeRowHeightDelegate(tree))

        style = self.style()
        icon_screens = style.standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)
        icon_logic = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        # Task "Studio: wyostrzenie stylu" Problem 3 - each inactive
        # branch gets a DIMMED version of the icon its own future active
        # counterpart would plausibly use (nav_tree.py's convention:
        # every branch is a real thing, styled to look reachable or not
        # - never a blank/generic filler glyph). SP_FileDialogInfoView
        # (a document with a small "i") stands in for the still-unbuilt
        # config/registry/setpoint pages generically - visually distinct
        # from the two ACTIVE branches' own icons above, so an active
        # and an inactive branch are never one accidental click apart.
        icon_inactive = _dimmed_icon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView))
        # The three newly-active leaves reuse icons from Studio's own
        # Win98-manner set (task "zestaw ikon Studio") rather than a
        # fourth standardIcon() - "about" (info circle) reads plainly as
        # "project info", "device_list"/"project_registers" already
        # exist for exactly "a list of hardware" / "a table of
        # registers", no new icon needed.
        icon_info = icons.icon("about")
        icon_io_cards = icons.icon("device_list")
        icon_point_registry = icons.icon("project_registers")
        # "draw_building" (a house) reads plainly as "a place" - reused
        # from Synoptic's own tool set for "Lokalizacje".
        icon_locations = icons.icon("draw_building")
        # "settings" (a gear) reads plainly as "a mechanism/apparatus" -
        # closer to "Aparaty" than any other icon already in the set.
        icon_devices = icons.icon("settings")
        # "Alarmówka" - "lock" (a zone is armed/disarmed, the same
        # concept a padlock already conveys) and "draw_wire" (a
        # supervised LINE, literally) - both reused from the existing
        # set rather than drawing two more single-purpose icons.
        icon_zones = icons.icon("lock")
        icon_lines = icons.icon("draw_wire")
        # "Zabezpieczenia" - "medium_electrical" (the yellow lightning
        # bolt) already means electrical current elsewhere in this same
        # set; "add_meter" (a gauge/dial) reads as "a measured process
        # value", the actual subject of process protection.
        icon_electrical = icons.icon("medium_electrical")
        icon_process = icons.icon("add_meter")

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

        def add_active_leaf(parent_item, key, label_key, icon):
            item = QTreeWidgetItem([tr(label_key)])
            item.setIcon(0, icon)
            item.setData(0, Qt.ItemDataRole.UserRole, ("active", key))
            parent_item.addChild(item)
            self._tree_label_refs.append((item, label_key))
            return item

        root = QTreeWidgetItem([tr("tree.root")])
        root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        f = root.font(0)
        f.setBold(True)
        root.setFont(0, f)
        tree.addTopLevelItem(root)
        self._tree_label_refs.append((root, "tree.root"))

        self._item_info = add_active_leaf(root, _TREE_ITEM_INFO, "tree.info", icon_info)

        config = add_group(root, "tree.group_config")
        self._item_io_cards = add_active_leaf(config, _TREE_ITEM_IO_CARDS, "tree.devices", icon_io_cards)
        self._item_locations = add_active_leaf(config, _TREE_ITEM_LOCATIONS, "tree.locations", icon_locations)
        self._item_point_registry = add_active_leaf(
            config, _TREE_ITEM_POINT_REGISTRY, "tree.point_registry", icon_point_registry
        )
        self._item_devices = add_active_leaf(
            config, _TREE_ITEM_DEVICES, "tree.apparatus_registry", icon_devices
        )

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
        self._item_zones = add_active_leaf(alarm, _TREE_ITEM_ZONES, "tree.security_zones", icon_zones)
        self._item_lines = add_active_leaf(alarm, _TREE_ITEM_LINES, "tree.security_lines", icon_lines)

        protection = add_group(root, "tree.group_protection")
        self._item_electrical_protection = add_active_leaf(
            protection, _TREE_ITEM_ELECTRICAL_PROTECTION, "tree.protection_electrical", icon_electrical
        )
        self._item_process_protection = add_active_leaf(
            protection, _TREE_ITEM_PROCESS_PROTECTION, "tree.protection_process", icon_process
        )

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
        tb = QToolBar(tr("app.title"), self)
        tb.setObjectName("SharedToolbar")
        tb.setMovable(False)
        # True 16x16, same reasoning as ContextToolbar's own
        # setIconSize() a few lines below in _AspectContainer - the
        # art is native pixel art, not meant to be upscaled.
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)
        self._shared_toolbar = tb

        # Task "zestaw ikon Studio w manierze Windows 98" - every icon
        # here now comes from studio/shell/icons (the colorful,
        # 16x16, hand-described PNG set that task built), replacing the
        # older flat logic_studio.ui.icons.action_icon() set this
        # toolbar used since "Studio: wyostrzenie stylu" - that set was
        # Logic Studio's own internal monochrome-ish icon language;
        # this one is Studio's own, shared with the contextual toolbars
        # below, so the fixed bar and the contextual one finally draw
        # from the same hand instead of two different styles meeting at
        # the same window.

        def _make(text_key, icon_name: str, handler):
            action = tb.addAction(icons.icon(icon_name), tr(text_key))
            action.triggered.connect(handler)
            return action

        self.act_shared_new = _make("toolbar.new", "new", self._shared_new)
        self.act_shared_open = _make("toolbar.open", "open", self._shared_open)
        self.act_shared_save = _make("toolbar.save", "save", self._shared_save)
        self.act_shared_save_as = _make("toolbar.save_as", "save_as", self._shared_save_as)
        tb.addSeparator()
        self.act_shared_undo = _make("toolbar.undo", "undo", self._shared_undo)
        self.act_shared_redo = _make("toolbar.redo", "redo", self._shared_redo)
        tb.addSeparator()
        self.act_shared_help = _make("toolbar.help", "help", self._help_topics)
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

    # ------------------------------------------------------------------
    # Contextual toolbar's shared core (Copy/Paste/Delete/Snap) - state
    # and routed actions. Task "Studio: wyostrzenie stylu — wspólny
    # rdzeń": same dispatch-on-_active pattern as the fixed toolbar
    # above, kept separate from it because these four live in the
    # CONTEXTUAL toolbar (rebuilt per aspect - menus.py's
    # _build_core_group()), not the fixed one.
    # ------------------------------------------------------------------

    def _core_copy(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_copy.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Copy")

    def _core_paste(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_paste.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Paste")

    def _core_delete(self):
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_delete.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Delete")

    def _core_cut(self):
        # Cut is Logic-only (menus.py's own measurement: Synoptic's Edit
        # menu has no Cut at all) - grayed there via
        # _set_core_toolbar_enabled's is_logic gate below, not wired to
        # anything when Screens is active.
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_cut.trigger()

    def _set_core_toolbar_enabled(self, can_copy, can_paste, can_delete, can_cut=False):
        # Guarded: the core actions only exist once _build_core_group()
        # has run at least once (the first tree click) - the state timer
        # can tick before that, while the neutral empty placeholder is
        # still showing.
        if not hasattr(self, "act_core_copy"):
            return
        has_editor = self._active is not None
        is_logic = self._active == _TREE_ITEM_LOGIC
        self.act_core_copy.setEnabled(has_editor and can_copy)
        self.act_core_paste.setEnabled(has_editor and can_paste)
        self.act_core_delete.setEnabled(has_editor and can_delete)
        # Cut/Zoom In/Zoom Out/Grid are real only in Logic (no Synoptic
        # equivalent exists anywhere - menus.py's own measurement) -
        # grayed while Screens is active, never removed, same rule the
        # fixed Widok menu already applies to Zoom/Grid.
        self.act_core_cut.setEnabled(is_logic and can_cut)
        self.act_core_zoom_in.setEnabled(is_logic)
        self.act_core_zoom_out.setEnabled(is_logic)
        self.act_core_grid.setEnabled(is_logic)
        # Snap is a plain toggle command, not gated on selection/
        # clipboard content - always clickable whenever an aspect is
        # active, same as it already was in the fixed Widok menu.
        self.act_core_snap.setEnabled(has_editor)

    def _refresh_shared_toolbar_state(self):
        if self._active == _TREE_ITEM_LOGIC and self._logic_panel is not None:
            mw = self._logic_panel.main_window()
            self._set_shared_toolbar_enabled(
                mw.is_dirty, len(mw.project.undo_stack) > 0, len(mw.project.redo_stack) > 0
            )
            # Point 5's own "korzystaj z mostu stanu, który już
            # zbudowałeś" - Logic Studio's own _update_clipboard_
            # actions()/selection tracking already keeps these three
            # correct; read straight from the real actions, not
            # recomputed here.
            self._set_core_toolbar_enabled(
                mw.act_copy.isEnabled(), mw.act_paste.isEnabled(), mw.act_delete.isEnabled(),
                mw.act_cut.isEnabled(),
            )
        elif self._active == _TREE_ITEM_SCREENS and self._synoptic_panel is not None:
            self._synoptic_panel.query_state(self._apply_synoptic_toolbar_state)
        else:
            self._set_shared_toolbar_enabled(False, False, False)
            self._set_core_toolbar_enabled(False, False, False)

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
            self._set_core_toolbar_enabled(False, False, False)
            return
        self._set_shared_toolbar_enabled(
            bool(state.get("isDirty")), bool(state.get("canUndo")), bool(state.get("canRedo"))
        )
        # hasSelection covers Copy/Delete honestly. Paste has no
        # equivalent signal in the read-only bridge (Blocker B's own
        # approved scope stopped at canUndo/canRedo/isDirty/
        # hasSelection - "clipboard has content" was never included) -
        # left enabled whenever Screens is active, same known,
        # previously-flagged gap as before this task, not silently
        # papered over.
        has_selection = bool(state.get("hasSelection"))
        self._set_core_toolbar_enabled(has_selection, True, has_selection)

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

    def _choose_canvas_background(self):
        """Task "Studio: wyostrzenie stylu" Problem 4.2 - reachable from
        the CONTEXTUAL toolbar (menus.py's build_*_context_toolbar), not
        the fixed Widok menu: canvas background is a property of the
        active aspect's own document, same category as Zoom/Grid/Snap
        conceptually, but unlike those it has no cross-aspect meaning at
        all when neither aspect is active - it belongs with the rest of
        that aspect's own tools, not the app-level chrome."""
        from studio.shell.color_picker import DEFAULT_CANVAS_BACKGROUND, StudioColorDialog

        def _open_with(current_hex, apply_callback):
            chosen = StudioColorDialog.get_color(current_hex or DEFAULT_CANVAS_BACKGROUND, self)
            if chosen is not None:
                apply_callback(chosen.name())

        if self._active == _TREE_ITEM_LOGIC:
            _open_with(self._logic_panel.canvas_background(), self._logic_panel.set_canvas_background)
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.query_canvas_background(
                lambda color: _open_with(color, self._synoptic_panel.set_canvas_background)
            )

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
        self._tree_header.setText(tr("tree.root"))
        for item, key in self._tree_label_refs:
            item.setText(0, tr(key))

        old_toolbar = self._shared_toolbar
        self.removeToolBar(old_toolbar)
        old_toolbar.deleteLater()
        self._build_shared_toolbar()

        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        build_fixed_menu(menubar, self)

        self._on_project_changed()
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
            elif key == _TREE_ITEM_INFO:
                self._open_info()
            elif key == _TREE_ITEM_IO_CARDS:
                self._open_io_cards()
            elif key == _TREE_ITEM_LOCATIONS:
                self._open_locations()
            elif key == _TREE_ITEM_POINT_REGISTRY:
                self._open_point_registry()
            elif key == _TREE_ITEM_DEVICES:
                self._open_devices()
            elif key == _TREE_ITEM_ZONES:
                self._open_zones()
            elif key == _TREE_ITEM_LINES:
                self._open_lines()
            elif key == _TREE_ITEM_ELECTRICAL_PROTECTION:
                self._open_electrical_protection()
            elif key == _TREE_ITEM_PROCESS_PROTECTION:
                self._open_process_protection()
        elif kind == "inactive":
            self._open_inactive(key)

    def _open_screens(self):
        if self._synoptic_panel is None:
            from studio.shell.synoptic_panel import SynopticPanel
            self._synoptic_panel = SynopticPanel()
            self._synoptic_panel.page_ready.connect(self._sync_device_registry_with_synoptic)
        else:
            # Already loaded from an earlier visit - page_ready won't
            # fire again, so run the sync directly (query_device_
            # registry() itself no-ops safely if the page somehow isn't
            # ready, same guard as every other bridge call).
            self._sync_device_registry_with_synoptic()
        self._show_aspect_container(
            _TREE_ITEM_SCREENS, self._synoptic_panel, build_synoptic_context_toolbar, self._synoptic_panel
        )
        self._status_editor.setText(tr("statusbar.active_editor", name=tr("editor.synoptic_name")))
        self._active = _TREE_ITEM_SCREENS
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _sync_device_registry_with_synoptic(self):
        """Task "Studio: rejestr punktów" follow-up ("most Cards/
        Locations do Synoptic"). ADD-ONLY, both directions - see
        synoptic_panel.py's query_device_registry()/
        push_device_registry() docstrings and main.tsx's own comment for
        why: a real rename/delete sync needs a conflict-resolution
        decision this task does not make. Pulls in any card/location
        Synoptic already has that Studio doesn't (spawning points for a
        newly-pulled card, same as adding one by hand), then pushes
        Studio's own list out so Synoptic picks up anything added there
        instead."""
        if self._synoptic_panel is None:
            return

        def _after_pull(registry):
            from studio.shell.project_panels import (
                card_from_synoptic_dict, card_to_synoptic_dict,
                location_from_synoptic_dict, location_to_synoptic_dict,
                sync_points_for_card,
            )
            project = self._project
            changed = False
            if registry:
                existing_card_ids = {c.id for c in project.cards}
                for card_data in registry.get("cards", []):
                    if card_data.get("id") in existing_card_ids:
                        continue
                    card = card_from_synoptic_dict(card_data)
                    project.cards.append(card)
                    sync_points_for_card(project, card)
                    existing_card_ids.add(card.id)
                    changed = True
                existing_codes = {l.code for l in project.locations}
                for location_data in registry.get("locations", []):
                    if location_data.get("code") in existing_codes:
                        continue
                    location = location_from_synoptic_dict(location_data)
                    project.locations.append(location)
                    existing_codes.add(location.code)
                    changed = True
            if changed:
                project.touch()
                self._on_project_changed()
                if self._cards_panel is not None:
                    self._cards_panel.refresh()
                if self._point_registry_panel is not None:
                    self._point_registry_panel.refresh()
            cards_out = [card_to_synoptic_dict(c) for c in self._project.cards]
            locations_out = [location_to_synoptic_dict(l) for l in self._project.locations]
            self._synoptic_panel.push_device_registry(cards_out, locations_out)

        self._synoptic_panel.query_device_registry(_after_pull)

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

    def _open_info(self):
        if self._project_info_panel is None:
            from studio.shell.project_panels import ProjectInfoPanel
            self._project_info_panel = ProjectInfoPanel(self)
        else:
            self._project_info_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_INFO, self._project_info_panel, build_project_info_toolbar, self._project_info_panel
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_INFO
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_io_cards(self):
        if self._cards_panel is None:
            from studio.shell.project_panels import CardsPanel
            self._cards_panel = CardsPanel(self)
        else:
            self._cards_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_IO_CARDS, self._cards_panel, build_cards_toolbar, self._cards_panel
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_IO_CARDS
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_locations(self):
        if self._locations_panel is None:
            from studio.shell.project_panels import LocationsPanel
            self._locations_panel = LocationsPanel(self)
        else:
            self._locations_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_LOCATIONS, self._locations_panel, build_locations_toolbar, self._locations_panel
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_LOCATIONS
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_point_registry(self):
        if self._point_registry_panel is None:
            from studio.shell.project_panels import PointRegistryPanel
            self._point_registry_panel = PointRegistryPanel(self)
        else:
            self._point_registry_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_POINT_REGISTRY, self._point_registry_panel, build_point_registry_toolbar,
            self._point_registry_panel,
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_POINT_REGISTRY
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_devices(self):
        if self._devices_panel is None:
            from studio.shell.project_panels import DevicesPanel
            self._devices_panel = DevicesPanel(self)
        else:
            self._devices_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_DEVICES, self._devices_panel, build_devices_toolbar, self._devices_panel
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_DEVICES
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_zones(self):
        if self._zones_panel is None:
            from studio.shell.project_panels import ZonesPanel
            self._zones_panel = ZonesPanel(self)
        else:
            self._zones_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_ZONES, self._zones_panel, build_zones_toolbar, self._zones_panel
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_ZONES
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_lines(self):
        if self._lines_panel is None:
            from studio.shell.project_panels import LinesPanel
            self._lines_panel = LinesPanel(self)
        else:
            self._lines_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_LINES, self._lines_panel, build_lines_toolbar, self._lines_panel
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_LINES
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_electrical_protection(self):
        if self._electrical_protection_panel is None:
            from studio.shell.project_panels import ElectricalProtectionPanel
            self._electrical_protection_panel = ElectricalProtectionPanel(self)
        else:
            self._electrical_protection_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_ELECTRICAL_PROTECTION, self._electrical_protection_panel,
            build_electrical_protection_toolbar, self._electrical_protection_panel,
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_ELECTRICAL_PROTECTION
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_process_protection(self):
        if self._process_protection_panel is None:
            from studio.shell.project_panels import ProcessProtectionPanel
            self._process_protection_panel = ProcessProtectionPanel(self)
        else:
            self._process_protection_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_PROCESS_PROTECTION, self._process_protection_panel,
            build_process_protection_toolbar, self._process_protection_panel,
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_PROCESS_PROTECTION
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    # ------------------------------------------------------------------
    # Project lifecycle (Informacje o projekcie's own toolbar) - separate
    # from _shared_new/_shared_open/etc above, see project_panels.py's
    # module docstring for why.
    # ------------------------------------------------------------------

    def _on_project_changed(self):
        """Called by project_panels.py after every edit (card added,
        point named, metadata changed, ...) - the one place that keeps
        the status bar and the info panel's own read-outs (path,
        revision) honest. Does NOT refresh the Cards/Point Registry
        panels themselves on every keystroke - each _open_* above
        already refreshes on entry, which is the only time stale data
        would actually be visible."""
        name = self._project.metadata.name or tr("project_info.default_name")
        marker = "*" if self._project.is_dirty else ""
        self._status_project.setText(f"{name}{marker}")
        if self._project_info_panel is not None:
            self._project_info_panel.refresh()

    def _confirm_discard_project(self) -> bool:
        """True = caller may proceed (nothing unsaved, or the user chose
        Save/Discard). False = Cancel, caller must stop."""
        if not self._project.is_dirty:
            return True
        reply = QMessageBox.question(
            self, tr("project_info.unsaved_title"), tr("project_info.unsaved_text"),
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            return self._save_project()
        return reply == QMessageBox.StandardButton.Discard

    def _new_project(self):
        if not self._confirm_discard_project():
            return
        self._project = new_project(tr("project_info.default_name"))
        self._project_path = None
        self._on_project_changed()
        if self._cards_panel is not None:
            self._cards_panel.refresh()
        if self._locations_panel is not None:
            self._locations_panel.refresh()
        if self._point_registry_panel is not None:
            self._point_registry_panel.refresh()
        if self._devices_panel is not None:
            self._devices_panel.refresh()
        if self._zones_panel is not None:
            self._zones_panel.refresh()
        if self._lines_panel is not None:
            self._lines_panel.refresh()
        if self._electrical_protection_panel is not None:
            self._electrical_protection_panel.refresh()
        if self._process_protection_panel is not None:
            self._process_protection_panel.refresh()

    def _open_project(self):
        if not self._confirm_discard_project():
            return
        path, _filter = QFileDialog.getOpenFileName(
            self, tr("project_info.open_dialog_title"),
            self.settings.value("project/last_dir", ""), "EPW Project (*.epw)",
        )
        if not path:
            return
        try:
            project = load_project(path)
        except (ProjectFormatError, OSError) as exc:
            QMessageBox.critical(self, tr("project_info.open_failed_title"), str(exc))
            return
        self._project = project
        self._project_path = path
        self.settings.setValue("project/last_dir", str(Path(path).parent))
        self._on_project_changed()
        if self._cards_panel is not None:
            self._cards_panel.refresh()
        if self._locations_panel is not None:
            self._locations_panel.refresh()
        if self._point_registry_panel is not None:
            self._point_registry_panel.refresh()
        if self._devices_panel is not None:
            self._devices_panel.refresh()
        if self._zones_panel is not None:
            self._zones_panel.refresh()
        if self._lines_panel is not None:
            self._lines_panel.refresh()
        if self._electrical_protection_panel is not None:
            self._electrical_protection_panel.refresh()
        if self._process_protection_panel is not None:
            self._process_protection_panel.refresh()

    def _save_project(self) -> bool:
        if self._project_path is None:
            return self._save_project_as()
        try:
            save_project(self._project, self._project_path)
        except OSError as exc:
            QMessageBox.critical(self, tr("project_info.save_failed_title"), str(exc))
            return False
        self._on_project_changed()
        return True

    def _save_project_as(self) -> bool:
        path, _filter = QFileDialog.getSaveFileName(
            self, tr("project_info.save_dialog_title"),
            self.settings.value("project/last_dir", ""), "EPW Project (*.epw)",
        )
        if not path:
            return False
        if not path.lower().endswith(".epw"):
            path += ".epw"
        try:
            save_project(self._project, path)
        except OSError as exc:
            QMessageBox.critical(self, tr("project_info.save_failed_title"), str(exc))
            return False
        self._project_path = path
        self.settings.setValue("project/last_dir", str(Path(path).parent))
        self._on_project_changed()
        return True

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
        # Task "edytor DI/DO/AI" - the Project is real/mutable for the
        # first time; closing without asking would silently discard
        # named points same as any other editor's unsaved-work loss.
        if not self._confirm_discard_project():
            event.ignore()
            return
        self.settings.setValue("shell/splitter_state", self.splitter.saveState())
        super().closeEvent(event)


def _placeholder_breadcrumb_key(key):
    return f"breadcrumb.{key}"
