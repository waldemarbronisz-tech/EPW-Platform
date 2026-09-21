"""Studio's menu/toolbar content.

Task "Studio: wyostrzenie stylu — wspólny rdzeń" rewrote everything
below the fixed menu (build_fixed_menu() itself is untouched - this
correction is only about toolbar CONTENT, "ta korekta dotyczy WYŁĄCZNIE
zawartości pasków"). Two rules drive every contextual-toolbar builder
now:

  1. "Ta sama funkcja = ta sama ikona = to samo miejsce" - _build_core_
     group() below (Copy/Paste/Cut/Delete/Zoom In/Zoom Out/Grid/Snap -
     see this task's own chat report for the two-pass history: the
     first pass measured a strict "both editors have a clickable
     surface for it" core down to four (Copy/Paste/Delete/Snap); task
     "zestaw ikon Studio" re-read its own "przycisk WYSZARZONY, nie
     usunięty" rule as already anticipating editor-specific items shown
     always and grayed where inapplicable, and widened back to eight on
     that basis - Cut/Zoom In/Zoom Out/Grid are real in Logic, grayed
     (never removed) while Synoptic is active. Select All and Fit-to-
     window stayed OUT even under the wider reading: neither exists as
     an invokable action in EITHER editor, so unlike the four above they
     would be permanently dead in both contexts, not "grayed in one" -
     that fails "zero fasad" in a way the grey-not-remove rule doesn't
     cover) is built FIRST, identically, by every build_*_context_
     toolbar() call - same icons, same order, same QAction identity
     pattern, so the pixel position never shifts when the active aspect
     changes. A more pronounced gap (double separator + a fixed-width
     spacer) marks where the core ends and the active editor's own
     tools begin.
  2. "ikony 16x16, tekst wyłącznie w podpowiedzi" - every action built
     here now carries a real icon (studio/shell/icons.py - re-exports
     logic_studio.ui.icons.action_icon() where that already has the
     right glyph, draws new ones where nothing existed anywhere in the
     platform to reuse) and BOTH context toolbars are set to
     ToolButtonIconOnly - Qt shows the action's own text as a tooltip
     automatically once no icon-adjacent text is displayed, so every
     tr()'d label from before still reaches the user, just on hover
     instead of printed on a wide button.

Behavior is still never reimplemented, only re-labelled/re-iconed and
re-routed - uściślenie 2.2's hard rule from Stage 2 still holds (never
merge the two editors' own undo/dirty mechanisms):
  - a Logic Studio action triggers the SAME QAction its own (hidden)
    MainWindow already built.
  - a Synoptic action clicks the SAME DOM node its own (hidden)
    MenuBar.tsx/Toolbar.tsx already renders.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QCursor, QKeySequence
from PySide6.QtWidgets import QMenuBar, QToolBar, QWidget, QToolButton

from studio.shell import icons
from studio.shell.i18n import get_language, tr

# The Synoptic editor's work modes, in switcher order (synoptic/src/project/WorkModes.ts).
SYNOPTIC_WORK_MODES = ("SYMBOLS", "ROOMS", "CONNECTIONS", "ANNOTATIONS")


def _mirror(container, label, source_action, shortcut=None, icon_name=None):
    """New QAction, parented to and added into `container` (a QMenu or
    a QToolBar - both share addAction()), that LOOKS like a fresh,
    translated item but DOES exactly what `source_action` (a real
    QAction already living on Logic Studio's own, now-hidden,
    MainWindow) does - clicking ours calls source_action.trigger(), so
    the real handler runs exactly once, on the real object. Enabled/
    checked state is mirrored live via QAction.changed (Logic Studio's
    own code already keeps source_action's enabled/checked correct -
    this just listens, it never decides that state itself).

    `icon_name`, when given, looks up studio/shell/icons.py explicitly
    instead of copying source_action's own icon - most of Logic
    Studio's own actions never had an icon at all before this task
    (plain text in its own Edit/Project/Help menus), and giving all of
    them one now belongs in Studio's own icon module, not scattered
    edits across logic_studio/ui/main_window.py for every single one.

    Parented to `container` on purpose: main_window.py throws away and
    rebuilds each aspect's contextual toolbar on every tree click (the
    same reasoning Stage 2's own menus.py docstring already spelled
    out for the old per-context QMenuBar - everything built here needs
    to die with its container, not pile up across repeated clicks)."""
    action = QAction(label, container)
    if icon_name:
        action.setIcon(icons.icon(icon_name))
    else:
        icon = source_action.icon()
        if not icon.isNull():
            action.setIcon(icon)
    if shortcut:
        action.setShortcut(shortcut)
    if source_action.isCheckable():
        action.setCheckable(True)
        action.setChecked(source_action.isChecked())
    action.setEnabled(source_action.isEnabled())

    def _sync():
        action.setEnabled(source_action.isEnabled())
        if source_action.isCheckable():
            action.setChecked(source_action.isChecked())

    source_action.changed.connect(_sync)
    action.triggered.connect(source_action.trigger)
    container.addAction(action)
    return action


def _clicker(panel, text, exact=False):
    """Returns a zero-arg callable for QAction.triggered - clicks the
    matching Synoptic dropdown item by text every time it's called."""
    return lambda: panel.trigger_menu_item(text, exact=exact)


