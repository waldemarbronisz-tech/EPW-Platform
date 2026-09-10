"""Studio's own shared QMenuBar content.

Task "EPW Studio: jedna szata graficzna" 2.1: Logic Studio's 36 menu
actions and Synoptic's 16 dropdown items are re-authored HERE as new,
translated QAction objects (every label goes through tr(), keys added
to studio/shell/locales/*.json) - not lifted wholesale from either
editor's own menu bar (both of which are now hidden, see
logic_panel.py's menuBar().setVisible(False) and synoptic_panel.py's
_STUDIO_SKIN_JS). Per the user's own decision resolving Blocker A: the
mixed English/Polish text INSIDE each editor (Object Library, panel
labels, etc.) is untouched and out of scope for this task - only the
menu/toolbar chrome that used to belong to each editor's own window
becomes Studio's, in one language.

Behavior is never reimplemented, only re-labelled and re-routed - this
is uściślenie 2.2's hard rule (Studio must never grow a second undo
history or a second dirty flag):
  - a Logic Studio menu item triggers the SAME QAction its own
    MainWindow already built (mw.act_undo.trigger(), etc.) - its own
    undo stack / is_dirty / clipboard state keeps being the single
    source of truth.
  - a Synoptic menu item clicks the SAME DOM node its own MenuBar.tsx
    already renders (SynopticPanel.trigger_menu_item() - Stage 1 proved
    this fires the real onClick handler regardless of the item's
    now-permanent display:none).

Every QAction built here is parented to the QMenu it lives in (never to
the long-lived StudioMainWindow) on purpose: main_window.py's
_rebuild_menu() throws the whole QMenuBar away and builds a fresh one
every time the active editor changes (Qt's own setMenuBar() deletes the
previous bar), so everything built here needs to die with it - both to
avoid an unbounded pile of stale QActions across repeated tree clicks,
and because a stale one left listening to a source_action.changed
signal would otherwise keep "mirroring" state forever for a menu item
nobody can even see any more.
"""
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import QMenuBar

from studio.shell.i18n import tr


def _mirror(menu, label, source_action, shortcut=None):
    """New QAction, parented to and added into `menu`, that LOOKS like a
    fresh, translated menu item but DOES exactly what `source_action` (a
    real QAction already living on Logic Studio's own, now-hidden,
    MainWindow) does - clicking ours calls source_action.trigger(), so
    the real handler runs exactly once, on the real object. Enabled/
    checked state is mirrored live via QAction.changed (Logic Studio's
    own code already keeps source_action's enabled/checked correct -
    e.g. _update_clipboard_actions() - this just listens, it never
    decides that state itself)."""
    action = QAction(label, menu)
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
    menu.addAction(action)
    return action


def _clicker(panel, text, exact=False):
    """Returns a zero-arg callable for QAction.triggered - clicks the
    matching Synoptic dropdown item by text every time it's called."""
    return lambda: panel.trigger_menu_item(text, exact=exact)


def _add(menu, label, handler):
    action = QAction(label, menu)
    action.triggered.connect(handler)
    menu.addAction(action)
    return action


def _add_exit(studio_window, file_menu):
    """One real Studio-level Exit, shared by both contexts - NOT a
    mirror of either editor's own act_exit/"Exit" item. Those close (or
    would try to close) just the editor's own top-level window, which
    doesn't exist here - MainWindow/App are embedded child widgets, not
    windows, so calling their own exit would either do nothing
    meaningful or silently misbehave. Closing the actual Studio
    QMainWindow is the only "Exit" that means what it says here."""
    exit_action = QAction(tr("menu.file.exit"), file_menu)
    exit_action.triggered.connect(studio_window.close)
    file_menu.addAction(exit_action)


def build_neutral_menu(menubar: QMenuBar, studio_window):
    """Shown when neither EKRANY/SCREENS nor LOGIKA/LOGIC is selected
    yet (Studio's own empty-placeholder state) - kept genuinely minimal
    rather than padded with disabled stand-ins for editor actions that
    don't apply to anything right now (zero fasad)."""
    file_menu = menubar.addMenu(tr("menu.titles.file"))
    _add_exit(studio_window, file_menu)

    help_menu = menubar.addMenu(tr("menu.titles.help"))
    hint = QAction(tr("menu.neutral_hint"), help_menu)
    hint.setEnabled(False)
    help_menu.addAction(hint)


