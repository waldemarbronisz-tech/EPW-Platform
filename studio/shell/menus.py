"""Studio's menu/toolbar content.

Task "Studio: wyostrzenie stylu — wspólny rdzeń" rewrote everything
below the fixed menu (build_fixed_menu() itself is untouched - this
correction is only about toolbar CONTENT, "ta korekta dotyczy WYŁĄCZNIE
zawartości pasków"). Two rules drive every contextual-toolbar builder
now:

  1. "Ta sama funkcja = ta sama ikona = to samo miejsce" - _CORE_GROUP
     below (Copy/Paste/Delete/Snap - see this task's own chat report
     for exactly how that four-item list was MEASURED, not assumed:
     Cut/Select All/Zoom/Grid were all measured OUT, each for a
     specific, checked reason) is built FIRST, identically, by every
     build_*_context_toolbar() call - same icons, same order, same
     QAction identity pattern, so the pixel position never shifts when
     the active aspect changes.
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
from PySide6.QtWidgets import QMenuBar, QToolBar

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
# The shared core - measured, not assumed. See this task's own chat
# report for the full measurement table; summarized here so the reason
# each one is (or isn't) in this list stays next to the list itself:
#
#   Copy    - both editors have it, both with a real clickable surface
#             (Synoptic: menu + its own toolbar button; Logic: act_copy).
#   Paste   - same, both real.
#   Delete  - same, both real.
#   Snap to grid - both real (Synoptic's own View menu item; Logic's
#             act_snap).
#   Cut     - MEASURED OUT. Logic has it (act_cut); Synoptic's own Edit
#             menu has Copy/Paste/Delete/Reroute but NO Cut at all -
#             not a shared function, stays in Logic's own section.
#   Zaznacz wszystko (Select All) - MEASURED OUT. Logic Studio has NO
#             select-all mechanism whatsoever (checked: no menu item,
#             no Ctrl+A binding anywhere in main_window.py). Synoptic
#             DOES have one (store.selectAll()) but it is reachable
#             ONLY via an undocumented Ctrl+A keydown handler in
#             Canvas.tsx - no menu item, no toolbar button, no DOM
#             element trigger_menu_item()/trigger_toolbar_button() could
#             ever click. Present in neither editor as an actual UI
#             surface - excluded from the core AND left unexposed in
#             Synoptic's own section too, rather than inventing a new
#             toolbar button in Synoptic's own source to expose it
#             (GRANICE: minimal+described changes only for the state
#             bridge/color bridge cases already approved, not a new
#             standing UI element).
#   Powiększ/Pomniejsz (Zoom In/Out) - MEASURED OUT. Synoptic has no
#             zoom UI at all (mouse wheel only, confirmed in Stage 1
#             reconnaissance) - stays Logic-only, in Logic's own
#             section, exactly as it already was.
#   Siatka (grid visibility toggle) - MEASURED OUT. Synoptic exposes
#             Snap to Grid but never a separate grid-VISIBILITY toggle -
#             stays Logic-only.
#   Dopasuj do okna (Fit to window) - MEASURED OUT, on stricter grounds
#             than the others: NEITHER editor actually has it. Logic's
#             "Reset Zoom" (act_reset_zoom) is view.resetTransform() -
#             zoom back to 100%, not "fit all content in view" - a
#             different function under a similar-sounding name. Synoptic
#             has no equivalent of either. Reset Zoom stays in Logic's
#             own section, under its own accurate name - not relabeled
#             as "Dopasuj do okna", which it does not do.
# ----------------------------------------------------------------------

def _build_core_group(toolbar, studio_window):
    """Built identically on every call, by both build_*_context_toolbar
    functions below, before anything editor-specific - the actual
    mechanism behind "IDENTYCZNA ikona/kolejność/pozycja od lewej
    krawędzi". Routing dispatches on studio_window._active as usual
    (studio_window._core_copy/_core_paste/_core_delete, and the
    already-existing _view_toggle_snap - reused as-is, not duplicated).
    Enabled state is refreshed by main_window.py's existing state-poll
    timer (_refresh_shared_toolbar_state), extended to cover these four
    too - point 5's own "korzystaj z mostu stanu, który już zbudowałeś"."""
    studio_window.act_core_copy = _add(toolbar, tr("menu.edit.copy"), studio_window._core_copy, icon_name="copy")
    studio_window.act_core_paste = _add(toolbar, tr("menu.edit.paste"), studio_window._core_paste, icon_name="paste")
    studio_window.act_core_delete = _add(toolbar, tr("menu.edit.delete"), studio_window._core_delete, icon_name="delete")
    studio_window.act_core_snap = _add(toolbar, tr("menu.view.snap"), studio_window._view_toggle_snap, icon_name="snap")
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

    _mirror(toolbar, tr("menu.view.zoom_in"), mw.act_zoom_in)
    _mirror(toolbar, tr("menu.view.zoom_out"), mw.act_zoom_out)
    _mirror(toolbar, tr("menu.view.reset_zoom"), mw.act_reset_zoom, icon_name="reset_zoom")
    _mirror(toolbar, tr("menu.view.grid"), mw.act_grid)
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.file.compare_saved"), mw.act_compare_saved, icon_name="compare")
    _mirror(toolbar, tr("menu.file.compare_files"), mw.act_compare_files, icon_name="compare")
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.edit.cut"), mw.act_cut)

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

    _mirror(toolbar, tr("menu.logic.compile"), mw.act_compile)
    _mirror(toolbar, tr("menu.logic.export_runtime"), mw.act_export_runtime, icon_name="export")
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.simulation.start"), mw.act_sim_start)
    _mirror(toolbar, tr("menu.simulation.pause"), mw.act_sim_pause)
    _mirror(toolbar, tr("menu.simulation.stop"), mw.act_sim_stop)
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.help.catalog"), mw.act_help_catalog, icon_name="help_catalog")
    _mirror(toolbar, tr("menu.help.shortcuts"), mw.act_help_shortcuts, icon_name="help_shortcuts")
    _mirror(toolbar, tr("menu.help.export_catalog"), mw.act_export_block_catalog, icon_name="export")
    _mirror(toolbar, tr("menu.help.about"), mw.act_about)
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