def _toolbar_clicker(panel, title, exact=True):
    """Same idea as _clicker(), for Synoptic's own toolbar (Toolbar.tsx)
    instead of its menu - matched by `title` attribute, not text
    content (SynopticPanel.trigger_toolbar_button())."""
    return lambda: panel.trigger_toolbar_button(title, exact=exact)


def _add(container, label, handler, icon_name=None):
    action = QAction(label, container)
    if icon_name:
        action.setIcon(icons.icon(icon_name))
    action.triggered.connect(handler)
    container.addAction(action)
    return action


def _add_exit(studio_window, file_menu):
    """One real Studio-level Exit, shared by both contexts - NOT a
    mirror of either editor's own act_exit/"Exit" item (see Stage 2's
    own reasoning: MainWindow/App are embedded child widgets here, not
    windows, so their own exit would do nothing meaningful)."""
    exit_action = QAction(tr("menu.file.exit"), file_menu)
    exit_action.triggered.connect(studio_window.close)
    file_menu.addAction(exit_action)


def build_fixed_menu(menubar: QMenuBar, studio_window):
    """The APP-level menu - Plik/Widok/Ustawienia/Pomoc, built exactly
    once. Untouched by this task's own correction (menu content, not
    toolbar content). Every action here routes to whichever aspect is
    currently active via studio_window's own methods (same dispatch
    pattern as its shared toolbar); studio_window keeps the QAction
    references (act_menu_*/act_view_*) so it can update enabled/checked
    state without ever touching this menu's STRUCTURE again."""
    file_menu = menubar.addMenu(tr("menu.titles.file"))
    studio_window.act_menu_new = _add(file_menu, tr("menu.file.new"), studio_window._shared_new)
    studio_window.act_menu_open = _add(file_menu, tr("menu.file.open"), studio_window._shared_open)
    studio_window.act_menu_save = _add(file_menu, tr("menu.file.save"), studio_window._shared_save)
    studio_window.act_menu_save_as = _add(file_menu, tr("menu.file.save_as"), studio_window._shared_save_as)
    # User report ("stwórz kreator urządzenia gdzie krok po kroku mówi
    # co gdzie dodawać") - the guided way to build a project's own
    # composition: info -> modules -> locations -> cards, then a summary
    # naming where the rest (points, apparatus, screens, logic) lives.
    # The OBJECT (user, 2026-09-18, Etango-style): one .epwsite listing
    # the devices' projects - new/open/save-all, add/remove a device.
    file_menu.addSeparator()
    studio_window.act_menu_new_site = _add(file_menu, tr("menu.file.new_site"), studio_window._new_site)
    studio_window.act_menu_open_site = _add(file_menu, tr("menu.file.open_site"), studio_window._open_site)
    studio_window.act_menu_save_site = _add(file_menu, tr("menu.file.save_site"), studio_window._save_site)
    file_menu.addSeparator()
    studio_window.act_menu_add_device = _add(file_menu, tr("menu.file.add_device"), studio_window._add_new_device)
    studio_window.act_menu_add_existing_device = _add(
        file_menu, tr("menu.file.add_existing_device"), studio_window._add_existing_device)
    studio_window.act_menu_remove_device = _add(
        file_menu, tr("menu.file.remove_device"), studio_window._remove_device)
    file_menu.addSeparator()
    studio_window.act_menu_device_wizard = _add(
        file_menu, tr("menu.file.device_wizard"), studio_window._run_device_wizard, icon_name="wizard"
    )
    file_menu.addSeparator()
    # Task point 8.1 - "Ostatnio otwarte projekty" - projekt.epw, the
    # same file act_menu_open/save above now operate on (user report:
    # the top bar is the PROJECT's - see main_window._build_shared_
    # toolbar). This submenu's own entries call _open_recent_project()
    # directly, no dialog. Built once, refreshed by content (menu.clear()
    # + rebuild), same "shape never changes, content does" split every
    # other fixed-menu item in this function already follows.
    studio_window.menu_recent_projects = file_menu.addMenu(tr("menu.file.recent_projects"))
    studio_window._refresh_recent_projects_menu()
    file_menu.addSeparator()
    # Task "fix/project-format-integrity" point 6 - "Sprawdź projekt":
    # not tied to any one aspect (unlike New/Open/Save above), so no
    # act_* enabled-state juggling needed - it operates on
    # studio_window._project directly, always available.
    studio_window.act_menu_check_project = _add(
        file_menu, tr("menu.file.check_project"), studio_window._check_project
    )
    # Task point 7 - "Eksportuj listę punktów" - same "not tied to any
    # one aspect" reasoning as "Sprawdź projekt" just above.
    studio_window.act_menu_export_points = _add(
        file_menu, tr("menu.file.export_points"), studio_window._export_point_list
    )
    file_menu.addSeparator()
    _add_exit(studio_window, file_menu)

    view_menu = menubar.addMenu(tr("menu.titles.view"))
    studio_window.act_view_zoom_in = _add(view_menu, tr("menu.view.zoom_in"), studio_window._view_zoom_in)
    studio_window.act_view_zoom_out = _add(view_menu, tr("menu.view.zoom_out"), studio_window._view_zoom_out)
    studio_window.act_view_reset_zoom = _add(view_menu, tr("menu.view.reset_zoom"), studio_window._view_reset_zoom)
    view_menu.addSeparator()
    studio_window.act_view_grid = _add(view_menu, tr("menu.view.grid"), studio_window._view_toggle_grid)
    studio_window.act_view_snap = _add(view_menu, tr("menu.view.snap"), studio_window._view_toggle_snap)

    settings_menu = menubar.addMenu(tr("menu.titles.settings"))
    lang_menu = settings_menu.addMenu(tr("menu.settings.language"))
    lang_group = QActionGroup(studio_window)
    lang_group.setExclusive(True)
    studio_window.act_lang_pl = QAction(tr("menu.settings.language_pl"), lang_menu)
    studio_window.act_lang_pl.setCheckable(True)
    studio_window.act_lang_en = QAction(tr("menu.settings.language_en"), lang_menu)
    studio_window.act_lang_en.setCheckable(True)
    current = get_language()
    studio_window.act_lang_pl.setChecked(current == "pl")
    studio_window.act_lang_en.setChecked(current == "en")
    lang_group.addAction(studio_window.act_lang_pl)
    lang_group.addAction(studio_window.act_lang_en)
    lang_menu.addAction(studio_window.act_lang_pl)
    lang_menu.addAction(studio_window.act_lang_en)
    studio_window.act_lang_pl.triggered.connect(lambda: studio_window._set_language("pl"))
    studio_window.act_lang_en.triggered.connect(lambda: studio_window._set_language("en"))

    help_menu = menubar.addMenu(tr("menu.titles.help"))
    studio_window.act_menu_help_topics = _add(help_menu, tr("menu.help.topics"), studio_window._help_topics)
    help_menu.addSeparator()
    _add(help_menu, tr("menu.help.about_studio"), studio_window._show_about_studio)


