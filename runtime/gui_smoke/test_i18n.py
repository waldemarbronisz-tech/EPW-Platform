"""Polish translation coverage: menu/nav/statusbar reflecting a language
switch after a fresh MainWindow rebuild, and the sweep proving every
individual page/dialog/popup this program has actually renders in
Polish, not just the ones reachable through a full MainWindow.

Split out of the old test_gui_smoke.py (refactor/test-suite-split task,
"translations" axis) - distinct from test_themes.py, which is about
color palettes, not language.
"""
from epw_os.i18n import set_language, tr

from gui_smoke._mocks import MockAccessManager, MockCommandManager, MockProjectManager, MockTagManager


def test_polish_menu_nav_statusbar_after_rebuild(make_window):
    set_language("pl")
    try:
        w_pl = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
        # main_view_group always stays expanded (Task: "grupa przygotowana
        # na wiele ekranow synoptycznych"), so its own top-level item
        # carries the group label "Widok glowny"; the single "Schemat
        # glowny" page lives one level below it. Sentence case, not the
        # underlying ALL-CAPS translation value - a display-only
        # transform nav_tree.py's own _display_case() applies (Task: "w
        # drzewie pisane sa normalnie, nie wersalikami" - the tree only,
        # page headers/nav.* elsewhere stay ALL-CAPS unchanged).
        assert w_pl.nav_tree.topLevelItem(0).text(0) == "Widok główny", w_pl.nav_tree.topLevelItem(0).text(0)
        assert w_pl.nav_tree._page_items["main_view"].text(0) == "Schemat główny", \
            w_pl.nav_tree._page_items["main_view"].text(0)
        assert w_pl.menuBar().actions()[0].text() == "Plik"
        assert "TRYB SYMULACJI" in w_pl.btn_sb_mode.text()
        pl_settings = [a.menu() for a in w_pl.menuBar().actions() if a.text() == "Ustawienia"][0]
        # Kiosk Mode's entry (and the separator before it) is always
        # present in the menu - only its *visibility* is Engineer-gated.
        # Same for Training Mode's own entry/separator just before it.
        assert [a.text() for a in pl_settings.actions()] == \
            ["Język...", "Zmień PIN...", "Wygaszanie ekranu...", "Klawiatura ekranowa", "Motyw...",
             "Konfiguracja funkcji...", "MQTT...", "Retencja danych...", "", "Tryb ćwiczebny", "",
             "Tryb kiosku..."]
        pl_project = [a.menu() for a in w_pl.menuBar().actions() if a.text() == "Projekt"][0]
        assert [a.text() for a in pl_project.actions() if not a.isSeparator()] == \
            ["Właściwości projektu...", "Ostatnio otwierane"]
    finally:
        set_language("en")


def _header_text(widget):
    hdrs = [w for w in widget.children() if hasattr(w, "objectName") and w.objectName() == "PageHeader"]
    return hdrs[0].text() if hdrs else None