def build_logic_menu(menubar: QMenuBar, logic_panel, studio_window):
    mw = logic_panel.main_window()

    file_menu = menubar.addMenu(tr("menu.titles.file"))
    _mirror(file_menu, tr("menu.file.new"), mw.act_new)
    _mirror(file_menu, tr("menu.file.open"), mw.act_open)
    _mirror(file_menu, tr("menu.file.save"), mw.act_save)
    _mirror(file_menu, tr("menu.file.save_as"), mw.act_save_as)
    file_menu.addSeparator()
    _mirror(file_menu, tr("menu.file.compare_saved"), mw.act_compare_saved)
    _mirror(file_menu, tr("menu.file.compare_files"), mw.act_compare_files)
    file_menu.addSeparator()
    _add_exit(studio_window, file_menu)

    edit_menu = menubar.addMenu(tr("menu.titles.edit"))
    _mirror(edit_menu, tr("menu.edit.undo"), mw.act_undo)
    _mirror(edit_menu, tr("menu.edit.redo"), mw.act_redo)
    edit_menu.addSeparator()
    _mirror(edit_menu, tr("menu.edit.cut"), mw.act_cut)
    _mirror(edit_menu, tr("menu.edit.copy"), mw.act_copy)
    _mirror(edit_menu, tr("menu.edit.paste"), mw.act_paste)
    _mirror(edit_menu, tr("menu.edit.delete"), mw.act_delete)
    edit_menu.addSeparator()

    # mw.align_menu is rebuilt from the CURRENT selection on every open
    # (populate_align_menu(), shared with the canvas's own context menu)
    # - reusing that QMenu object as a real submenu here would reparent
    # it away from mw's own (hidden) Edit menu. Popping the same, freshly
    # rebuilt menu at the cursor instead reuses the exact same 8 actions
    # without touching Logic Studio's own object graph.
    def _show_align_popup():
        mw._rebuild_align_menu()
        mw.align_menu.popup(QCursor.pos())

    _add(edit_menu, tr("menu.edit.align"), _show_align_popup)

    edit_menu.addSeparator()
    _mirror(edit_menu, tr("menu.edit.disable_selected"), mw.act_disable_selected)
    _mirror(edit_menu, tr("menu.edit.enable_selected"), mw.act_enable_selected)

    view_menu = menubar.addMenu(tr("menu.titles.view"))
    _mirror(view_menu, tr("menu.view.zoom_in"), mw.act_zoom_in)
    _mirror(view_menu, tr("menu.view.zoom_out"), mw.act_zoom_out)
    _mirror(view_menu, tr("menu.view.reset_zoom"), mw.act_reset_zoom)
    view_menu.addSeparator()
    _mirror(view_menu, tr("menu.view.grid"), mw.act_grid)
    _mirror(view_menu, tr("menu.view.snap"), mw.act_snap)
    view_menu.addSeparator()
    toolbar_menu = view_menu.addMenu(tr("menu.view.toolbar"))
    _mirror(toolbar_menu, tr("menu.view.toolbar_icons"), mw.act_toolbar_icons)
    _mirror(toolbar_menu, tr("menu.view.toolbar_icons_text"), mw.act_toolbar_icons_text)
    _mirror(toolbar_menu, tr("menu.view.toolbar_text"), mw.act_toolbar_text)

    project_menu = menubar.addMenu(tr("menu.titles.project"))
    _mirror(project_menu, tr("menu.project.settings"), mw.act_project_settings)
    _mirror(project_menu, tr("menu.project.export_signals"), mw.act_export_signals)
    _mirror(project_menu, tr("menu.project.export_pdf"), mw.act_export_pdf)

    logic_menu = menubar.addMenu(tr("menu.titles.logic"))
    _mirror(logic_menu, tr("menu.logic.compile"), mw.act_compile)
    _mirror(logic_menu, tr("menu.logic.export_runtime"), mw.act_export_runtime)

    sim_menu = menubar.addMenu(tr("menu.titles.simulation"))
    _mirror(sim_menu, tr("menu.simulation.start"), mw.act_sim_start)
    _mirror(sim_menu, tr("menu.simulation.pause"), mw.act_sim_pause)
    _mirror(sim_menu, tr("menu.simulation.stop"), mw.act_sim_stop)

    help_menu = menubar.addMenu(tr("menu.titles.help"))
    _mirror(help_menu, tr("menu.help.topics"), mw.act_help)
    _mirror(help_menu, tr("menu.help.catalog"), mw.act_help_catalog)
    _mirror(help_menu, tr("menu.help.shortcuts"), mw.act_help_shortcuts)
    _mirror(help_menu, tr("menu.help.export_catalog"), mw.act_export_block_catalog)
    help_menu.addSeparator()
    _mirror(help_menu, tr("menu.help.about"), mw.act_about)


def build_synoptic_menu(menubar: QMenuBar, synoptic_panel, studio_window):
    file_menu = menubar.addMenu(tr("menu.titles.file"))
    _add(file_menu, tr("menu.file.new"), _clicker(synoptic_panel, "New", exact=True))
    _add(file_menu, tr("menu.file.open"), _clicker(synoptic_panel, "Open"))
    _add(file_menu, tr("menu.file.save"), _clicker(synoptic_panel, "Save", exact=True))
    _add(file_menu, tr("menu.file.save_as"), _clicker(synoptic_panel, "Save As"))
    file_menu.addSeparator()
    _add_exit(studio_window, file_menu)

    edit_menu = menubar.addMenu(tr("menu.titles.edit"))
    _add(edit_menu, tr("menu.edit.undo"), _clicker(synoptic_panel, "Undo"))
    _add(edit_menu, tr("menu.edit.redo"), _clicker(synoptic_panel, "Redo"))
    edit_menu.addSeparator()
    _add(edit_menu, tr("menu.edit.copy"), _clicker(synoptic_panel, "Copy"))
    _add(edit_menu, tr("menu.edit.paste"), _clicker(synoptic_panel, "Paste"))
    _add(edit_menu, tr("menu.edit.delete"), _clicker(synoptic_panel, "Delete"))
    _add(edit_menu, tr("menu.edit.reroute"), _clicker(synoptic_panel, "Reroute"))

    view_menu = menubar.addMenu(tr("menu.titles.view"))
    _add(view_menu, tr("menu.view.snap"), _clicker(synoptic_panel, "Snap to Grid"))
    _add(view_menu, tr("menu.view.scada_preview"), _clicker(synoptic_panel, "SCADA Style Preview"))

    devices_menu = menubar.addMenu(tr("menu.titles.devices"))
    _add(devices_menu, tr("menu.devices.project_registers"), _clicker(synoptic_panel, "Project Registers"))
    _add(devices_menu, tr("menu.devices.device_list"), _clicker(synoptic_panel, "Device List"))

    help_menu = menubar.addMenu(tr("menu.titles.help"))
    _add(help_menu, tr("menu.help.topics"), _clicker(synoptic_panel, "Help Topics"))