# ----------------------------------------------------------------------
# The shared core - two measurement passes, both recorded here so the
# reason each item is (or isn't) in this list stays next to the list:
#
#   Copy/Paste/Delete/Snap to grid - both editors have a real clickable
#             surface for each (Synoptic: menu + its own toolbar button;
#             Logic: act_copy/act_paste/act_delete/act_snap). Core since
#             the first pass.
#   Cut     - Logic has it (act_cut); Synoptic's own Edit menu has no
#             Cut at all. First pass measured this OUT to Logic's own
#             section. Second pass (task "zestaw ikon Studio") put it
#             back IN the core, grayed while Synoptic is active - the
#             existing "przycisk WYSZARZONY, nie usunięty" rule already
#             anticipates exactly this: an editor-specific function
#             shown in a fixed, shared place, disabled where it doesn't
#             apply, not hidden.
#   Powiększ/Pomniejsz (Zoom In/Out), Siatka (grid visibility) - same
#             story as Cut: real only in Logic (Synoptic has no zoom UI
#             beyond the mouse wheel, and exposes Snap to Grid but never
#             a separate grid-visibility toggle), first pass measured
#             them out, second pass put them back in the core grayed for
#             Synoptic.
#   Zaznacz wszystko (Select All) - stays OUT under BOTH passes, on
#             different grounds than Cut/Zoom/Grid: Logic Studio has no
#             select-all mechanism at all (no menu item, no Ctrl+A
#             binding anywhere), and Synoptic's own store.selectAll()
#             is reachable ONLY via an undocumented Ctrl+A keydown in
#             Canvas.tsx - no menu item, no toolbar button, nothing
#             trigger_menu_item()/trigger_toolbar_button() could ever
#             click. Present in NEITHER editor as an actual UI surface,
#             so grey-not-remove doesn't apply - there is no editor left
#             for it to be real in. Excluded from the core and left
#             unexposed in Synoptic's own section too (GRANICE: no new
#             standing UI element invented in Synoptic's own source).
#   Dopasuj do okna (Fit to window) - stays OUT on the same grounds:
#             NEITHER editor has it. Logic's "Reset Zoom" (act_reset_
#             zoom) is view.resetTransform() - zoom back to 100%, not
#             "fit all content in view" - a different function under a
#             similar-sounding name, kept in Logic's own section under
#             its own accurate name rather than relabeled as this.
# ----------------------------------------------------------------------

