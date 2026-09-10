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
from PySide6.QtGui import QAction, QActionGroup, QCursor
from PySide6.QtWidgets import QMenuBar, QToolBar, QWidget

from studio.shell import icons
from studio.shell.i18n import get_language, tr


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


def build_synoptic_context_toolbar(toolbar, synoptic_panel, studio_window):
    """The contextual zone's tools while EKRANY/Schemat synoptyczny is
    the active aspect: the shared core first, then everything
    Synoptic's own (now-hidden) menu AND its own (now-hidden) drawing
    toolbar offered beyond File/Undo/Redo (fixed top chrome) and
    Copy/Paste/Delete/Snap (now the core, immediately above)."""
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    _build_core_group(toolbar, studio_window)

    _add(toolbar, tr("menu.edit.reroute"), _clicker(synoptic_panel, "Reroute"), icon_name="reroute")
    toolbar.addSeparator()

    _add(toolbar, tr("canvas.draw_wire"), _toolbar_clicker(synoptic_panel, "Draw Wire", exact=False), icon_name="draw_wire")
    _add(toolbar, tr("canvas.draw_frame"), _toolbar_clicker(synoptic_panel, "Draw Frame", exact=False), icon_name="draw_frame")
    _add(toolbar, tr("canvas.draw_building"), _toolbar_clicker(synoptic_panel, "Draw Building", exact=False), icon_name="draw_building")
    toolbar.addSeparator()

    _add(toolbar, tr("canvas.medium_electrical"), _toolbar_clicker(synoptic_panel, "Prad"), icon_name="medium_electrical")
    _add(toolbar, tr("canvas.medium_water"), _toolbar_clicker(synoptic_panel, "Woda"), icon_name="medium_water")
    _add(toolbar, tr("canvas.medium_ventilation"), _toolbar_clicker(synoptic_panel, "Wentylacja"), icon_name="medium_ventilation")
    toolbar.addSeparator()

    _add(toolbar, tr("canvas.wire_style_normal"), _toolbar_clicker(synoptic_panel, "Normal"), icon_name="wire_style_normal")
    _add(toolbar, tr("canvas.wire_style_bus"), _toolbar_clicker(synoptic_panel, "Bus", exact=False), icon_name="wire_style_bus")
    toolbar.addSeparator()

    _add(toolbar, tr("canvas.routing_direct"), _toolbar_clicker(synoptic_panel, "Direct", exact=False), icon_name="routing_direct")
    _add(toolbar, tr("canvas.routing_avoid"), _toolbar_clicker(synoptic_panel, "Avoid", exact=False), icon_name="routing_avoid")
    toolbar.addSeparator()

    _add(toolbar, tr("canvas.distribute_h"), _toolbar_clicker(synoptic_panel, "Distribute Horizontally"), icon_name="distribute_h")
    _add(toolbar, tr("canvas.distribute_v"), _toolbar_clicker(synoptic_panel, "Distribute Vertically"), icon_name="distribute_v")
    _add(toolbar, tr("canvas.align_left"), _toolbar_clicker(synoptic_panel, "Align Left"), icon_name="align_left")
    _add(toolbar, tr("canvas.align_center"), _toolbar_clicker(synoptic_panel, "Align Center"), icon_name="align_center")
    _add(toolbar, tr("canvas.align_right"), _toolbar_clicker(synoptic_panel, "Align Right"), icon_name="align_right")
    _add(toolbar, tr("canvas.align_middle"), _toolbar_clicker(synoptic_panel, "Align Middle"), icon_name="align_middle")
    toolbar.addSeparator()

    _add(toolbar, tr("canvas.bring_front"), _toolbar_clicker(synoptic_panel, "Bring to Front"), icon_name="bring_front")
    _add(toolbar, tr("canvas.send_back"), _toolbar_clicker(synoptic_panel, "Send to Back"), icon_name="send_back")
    _add(toolbar, tr("canvas.lock"), _toolbar_clicker(synoptic_panel, "Lock"), icon_name="lock")
    _add(toolbar, tr("canvas.unlock"), _toolbar_clicker(synoptic_panel, "Unlock"), icon_name="unlock")
    _add(toolbar, tr("canvas.rotate_left"), _toolbar_clicker(synoptic_panel, "Rotate Left"), icon_name="rotate_left")
    _add(toolbar, tr("canvas.rotate_right"), _toolbar_clicker(synoptic_panel, "Rotate Right"), icon_name="rotate_right")
    toolbar.addSeparator()

    _add(toolbar, tr("canvas.add_meter"), _toolbar_clicker(synoptic_panel, "Add Meter"), icon_name="add_meter")
    _add(toolbar, tr("canvas.add_signal_panel"), _toolbar_clicker(synoptic_panel, "Add Signal Panel"), icon_name="add_signal_panel")
    _add(toolbar, tr("canvas.add_group_command"), _toolbar_clicker(synoptic_panel, "Add Group Command Button"), icon_name="add_group_command")
    _add(toolbar, tr("canvas.add_setpoint_panel"), _toolbar_clicker(synoptic_panel, "Add Setpoint Panel"), icon_name="add_setpoint_panel")
    toolbar.addSeparator()

    _add(toolbar, tr("menu.view.scada_preview"), _clicker(synoptic_panel, "SCADA Style Preview"), icon_name="scada_preview")
    toolbar.addSeparator()

    _add(toolbar, tr("menu.devices.project_registers"), _clicker(synoptic_panel, "Project Registers"), icon_name="project_registers")
    _add(toolbar, tr("menu.devices.device_list"), _clicker(synoptic_panel, "Device List"), icon_name="device_list")
    toolbar.addSeparator()

    _add(toolbar, tr("canvas.background_color"), studio_window._choose_canvas_background, icon_name="background_color")
