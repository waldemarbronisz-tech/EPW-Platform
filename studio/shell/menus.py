"""Studio's menu/toolbar content.

Task "EPW Studio: przebudowa nawigacji wg wzorca e²TANGO" replaces
Stage 2's per-context QMenuBar (one whole menu bar rebuilt on every
tree click) with the e²TANGO pattern this task's diagnosis names
directly: Studio was structurally two application MODES wearing one
skin, which is why the chrome kept jumping. Now:

  - build_fixed_menu() builds the APP-level menu (Plik/Widok/
    Ustawienia/Pomoc) exactly ONCE, in main_window.py's __init__ - it
    is never rebuilt, never grows or shrinks a menu when the active
    aspect changes. Only individual items' enabled/checked state
    changes (main_window.py's _refresh_fixed_menu_state()), the same
    way Cofnij/Ponów already behaved in Stage 2.
  - build_logic_context_toolbar()/build_synoptic_context_toolbar()
    build each aspect's OWN tools - Stage 2's build_logic_menu/
    build_synoptic_menu content, mostly unchanged, just re-targeted at
    a QToolBar living in the CONTEXTUAL zone (1.3) instead of the top
    QMenuBar. QToolBar and QMenu share the same addAction()/
    addSeparator() surface, so _mirror()/_add() below don't care which
    one they're given.

Behavior is still never reimplemented, only re-labelled and re-routed -
uściślenie 2.2's hard rule from Stage 2 still holds (never merge the
two editors' own undo/dirty mechanisms):
  - a Logic Studio action triggers the SAME QAction its own (hidden)
    MainWindow already built.
  - a Synoptic action clicks the SAME DOM node its own (hidden)
    MenuBar.tsx already renders (SynopticPanel.trigger_menu_item()).
"""
from PySide6.QtGui import QAction, QActionGroup, QCursor
from PySide6.QtWidgets import QMenuBar

from studio.shell.i18n import get_language, tr


def _mirror(container, label, source_action, shortcut=None):
    """New QAction, parented to and added into `container` (a QMenu or
    a QToolBar - both share addAction()), that LOOKS like a fresh,
    translated item but DOES exactly what `source_action` (a real
    QAction already living on Logic Studio's own, now-hidden,
    MainWindow) does - clicking ours calls source_action.trigger(), so
    the real handler runs exactly once, on the real object. Enabled/
    checked state is mirrored live via QAction.changed (Logic Studio's
    own code already keeps source_action's enabled/checked correct -
    this just listens, it never decides that state itself).

    Parented to `container` on purpose: main_window.py throws away and
    rebuilds each aspect's contextual toolbar on every tree click (the
    same reasoning Stage 2's own menus.py docstring already spelled
    out for the old per-context QMenuBar - everything built here needs
    to die with its container, not pile up across repeated clicks)."""
    action = QAction(label, container)
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


def _add(container, label, handler):
    action = QAction(label, container)
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
    once. Every action here routes to whichever aspect is currently
    active via studio_window's own methods (same dispatch pattern as
    its shared toolbar); studio_window keeps the QAction references
    (act_menu_*/act_view_*) so it can update enabled/checked state
    without ever touching this menu's STRUCTURE again."""
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


def build_logic_context_toolbar(toolbar, logic_panel, studio_window):
    """The contextual zone's tools while LOGIKA is the active aspect -
    everything Logic Studio's own (now-hidden) menu offered beyond
    File/Zoom/Grid/Snap (those moved to the fixed top chrome, task
    1.1/1.2)."""
    mw = logic_panel.main_window()

    _mirror(toolbar, tr("menu.file.compare_saved"), mw.act_compare_saved)
    _mirror(toolbar, tr("menu.file.compare_files"), mw.act_compare_files)
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.edit.cut"), mw.act_cut)
    _mirror(toolbar, tr("menu.edit.copy"), mw.act_copy)
    _mirror(toolbar, tr("menu.edit.paste"), mw.act_paste)
    _mirror(toolbar, tr("menu.edit.delete"), mw.act_delete)

    # mw.align_menu is rebuilt from the CURRENT selection on every open
    # (populate_align_menu(), shared with the canvas's own context
    # menu) - popping the same, freshly rebuilt menu at the cursor
    # reuses those exact 8 actions without touching Logic Studio's own
    # object graph (same technique Stage 2 used when this lived in the
    # top menu).
    def _show_align_popup():
        mw._rebuild_align_menu()
        mw.align_menu.popup(QCursor.pos())

    _add(toolbar, tr("menu.edit.align"), _show_align_popup)
    _mirror(toolbar, tr("menu.edit.disable_selected"), mw.act_disable_selected)
    _mirror(toolbar, tr("menu.edit.enable_selected"), mw.act_enable_selected)
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.view.toolbar_icons"), mw.act_toolbar_icons)
    _mirror(toolbar, tr("menu.view.toolbar_icons_text"), mw.act_toolbar_icons_text)
    _mirror(toolbar, tr("menu.view.toolbar_text"), mw.act_toolbar_text)
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.project.settings"), mw.act_project_settings)
    _mirror(toolbar, tr("menu.project.export_signals"), mw.act_export_signals)
    _mirror(toolbar, tr("menu.project.export_pdf"), mw.act_export_pdf)
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.logic.compile"), mw.act_compile)
    _mirror(toolbar, tr("menu.logic.export_runtime"), mw.act_export_runtime)
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.simulation.start"), mw.act_sim_start)
    _mirror(toolbar, tr("menu.simulation.pause"), mw.act_sim_pause)
    _mirror(toolbar, tr("menu.simulation.stop"), mw.act_sim_stop)
    toolbar.addSeparator()

    _mirror(toolbar, tr("menu.help.catalog"), mw.act_help_catalog)
    _mirror(toolbar, tr("menu.help.shortcuts"), mw.act_help_shortcuts)
    _mirror(toolbar, tr("menu.help.export_catalog"), mw.act_export_block_catalog)
    _mirror(toolbar, tr("menu.help.about"), mw.act_about)


def build_synoptic_context_toolbar(toolbar, synoptic_panel, studio_window):
    """The contextual zone's tools while EKRANY/Schemat synoptyczny is
    the active aspect - everything Synoptic's own (now-hidden) menu
    offered beyond File/Snap (Undo/Redo stay on the fixed top toolbar,
    not repeated here)."""
    _add(toolbar, tr("menu.edit.copy"), _clicker(synoptic_panel, "Copy"))
    _add(toolbar, tr("menu.edit.paste"), _clicker(synoptic_panel, "Paste"))
    _add(toolbar, tr("menu.edit.delete"), _clicker(synoptic_panel, "Delete"))
    _add(toolbar, tr("menu.edit.reroute"), _clicker(synoptic_panel, "Reroute"))
    toolbar.addSeparator()

    _add(toolbar, tr("menu.view.scada_preview"), _clicker(synoptic_panel, "SCADA Style Preview"))
    toolbar.addSeparator()

    _add(toolbar, tr("menu.devices.project_registers"), _clicker(synoptic_panel, "Project Registers"))
    _add(toolbar, tr("menu.devices.device_list"), _clicker(synoptic_panel, "Device List"))