def _build_core_group(toolbar, studio_window):
    """Built identically on every call, by both build_*_context_toolbar
    functions below, before anything editor-specific - the actual
    mechanism behind "IDENTYCZNA ikona/kolejność/pozycja od lewej
    krawędzi". Eight items, grouped Copy/Paste/Cut/Delete |
    Zoom In/Zoom Out | Grid/Snap, each group separated by a plain
    separator; a MORE pronounced gap (separator + fixed-width spacer +
    separator) marks the end of the core, before the active editor's
    own tools start. Routing dispatches on studio_window._active as
    usual; Cut/Zoom In/Zoom Out/Grid reuse the same dispatch methods the
    fixed Widok menu and Logic's own toolbar already call
    (_view_zoom_in/_view_zoom_out/_view_toggle_grid), not duplicated
    here - only _core_cut is new (mirrors _core_copy/_core_paste/
    _core_delete's own pattern). Enabled state is refreshed by
    main_window.py's existing state-poll timer
    (_refresh_shared_toolbar_state)."""
    studio_window.act_core_copy = _add(toolbar, tr("menu.edit.copy"), studio_window._core_copy, icon_name="copy")
    studio_window.act_core_paste = _add(toolbar, tr("menu.edit.paste"), studio_window._core_paste, icon_name="paste")
    studio_window.act_core_cut = _add(toolbar, tr("menu.edit.cut"), studio_window._core_cut, icon_name="cut")
    studio_window.act_core_delete = _add(toolbar, tr("menu.edit.delete"), studio_window._core_delete, icon_name="delete")
    toolbar.addSeparator()
    studio_window.act_core_zoom_in = _add(toolbar, tr("menu.view.zoom_in"), studio_window._view_zoom_in, icon_name="zoom_in")
    studio_window.act_core_zoom_out = _add(toolbar, tr("menu.view.zoom_out"), studio_window._view_zoom_out, icon_name="zoom_out")
    toolbar.addSeparator()
    studio_window.act_core_grid = _add(toolbar, tr("menu.view.grid"), studio_window._view_toggle_grid, icon_name="grid")
    studio_window.act_core_snap = _add(toolbar, tr("menu.view.snap"), studio_window._view_toggle_snap, icon_name="snap")
    toolbar.addSeparator()
    _core_end_spacer = QWidget(toolbar)
    _core_end_spacer.setFixedWidth(6)
    toolbar.addWidget(_core_end_spacer)
    toolbar.addSeparator()


