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

from PySide6.QtCore import Qt, QElapsedTimer, QEventLoop, QSettings, QSize, QTimer
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QMainWindow, QMenuBar, QMessageBox, QSplitter, QStyle, QStyledItemDelegate,
    QToolBar, QTreeWidget, QTreeWidgetItem, QStackedWidget, QLabel, QWidget,
    QVBoxLayout,
)

from studio.shell import icons
from studio.shell.i18n import get_language, set_language, tr
from studio.shell.menus import (
    build_cards_toolbar, build_controller_toolbar, build_devices_toolbar,
    build_electrical_protection_toolbar, build_fixed_menu, build_help_toolbar, build_lines_toolbar,
    build_locations_toolbar, build_logic_context_toolbar, build_modules_toolbar,
    build_mqtt_toolbar, build_point_registry_toolbar, build_process_protection_toolbar,
    build_project_info_toolbar, build_service_notes_toolbar, build_synoptic_context_toolbar, build_zones_toolbar,
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
# Task "fix/project-format-integrity" point 2.1 - REVERTED the previous
# session's rename: this leaf is "Karty wejść/wyjść" again ("tree.
# io_cards"), freeing "Skład urządzenia"/"devices" for its OWN,
# different, real meaning - the contract's own one (SPEC_PROJEKT_EPW.md:
# "modules: lista nazw modułów... TO NIE JEST lista przełączników" -
# which FUNCTIONAL subsystems this controller has, not which physical
# ELA/ADA cards). The previous rename conflated the two because nothing
# used `modules` yet; now something does (_TREE_ITEM_MODULES below).
# "Karty wejść/wyjść" over the task's other offered option ("Moduły
# sprzętowe"): it matches project_format.Card's own field names/SPEC
# wording directly, and "moduły" would collide in READER'S HEAD with
# the new "Skład urządzenia" - which is exactly about "moduły" in the
# functional sense. Two different "moduły" one screen apart is the
# confusion this rename exists to remove, not reintroduce.
_TREE_ITEM_IO_CARDS = "io_cards"
_TREE_ITEM_LOCATIONS = "locations"
_TREE_ITEM_POINT_REGISTRY = "point_registry"
# "Co jeszcze możemy dorobić" follow-up - SPEC's next section, Aparaty
# (a device's feedback/command point lists), same "active" leaf pattern.
_TREE_ITEM_DEVICES = "apparatus_registry"
# Task "fix/project-format-integrity" point 2/3 - "Skład urządzenia":
# the REAL contract concept, mirrored from runtime/epw_os/core/
# feature_config.py's own ALWAYS_ON_FEATURES/TOGGLABLE_FEATURES (see
# project_panels.MODULE_CATALOG's own docstring) - which FUNCTIONAL
# subsystems (Alarmówka, Zabezpieczenia...) this controller has at all.
# First leaf under PROJEKT, above KONFIGURACJA (task's own placement).
_TREE_ITEM_MODULES = "devices"

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
# "Połączenie ze sterownikiem" + "dział help pełny" - the last two
# promotions: STEROWNIK's own last inactive placeholder, and a new
# "Pomoc" leaf (not part of SPEC_FORMAT_EPW.md's own structure, but
# task explicitly asked for a full help department, same active-leaf
# navigation pattern as everything else rather than a plain dialog).
_TREE_ITEM_CONTROLLER = "controller_connection"
# 2026-09-18: two more project aspects - the MQTT integration (a setting
# of the project, no longer controller-local) and the service notes the
# panel writes (read here).
_TREE_ITEM_MQTT = "mqtt"
_TREE_ITEM_SERVICE_NOTES = "service_notes"
_TREE_ITEM_HELP = "help"

_BREADCRUMB_KEYS = {
    _TREE_ITEM_SCREENS: "breadcrumb.screens",
    _TREE_ITEM_LOGIC: "breadcrumb.logic",
    _TREE_ITEM_INFO: "breadcrumb.info",
    _TREE_ITEM_IO_CARDS: "breadcrumb.io_cards",
    _TREE_ITEM_MODULES: "breadcrumb.devices",
    _TREE_ITEM_LOCATIONS: "breadcrumb.locations",
    _TREE_ITEM_POINT_REGISTRY: "breadcrumb.point_registry",
    _TREE_ITEM_DEVICES: "breadcrumb.apparatus_registry",
    _TREE_ITEM_ZONES: "breadcrumb.security_zones",
    _TREE_ITEM_LINES: "breadcrumb.security_lines",
    _TREE_ITEM_ELECTRICAL_PROTECTION: "breadcrumb.protection_electrical",
    _TREE_ITEM_PROCESS_PROTECTION: "breadcrumb.protection_process",
    _TREE_ITEM_CONTROLLER: "breadcrumb.controller_connection",
    _TREE_ITEM_MQTT: "breadcrumb.mqtt",
    _TREE_ITEM_SERVICE_NOTES: "breadcrumb.service_notes",
    _TREE_ITEM_HELP: "breadcrumb.help",
}

# Task point 5.3 - "Mapowanie gałąź drzewa -> temat pomocy." Tree keys
# (left column) are this file's own _TREE_ITEM_* constants; help-topic
# keys (right column) are generate_help.py's TOPICS keys (see that
# file's own _manifest.py). Deliberately NOT the same string in every
# row - e.g. _TREE_ITEM_DEVICES is "apparatus_registry" on the tree
# side but "apparatus" on the help side, and _TREE_ITEM_INFO ("info")
# happens to match both. _TREE_ITEM_HELP itself is omitted - F1 while
# already on the Pomoc department has no "surrounding" topic to jump
# to, so it's a no-op there (see _open_contextual_help's None guard).
_HELP_TOPIC_BY_TREE_KEY = {
    _TREE_ITEM_INFO: "info",
    _TREE_ITEM_MODULES: "devices",
    _TREE_ITEM_IO_CARDS: "io_cards",
    _TREE_ITEM_LOCATIONS: "locations",
    _TREE_ITEM_POINT_REGISTRY: "points",
    _TREE_ITEM_DEVICES: "apparatus",
    _TREE_ITEM_SCREENS: "screens",
    _TREE_ITEM_LOGIC: "logic",
    _TREE_ITEM_ZONES: "zones",
    _TREE_ITEM_LINES: "lines",
    _TREE_ITEM_ELECTRICAL_PROTECTION: "protection_electrical",
    _TREE_ITEM_PROCESS_PROTECTION: "protection_process",
    _TREE_ITEM_CONTROLLER: "controller",
    _TREE_ITEM_MQTT: "mqtt",
    _TREE_ITEM_SERVICE_NOTES: "service_notes",
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

        # Task "jedno źródło listy kart" etap 4 - measured (spike/
        # addressing_migration/... cache in the chat report): switching
        # BACK to an already-open aspect (Logika above all - it embeds
        # Logic Studio's whole MainWindow) cost ~135ms per switch, almost
        # entirely `editor_widget` being RE-PARENTED into a brand new
        # _AspectContainer's layout every single visit (main_window.py's
        # own _show_aspect_container built one fresh every time - see its
        # OWN prior docstring, now updated, for why: toolbar_builder's
        # QActions pile up on a reused toolbar otherwise). The editor
        # widget never actually needs to move once placed - only the
        # toolbar's own aspect-specific actions need clearing and
        # rebuilding on each re-visit, so this baseline (everything
        # already on the toolbar right here, before toolbar_builder ever
        # runs: the breadcrumb + separator) is what _show_aspect_
        # container clears back down to instead of discarding this whole
        # container and rebuilding it.
        self._toolbar_baseline_action_count = len(self.context_toolbar.actions())


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
        self._synoptic_dirty = False  # last isDirty read off the Synoptic state bridge
        self._logic_dirty_seen = False
        self._project_info_panel = None
        self._modules_panel = None
        self._cards_panel = None
        self._locations_panel = None
        self._point_registry_panel = None
        self._devices_panel = None
        self._zones_panel = None
        self._lines_panel = None
        self._electrical_protection_panel = None
        self._process_protection_panel = None
        self._controller_panel = None
        self._mqtt_panel = None
        self._service_notes_panel = None
        self._help_panel = None
        self._validation_dialog = None
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

        # Task point 5.3 - "F1 otwiera temat DOTYCZĄCY aktywnego
        # działu, nie spis treści." A window-wide shortcut (not per-
        # panel) so it works no matter which widget inside the active
        # aspect happens to have focus - see _HELP_TOPIC_BY_TREE_KEY
        # and _open_contextual_help above for the actual mapping/logic.
        self._help_shortcut = QShortcut(QKeySequence("F1"), self)
        self._help_shortcut.activated.connect(self._open_contextual_help)

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
        # Task point 8.3 - "Wersja Studio widoczna w pasku stanu albo
        # tytule" - status bar chosen over the title (the title already
        # carries app.title, retranslated on every language switch;
        # tacking a version number onto that string is one more thing
        # that string would have to keep consistent forever). Rightmost
        # permanent widget - never covered by a transient showMessage()
        # (see _export_point_list's own status message).
        from studio.shell.version import STUDIO_VERSION
        self._status_version = QLabel(f"EPW Studio {STUDIO_VERSION}")
        status_bar.addPermanentWidget(self._status_version)
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
        # The two DEPARTMENT icons. These were Qt standard icons - a
        # desktop and a detailed-list-view - which said "a computer" and
        # "a list", and told a user nothing about what either department
        # holds. Both are now drawn in Studio's own set: an AND gate for
        # LOGIKA and a fragment of a one-line diagram for SCHEMAT
        # SYNOPTYCZNY, i.e. a picture of the thing itself.
        icon_screens = icons.icon("synoptic")
        icon_logic = icons.icon("logic")
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
        # "add_group_command" (cascading overlapping squares - "a group
        # of things") reads as "a set of installed modules", distinct
        # from "device_list" (a flat list - the physical card registry).
        icon_modules = icons.icon("add_group_command")
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
        # "scada_preview" (a small monitor) reads as "a live connection
        # to a remote device"; "help" (blue question mark) is Help's own
        # existing icon, reused from the fixed toolbar for consistency.
        icon_controller = icons.icon("scada_preview")
        icon_help = icons.icon("help")

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
        # "Pierwszy pod PROJEKT, nad Konfiguracją" (task's own placement).
        self._item_modules = add_active_leaf(root, _TREE_ITEM_MODULES, "tree.devices", icon_modules)

        config = add_group(root, "tree.group_config")
        self._item_io_cards = add_active_leaf(config, _TREE_ITEM_IO_CARDS, "tree.io_cards", icon_io_cards)
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

        # 2026-09-18: the MQTT integration is a project setting, the
        # service notes are the panel's logbook read here - both under
        # KONFIGURACJA, after the two editors.
        self._item_mqtt = add_active_leaf(config, _TREE_ITEM_MQTT, "tree.mqtt", icons.icon("draw_wire"))
        self._item_service_notes = add_active_leaf(
            config, _TREE_ITEM_SERVICE_NOTES, "tree.service_notes", icons.icon("project_registers")
        )

        # Task "fix/project-format-integrity" point 2.3 - these two
        # groups' own children are shown/hidden by _refresh_module_
        # visibility() below, based on self._project.modules - kept as
        # instance attrs (not local vars) so that method can reach them
        # after _build_tree() returns.
        self._group_alarm = add_group(root, "tree.group_alarm")
        self._item_zones = add_active_leaf(
            self._group_alarm, _TREE_ITEM_ZONES, "tree.security_zones", icon_zones
        )
        self._item_lines = add_active_leaf(
            self._group_alarm, _TREE_ITEM_LINES, "tree.security_lines", icon_lines
        )

        self._group_protection = add_group(root, "tree.group_protection")
        self._item_electrical_protection = add_active_leaf(
            self._group_protection, _TREE_ITEM_ELECTRICAL_PROTECTION, "tree.protection_electrical", icon_electrical
        )
        self._item_process_protection = add_active_leaf(
            self._group_protection, _TREE_ITEM_PROCESS_PROTECTION, "tree.protection_process", icon_process
        )

        controller = add_group(root, "tree.group_controller")
        self._item_controller = add_active_leaf(
            controller, _TREE_ITEM_CONTROLLER, "tree.controller_connection", icon_controller
        )

        self._item_help = add_active_leaf(root, _TREE_ITEM_HELP, "tree.help", icon_help)

        tree.expandAll()
        tree.currentItemChanged.connect(self._on_tree_selection_changed)
        return tree

    def _build_shared_toolbar(self):
        """Task 1.2 - the fixed top toolbar: Nowy/Otwórz/Zapisz/Zapisz
        jako/Cofnij/Ponów/Pomoc, always the same regardless of the
        active aspect.

        User report ("nie działa pasek na górze gdzie wpisujemy projekt
        zapis odczyt"): Nowy/Otwórz/Zapisz/Zapisz jako are THE PROJECT's
        (projekt.epw - _new_project()/_open_project()/_save_project()/
        _save_project_as() below), on every aspect. They used to
        dispatch to the active editor's OWN document instead (Logic's
        .epwlogic / Synoptic's .epwsyn) and do nothing at all on every
        other branch - Cards, Point Registry, Locations... - which is
        exactly where a user configuring a project spends most of the
        time, and where "the top bar is dead" was reported from. The
        editor documents' own lifecycle is not lost: it moved to each
        editor's contextual toolbar (menus.py's build_logic_context_
        toolbar()/build_synoptic_context_toolbar()), next to the rest of
        that editor's own tools. Undo/Redo stay the active editor's (a
        project table has no undo stack) - their enabled state is kept
        honest by _refresh_shared_toolbar_state()."""
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
        self._set_shared_toolbar_enabled(False, False)

    # ------------------------------------------------------------------
    # Shared (fixed) toolbar - state
    # ------------------------------------------------------------------

    def _set_shared_toolbar_enabled(self, can_undo, can_redo):
        # Nowy/Otwórz/Zapisz/Zapisz jako are the project's own (see
        # _build_shared_toolbar) - there is always a project, so they
        # are always live, whatever branch of the tree is open.
        self.act_shared_new.setEnabled(True)
        self.act_shared_open.setEnabled(True)
        self.act_shared_save.setEnabled(True)
        self.act_shared_save_as.setEnabled(True)
        has_editor = self._active is not None
        self.act_shared_undo.setEnabled(has_editor and can_undo)
        self.act_shared_redo.setEnabled(has_editor and can_redo)
        # Pomoc is NOT an editor command and must not be greyed out with
        # the rest of them. It used to be wired to has_editor like its
        # neighbours, which left it dead (and, being disabled, drawn as
        # a washed-out grey disc instead of its own blue "?" - the icon
        # looked broken, which is how this was noticed) on a freshly
        # started Studio, with no editor open: precisely the moment a
        # user is most likely to reach for help. _help_topics() below
        # now always has somewhere to go, so this is always live.
        self.act_shared_help.setEnabled(True)

    def _shared_new(self):
        self._new_project()

    def _shared_open(self):
        self._open_project()

    def _shared_save(self):
        self._save_project()

    def _shared_save_as(self):
        self._save_project_as()

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
        if self._logic_panel is not None:
            logic_dirty = self._logic_panel.is_dirty()
            if logic_dirty != self._logic_dirty_seen:
                self._logic_dirty_seen = logic_dirty
                self._on_project_changed()
        if self._active == _TREE_ITEM_LOGIC and self._logic_panel is not None:
            mw = self._logic_panel.main_window()
            self._set_shared_toolbar_enabled(len(mw.project.undo_stack) > 0, len(mw.project.redo_stack) > 0)
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
            self._set_shared_toolbar_enabled(False, False)
            self._set_core_toolbar_enabled(False, False, False)
            # The screens are part of the project file - their unsaved
            # state has to show in the project's own marker even while
            # another branch is open.
            if self._synoptic_panel is not None and self._synoptic_panel.is_page_ready():
                self._synoptic_panel.query_state(self._note_synoptic_dirty)

    def _apply_synoptic_mode_checks(self, state):
        """Brings the Synoptic toolbar in line with the editor (menus.py's
        synoptic_mode_actions / synoptic_mode_groups): ticks the active work
        mode, shows only that mode's tool group, and ticks the armed tool
        and the medium, wire style and routing a new wire gets."""
        actions = getattr(self, "synoptic_mode_actions", None) or {}
        groups = getattr(self, "synoptic_mode_groups", None) or {}
        work_mode = state.get("workMode") or "SYMBOLS"
        frame = state.get("drawingFrame")
        wanted = {
            "wire": bool(state.get("drawingWire")),
            "frame": frame == "PLAIN",
            "building": frame == "BUILDING",
            "wall": bool(state.get("drawingWallTool")),
            "room": bool(state.get("drawingRoomTool")),
        }
        for key in ("medium", "style", "routing"):
            value = state.get({"medium": "drawingMedium", "style": "drawingStyle", "routing": "wireRoutingMode"}[key])
            for action_key in actions:
                if action_key.startswith(key + ":"):
                    wanted[action_key] = action_key == f"{key}:{value}"
        for action_key in actions:
            if action_key.startswith("mode:"):
                wanted[action_key] = action_key == f"mode:{work_mode}"
        for action_key, action in actions.items():
            try:
                if action.isChecked() != wanted.get(action_key, False):
                    action.setChecked(wanted.get(action_key, False))
            except RuntimeError:
                # The toolbar was rebuilt and this action died with it.
                continue
        for mode, group in groups.items():
            for action in group:
                try:
                    if action.isVisible() != (mode == work_mode):
                        action.setVisible(mode == work_mode)
                except RuntimeError:
                    continue

    def _note_synoptic_dirty(self, state):
        dirty = bool(state.get("isDirty")) if state else False
        if dirty != self._synoptic_dirty:
            self._synoptic_dirty = dirty
            self._on_project_changed()

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
            self._set_shared_toolbar_enabled(False, False)
            self._set_core_toolbar_enabled(False, False, False)
            return
        self._note_synoptic_dirty(state)
        self._set_shared_toolbar_enabled(bool(state.get("canUndo")), bool(state.get("canRedo")))
        self._apply_synoptic_mode_checks(state)
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
        # Same reasoning as act_shared_help in _set_shared_toolbar_
        # enabled(): Pomoc always has a destination, so the menu entry
        # for it is never disabled either - the toolbar button and the
        # menu item run the same handler and must agree.
        self.act_menu_help_topics.setEnabled(True)

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
        """The active editor's own help topics or, when no editor is
        open, Studio's own Pomoc section - the same one the tree's Pomoc
        leaf opens. Without that last branch this method did nothing at
        all outside Logika/Schemat synoptyczny, which is why its two
        entry points had to be disabled there; now that it always lands
        somewhere, both stay enabled."""
        if self._active == _TREE_ITEM_LOGIC:
            self._logic_panel.main_window().act_help.trigger()
        elif self._active == _TREE_ITEM_SCREENS:
            self._synoptic_panel.trigger_menu_item("Help Topics")
        else:
            self._open_help()

    def _open_contextual_help(self):
        """Task point 5.3 - F1 opens the help TOPIC for whatever
        department is on screen, not the help table of contents (the
        toolbar "?" button/_help_topics above still does the old
        Logic/Synoptic-only thing - kept as-is, F1 is a new, separate
        path that covers every department, not a rewrite of that one).
        _HELP_TOPIC_BY_TREE_KEY is a real mapping (not an identity
        function) because tree keys and help-topic keys genuinely
        differ for several panels (e.g. "apparatus_registry" -> "apparatus")."""
        topic_key = _HELP_TOPIC_BY_TREE_KEY.get(self._active)
        if topic_key is None:
            return
        self.tree.setCurrentItem(self._item_help)
        self._open_help()
        self._help_panel.select_topic(topic_key)

    def _show_about_studio(self):
        from studio.shell.project_panels import AboutDialog
        AboutDialog(self).exec()

    # Task point 6 - "Sprawdź projekt": target string -> (tree item to
    # open, the open_* method that lazily constructs/shows that panel,
    # the panel attribute to call the issue's own `selector` on). Kept
    # here (not in project_panels.py) precisely because it's the one
    # place that legitimately knows both this file's _TREE_ITEM_*
    # constants and project_panels.ValidationIssue's own `target`
    # strings - see ValidationIssue's own docstring for why that module
    # doesn't (and shouldn't) know this mapping itself.
    _VALIDATION_TARGETS = {
        "devices": ("_devices_panel", "_open_devices"),
        "points": ("_point_registry_panel", "_open_point_registry"),
        "lines": ("_lines_panel", "_open_lines"),
        "process_protection": ("_process_protection_panel", "_open_process_protection"),
        "modules": ("_modules_panel", "_open_modules"),
    }

    def _check_project(self):
        from studio.shell.project_panels import ValidationReportDialog, validate_project
        issues = validate_project(self._project)
        dialog = ValidationReportDialog(issues, self._navigate_to_validation_issue, parent=self)
        dialog.show()
        # Kept alive past this method's return (a non-modal dialog with
        # no other reference would otherwise be garbage-collected the
        # instant Python's GC runs) - re-running "Sprawdź projekt"
        # simply replaces this reference, closing the previous window's
        # Python object but not its already-shown, already-closed self.
        self._validation_dialog = dialog

    def _navigate_to_validation_issue(self, issue):
        target = self._VALIDATION_TARGETS.get(issue.target)
        if target is None:
            return
        panel_attr, open_method_name = target
        getattr(self, open_method_name)()
        panel = getattr(self, panel_attr, None)
        if panel is not None and issue.selector:
            selector = getattr(panel, issue.selector, None)
            if selector is not None:
                selector(issue.arg)

    def _run_device_wizard(self):
        """User report: "stwórz kreator urządzenia gdzie krok po kroku
        mówi co gdzie dodawać" - device_wizard.DeviceWizard, prefilled
        from the current project, written back only on Finish (add-and-
        update, never removal - see that module's docstring). Ends on the
        Point Registry: the first thing a freshly-carded project has to
        show, and the branch the wizard's own last page points at."""
        from studio.shell.device_wizard import DeviceWizard
        wizard = DeviceWizard(self._project, self)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return
        wizard.apply_to_project(self._project)
        self._on_project_changed()
        self._refresh_all_project_panels()
        self._open_point_registry()

    def _export_point_list(self):
        """Task point 7 - "Eksportuj listę punktów": Waldek's own
        technical notes in the point registry, turned into a printable
        terminal-block table (HTML) or a spreadsheet (CSV) - no new
        data entry, just a different view of project.points that
        already exists. Both formats built by project_panels.py's own
        export_points_csv()/export_points_html() (pure, no Qt - see
        their docstrings), this method is only the file-picker/write."""
        if not self._project.points:
            QMessageBox.information(self, tr("export.dialog_title"), tr("export.no_points"))
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self, tr("export.dialog_title"), "",
            f"{tr('export.filter_csv')};;{tr('export.filter_html')}",
        )
        if not path:
            return
        from studio.shell.project_panels import export_points_csv, export_points_html
        is_html = ".html" in selected_filter.lower() or path.lower().endswith(".html")
        if is_html:
            if not path.lower().endswith(".html"):
                path += ".html"
            content = export_points_html(self._project)
        else:
            if not path.lower().endswith(".csv"):
                path += ".csv"
            content = export_points_csv(self._project)
        try:
            # utf-8-sig (BOM) for CSV - the task's own stated audience
            # is Excel, which otherwise mis-renders Polish diacritics in
            # a plain utf-8 CSV; HTML declares its own charset in the
            # <head> instead, no BOM needed there.
            encoding = "utf-8-sig" if not is_html else "utf-8"
            newline = "" if not is_html else None
            with open(path, "w", encoding=encoding, newline=newline) as f:
                f.write(content)
        except OSError as e:
            QMessageBox.warning(self, tr("export.dialog_title"), tr("export.error_write", error=str(e)))
            return
        self.statusBar().showMessage(tr("export.done", path=path), 5000)

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
            elif key == _TREE_ITEM_MODULES:
                self._open_modules()
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
            elif key == _TREE_ITEM_CONTROLLER:
                self._open_controller()
            elif key == _TREE_ITEM_MQTT:
                self._open_mqtt()
            elif key == _TREE_ITEM_SERVICE_NOTES:
                self._open_service_notes()
            elif key == _TREE_ITEM_HELP:
                self._open_help()
        elif kind == "inactive":
            self._open_inactive(key)

    # ------------------------------------------------------------------
    # Editor panels - construction and startup warm-up
    # ------------------------------------------------------------------

    def _ensure_synoptic_panel(self) -> bool:
        """Builds the Synoptic panel if it does not exist yet; returns
        True only if THIS call built it. The single place that knows
        how, called both by _open_screens() (a real click) and by
        preload_editors() (the startup warm-up), so the two can never
        drift - the page_ready connection in particular is exactly the
        kind of line that goes missing from a second copy."""
        if self._synoptic_panel is not None:
            return False
        from studio.shell.synoptic_panel import SynopticPanel
        self._synoptic_panel = SynopticPanel()
        self._synoptic_panel.page_ready.connect(self._sync_device_registry_with_synoptic)
        # Task "Studio osadza ekrany i logikę w projekt.epw": a project
        # opened before the page was up hands its screens over now.
        self._synoptic_panel.page_ready.connect(self._push_screens_to_synoptic)
        return True

    def _ensure_logic_panel(self) -> bool:
        """Same contract as _ensure_synoptic_panel() above."""
        if self._logic_panel is not None:
            return False
        from studio.shell.logic_panel import LogicPanel
        self._logic_panel = LogicPanel()
        return True

    def preload_editors(self, on_progress=None, timeout_ms: int = 15000) -> None:
        """Builds BOTH editor panels up front, at startup, instead of on
        the first click that happens to need one.

        Why: lazily built panels meant the first visit to Logika or
        Schemat synoptyczny paid the whole construction cost right
        then, in front of the user. Synoptic's is the visible one - it
        starts a loopback HTTP server and a QWebEngineView that needs
        0.35-1.05s to load, with its own loading page on screen
        meanwhile - and watching an editor assemble itself on arrival
        reads as the application reloading. Built here instead, while
        the splash is still up, both panels are simply there the first
        time they are clicked.

        The trade-off, stated plainly because it reverses an earlier
        deliberate decision (see SynopticPanel's own docstring): a
        session that never opens the screen editor now pays Chromium's
        startup and memory cost anyway. That is the price of the first
        click being instant.

        `on_progress`, if given, is called with a short human-readable
        string before each step - studio/main.py puts it on the splash.

        Never raises. SynopticPanel already turns its own build
        failures into an error page rather than an exception, and the
        wait below is bounded by `timeout_ms` AND ends the moment the
        page stops being pending, so neither a failed build nor a page
        that never loads can hang startup."""
        if on_progress is not None:
            on_progress(tr("splash.loading_logic"))
        self._ensure_logic_panel()

        if on_progress is not None:
            on_progress(tr("splash.loading_synoptic"))
        self._ensure_synoptic_panel()

        # A local QEventLoop is what actually lets the web view load
        # while the splash is still up: the view needs a running event
        # loop and QApplication.exec() has not started yet at this
        # point. Polling is-it-still-pending (rather than just waiting
        # on page_ready) is what makes a FAILED build cost nothing -
        # that path never emits page_ready and would otherwise sit here
        # for the full timeout.
        if self._synoptic_panel.is_page_pending():
            loop = QEventLoop()
            elapsed = QElapsedTimer()
            elapsed.start()
            poll = QTimer()
            poll.setInterval(50)
            poll.timeout.connect(
                lambda: (
                    loop.quit()
                    if not self._synoptic_panel.is_page_pending() or elapsed.hasExpired(timeout_ms)
                    else None
                )
            )
            poll.start()
            loop.exec()
            poll.stop()

        if on_progress is not None:
            on_progress(tr("splash.ready"))

    def _open_screens(self):
        if not self._ensure_synoptic_panel():
            # Already built - by an earlier visit or by preload_editors()
            # at startup - so page_ready has either already fired or
            # will fire on its own; run the sync directly here
            # (query_device_registry() no-ops safely if the page isn't
            # ready yet, same guard as every other bridge call).
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
        instead. Apparatuses go the same way (punkt 2 / luka 7: the
        two apparatus registries are one list - see project_panels.py's
        device_to_synoptic_dict()/device_from_synoptic_dict())."""
        if self._synoptic_panel is None:
            return

        def _after_pull(registry):
            from studio.shell.project_panels import (
                cards_from_synoptic_dicts, card_to_synoptic_dicts,
                device_from_synoptic_dict, device_to_synoptic_dict,
                location_from_synoptic_dict, location_to_synoptic_dict,
                sync_points_for_card,
            )
            project = self._project
            changed = False
            if registry:
                # A card id is unique again - one physical module, one
                # Card row, with its OWN several kinds when it has them
                # (see Card's own docstring: "karta ELA1 ma DI oraz AI").
                # Synoptic's own registry stays flat, one CardEntry per
                # kind (it never reads Modbus/location, so it has no
                # reason to merge them into one row - see
                # cards_from_synoptic_dicts()'s own docstring).
                # "already have this" now means "already have this KIND
                # under this id": pulling in Synoptic's AI entry for a
                # module Studio already has a DI row for must ADD the AI
                # kind to that existing row, not skip it as "id already
                # exists" and not create a second row for the same id.
                cards_by_id = {c.id: c for c in project.cards}
                for candidate in cards_from_synoptic_dicts(registry.get("cards", [])):
                    existing = cards_by_id.get(candidate.id)
                    if existing is None:
                        project.cards.append(candidate)
                        cards_by_id[candidate.id] = candidate
                        sync_points_for_card(project, candidate)
                        changed = True
                        continue
                    new_kinds = {
                        kind: channels for kind, channels in candidate.channel_kinds.items()
                        if kind not in existing.channel_kinds
                    }
                    if new_kinds:
                        existing.channel_kinds.update(new_kinds)
                        sync_points_for_card(project, existing)
                        changed = True
                existing_codes = {l.code for l in project.locations}
                for location_data in registry.get("locations", []):
                    if location_data.get("code") in existing_codes:
                        continue
                    location = location_from_synoptic_dict(location_data)
                    project.locations.append(location)
                    existing_codes.add(location.code)
                    changed = True
                existing_device_ids = {d.id for d in project.devices}
                for device_data in registry.get("devices", []):
                    if not isinstance(device_data, dict) or not device_data.get("id"):
                        continue
                    if device_data["id"] in existing_device_ids:
                        continue
                    project.devices.append(device_from_synoptic_dict(device_data))
                    existing_device_ids.add(device_data["id"])
                    changed = True
            if changed:
                project.touch()
                self._on_project_changed()
                if self._cards_panel is not None:
                    self._cards_panel.refresh()
                if self._point_registry_panel is not None:
                    self._point_registry_panel.refresh()
                if self._devices_panel is not None:
                    self._devices_panel.refresh()
            cards_out = [d for c in self._project.cards for d in card_to_synoptic_dicts(c)]
            locations_out = [location_to_synoptic_dict(l) for l in self._project.locations]
            devices_out = [device_to_synoptic_dict(d) for d in self._project.devices if d.id]
            self._synoptic_panel.push_device_registry(cards_out, locations_out, devices_out)

        self._synoptic_panel.query_device_registry(_after_pull)

    def _open_logic(self):
        self._ensure_logic_panel()
        # Task "jedno źródło listy kart": cheap even when nothing changed
        # (sync_cards_from_studio() own list-equality guard) - covers the
        # case this is the first-ever open (the constructor above never
        # saw the project's cards) and any card edit made while Logika
        # wasn't the active tab (_on_project_changed() also calls this,
        # but only while _logic_panel already exists).
        self._logic_panel.sync_cards_from_studio(self._project)
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

    def _open_modules(self):
        if self._modules_panel is None:
            from studio.shell.project_panels import ModuleCompositionPanel
            self._modules_panel = ModuleCompositionPanel(self)
        else:
            self._modules_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_MODULES, self._modules_panel, build_modules_toolbar, self._modules_panel
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_MODULES
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

    def _open_controller(self):
        if self._controller_panel is None:
            from studio.shell.project_panels import ControllerPanel
            self._controller_panel = ControllerPanel(self)
        self._show_aspect_container(
            _TREE_ITEM_CONTROLLER, self._controller_panel, build_controller_toolbar, self._controller_panel
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_CONTROLLER
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_mqtt(self):
        if self._mqtt_panel is None:
            from studio.shell.project_panels import MqttPanel
            self._mqtt_panel = MqttPanel(self)
        else:
            self._mqtt_panel.refresh()
        self._show_aspect_container(_TREE_ITEM_MQTT, self._mqtt_panel, build_mqtt_toolbar, self._mqtt_panel)
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_MQTT
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_service_notes(self):
        if self._service_notes_panel is None:
            from studio.shell.project_panels import ServiceNotesPanel
            self._service_notes_panel = ServiceNotesPanel(self)
        else:
            self._service_notes_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_SERVICE_NOTES, self._service_notes_panel, build_service_notes_toolbar, self._service_notes_panel
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_SERVICE_NOTES
        self._refresh_fixed_menu_state()
        self._refresh_shared_toolbar_state()

    def _open_help(self):
        if self._help_panel is None:
            from studio.shell.project_panels import HelpPanel
            self._help_panel = HelpPanel(self)
        else:
            self._help_panel.refresh()
        self._show_aspect_container(
            _TREE_ITEM_HELP, self._help_panel, build_help_toolbar, self._help_panel
        )
        self._status_editor.setText(tr("statusbar.no_editor"))
        self._active = _TREE_ITEM_HELP
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
        marker = "*" if (self._project.is_dirty or self._editors_dirty()) else ""
        self._status_project.setText(f"{name}{marker}")
        if self._project_info_panel is not None:
            self._project_info_panel.refresh()
        self._refresh_module_visibility()
        # Task "jedno źródło listy kart": keeps Logic Studio's own card
        # list current even while Logika isn't the active tab (e.g. a
        # card added while looking at Rejestr punktów) - cheap when
        # nothing actually changed, see sync_cards_from_studio()'s own
        # list-equality guard (etap 4: this must NOT rebuild Logika's
        # heavy panels on every unrelated edit).
        if self._logic_panel is not None:
            self._logic_panel.sync_cards_from_studio(self._project)

    def _refresh_module_visibility(self):
        """Task "fix/project-format-integrity" point 2.3 - "Moduł spoza
        składu NIE ISTNIEJE" (a module outside the composition doesn't
        exist - not merely disabled): a branch whose module isn't in
        self._project.modules is REMOVED from the tree outright (not
        just hidden/grayed - that convention is reserved for "this
        editor doesn't have it", a different situation from "this
        controller doesn't have this module at all"). Runs on every
        project change (called from _on_project_changed(), not just
        from the module-toggle panel) so a brand-new/just-opened project
        starts correct without a separate call site to remember.

        Always removes then re-adds the active items of each group in a
        FIXED, canonical order (not whatever order toggles happened in)
        - stable, predictable tree order regardless of click sequence.
        A group with zero visible children hides itself too, rather
        than showing an empty bold header."""
        modules = set(self._project.modules)

        def _sync_group(group, ordered):
            for _feature_id, item in ordered:
                parent = item.parent()
                if parent is not None:
                    parent.removeChild(item)
            visible_count = 0
            for feature_id, item in ordered:
                if feature_id in modules:
                    group.addChild(item)
                    visible_count += 1
            group.setHidden(visible_count == 0)

        _sync_group(self._group_alarm, [
            ("intrusion", self._item_zones),
            ("intrusion", self._item_lines),
        ])
        _sync_group(self._group_protection, [
            ("protection_settings", self._item_electrical_protection),
            ("protection_process", self._item_process_protection),
        ])

        # If the branch currently open just became invisible (its
        # module was removed from composition while the user was
        # looking at it), don't leave the content area showing an
        # orphaned panel with no matching tree selection - fall back to
        # "Skład urządzenia" itself, the obvious place to go fix that.
        active_item = {
            _TREE_ITEM_ZONES: self._item_zones,
            _TREE_ITEM_LINES: self._item_lines,
            _TREE_ITEM_ELECTRICAL_PROTECTION: self._item_electrical_protection,
            _TREE_ITEM_PROCESS_PROTECTION: self._item_process_protection,
        }.get(self._active)
        if active_item is not None and active_item.parent() is None:
            self.tree.setCurrentItem(self._item_modules)

    def _confirm_discard_project(self) -> bool:
        """True = caller may proceed (nothing unsaved, or the user chose
        Save/Discard). False = Cancel, caller must stop."""
        if not self._project.is_dirty and not self._editors_dirty():
            return True
        reply = QMessageBox.question(
            self, tr("project_info.unsaved_title"), tr("project_info.unsaved_text"),
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            return self._save_project()
        return reply == QMessageBox.StandardButton.Discard

    def _refresh_all_project_panels(self):
        """Every panel that reads project.* eagerly at construction
        time (unlike ModuleCompositionPanel/etc's own lazy _open_*())
        needs a real refresh() after a wholesale project swap
        (Nowy/Otwórz/Ostatnio otwarte) - factored out of _new_project()/
        _open_project() (task point 8.1's own _open_recent_project()
        needs the exact same sequence a third time) so the list can't
        drift between call sites the way three independent copies
        eventually would."""
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
        if self._mqtt_panel is not None:
            self._mqtt_panel.refresh()
        if self._service_notes_panel is not None:
            self._service_notes_panel.refresh()

    def _new_project(self):
        if not self._confirm_discard_project():
            return
        self._project = new_project(tr("project_info.default_name"))
        self._project_path = None
        self._push_editor_documents()
        self._on_project_changed()
        self._refresh_all_project_panels()

    def _open_project(self):
        if not self._confirm_discard_project():
            return
        path, _filter = QFileDialog.getOpenFileName(
            self, tr("project_info.open_dialog_title"),
            self.settings.value("project/last_dir", ""), "EPW Project (*.epw)",
        )
        if not path:
            return
        self._load_project_from_path(path)

    def _load_project_from_path(self, path: str):
        """Shared by _open_project() (file dialog) and
        _open_recent_project() (task 8.1, no dialog - the path is
        already known) - the ONE place that actually calls
        load_project() and reacts to it, so the two entry points can
        never drift on error handling/panel refresh/recent-list update."""
        try:
            project = load_project(path)
        except (ProjectFormatError, OSError) as exc:
            # A refusal carries a key + params (shared/project_format.py has
            # no text of its own) - translated here, English as the fallback.
            message = (tr("project_format." + exc.key, str(exc), **exc.params)
                       if isinstance(exc, ProjectFormatError) else str(exc))
            QMessageBox.critical(self, tr("project_info.open_failed_title"), message)
            self._remove_recent_project(path)  # a saved-but-now-broken/missing entry is worse than none
            return
        self._project = project
        self._project_path = path
        self.settings.setValue("project/last_dir", str(Path(path).parent))
        self._remember_recent_project(path)
        self._push_editor_documents()
        self._on_project_changed()
        self._refresh_all_project_panels()

    def _open_recent_project(self, path: str):
        if not self._confirm_discard_project():
            return
        self._load_project_from_path(path)

    # ------------------------------------------------------------------
    # Task point 8.1 - "Ostatnio otwarte projekty - menu Plik, pięć
    # pozycji, QSettings." A submenu (not five flat top-level entries) -
    # Plik already grew two new items this session (points 6/7); five
    # more flat entries there would make it the least scannable menu in
    # the whole app for no real gain over one more level.
    # ------------------------------------------------------------------
    _RECENT_PROJECTS_KEY = "project/recent_files"
    _RECENT_PROJECTS_MAX = 5

    def _recent_projects(self) -> list:
        return list(self.settings.value(self._RECENT_PROJECTS_KEY, []) or [])

    def _remember_recent_project(self, path: str):
        recent = [p for p in self._recent_projects() if p != path]
        recent.insert(0, path)
        del recent[self._RECENT_PROJECTS_MAX:]
        self.settings.setValue(self._RECENT_PROJECTS_KEY, recent)
        self._refresh_recent_projects_menu()

    def _remove_recent_project(self, path: str):
        recent = [p for p in self._recent_projects() if p != path]
        self.settings.setValue(self._RECENT_PROJECTS_KEY, recent)
        self._refresh_recent_projects_menu()

    def _refresh_recent_projects_menu(self):
        menu = getattr(self, "menu_recent_projects", None)
        if menu is None:
            return  # called once before build_fixed_menu() builds the menu itself - harmless no-op
        menu.clear()
        recent = self._recent_projects()
        if not recent:
            empty_action = menu.addAction(tr("menu.file.recent_projects_empty"))
            empty_action.setEnabled(False)
            return
        for path in recent:
            menu.addAction(path, lambda checked=False, p=path: self._open_recent_project(p))

    def _save_project(self) -> bool:
        if self._project_path is None:
            return self._save_project_as()
        if not self._collect_editor_documents():
            return False
        try:
            save_project(self._project, self._project_path)
        except OSError as exc:
            QMessageBox.critical(self, tr("project_info.save_failed_title"), str(exc))
            return False
        self._mark_editors_saved()
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
        if not self._collect_editor_documents():
            return False
        try:
            save_project(self._project, path)
        except OSError as exc:
            QMessageBox.critical(self, tr("project_info.save_failed_title"), str(exc))
            return False
        self._project_path = path
        self.settings.setValue("project/last_dir", str(Path(path).parent))
        self._remember_recent_project(path)
        self._mark_editors_saved()
        self._on_project_changed()
        return True

    # ------------------------------------------------------------------
    # Task "Studio osadza ekrany i logikę w projekt.epw" - user report:
    # "tworząc synoptykę w projekcie i zapisując projekt na głównym pasku,
    # synoptyka nie zapisuje się, podejrzewam że to samo jest z logiką -
    # dalej to traktowane jest jako osobne programy". The two editors'
    # documents are part of the project now (Project.screens / logic /
    # logic_runtime): Save reads them out of the live editors first, Open/
    # New hand them back in. SPEC: "Ekrany są W ŚRODKU pliku projektu".
    # ------------------------------------------------------------------

    _SYNOPTIC_DOCUMENT_TIMEOUT_MS = 4000

    def _collect_editor_documents(self) -> bool:
        """Pulls the current Logic and Synoptic documents into
        self._project before it is written. False = do NOT save: the
        Synoptic editor refused to produce its document (its own
        validation - the same refusal its Save As shows) and the user
        chose not to keep the previously saved screens instead. A page
        that is not up yet simply keeps the project's current `screens`
        (nothing was edited there to lose)."""
        if self._logic_panel is not None:
            self._project.logic = self._logic_panel.document()
            compiled = self._logic_panel.runtime_document()
            if compiled is not None:
                self._project.logic_runtime = compiled
            elif self._project.logic.get("blocks"):
                self.statusBar().showMessage(tr("project_info.logic_not_compiled"), 8000)

        panel = self._synoptic_panel
        if panel is None or not panel.is_page_ready():
            return True
        outcome = {"done": False, "document": None}
        loop = QEventLoop()

        def _received(document):
            outcome["done"] = True
            outcome["document"] = document
            loop.quit()

        panel.query_project_data(_received)
        QTimer.singleShot(self._SYNOPTIC_DOCUMENT_TIMEOUT_MS, loop.quit)
        loop.exec()
        if outcome["done"] and outcome["document"] is not None:
            self._project.screens = outcome["document"]
            return True
        reply = QMessageBox.question(
            self, tr("project_info.screens_unavailable_title"), tr("project_info.screens_unavailable_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _mark_editors_saved(self):
        name = self._project.metadata.name or tr("project_info.default_name")
        if self._logic_panel is not None:
            self._logic_panel.mark_saved()
        if self._synoptic_panel is not None:
            self._synoptic_panel.mark_saved(name)
        self._synoptic_dirty = False
        self._logic_dirty_seen = False

    def _push_editor_documents(self):
        """After a New/Open: the editors show what the project holds.
        A Logic document this build cannot open (an unknown block type,
        a newer schema) is reported, never silently turned into an empty
        canvas - and the project itself stays open."""
        if self._logic_panel is not None:
            try:
                self._logic_panel.load_document(self._project.logic)
            except Exception as exc:  # Project.deserialize() raises ValueError, but never trust one type
                QMessageBox.critical(self, tr("project_info.logic_load_failed_title"), str(exc))
        self._push_screens_to_synoptic()
        self._synoptic_dirty = False
        self._logic_dirty_seen = False

    def _push_screens_to_synoptic(self):
        if self._synoptic_panel is None or not self._synoptic_panel.is_page_ready():
            return  # page_ready (connected in _ensure_synoptic_panel) calls this again
        name = self._project.metadata.name or tr("project_info.default_name")
        self._synoptic_panel.load_project_data(self._project.screens, name)

    def _editors_dirty(self) -> bool:
        """Unsaved work in either editor counts as unsaved project work -
        it is part of the project file now."""
        if self._logic_panel is not None and self._logic_panel.is_dirty():
            return True
        return bool(self._synoptic_dirty)

    def _show_aspect_container(self, key, editor_widget, toolbar_builder, panel_for_builder):
        """Wraps `editor_widget` in an _AspectContainer (breadcrumb +
        contextual toolbar) and swaps it into the stack - built once per
        `key`, then REUSED on every later visit (etap-4 fix: building a
        fresh one every time meant re-parenting `editor_widget` into a
        new layout on every single visit, ~135ms of measured jank for
        Logika specifically - see _AspectContainer.__init__'s own
        comment for the measurement and the full reasoning). Only the
        toolbar's own aspect-specific actions are torn down and rebuilt
        on a re-visit (back to `_toolbar_baseline_action_count` - the
        breadcrumb + separator every container starts with, untouched) -
        this is what actually prevents toolbar_builder's QActions from
        piling up across repeated tree clicks, the concern the old
        "rebuild the whole container" approach was solving the hard way.
        `editor_widget` itself was already never rebuilt (still isn't) -
        SynopticPanel/LogicPanel stay exactly as expensive to construct
        as before, just no longer reparented on every re-visit."""
        container = self._aspect_containers.get(key)
        if container is None:
            container = _AspectContainer(tr(_BREADCRUMB_KEYS[key]), editor_widget)
            self.stack.addWidget(container)
            self._aspect_containers[key] = container
        else:
            for action in container.context_toolbar.actions()[container._toolbar_baseline_action_count:]:
                container.context_toolbar.removeAction(action)
                # menus.py's own _add() parents every QAction it creates
                # to the toolbar passed in (`QAction(label, container)`)
                # - removeAction() alone only detaches it from the
                # VISIBLE toolbar, it stays alive as container's child
                # otherwise. Since container itself is now long-lived
                # (reused, never deleted - the whole point of this fix),
                # that would accumulate one full generation of orphaned
                # QActions per re-visit instead of being cleaned up the
                # old "whole container gets deleted" way used to do for
                # free.
                action.deleteLater()
        toolbar_builder(container.context_toolbar, panel_for_builder, self)
        self.stack.setCurrentWidget(container)

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