def test_polish_translation_reaches_every_page_and_dialog():
    # Runtime proof (not static analysis) that the i18n expansion task's
    # tr() calls actually render Polish text, for every page/dialog file
    # it touched. Constructed directly (not via MainWindow.stacked_widget)
    # so a page's own constructor requirements stay minimal and explicit.
    from gui_smoke._mocks import PageMockAccessManager, PageMockProtectionManager, PageMockTagManager

    set_language("pl")
    try:
        from epw_os.gui.pages.page_alarms import PageAlarms
        from epw_os.gui.pages.page_analog_inputs import PageAnalogInputs
        from epw_os.gui.pages.page_audit_log import PageAuditLog
        from epw_os.gui.pages.page_control_outputs import PageControlOutputs
        from epw_os.gui.pages.page_digital_inputs import PageDigitalInputs
        from epw_os.gui.pages.page_engineer_mode import PageEngineerMode
        from epw_os.gui.pages.page_entry_gate import PageEntryGate
        from epw_os.gui.pages.page_event_recorder import PageEventRecorder
        from epw_os.gui.pages.page_intrusion import (
            PageIntrusionConfiguration, PageIntrusionHistory, PageIntrusionOverview,
        )
        from epw_os.gui.pages.page_power_quality import PagePowerQuality
        from epw_os.gui.pages.page_protection_electrical import PageProtectionElectrical
        from epw_os.gui.pages.page_protection_process import PageProtectionProcess
        from epw_os.gui.pages.page_system_topology import PageSystemTopology

        pl_pages = []
        p = PageDigitalInputs(PageMockTagManager(), PageMockAccessManager()); pl_pages.append(p)
        assert _header_text(p) == "WEJŚCIA CYFROWE", _header_text(p)

        p = PageControlOutputs(PageMockTagManager(), PageMockAccessManager()); pl_pages.append(p)
        assert _header_text(p) == "CENTRUM STEROWANIA OPERATORA", _header_text(p)

        p = PageAnalogInputs(PageMockTagManager(), PageMockAccessManager()); pl_pages.append(p)
        assert _header_text(p) == "WEJŚCIA ANALOGOWE", _header_text(p)
        assert p.btn_add.text() == "Dodaj punkt", p.btn_add.text()

        p = PageAuditLog(None, PageMockAccessManager()); pl_pages.append(p)
        assert _header_text(p) == "DZIENNIK AUDYTOWY", _header_text(p)

        p = PageEntryGate(PageMockTagManager()); pl_pages.append(p)  # constructs OK, no page title of its own
        p.sim_timer.stop()  # never shown/run through a Qt event loop here, so it just needs to be stopped

        p = PageSystemTopology(PageMockTagManager()); pl_pages.append(p)
        assert _header_text(p) == "TOPOLOGIA SYSTEMU", _header_text(p)

        p = PageEngineerMode(PageMockTagManager(), PageMockProtectionManager(), PageMockAccessManager())
        pl_pages.append(p)
        assert _header_text(p) == "WERYFIKACJA ZABEZPIECZEŃ", _header_text(p)

        p = PageEventRecorder(PageMockTagManager()); pl_pages.append(p)
        assert _header_text(p) == "REJESTRATOR ZDARZEŃ", _header_text(p)

        p = PageAlarms(None, PageMockAccessManager()); pl_pages.append(p)
        assert _header_text(p) == "ALARMY", _header_text(p)
        assert p.lbl_gate.text() == "Zaloguj się jako Operator, aby potwierdzać alarmy.", p.lbl_gate.text()

        p = PageProtectionElectrical(PageMockTagManager(), PageMockAccessManager()); pl_pages.append(p)
        assert _header_text(p) == "ELEKTRYCZNE", _header_text(p)

        p = PageProtectionProcess(None, PageMockAccessManager()); pl_pages.append(p)  # manager may be None (feature off)
        assert _header_text(p) == "PROCESOWE", _header_text(p)

        p = PageIntrusionOverview(None, PageMockAccessManager()); pl_pages.append(p)  # manager may be None (feature off)
        assert _header_text(p) == "PODGLĄD", _header_text(p)

        p = PageIntrusionHistory(None, PageMockAccessManager()); pl_pages.append(p)
        assert _header_text(p) == "HISTORIA ZDARZEŃ", _header_text(p)

        p = PageIntrusionConfiguration(None, PageMockAccessManager()); pl_pages.append(p)
        assert _header_text(p) == "KONFIGURACJA", _header_text(p)
        assert p.lbl_gate.text() == "Zaloguj się jako Engineer, aby konfigurować strefy i linie.", p.lbl_gate.text()

        p = PagePowerQuality(PageMockTagManager()); pl_pages.append(p)
        assert _header_text(p) == "JAKOŚĆ ENERGII", _header_text(p)

        from epw_os.gui.pages.page_trends import PageTrends

        class _PageMockHistorian:
            def get_distinct_tag_names(self): return []

        p = PageTrends(PageMockTagManager(), _PageMockHistorian(), None); pl_pages.append(p)
        assert _header_text(p) == "TRENDY", _header_text(p)
        p.shutdown()

        from epw_os.gui.pages.page_bus_diagnostics import PageBusDiagnostics

        class _PageMockDeviceManager:
            devices = {}

        class _PageMockDriverManager:
            drivers = {}
            def get_driver(self, driver_id): return None

        p = PageBusDiagnostics(_PageMockDeviceManager(), _PageMockDriverManager(), PageMockAccessManager())
        pl_pages.append(p)
        assert _header_text(p) == "DIAGNOSTYKA MAGISTRALI", _header_text(p)
        p.shutdown()

        from epw_os.gui.widgets.about_dialog import AboutDialog
        from epw_os.gui.widgets.popups import ConfirmationPopup, ForceOutputConfirmPopup

        conf = ConfirmationPopup("DO01", "OTWARTY", "CLOSE", "Operator")
        assert conf.btn_confirm.text() == "POTWIERDŹ", conf.btn_confirm.text()
        force = ForceOutputConfirmPopup("DO01", "OTWARTY", "CLOSE", "Engineer")
        assert force.btn_confirm.text() == "TAK, WYMUŚ CLOSE", force.btn_confirm.text()
        ad = AboutDialog()
        assert ad.windowTitle() == "O programie EPW OS", ad.windowTitle()

        from epw_os.gui.widgets.historian_export_dialog import HistorianExportDialog

        class _MockHistorian:
            def get_distinct_tag_names(self): return []

        hed = HistorianExportDialog(_MockHistorian(), None)
        assert hed.windowTitle() == "Eksport danych historycznych", hed.windowTitle()

        from epw_os.core.events import EventBus as PresEventBus
        from epw_os.core.presentation_mode import PresentationMode as RealPresentationMode
        from epw_os.gui.widgets.presentation_dialog import PresentationDialog

        class _MockTrainingMode:
            active = False

        pres_bus = PresEventBus()
        pres_mode = RealPresentationMode(pres_bus, PageMockTagManager(), MockCommandManager(), None, _MockTrainingMode())
        prd = PresentationDialog(pres_mode, _MockTrainingMode(), PageMockAccessManager())
        assert prd.windowTitle() == "Tryb prezentacji", prd.windowTitle()

        from epw_os.gui.widgets.project_properties_dialog import ProjectPropertiesDialog

        ppd = ProjectPropertiesDialog(MockProjectManager(), MockTagManager(), PageMockAccessManager(), None)
        assert ppd.windowTitle() == "Właściwości projektu", ppd.windowTitle()

        assert len(pl_pages) == 17, \
            "the exact page/dialog count this sweep exercises - preserved from the original " \
            "test_gui_smoke.py so a future accidental deletion here is caught"
    finally:
        set_language("en")


def test_rest_api_exposure_indicator(make_window):
    # Task: REST API security - the status-bar warning indicator shows
    # only when api_host is exposed beyond localhost, never for the
    # default/local case. isHidden() (the widget's own explicit
    # shown/hidden flag), not isVisible() (which also needs the whole
    # ancestor chain actually shown on screen - neither window below is
    # ever .show()n here).
    w_local = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), api_host="127.0.0.1")
    assert w_local.lbl_sb_api_warning.isHidden(), "127.0.0.1 must never show the exposure warning"

    w_exposed = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), api_host="0.0.0.0")
    assert not w_exposed.lbl_sb_api_warning.isHidden(), "a non-local api_host must show the exposure warning"
    assert "0.0.0.0" in w_exposed.lbl_sb_api_warning.text()