def build_logic_context_toolbar(toolbar, logic_panel, studio_window):
    """The contextual zone's tools while LOGIKA is the active aspect:
    the shared core first, then everything Logic Studio's own (now-
    hidden) menu AND its own (now-hidden) toolbar offered beyond File
    (fixed top chrome) and Copy/Paste/Delete/Snap (now the core,
    immediately above - not repeated here)."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _build_core_group(toolbar, studio_window)
    mw = logic_panel.main_window()

    # The LOGIC DIAGRAM's own document (.epwlogic) - its lifecycle moved
    # here from the fixed top toolbar, which is the project's
    # (projekt.epw) now on every branch (user report, see main_window.
    # _build_shared_toolbar). Labelled as the diagram's, not "Save", so
    # the two never read as the same button.
    _mirror(toolbar, tr("toolbar.logic_new"), mw.act_new, icon_name="new")
    _mirror(toolbar, tr("toolbar.logic_open"), mw.act_open, icon_name="open")
    _mirror(toolbar, tr("toolbar.logic_save"), mw.act_save, icon_name="save")
    _mirror(toolbar, tr("toolbar.logic_save_as"), mw.act_save_as, icon_name="save_as")
    toolbar.addSeparator()

    # Zoom In/Zoom Out/Grid/Cut now live in the core group above (real
    # here, grayed in Synoptic) - not repeated here to avoid the same
    # function appearing twice in one toolbar. Reset Zoom stays here:
    # it measured out of the core as its own, un-shared function (see
    # _build_core_group's own docstring).
    _mirror(toolbar, tr("menu.view.reset_zoom"), mw.act_reset_zoom, icon_name="reset_zoom")
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.file.compare_saved"), mw.act_compare_saved, icon_name="compare")
    _mirror(toolbar, tr("menu.file.compare_files"), mw.act_compare_files, icon_name="compare")
    toolbar.addSeparator()

    def _show_align_popup():
        mw._rebuild_align_menu()
        mw.align_menu.popup(QCursor.pos())

    _add(toolbar, tr("menu.edit.align"), _show_align_popup, icon_name="align_popup")
    _mirror(toolbar, tr("menu.edit.disable_selected"), mw.act_disable_selected, icon_name="disable_selected")
    _mirror(toolbar, tr("menu.edit.enable_selected"), mw.act_enable_selected, icon_name="enable_selected")
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.view.toolbar_icons"), mw.act_toolbar_icons, icon_name="toolbar_style_icons")
    _mirror(toolbar, tr("menu.view.toolbar_icons_text"), mw.act_toolbar_icons_text, icon_name="toolbar_style_icons_text")
    _mirror(toolbar, tr("menu.view.toolbar_text"), mw.act_toolbar_text, icon_name="toolbar_style_text")
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.project.settings"), mw.act_project_settings, icon_name="settings")
    _mirror(toolbar, tr("menu.project.export_signals"), mw.act_export_signals, icon_name="export")
    _mirror(toolbar, tr("menu.project.export_pdf"), mw.act_export_pdf, icon_name="export")
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.logic.compile"), mw.act_compile, icon_name="compile")
    _mirror(toolbar, tr("menu.logic.export_runtime"), mw.act_export_runtime, icon_name="export")
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.simulation.start"), mw.act_sim_start, icon_name="sim_start")
    _mirror(toolbar, tr("menu.simulation.pause"), mw.act_sim_pause, icon_name="sim_pause")
    _mirror(toolbar, tr("menu.simulation.stop"), mw.act_sim_stop, icon_name="sim_stop")
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.help.catalog"), mw.act_help_catalog, icon_name="help_catalog")
    _mirror(toolbar, tr("menu.help.shortcuts"), mw.act_help_shortcuts, icon_name="help_shortcuts")
    _mirror(toolbar, tr("menu.help.export_catalog"), mw.act_export_block_catalog, icon_name="export")
    _mirror(toolbar, tr("menu.help.about"), mw.act_about, icon_name="about")
    toolbar.addSeparator()

    _add(toolbar, tr("canvas.background_color"), studio_window._choose_canvas_background, icon_name="background_color")


# ----------------------------------------------------------------------
# Task "edytor DI/DO/AI" - the three new project panels' own contextual
# toolbars. Deliberately NOT built on _build_core_group() - Copy/Paste/
# Cut/Zoom/Grid/Snap describe drawing-canvas editing, not a data table;
# forcing that shape onto a table editor would be a facade (buttons that
# do nothing here), not consistency.
# ----------------------------------------------------------------------

def build_modules_toolbar(toolbar, _panel, _studio_window):
    """"Skład urządzenia" - a FIXED, real list mirrored from runtime's
    own feature_config.py (see project_panels.MODULE_CATALOG's own
    docstring) - no add/remove, same "the catalog is not a choice"
    stance build_electrical_protection_toolbar() already has for its
    own fixed ANSI function catalog."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)


def build_project_info_toolbar(toolbar, _panel, studio_window):
    """The project lifecycle (Nowy/Otwórz/Zapisz/Zapisz jako projekt)
    used to live HERE and only here - user report ("nie działa pasek na
    górze gdzie wpisujemy projekt zapis odczyt"): it is the fixed top
    toolbar's now, on every branch (main_window._build_shared_toolbar),
    so this toolbar no longer repeats it. What this branch keeps is the
    one thing that starts here: the guided device wizard."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("menu.file.device_wizard"), studio_window._run_device_wizard, icon_name="wizard")


def build_cards_toolbar(toolbar, panel, _studio_window):
    """"Skład urządzenia" - Dodaj/Usuń kartę (ELA/ADA module), table-row
    actions, not document actions, hence the new add_row/remove_row
    icons instead of reusing Copy/Paste/Delete's own (those mean
    something else: acting on a drawing-canvas SELECTION, not a table
    row)."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("cards.add_card"), panel.add_card, icon_name="add_row")
    _add(toolbar, tr("cards.remove_card"), panel.remove_selected_card, icon_name="remove_row")


def build_locations_toolbar(toolbar, panel, _studio_window):
    """"Lokalizacje" - its own toolbar now (task "ostatnie dwa działy"),
    Locations having moved out of CardsPanel into its own tree branch."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("cards.add_location"), panel.add_location, icon_name="add_row")
    _add(toolbar, tr("cards.remove_location"), panel.remove_selected_location, icon_name="remove_row")


def build_devices_toolbar(toolbar, panel, _studio_window):
    """SPEC's "Aparaty" - Dodaj/Usuń aparat, same add_row/remove_row
    icons as build_cards_toolbar (table-row actions, not Copy/Paste/
    Delete's canvas-selection meaning)."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("devices.add_device"), panel.add_device, icon_name="add_row")
    _add(toolbar, tr("devices.remove_device"), panel.remove_selected_device, icon_name="remove_row")


def build_zones_toolbar(toolbar, panel, _studio_window):
    """SPEC's "Alarmówka" - Dodaj/Usuń strefę."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("zones.add_zone"), panel.add_zone, icon_name="add_row")
    _add(toolbar, tr("zones.remove_zone"), panel.remove_selected_zone, icon_name="remove_row")


def build_lines_toolbar(toolbar, panel, _studio_window):
    """SPEC's "Alarmówka" - Dodaj/Usuń linię dozorową."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("lines.add_line"), panel.add_line, icon_name="add_row")
    _add(toolbar, tr("lines.remove_line"), panel.remove_selected_line, icon_name="remove_row")


def build_intrusion_users_toolbar(toolbar, panel, _studio_window):
    """"Alarmówka: stopnie dostępu" - add/remove a person. Their CODE is
    set on the controller, never here (see IntrusionUsersPanel)."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("intrusion.btn_add_user"), panel.add_user, icon_name="add_row")
    _add(toolbar, tr("intrusion.btn_remove_user"), panel.remove_selected_user, icon_name="remove_row")


def build_electrical_protection_toolbar(toolbar, _panel, _studio_window):
    """No add/remove - the catalog (which functions/stages exist) is
    fixed (ADA01 hardware), same "no add/remove" stance
    build_point_registry_toolbar() already has for the same reason."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)


def build_process_protection_toolbar(toolbar, panel, _studio_window):
    """Dodaj/Usuń zabezpieczenie procesowe - a dynamic, user-created
    list, unlike Electrical's fixed catalog."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("process.add_protection"), panel.add_protection, icon_name="add_row")
    _add(toolbar, tr("process.remove_protection"), panel.remove_selected_protection, icon_name="remove_row")


def build_controller_toolbar(toolbar, _panel, _studio_window):
    """No table here, nothing to add/remove - the panel's own buttons
    (Testuj połączenie/Wyślij/Zgraj/Pobierz podgląd) are enough on their
    own, same "empty toolbar beyond the breadcrumb" as
    build_point_registry_toolbar()."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)


def build_protection_tests_toolbar(toolbar, panel, _studio_window):
    """The panel's own buttons do the work; the toolbar repeats the two
    that matter while a table has the focus."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("protection_tests.run"), panel.run_selected_test, icon_name="sim_start")
    _add(toolbar, tr("protection_tests.export_csv"), panel.export_csv, icon_name="export")


def build_mqtt_toolbar(toolbar, panel, _studio_window):
    """The two tables' add/remove (incoming mappings, per-tag
    deadbands) - the same shape as every other list panel's toolbar."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("mqtt.add_link"), panel.add_link, icon_name="add_row")
    _add(toolbar, tr("mqtt.remove_link"), panel.remove_selected_link, icon_name="remove_row")


def build_signals_toolbar(toolbar, panel, _studio_window):
    """Add/remove act on the INTERNAL tab - the system tab is a platform
    contract and has nothing to add to (signals_panel.py's own note)."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("signals.add"), panel.internal_tab.add_signal, icon_name="add_row")
    _add(toolbar, tr("signals.delete"), panel.internal_tab.delete_selected, icon_name="remove_row")


def build_object_links_toolbar(toolbar, panel, _studio_window):
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("object_links.add"), panel.add_link, icon_name="add_row")
    _add(toolbar, tr("object_links.remove"), panel.remove_selected_link, icon_name="remove_row")


def build_service_notes_toolbar(toolbar, _panel, _studio_window):
    """Read-only: notes are written at the cabinet, never here."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)


def build_help_toolbar(toolbar, _panel, _studio_window):
    """"Dział help pełny" - the panel's own topic list is the
    navigation; nothing to add here beyond the breadcrumb."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)


def build_point_registry_toolbar(toolbar, panel, studio_window):
    """No add/remove here on purpose - SPEC_PROJEKT_EPW.md's own rule:
    "Karty rodzą punkty [...] Nie wpisujesz ich ręcznie" - a point's
    only entry points are a card being added/resized (CardsPanel) or
    removed. The panel's own card filter combo lives in the widget
    itself, not the toolbar.

    Task "jedno źródło listy kart" 3.4: the one real action this
    toolbar DOES need - bulk-setting the location of every selected row
    (PointRegistryPanel.set_location_for_selected(), a no-op with
    nothing selected). No dedicated icon exists for "location" in
    icons.py - "settings" is the closest existing one ("configure a
    property of the selection"), same reuse-over-invent reasoning
    already applied elsewhere in this module rather than adding a new
    icon asset for one button."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _add(toolbar, tr("points.set_location_for_selected"), panel.set_location_for_selected, icon_name="settings")
    toolbar.addSeparator()
    # SPEC "Wymuszanie stanów": force mode is entered deliberately here,
    # a force is set from a row's own menu, and everything is dropped
    # with one button.
    studio_window.act_force_mode = _add(toolbar, tr("points.force_mode"),
                                        lambda checked=False: studio_window.set_force_mode(bool(checked)),
                                        icon_name="lock")
    studio_window.act_force_mode.setCheckable(True)
    studio_window.act_force_mode.setChecked(studio_window.force_mode_enabled())
    _add(toolbar, tr("points.release_all_forces"), studio_window.release_all_forces, icon_name="remove_row")


def build_synoptic_context_toolbar(toolbar, synoptic_panel, studio_window):
    """The contextual zone's tools while EKRANY/Schemat synoptyczny is
    the active aspect: the shared core first, then everything
    Synoptic's own (now-hidden) menu AND its own (now-hidden) drawing
    toolbar offered beyond File/Undo/Redo (fixed top chrome) and
    Copy/Paste/Delete/Snap (now the core, immediately above)."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _build_core_group(toolbar, studio_window)

    # The SCREEN's own document (.epwsyn) - its lifecycle moved here from
    # the fixed top toolbar, which is the project's (projekt.epw) now on
    # every branch (user report, see main_window._build_shared_toolbar).
    # Same trigger_menu_item() route the top bar used to take.
    _add(toolbar, tr("toolbar.synoptic_new"), lambda: synoptic_panel.trigger_menu_item("New", exact=True),
         icon_name="new")
    _add(toolbar, tr("toolbar.synoptic_open"), lambda: synoptic_panel.trigger_menu_item("Open"), icon_name="open")
    _add(toolbar, tr("toolbar.synoptic_save"), lambda: synoptic_panel.trigger_menu_item("Save", exact=True),
         icon_name="save")
    _add(toolbar, tr("toolbar.synoptic_save_as"), lambda: synoptic_panel.trigger_menu_item("Save As"),
         icon_name="save_as")
    toolbar.addSeparator()
    # SPEC "Widok główny": the main view screen full screen, as the panel
    # shows it, operable (F11 too; Esc in the editor returns).
    _add(toolbar, tr("toolbar.synoptic_panel_preview"), studio_window.toggle_panel_preview, icon_name="scada_preview")
    toolbar.addSeparator()

    # feat/synoptic-modes: the work-mode switch - SYMBOLS / ROOMS /
    # CONNECTIONS / ANNOTATIONS - as four named, mutually exclusive
    # buttons (Ctrl+1..4), then the tools of the current mode, each group
    # between separators. A mode decides what a click on the canvas can
    # reach, so only its own tools are shown; the window ticks the active
    # mode and shows its group from Synoptic's state bridge on every poll
    # (main_window._apply_synoptic_mode_checks).
    command = lambda cmd: (lambda: synoptic_panel.trigger_command(cmd))
    modes = {}
    mode_group = QActionGroup(toolbar)
    mode_group.setExclusive(True)
    for index, mode in enumerate(SYNOPTIC_WORK_MODES):
        name = tr(f"canvas.mode_{mode.lower()}")
        shortcut = f"Ctrl+{index + 1}"
        action = QAction(name, toolbar)
        action.setCheckable(True)
        action.setShortcut(QKeySequence(shortcut))
        action.setToolTip(tr("canvas.mode_tooltip", name=name, shortcut=shortcut))
        action.setChecked(mode == "SYMBOLS")
        action.triggered.connect(command(f"mode:{mode}"))
        mode_group.addAction(action)
        button = QToolButton(toolbar)
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setObjectName(f"SynopticMode_{mode}")
        toolbar.addWidget(button)
        modes[f"mode:{mode}"] = action
    toolbar.addSeparator()

    groups = {mode: [] for mode in SYNOPTIC_WORK_MODES}

    def tool(mode, key, label_key, cmd, icon):
        action = _add(toolbar, tr(label_key), command(cmd), icon_name=icon)
        groups[mode].append(action)
        if key:
            action.setCheckable(True)
            modes[key] = action
        return action

    def separator(mode):
        groups[mode].append(toolbar.addSeparator())

    # SYMBOLS - arranging what is placed.
    tool("SYMBOLS", None, "canvas.bring_front", "bring_front", "bring_front")
    tool("SYMBOLS", None, "canvas.send_back", "send_back", "send_back")
    separator("SYMBOLS")
    tool("SYMBOLS", None, "canvas.lock", "lock", "lock")
    tool("SYMBOLS", None, "canvas.unlock", "unlock", "unlock")
    separator("SYMBOLS")
    tool("SYMBOLS", None, "canvas.rotate_left", "rotate_left", "rotate_left")
    tool("SYMBOLS", None, "canvas.rotate_right", "rotate_right", "rotate_right")
    separator("SYMBOLS")

    # ROOMS - walls and rooms, then frames and building outlines.
    tool("ROOMS", "wall", "canvas.draw_wall", "draw_wall", "draw_wall")
    tool("ROOMS", "room", "canvas.draw_room", "draw_room", "draw_room")
    separator("ROOMS")
    tool("ROOMS", "frame", "canvas.draw_frame", "draw_frame", "draw_frame")
    tool("ROOMS", "building", "canvas.draw_building", "draw_building", "draw_building")
    separator("ROOMS")
    # Turning something is part of drawing a room too (owner,
    # 2026-09-20) - the same two commands the Symbols group sends, so
    # the canvas needs nothing new to understand them.
    tool("ROOMS", None, "canvas.rotate_left", "rotate_left", "rotate_left")
    tool("ROOMS", None, "canvas.rotate_right", "rotate_right", "rotate_right")
    separator("ROOMS")

    # CONNECTIONS - the wire tool, medium, wire style, routing.
    tool("CONNECTIONS", "wire", "canvas.draw_wire", "draw_wire", "draw_wire")
    reroute = _add(toolbar, tr("menu.edit.reroute"), _clicker(synoptic_panel, "Reroute"), icon_name="reroute")
    groups["CONNECTIONS"].append(reroute)
    separator("CONNECTIONS")
    tool("CONNECTIONS", "medium:ELECTRICAL", "canvas.medium_electrical", "medium:ELECTRICAL", "medium_electrical")
    tool("CONNECTIONS", "medium:WATER", "canvas.medium_water", "medium:WATER", "medium_water")
    tool("CONNECTIONS", "medium:VENTILATION", "canvas.medium_ventilation", "medium:VENTILATION", "medium_ventilation")
    separator("CONNECTIONS")
    tool("CONNECTIONS", "style:NORMAL", "canvas.wire_style_normal", "style:NORMAL", "wire_style_normal")
    tool("CONNECTIONS", "style:BUS", "canvas.wire_style_bus", "style:BUS", "wire_style_bus")
    separator("CONNECTIONS")
    tool("CONNECTIONS", "routing:STRAIGHT", "canvas.routing_direct", "routing:STRAIGHT", "routing_direct")
    tool("CONNECTIONS", "routing:AVOID", "canvas.routing_avoid", "routing:AVOID", "routing_avoid")
    separator("CONNECTIONS")

    # ANNOTATIONS - text boxes (their formatting is the row under the bar).
    tool("ANNOTATIONS", None, "canvas.text_box", "text_box", "text_box")
    separator("ANNOTATIONS")

    for mode, actions in groups.items():
        for action in actions:
            action.setVisible(mode == "SYMBOLS")
    studio_window.synoptic_mode_actions = modes
    studio_window.synoptic_mode_groups = groups

    _add(toolbar, tr("menu.devices.project_registers"), _clicker(synoptic_panel, "Project Registers"), icon_name="project_registers")
    _add(toolbar, tr("menu.devices.device_list"), _clicker(synoptic_panel, "Device List"), icon_name="device_list")
    toolbar.addSeparator()

    _add(toolbar, tr("canvas.background_color"), studio_window._choose_canvas_background, icon_name="background_color")
