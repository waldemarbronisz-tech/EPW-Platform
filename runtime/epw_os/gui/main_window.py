import os
import time

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QStackedWidget, QStatusBar, QLabel, QFrame,
                             QToolButton, QMenu, QFileDialog, QMessageBox, QApplication)
from PySide6.QtCore import Qt, QTimer, QTime, QDate
from PySide6.QtGui import QKeySequence
from epw_os.gui.style import WINDOWS_NT_STYLE, build_stylesheet
from epw_os.gui.pages.page_entry_gate import PageEntryGate
from epw_os.gui.pages.page_digital_inputs import PageDigitalInputs
from epw_os.gui.pages.page_analog_inputs import PageAnalogInputs
from epw_os.gui.pages.page_control_outputs import PageControlOutputs
from epw_os.gui.widgets.engineer_popups import PinPromptPopup, AccessTimeoutPopup
from epw_os.gui.widgets.settings_popups import LanguageDialog, ChangePinDialog, ScreenSleepDialog, ThemeDialog
from epw_os.gui.widgets.feature_config_dialog import FeatureConfigDialog
from epw_os.gui.widgets.screen_sleep_overlay import ScreenSleepOverlay
from epw_os.gui.widgets.onscreen_keyboard import OnScreenKeyboardController
from epw_os.gui.pages.page_engineer_mode import PageEngineerMode
from epw_os.gui.pages.page_intrusion import PageIntrusionOverview, PageIntrusionHistory, PageIntrusionConfiguration
from epw_os.core.intrusion_manager import ZoneState
from epw_os.gui import window_state
from epw_os.gui.theme_manager import get_theme_manager
from epw_os.core.access_manager import AccessLevel
from epw_os.core.api_auth import is_local_host
from epw_os.core.alarm_manager import AlarmState
from epw_os.i18n import tr
from epw_os.version import __version__, APP_NAME

class MainWindow(QMainWindow):
    def __init__(self, tag_manager, command_manager, access_manager, project_manager=None,
                 audit_logger=None, time_sync_monitor=None, alarm_manager=None, historian=None,
                 kiosk=False, switching_counters=None, training_mode=None, service_notes=None,
                 health_manager=None, command_status_signal=None, driver_scan_cycle_signal=None,
                 device_manager=None, driver_manager=None, presentation_mode=None,
                 presentation_started_signal=None, presentation_stopped_signal=None,
                 presentation_paused_signal=None, presentation_resumed_signal=None,
                 presentation_step_signal=None, api_host=None, intrusion_manager=None,
                 process_protection_manager=None,
                 language_changed_callback=None, feature_config=None, feature_config_changed_callback=None,
                 mqtt_manager=None, mqtt_status_changed_signal=None):
        super().__init__()
        self.tag_manager = tag_manager
        self.command_manager = command_manager
        self.access_manager = access_manager
        # Task (page-split): passed straight through like intrusion_manager
        # above - headless, no Qt dependency of its own. None in isolated
        # widget tests / when the "protection_process" feature is off.
        self.process_protection_manager = process_protection_manager
        # Task ("okno konfiguracji funkcji") - Qt-free (get_enabled_features()/
        # set_feature_enabled()/feature_referenced_by_logic()/
        # get_feature_tag_names() are plain sync calls - see
        # GUIFeatureConfigAdapter in main.py), passed straight through like
        # project_manager/historian. May be None in isolated widget tests -
        # every togglable feature then reads as enabled (see the fallback
        # just below), matching this app's existing "isolated test = show
        # everything" stance for every other optional manager.
        self.feature_config = feature_config
        # MQTT integration (Task: "integracja MQTT") - Qt-free
        # (get_config()/configure()/get_state()/get_stats() are plain
        # sync calls - see GUIMqttAdapter in main.py), passed straight
        # through like project_manager/historian above. `mqtt_status_
        # changed_signal` is the one Qt-signal exception (a background
        # network thread's connection-state changes need to reach the
        # GUI thread through a real signal, same "wrap only what
        # crosses a thread boundary" reasoning as time_sync_monitor/
        # alarm_manager above). Both may be None in isolated widget
        # tests - the dialog simply isn't reachable then (same
        # tolerance every other optional manager here already has).
        self.mqtt_manager = mqtt_manager
        self.mqtt_status_changed_signal = mqtt_status_changed_signal
        from epw_os.core.feature_config import normalize_enabled_features, DEFAULT_ENABLED_FEATURES, is_feature_enabled
        if self.feature_config is not None:
            self.enabled_features = normalize_enabled_features(self.feature_config.get_enabled_features())
        else:
            self.enabled_features = dict(DEFAULT_ENABLED_FEATURES)
        # May be None in isolated widget tests; every File-menu handler and
        # the close confirmation guard against that.
        self.project_manager = project_manager
        # Both Qt-free (audit_logger/alarm_manager are plain sync method
        # calls; passed straight through like project_manager - see
        # main.py), or a thin Qt-signal adapter for time_sync_monitor (its
        # status changes on a background thread and needs to reach the
        # GUI thread through a real Qt signal, same reasoning as
        # tag_manager/access_manager). alarm_manager is likewise wrapped
        # in a thin adapter for its alarms_changed signal - see
        # GUIAlarmAdapter in main.py. May be None in isolated widget tests.
        self.audit_logger = audit_logger
        self.time_sync_monitor = time_sync_monitor
        self.alarm_manager = alarm_manager
        # Qt-free (query_tag_history/get_distinct_tag_names are plain sync
        # DB calls) - passed straight through, like project_manager.
        self.historian = historian
        # Qt-free too (get_snapshot/reset_counter/set_warning_threshold/
        # is_over_threshold are plain sync calls; counting itself already
        # happens core-side, straight off the event bus - see
        # epw_os/core/switching_counters.py) - passed straight through,
        # like project_manager/historian. May be None in isolated widget
        # tests; page_digital_inputs.py/page_entry_gate.py/popups.py all
        # guard against that (counters simply don't display).
        self.switching_counters = switching_counters
        # Qt-free too (set_active()/the .active flag are plain sync -
        # see epw_os/core/training_mode.py) - passed straight through,
        # like switching_counters. May be None in isolated widget tests;
        # the Settings menu action and the persistent indicator both
        # guard against that (the action simply does nothing/the
        # indicator never shows).
        self.training_mode = training_mode
        # Qt-free too (add_note()/get_notes() are plain sync calls - see
        # epw_os/core/service_notes.py). May be None in isolated widget
        # tests; every notes-related widget guards against that (notes
        # simply don't display, and Add is unavailable).
        self.service_notes = service_notes
        # Qt-free too (get_health() is a plain sync call - see
        # epw_os/core/health_manager.py) - passed straight through, like
        # project_manager/historian. May be None in isolated widget tests;
        # _check_db_health() below guards against that (the DB status
        # label just shows a neutral "no data" state).
        self.health_manager = health_manager
        # Real Qt signals (bridge.command_status/bridge.driver_scan_cycle
        # in main.py), not thin adapters like access_manager/tag_manager -
        # there's no per-call logic to wrap, just events this window wants
        # to listen to. May be None in isolated widget tests; both connect
        # calls below guard against that (Latency/Scan just never update
        # from their initial "no data" state).
        self._command_status_signal = command_status_signal
        self._driver_scan_cycle_signal = driver_scan_cycle_signal
        # Qt-free too (device_manager.devices is a plain dict,
        # driver_manager.get_driver()/.drivers are plain sync calls) -
        # passed straight through, like project_manager/historian. May
        # be None in isolated widget tests; PageBusDiagnostics guards
        # against that (shows "no data" instead of crashing).
        self.device_manager = device_manager
        self.driver_manager = driver_manager
        # Presentation Mode (Task) - Qt-free core object (plain sync
        # start()/stop()/pause()/resume()/step_forward() calls, like
        # training_mode/switching_counters), passed straight through;
        # the 5 signals are real Qt signals bridging its own
        # event_bus.emit() calls (main.py) - both the status-bar
        # indicator below and PresentationDialog connect to them. May
        # be None in isolated widget tests; every presentation-related
        # method guards against that.
        self.presentation_mode = presentation_mode
        self._presentation_started_signal = presentation_started_signal
        self._presentation_stopped_signal = presentation_stopped_signal
        self._presentation_paused_signal = presentation_paused_signal
        self._presentation_resumed_signal = presentation_resumed_signal
        self._presentation_step_signal = presentation_step_signal
        # Task: DODATKOWO - REST API exposed beyond localhost must be
        # signaled in the interface too, not just the startup log (see
        # main.py). A plain string (or None in isolated widget tests,
        # where the indicator just never shows) - boot-time-only, no
        # live reconfiguration UI exists for api_host, so this is read
        # once here rather than wired to a signal.
        self.api_host = api_host
        # Intrusion (burglar) alarm system (Task: "system alarmowy") -
        # Qt-free too (arm_zone()/disarm_zone()/bypass_line()/get_zones()/
        # etc. are plain sync calls - see epw_os/core/intrusion_manager.py),
        # passed straight through like switching_counters/training_mode/
        # service_notes above. Live updates reach page_intrusion.py and
        # this window's own status-bar indicator through the existing
        # tag_changed bridge (every zone/line/system state is a real
        # TagManager "Security.*" tag), not a dedicated signal. May be
        # None in isolated widget tests; page_intrusion.py and
        # _refresh_intrusion_indicator() both guard against that.
        self.intrusion_manager = intrusion_manager
        # Task: switch interface language without restarting the kiosk -
        # main.py owns the actual rebuild (it constructed this window in
        # the first place, and holds the QApplication/bridge/adapters this
        # window shares with whatever replaces it), so this is a plain
        # callback rather than a Qt signal - no other object needs to
        # observe it. Invoked from _open_language_dialog() below, once,
        # only when the saved language actually changed. May be None in
        # isolated widget tests or if main.py ever constructs this window
        # without wiring one up - _open_language_dialog() guards against
        # that (the dialog still works, the interface just won't refresh
        # until an actual restart, same as before this task).
        self._language_changed_callback = language_changed_callback
        # Same rebuild-the-window-in-place mechanism as language above -
        # see _open_feature_config_dialog()'s own docstring for why a
        # feature-configuration change needs exactly the same "tear
        # down and reconstruct" treatment (new/gone pages, new/gone nav
        # entries) rather than trying to patch the running window.
        self._feature_config_changed_callback = feature_config_changed_callback
        # Latency measurement state (see _on_command_status()) and DB
        # health trend state (see _check_db_health()) - both new, both
        # purely in-memory/session-local, nothing persisted.
        self._pending_command_times = {}
        self._db_queue_history = []
        self._device_status_tags = [
            "Device.OrangePi.Status", "Device.ELA01.Status",
            "Device.ADA01.Status", "Device.Modbus.Status"
        ]
        self.setWindowTitle(tr("app.title"))
        # Normal resizable window (drag edges, maximize) like any desktop
        # app. A minimum size keeps the nav panel + a data table from
        # colliding; the last size / maximized state is restored from a
        # machine-local file (not the project) and re-saved on close.
        self.setMinimumSize(window_state.MIN_WIDTH, window_state.MIN_HEIGHT)
        _ws = window_state.load()
        self.resize(_ws["width"], _ws["height"])
        if _ws["maximized"]:
            # Deferred: showMaximized() only takes effect once the window
            # is actually shown (main.py calls show() after construction).
            QTimer.singleShot(0, self.showMaximized)
        # Visual theme (Task: przelaczane motywy wizualne) - a process-wide
        # singleton (get_theme_manager()) rather than an attribute private
        # to this window, so widgets constructed far from here (e.g.
        # StatusLabel instances on other pages) can react to a theme
        # change without MainWindow having to know about every one of
        # them individually. bind_tag_manager() (below, once
        # self.tag_manager exists) is what makes Task 4's "sterowanie z
        # logiki" possible - see theme_manager.py's docstring.
        self.theme_manager = get_theme_manager()
        self.setStyleSheet(build_stylesheet(self.theme_manager.current_colors()))
        self.theme_manager.theme_changed.connect(self._on_theme_changed)
        self.theme_manager.bind_tag_manager(self.tag_manager)

        # Kiosk mode (Orange Pi target only, opt-in via main.py's --kiosk
        # flag - see main(), or live via Settings > Kiosk Mode, Engineer
        # only - see enter_kiosk_mode()). Layered ON TOP of the normal
        # window setup above rather than replacing any of it: every line
        # above this block runs identically whether or not --kiosk was
        # passed, so non-kiosk behavior (including window_state
        # persistence, sizing, restoring "was maximized") is provably
        # untouched. Deliberately never persisted anywhere (unlike every
        # other piece of state in this constructor) - restarting the
        # program without --kiosk must always come back up in normal
        # mode, so there is always a way out if something goes wrong.
        #
        # self.kiosk itself is set synchronously (not deferred) - the
        # On-Screen Keyboard's own kiosk_default below reads it
        # immediately, and enter_kiosk_mode()'s actual window changes
        # (frameless/fullscreen/hidden menu) are what's deferred, for the
        # same reason showMaximized() above is: they only take effect
        # once the window is actually shown (main.py calls show() after
        # construction).
        self.kiosk = bool(kiosk)
        if self.kiosk:
            QTimer.singleShot(0, self.enter_kiosk_mode)

        # On-screen touch keyboard - off by default (a physical keyboard
        # makes it pure friction on a dev machine), on by default under
        # --kiosk (an Orange Pi touchscreen has no physical keyboard at
        # all) unless the operator has already explicitly chosen
        # something in Settings, which always wins - see
        # window_state.load_keyboard_enabled()'s docstring. Toggling
        # applies live (Settings > On-Screen Keyboard, a checkable
        # action below), no restart needed - same as screen sleep,
        # unlike Language. The controller is a QApplication-wide event
        # filter (same installEventFilter pattern as self below) so it
        # reaches every QLineEdit/QAbstractSpinBox in the whole app,
        # including separate popups like PinPromptPopup, without any
        # page/dialog needing to know it exists.
        self.keyboard_enabled = window_state.load_keyboard_enabled(kiosk_default=self.kiosk)
        self._keyboard_controller = OnScreenKeyboardController(lambda: self.keyboard_enabled)
        QApplication.instance().installEventFilter(self._keyboard_controller)

        self.setup_menu()

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top panel
        top_panel = QFrame()
        top_panel.setObjectName("TopPanel")
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(5, 5, 5, 5)

        self.lbl_clock = QLabel()
        # Task: podpowiedzi - static (the clock's own ticking text is the
        # dynamic part; what the tooltip explains, where the time/sync
        # source comes from, doesn't change tick to tick), set once here.
        self.lbl_clock.setToolTip(tr("topbar.tooltip_clock"))
        # Color is applied by update_comm_status() below (called right
        # after construction, and again on every comm-status/theme
        # change) - no need to set an initial style here, it would just
        # be overwritten immediately.
        self.lbl_comm_status = QLabel(tr("topbar.comm_ok"))

        self.lbl_project = QLabel(f"{tr('topbar.project')}: {self._project_display_name()}")
        self.lbl_project.setToolTip(tr("topbar.tooltip_project"))
        # Alarm count's tooltip is dynamic (active/unacknowledged
        # breakdown) - set in _update_alarm_counter() below, alongside
        # its text, not here.
        self.lbl_alarm_cnt = QLabel(f"{tr('topbar.alarms')}: 0")

        # Access level selector - a dropdown with the 3 levels rather than
        # a passive label + separate Logout button, so switching access is
        # a single control: pick User to always drop straight back down
        # (no PIN needed - see AccessManager.demote), pick Operator/
        # Engineer to either drop down to it (if already at or above) or
        # get PIN-prompted up to it (request_access, existing flow).
        self.btn_access_level = QToolButton()
        self.btn_access_level.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        # Colored by _update_access_label() below (called right after
        # construction, and on every level/theme change) - no initial
        # style needed here, it would just be overwritten immediately.
        access_menu = QMenu(self.btn_access_level)
        self._access_level_actions = {}
        for level, menu_key in (
            (AccessLevel.USER, "access.menu_user"),
            (AccessLevel.OPERATOR, "access.menu_operator"),
            (AccessLevel.ENGINEER, "access.menu_engineer"),
        ):
            action = access_menu.addAction(tr(menu_key))
            action.triggered.connect(lambda checked=False, lv=level: self._on_access_level_selected(lv))
            self._access_level_actions[level] = action
        self.btn_access_level.setMenu(access_menu)

        # Colored/text set by update_comm_status() below (called right
        # after construction, and on every device-status/theme change,
        # same as lbl_comm_status just below it) - no initial value here,
        # it would just be overwritten immediately. Task: was a permanent
        # "Q: 100%" that never changed - now the real percentage of
        # registered devices currently ONLINE (DeviceManager has no
        # per-exchange success/fail counters to draw a true "% successful
        # exchanges" from - see SESSION_REPORT.md - so this is the
        # honest, cheap, already-tracked proxy: reuses the exact same
        # _device_status_tags this window already watches for
        # lbl_comm_status, at zero extra wiring cost).
        self.lbl_comm_quality = QLabel()

        top_layout.addWidget(self.lbl_clock)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_project)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_access_level)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_alarm_cnt)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_comm_quality)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_comm_status)
        main_layout.addWidget(top_panel)

        # Content Layout
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)

        # Left Vertical Navigation - Task: "przebudowac lewe menu
        # nawigacji na drzewo w stylu Windows 98" + "okno konfiguracji
        # funkcji" - which pages/groups even exist now comes from
        # epw_os.core.nav_model.build_nav_tree(self.enabled_features),
        # not a hardcoded flat list; NavTreeWidget (epw_os/gui/widgets/
        # nav_tree.py) renders it. A feature's PAGE is only ever
        # constructed below when is_feature_enabled() says so - Task:
        # "wylaczona funkcja... znika z drzewa nawigacji" - never just
        # hidden with the underlying widget still alive.
        from epw_os.gui.widgets.nav_tree import NavTreeWidget
        from epw_os.core.nav_model import engineer_mode_available
        from epw_os.gui.pages.page_power_quality import PagePowerQuality
        from epw_os.gui.pages.page_protection_electrical import PageProtectionElectrical
        from epw_os.gui.pages.page_protection_process import PageProtectionProcess
        from epw_os.gui.pages.page_event_recorder import PageEventRecorder
        from epw_os.gui.pages.page_system_topology import PageSystemTopology
        from epw_os.gui.pages.page_audit_log import PageAuditLog
        from epw_os.gui.pages.page_alarms import PageAlarms
        from epw_os.gui.pages.page_trends import PageTrends
        from epw_os.gui.pages.page_bus_diagnostics import PageBusDiagnostics

        self.nav_tree = NavTreeWidget()
        self.nav_tree.setFixedWidth(190)
        content_layout.addWidget(self.nav_tree)

        # Stacked widget for pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("SunkenFrame")
        # page_id -> stacked_widget index - the ONLY place a page's
        # position is looked up from now on (Task 5: "kolejnosc...
        # zdefiniowana w JEDNYM miejscu" - nav_model.NAV_STRUCTURE is
        # that place for ORDER; this dict is just its runtime mirror,
        # since which pages exist can change without a restart).
        self._page_index = {}

        def _add_page(page_id, widget):
            self._page_index[page_id] = self.stacked_widget.count()
            self.stacked_widget.addWidget(widget)

        # "MAIN VIEW" (was "ENTRY GATE") - this page will host switchable
        # synoptic screens once the Synoptic Editor integration lands;
        # PageEntryGate/self.page_entry_gate keep their internal names for
        # now since renaming the class is a separate, larger refactor with
        # no behavior change of its own. ALWAYS ON (feature_config.
        # ALWAYS_ON_FEATURES) - always constructed first, so index 0 is
        # always Main View regardless of what else is enabled.
        self.page_entry_gate = PageEntryGate(self.tag_manager, switching_counters=self.switching_counters,
                                              service_notes=self.service_notes)
        _add_page("main_view", self.page_entry_gate)

        # ALWAYS ON.
        self.page_di = PageDigitalInputs(self.tag_manager, self.access_manager,
                                          switching_counters=self.switching_counters, service_notes=self.service_notes)
        _add_page("digital_inputs", self.page_di)

        self.page_ai = None
        if is_feature_enabled(self.enabled_features, "analog_inputs"):
            self.page_ai = PageAnalogInputs(self.tag_manager, self.access_manager)
            _add_page("analog_inputs", self.page_ai)

        # ALWAYS ON.
        self.page_do = PageControlOutputs(self.tag_manager, self.access_manager, service_notes=self.service_notes)
        _add_page("control_outputs", self.page_do)

        # Task (page-split): SYSTEM ALARMOWY is now 3 pages, not 1 - see
        # nav_model.py's own module docstring. All three read the SAME
        # live IntrusionManager instance; Overview and History/
        # Configuration are only ever constructed when the whole module
        # ("intrusion") is on (Konfiguracja/Historia's own sub-toggles
        # only matter once that's already true - see
        # nav_model.intrusion_subpage_available()).
        self.page_intrusion_overview = None
        self.page_intrusion_history = None
        self.page_intrusion_config = None
        if is_feature_enabled(self.enabled_features, "intrusion"):
            self.page_intrusion_overview = PageIntrusionOverview(
                self.intrusion_manager, self.access_manager, audit_logger=self.audit_logger)
            _add_page("intrusion_overview", self.page_intrusion_overview)
            if is_feature_enabled(self.enabled_features, "intrusion_history"):
                self.page_intrusion_history = PageIntrusionHistory(self.intrusion_manager, self.access_manager)
                _add_page("intrusion_history", self.page_intrusion_history)
            if is_feature_enabled(self.enabled_features, "intrusion_config"):
                self.page_intrusion_config = PageIntrusionConfiguration(
                    self.intrusion_manager, self.access_manager, audit_logger=self.audit_logger,
                    on_zones_or_lines_changed=self.page_intrusion_overview.refresh)
                _add_page("intrusion_config", self.page_intrusion_config)

        self.page_power = None
        if is_feature_enabled(self.enabled_features, "power_quality"):
            self.page_power = PagePowerQuality(self.tag_manager)
            _add_page("power_quality", self.page_power)

        self.page_trends = None
        if is_feature_enabled(self.enabled_features, "trends"):
            self.page_trends = PageTrends(self.tag_manager, self.historian, self.project_manager)
            _add_page("trends", self.page_trends)

        # ALWAYS ON: Event Recorder, Alarms, Audit Log (Task's own list -
        # "podstawowa diagnostyka").
        self.page_events = PageEventRecorder(self.tag_manager)
        _add_page("events", self.page_events)
        self.page_alarms = PageAlarms(self.alarm_manager, self.access_manager)
        _add_page("alarms", self.page_alarms)
        self.page_audit = PageAuditLog(self.audit_logger, self.access_manager)
        _add_page("audit_log", self.page_audit)

        self.page_topology = None
        if is_feature_enabled(self.enabled_features, "system_topology"):
            self.page_topology = PageSystemTopology(self.tag_manager)
            _add_page("system_topology", self.page_topology)

        self.page_bus_diagnostics = None
        if is_feature_enabled(self.enabled_features, "bus_diagnostics"):
            self.page_bus_diagnostics = PageBusDiagnostics(self.device_manager, self.driver_manager, self.access_manager)
            _add_page("bus_diagnostics", self.page_bus_diagnostics)

        # Task (page-split): ZABEZPIECZENIA is now 2 independent pages -
        # see nav_model.py's own module docstring. Elektryczne is the
        # direct successor of the old single Protection Settings page
        # (still "protection_settings" underneath); Procesowe is a
        # brand-new, independently-toggled module with its own core
        # manager (see epw_core.py's _start_process_protection()).
        self.page_protection_electrical = None
        if is_feature_enabled(self.enabled_features, "protection_settings"):
            self.page_protection_electrical = PageProtectionElectrical(self.tag_manager, self.access_manager)
            _add_page("protection_electrical", self.page_protection_electrical)

        self.page_protection_process = None
        if is_feature_enabled(self.enabled_features, "protection_process"):
            self.page_protection_process = PageProtectionProcess(self.process_protection_manager, self.access_manager)
            _add_page("protection_process", self.page_protection_process)

        # Engineer Mode reuses Protection Settings' (Elektryczne's) own
        # ProtectionManager instance (verifies the ACTUAL configured
        # protection settings, not a blank one) - see nav_model.
        # engineer_mode_available()'s own docstring for why it's
        # therefore only ever available when Protection Settings is
        # too, regardless of its own toggle.
        self.page_engineer_mode = None
        if self.page_protection_electrical is not None and engineer_mode_available(self.enabled_features) \
                and is_feature_enabled(self.enabled_features, "engineer_mode"):
            self.page_engineer_mode = PageEngineerMode(self.tag_manager,
                                                         self.page_protection_electrical.protection_manager,
                                                         self.access_manager, self.audit_logger)
            _add_page("engineer_mode", self.page_engineer_mode)

        content_layout.addWidget(self.stacked_widget, stretch=1)

        self.nav_tree.populate(self.enabled_features)
        self._current_page_id = "main_view"
        self.stacked_widget.setCurrentIndex(self._page_index["main_view"])
        self.nav_tree.set_current_page("main_view")
        self.nav_tree.page_requested.connect(self._navigate_to)

        self.setup_statusbar()

        # Timers
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()
        
        self.access_timeout_timer = QTimer(self)
        self.access_timeout_timer.setSingleShot(True)
        self.access_timeout_timer.timeout.connect(self.on_access_timeout)

        # Database size warning (Task B3) - the database keeps growing
        # during a run, so this indicator needs to be re-checked
        # periodically, not just at construction/theme-change time. A
        # plain row-count/file-size query is cheap; 60s matches
        # Historian's own RETENTION_CHECK_INTERVAL_S as "how often is
        # reasonable for a background administrative check".
        self.db_size_check_timer = QTimer(self)
        self.db_size_check_timer.timeout.connect(self._refresh_db_size_warning_indicator)
        self.db_size_check_timer.start(60_000)

        # Screen sleep (blank the display after idle time) - independent
        # of the 5-minute access-timeout above: this never changes
        # access_manager.level or logs anyone out, it only blanks the
        # screen. Configurable idle time (Settings > Screen Sleep...),
        # persisted machine-locally (window_state.py) like window
        # geometry, not project data.
        self.screen_sleep_overlay = ScreenSleepOverlay(self)
        self.screen_sleep_overlay.woken.connect(self.exit_screen_sleep)
        self.screen_sleep_timer = QTimer(self)
        self.screen_sleep_timer.setSingleShot(True)
        self.screen_sleep_timer.timeout.connect(self.enter_screen_sleep)
        self._screen_sleep_minutes = window_state.load_screen_sleep_minutes()
        self._restart_screen_sleep_timer()

        # Single source of truth for the top-bar label: whatever raises or
        # lowers access_manager.level (a PIN prompt here, a Logout click, a
        # timeout, or - in future - some other page) flows back through
        # this one signal instead of every call site updating the label
        # itself.
        self.access_manager.level_changed.connect(self._update_access_label)
        self._update_access_label()

        # COMM status reacts to real Device.*.Status tags instead of being
        # a permanently-hardcoded "COMM: OK".
        self.tag_manager.tag_changed.connect(self.on_comm_tag_changed)
        self.update_comm_status()
        self.tag_manager.tag_changed.connect(self._on_intrusion_tag_changed)

        # "Alarms: X" was a permanently-hardcoded "Alarms: 0" - now reacts
        # to the real AlarmManager (see page_alarms.py / epw_core.py for
        # what actually raises alarms today). Seeded from the current
        # count directly at construction (same "don't rely solely on a
        # future signal" pattern as the Device Status panel/System
        # Topology/time-sync indicator fixes), not just the live signal.
        if self.alarm_manager is not None and hasattr(self.alarm_manager, "alarms_changed"):
            self.alarm_manager.alarms_changed.connect(self._update_alarm_counter)
        self._update_alarm_counter()

        # Install event filter to track user activity
        self._event_filter_installed = False
        QApplication.instance().installEventFilter(self)
        self._event_filter_installed = True

    def shutdown_gui(self):
        """Explicit, idempotent GUI teardown. MUST run before this
        MainWindow instance is garbage-collected - not just "nice to have".

        installEventFilter(self) above registers this object as a raw
        pointer inside QApplication's own internal filter list.
        QApplication does NOT own it via Qt's normal parent-child
        mechanism (unlike self.clock_timer/self.access_timeout_timer,
        which are QTimer(self) and get cleaned up automatically when this
        widget's C++ side is destroyed). If this MainWindow's C++ object
        is deleted while still registered, QApplication is left holding a
        dangling pointer - crashing (SIGSEGV / exit 139, "access
        violation" under faulthandler) the next time Qt walks its filter
        list, which can happen as late as interpreter shutdown if nothing
        ever explicitly closed the window (e.g. a script that constructs
        a MainWindow, asserts things, and exits without calling close()).

        Root-caused by removing installEventFilter() entirely in
        isolation and confirming the crash disappeared, before adding
        this proper removeEventFilter()-based fix instead - see
        SESSION_REPORT.md.

        The same dangling-pointer risk applies to
        self._keyboard_controller (also installEventFilter()'d on
        QApplication, for the same reason) - removed here too.

        Called from closeEvent() (interactive close / File > Exit), and
        should also be called explicitly by any script that constructs a
        MainWindow without ever showing/closing it through the normal Qt
        event loop (main.py after app.exec() returns; test scripts before
        they exit)."""
        if getattr(self, "_gui_shutdown_done", False):
            return
        self._gui_shutdown_done = True
        if self._event_filter_installed:
            QApplication.instance().removeEventFilter(self)
            self._event_filter_installed = False
        QApplication.instance().removeEventFilter(self._keyboard_controller)
        # The on-screen keyboard windows (Part 2 of the task: real
        # floating windows that now stay open across field switches, not
        # a docked bar auto-hidden on every OK) have no Qt parent, so
        # they won't be cleaned up automatically just because this
        # MainWindow closes - hide them explicitly instead of leaving a
        # stray floating window on screen after the app is gone.
        self._keyboard_controller.hide_all()
        self.clock_timer.stop()
        self.access_timeout_timer.stop()
        self.db_size_check_timer.stop()
        # Trends page (Task): a background QThread doing a HISTORY-mode
        # DB query, or a still-ticking LIVE-mode timer, left running past
        # process exit is the same class of dangling-callback risk this
        # whole method exists to prevent for everything else it stops.
        # May be None (feature-configuration toggle - Task: "okno
        # konfiguracji funkcji" - left the page never constructed).
        if self.page_trends is not None:
            self.page_trends.shutdown()
        # Bus Diagnostics' own refresh QTimer - same reasoning.
        if self.page_bus_diagnostics is not None:
            self.page_bus_diagnostics.shutdown()

    def setup_menu(self):
        menubar = self.menuBar()

        # --- File: fully functional -------------------------------------
        file_menu = menubar.addMenu(tr("menu.file"))
        self._file_actions = {}

        def _add(key, slot, separator_before=False):
            if separator_before:
                file_menu.addSeparator()
            action = file_menu.addAction(tr(key))
            action.triggered.connect(slot)
            self._file_actions[key] = action
            return action

        _add("menu.file_new", self._file_new_project)
        _add("menu.file_open", self._file_open_project)
        _add("menu.file_save", self._file_save_project)
        _add("menu.file_save_as", self._file_save_project_as)
        _add("menu.file_export", self._file_export_project, separator_before=True)
        _add("menu.file_import", self._file_import_project)
        _add("menu.file_exit", lambda: self.close(), separator_before=True)

        # --- Edit: removed entirely (was an empty placeholder) ----------

        # --- View: Fullscreen Mode (convenience, not security - see
        # enter_kiosk_mode()/_on_fullscreen_toggled() for how this stays
        # distinct from Kiosk Mode) ---------------------------------------
        view_menu = menubar.addMenu(tr("menu.view"))
        self._fullscreen_action = view_menu.addAction(tr("menu.view_fullscreen"))
        self._fullscreen_action.setCheckable(True)
        self._fullscreen_action.setShortcut(QKeySequence(Qt.Key.Key_F11))
        self._fullscreen_action.toggled.connect(self._on_fullscreen_toggled)

        # --- Project: Properties + Recently opened -----------------------
        # (was an empty placeholder menu; this is its first real content -
        # menu.devices removed entirely, its natural content - bus config/
        # device list/scan - needs a Modbus driver that doesn't exist yet,
        # see SESSION_REPORT.md).
        project_menu = menubar.addMenu(tr("menu.project"))
        act_project_properties = project_menu.addAction(tr("menu.project_properties"))
        act_project_properties.triggered.connect(self._open_project_properties_dialog)

        project_menu.addSeparator()
        self._recent_projects_menu = project_menu.addMenu(tr("menu.project_recent"))
        # Rebuilt on demand right before it's shown, not kept in sync
        # eagerly - the list only ever changes via Open/Save As/clicking
        # an entry here/Clear, all of which are user actions this same
        # window mediates, so "about to show" is always fresh enough and
        # needs no separate change-notification plumbing.
        self._recent_projects_menu.aboutToShow.connect(self._refresh_recent_projects_menu)

        # --- Tools: general Historian tag-trend export -------------------
        # (was an empty placeholder menu; this is its first real action)
        tools_menu = menubar.addMenu(tr("menu.tools"))
        act_export_history = tools_menu.addAction(tr("menu.tools_export_history"))
        act_export_history.triggered.connect(self._open_historian_export_dialog)

        # Task: "Eksportuj liste sygnalow..." - a plain "pick a location,
        # write the file" action, same shape as _file_export_project()
        # below, not a whole configuration dialog (there's nothing to
        # configure - the export is always "every tag, right now"). No
        # access gate: read-only, and every GUI page in this app is
        # already viewable at User level with no PIN (same reasoning
        # backend/api.py's own GET endpoints already document).
        act_export_tags = tools_menu.addAction(tr("menu.tools_export_tag_list"))
        act_export_tags.triggered.connect(self._export_tag_list)

        # Task: "Tryb prezentacji" - Engineer-only (same hidden+disabled,
        # re-checked-on-level-change pattern as Training Mode/Kiosk
        # Mode's own menu entries), re-verified again at click time in
        # _open_presentation_dialog() below in case access was lost
        # between the menu opening and the click.
        tools_menu.addSeparator()
        self._act_presentation_mode = tools_menu.addAction(tr("menu.tools_presentation_mode"))
        self._act_presentation_mode.triggered.connect(self._open_presentation_dialog)
        self._refresh_presentation_mode_action_visibility()
        self.access_manager.level_changed.connect(self._refresh_presentation_mode_action_visibility)

        # --- Settings: Language + Change PIN popups ---------------------
        # (was a full page in the left nav; now menu-driven QDialogs)
        settings_menu = menubar.addMenu(tr("menu.settings"))
        self._settings_actions = {}
        act_lang = settings_menu.addAction(tr("menu.settings_language"))
        act_lang.triggered.connect(self._open_language_dialog)
        self._settings_actions["menu.settings_language"] = act_lang
        act_pin = settings_menu.addAction(tr("menu.settings_change_pin"))
        act_pin.triggered.connect(self._open_change_pin_dialog)
        self._settings_actions["menu.settings_change_pin"] = act_pin
        act_sleep = settings_menu.addAction(tr("menu.settings_screen_sleep"))
        act_sleep.triggered.connect(self._open_screen_sleep_dialog)
        self._settings_actions["menu.settings_screen_sleep"] = act_sleep
        act_keyboard = settings_menu.addAction(tr("menu.settings_keyboard"))
        act_keyboard.setCheckable(True)
        act_keyboard.setChecked(self.keyboard_enabled)
        act_keyboard.toggled.connect(self._on_keyboard_toggled)
        self._settings_actions["menu.settings_keyboard"] = act_keyboard
        act_theme = settings_menu.addAction(tr("menu.settings_theme"))
        act_theme.triggered.connect(self._open_theme_dialog)
        self._settings_actions["menu.settings_theme"] = act_theme

        # Feature Configuration (Task: "okno konfiguracji, w ktorym
        # wlacza i wylacza sie poszczegolne funkcje sterownika") -
        # Engineer only, same hidden+disabled belt-and-suspenders gate
        # as Training Mode/Kiosk Mode just below, re-checked again at
        # click time inside FeatureConfigDialog itself (EPWCore.
        # set_feature_enabled() re-verifies the level regardless).
        self._act_feature_config = settings_menu.addAction(tr("menu.settings_feature_config"))
        self._act_feature_config.triggered.connect(self._open_feature_config_dialog)
        self._refresh_feature_config_action_visibility()
        self.access_manager.level_changed.connect(self._refresh_feature_config_action_visibility)

        # MQTT integration (Task: "integracja MQTT") - Engineer only,
        # same hidden+disabled belt-and-suspenders gate as Feature
        # Configuration just above (re-checked again at Save time inside
        # MqttManager.configure() itself regardless).
        self._act_mqtt_config = settings_menu.addAction(tr("menu.settings_mqtt"))
        self._act_mqtt_config.triggered.connect(self._open_mqtt_config_dialog)
        self._refresh_mqtt_config_action_visibility()
        self.access_manager.level_changed.connect(self._refresh_mqtt_config_action_visibility)

        # Data Retention (Task: feature/retention-and-test-fix, B4) -
        # Engineer only, same hidden+disabled belt-and-suspenders gate as
        # Feature Configuration/MQTT just above (re-checked again at Save
        # time inside Historian.configure_retention()/AuditLogger.
        # configure_retention() themselves regardless).
        self._act_data_retention = settings_menu.addAction(tr("menu.settings_data_retention"))
        self._act_data_retention.triggered.connect(self._open_data_retention_dialog)
        self._refresh_data_retention_action_visibility()
        self.access_manager.level_changed.connect(self._refresh_data_retention_action_visibility)

        # Training Mode (Task: tryb cwiczebny) - Engineer only, same
        # visible/enabled gate as Kiosk Mode below (hidden AND disabled
        # below Engineer - belt and suspenders), re-checked again at
        # click time in _on_training_mode_toggled() in case access was
        # lost between the menu opening and the click. A plain checkable
        # action (unlike Kiosk Mode, this has no PIN-gated exit and no
        # window-state changes - flipping it back off is exactly as easy
        # as turning it on, by design: it's a teaching aid, not a lockout).
        settings_menu.addSeparator()
        self._act_training_mode = settings_menu.addAction(tr("menu.settings_training_mode"))
        self._act_training_mode.setCheckable(True)
        self._act_training_mode.setChecked(self.training_mode.active if self.training_mode is not None else False)
        self._act_training_mode.toggled.connect(self._on_training_mode_toggled)
        self._refresh_training_mode_action_visibility()
        self.access_manager.level_changed.connect(self._refresh_training_mode_action_visibility)

        # Kiosk Mode - Engineer only (visible/clickable only at that
        # level; re-checked again at click time in _on_kiosk_action_triggered()
        # in case access was lost between the menu opening and the click,
        # same re-verification pattern as every Force button in this app).
        # Bug 4: this entry now also serves as the exit path while already
        # in kiosk, provided the level is Engineer - see
        # _refresh_kiosk_action_visibility()/exit_kiosk_mode(). Exiting is
        # still only ever reachable through the Engineer PIN gate
        # (_kiosk_authorize_exit(), the same one closeEvent() uses) -
        # closing the program remains the other, unchanged way out.
        settings_menu.addSeparator()
        self._act_kiosk = settings_menu.addAction(tr("menu.settings_kiosk_mode"))
        self._act_kiosk.triggered.connect(self._on_kiosk_action_triggered)
        self._refresh_kiosk_action_visibility()
        self.access_manager.level_changed.connect(self._refresh_kiosk_action_visibility)
        # Bug 4: menu bar appears at Engineer level while in Kiosk Mode
        # (service work without leaving the kiosk) and disappears again
        # the instant the level drops - manual downgrade or the 5-minute
        # auto-logout both flow through this same signal.
        self.access_manager.level_changed.connect(self._refresh_kiosk_menubar_visibility)

        # --- Help: Topics/Index (real content, Windows 98 Help style) + About
        help_menu = menubar.addMenu(tr("menu.help"))
        self._act_help_topics = help_menu.addAction(tr("menu.help_topics"))
        # F1 opens Help from anywhere in the program, at every access
        # level, with no PIN (task requirement). A QAction's shortcut only
        # fires while (one of) its owning widget(s) is visible - a QMenu
        # hidden along with the QMenuBar in Kiosk Mode below Engineer (see
        # _refresh_kiosk_menubar_visibility()) stops the shortcut from
        # firing too, confirmed empirically (QTest.keyClick(F1) was a
        # no-op with the menu bar hidden). Registering the SAME action on
        # `self` as well - the MainWindow itself, which stays visible the
        # entire time Kiosk Mode is active - keeps the shortcut alive
        # regardless of the menu bar's own visibility, while the menu item
        # itself is unaffected (a QAction can belong to more than one
        # widget). Deliberately NOT access-gated, unlike almost everything
        # else reachable from this menu bar.
        self._act_help_topics.setShortcut(QKeySequence(Qt.Key.Key_F1))
        self._act_help_topics.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.addAction(self._act_help_topics)
        self._act_help_topics.triggered.connect(lambda: self._open_help_window("contents"))
        self._act_help_index = help_menu.addAction(tr("menu.help_index"))
        self._act_help_index.triggered.connect(lambda: self._open_help_window("index"))
        help_menu.addSeparator()
        act_about = help_menu.addAction(tr("menu.help_about"))
        act_about.triggered.connect(self._open_about_dialog)

    def _open_help_window(self, tab: str = "contents"):
        """Reuses one HelpWindow instance across repeated F1 presses/menu
        clicks (rather than rebuilding it each time) so Back/Forward
        history survives - see help_window.py."""
        from epw_os.gui.widgets.help_window import HelpWindow
        if getattr(self, "_help_window", None) is None:
            self._help_window = HelpWindow(parent=self)
        self._help_window.select_tab(tab)
        self._help_window.show()
        self._help_window.raise_()
        self._help_window.activateWindow()

    def _open_about_dialog(self):
        from epw_os.gui.widgets.about_dialog import AboutDialog
        AboutDialog(self).exec()

    def _open_historian_export_dialog(self):
        if self.historian is None:
            self._warn("Historian is not available in this session.")
            return
        from epw_os.gui.widgets.historian_export_dialog import HistorianExportDialog
        HistorianExportDialog(self.historian, self.tag_manager, self).exec()

    def _export_tag_list(self):
        """Task: signal-list export for Logic Studio/Synoptic Editor.
        build_tag_list_export() (epw_os.core.tag_export) is the exact
        same function the REST API's GET /api/v1/tags/export calls -
        this menu action just writes its result to a file instead of
        returning it as a response. Read-only - never touches
        project.json (see that module's own docstring)."""
        import json
        from epw_os.core.tag_export import build_tag_list_export
        export = build_tag_list_export(self.tag_manager, self.project_manager)
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dialog.tag_list_export_title"), "epw_signal_list.json", tr("dialog.tag_list_filter"))
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export, f, ensure_ascii=False, indent=2)
        except OSError as e:
            self._warn(tr("dialog.tag_list_export_failed", error=e))
            return
        self._info(tr("dialog.tag_list_exported", n=export["tag_count"], path=path))

    def _refresh_presentation_mode_action_visibility(self, *_):
        """Same belt-and-suspenders pattern as Training Mode/Kiosk
        Mode's own menu entries: hidden AND disabled below Engineer."""
        is_engineer = self.access_manager.has_access(AccessLevel.ENGINEER)
        self._act_presentation_mode.setVisible(is_engineer)
        self._act_presentation_mode.setEnabled(is_engineer)

    def _open_presentation_dialog(self):
        # Re-verified at click time - access could have lapsed between
        # the menu opening and the click (same re-verification pattern
        # as every other Engineer-gated action in this app).
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.deny_access(AccessLevel.ENGINEER, "Presentation Mode")
            return
        if self.presentation_mode is None:
            self._warn("Presentation Mode is not available in this session.")
            return
        # Reused across repeated clicks (same pattern as _open_help_window())
        # so a demo in progress isn't lost if the menu item is clicked again.
        if getattr(self, "_presentation_dialog", None) is None:
            from epw_os.gui.widgets.presentation_dialog import PresentationDialog
            self._presentation_dialog = PresentationDialog(
                self.presentation_mode, self.training_mode, self.access_manager,
                started_signal=self._presentation_started_signal,
                stopped_signal=self._presentation_stopped_signal,
                paused_signal=self._presentation_paused_signal,
                resumed_signal=self._presentation_resumed_signal,
                step_signal=self._presentation_step_signal,
                parent=self,
            )
        self._presentation_dialog.show()
        self._presentation_dialog.raise_()
        self._presentation_dialog.activateWindow()

    def _open_language_dialog(self):
        """Task: switch language without restarting - LanguageDialog
        itself only ever persists the choice (unchanged by this task, see
        its own docstring); detecting whether it actually changed, and
        acting on that, happens here, the one call site. Compares
        project_manager's saved value before/after exec() rather than
        having the dialog report back directly - simpler than adding a
        return channel to a dialog whose only other caller (isolated
        widget tests) has no interest in it either.

        The actual rebuild is deferred (QTimer.singleShot(0, ...)), not
        called straight from here: this method is itself a slot running
        on THIS window, and the callback's job is to tear this same
        window down - doing that before this call stack (and the Settings
        menu's own click handling) has fully unwound is exactly the
        "destroyed while still executing" hazard shutdown_gui()'s own
        docstring warns about elsewhere. Deferring to the next event-loop
        iteration is the same pattern this codebase already uses for
        showMaximized()/enter_kiosk_mode() at construction time."""
        if self.project_manager is None:
            LanguageDialog(self.project_manager, self).exec()
            return
        old_language = self.project_manager.get_language()
        LanguageDialog(self.project_manager, self).exec()
        new_language = self.project_manager.get_language()
        if new_language != old_language and self._language_changed_callback is not None:
            QTimer.singleShot(0, self._language_changed_callback)

    def _open_change_pin_dialog(self):
        # No keyboard_enabled here (this task): ChangePinDialog's embedded
        # keypad is always present now, independent of the Settings
        # toggle - see ChangePinDialog/PinChangeSection docstrings and
        # SESSION_REPORT.md.
        ChangePinDialog(self.access_manager, self).exec()

    def _open_screen_sleep_dialog(self):
        ScreenSleepDialog(self._screen_sleep_minutes, self).exec()

    def _open_theme_dialog(self):
        ThemeDialog(self.theme_manager, self).exec()

    def _refresh_feature_config_action_visibility(self, *_):
        """Engineer-only - both invisible and disabled below that level,
        same belt-and-suspenders pattern as Training Mode/Kiosk Mode's
        own entries."""
        is_engineer = self.access_manager.has_access(AccessLevel.ENGINEER)
        self._act_feature_config.setVisible(is_engineer)
        self._act_feature_config.setEnabled(is_engineer)

    def _refresh_mqtt_config_action_visibility(self, *_):
        """Engineer-only, same belt-and-suspenders pattern as Feature
        Configuration just above."""
        is_engineer = self.access_manager.has_access(AccessLevel.ENGINEER)
        self._act_mqtt_config.setVisible(is_engineer)
        self._act_mqtt_config.setEnabled(is_engineer)

    def _open_mqtt_config_dialog(self):
        if self.mqtt_manager is None:
            self._warn(tr("mqtt.unavailable_in_this_session"))
            return
        from epw_os.gui.widgets.mqtt_config_dialog import MqttConfigDialog
        MqttConfigDialog(self.mqtt_manager, self.access_manager, self.mqtt_status_changed_signal, self).exec()

    def _refresh_data_retention_action_visibility(self, *_):
        """Engineer-only, same belt-and-suspenders pattern as Feature
        Configuration/MQTT above."""
        is_engineer = self.access_manager.has_access(AccessLevel.ENGINEER)
        self._act_data_retention.setVisible(is_engineer)
        self._act_data_retention.setEnabled(is_engineer)

    def _open_data_retention_dialog(self):
        if self.historian is None and self.audit_logger is None:
            return
        from epw_os.gui.widgets.data_retention_dialog import DataRetentionDialog
        DataRetentionDialog(self.historian, self.audit_logger, self.access_manager, self).exec()
        self._refresh_db_size_warning_indicator()

    def _open_feature_config_dialog(self):
        """FeatureConfigDialog applies each toggle IMMEDIATELY as it's
        clicked (see its own docstring) - by the time exec() returns
        here, zero or more features may have actually changed. Same
        before/after comparison + deferred rebuild as
        _open_language_dialog() above, and the same reasoning for why
        it's deferred (this method is itself a slot on the window the
        callback is about to tear down)."""
        if self.feature_config is None:
            return
        before = self.feature_config.get_enabled_features()
        FeatureConfigDialog(self.feature_config, self.access_manager, self).exec()
        after = self.feature_config.get_enabled_features()
        if after != before and self._feature_config_changed_callback is not None:
            QTimer.singleShot(0, self._feature_config_changed_callback)

    def _on_theme_changed(self, _index):
        """Fires on EVERY theme change, regardless of source - the
        Settings dialog, a "System.Theme" tag write from logic, or a
        restored-on-startup value (Task: menu and tag must always agree,
        and the switch must be immediate, no restart).

        Re-applying the stylesheet alone (a single setStyleSheet() call)
        already re-colors every QSS-driven widget in the whole app -
        that's most of the UI. What's left are the handful of places
        that set a color directly in Python rather than through the QSS
        (see SESSION_REPORT.md's "moved from" list): MainWindow's own
        top-bar labels, refreshed right here, and each page's own
        dynamic colors (Protection's tree, Alarms' rows, Control
        Outputs' Force button, ...) - those pages each subscribe to
        get_theme_manager().theme_changed directly in their own
        __init__ (see e.g. page_protection.py), so they refresh
        themselves without MainWindow needing to know they exist."""
        self.setStyleSheet(build_stylesheet(self.theme_manager.current_colors()))
        self.update_comm_status()
        self._refresh_mode_button_style()
        self._update_alarm_counter()
        self._update_access_label()
        self._update_status_user_label()
        self._check_db_health()
        status = getattr(self, "_last_time_sync_status", None)
        if status is not None:
            self._update_time_sync_label(status, getattr(self, "_last_time_sync_detail", ""))
        self._refresh_training_mode_indicator()
        self._refresh_presentation_indicator()
        self._refresh_api_warning_indicator()
        self._refresh_db_size_warning_indicator()
        self._refresh_intrusion_indicator()

    def _on_keyboard_toggled(self, checked: bool):
        """Settings > On-Screen Keyboard - takes effect immediately (the
        next field focused reads self.keyboard_enabled through the
        OnScreenKeyboardController's callable), not just on next launch.
        Turning it off also closes whatever keyboard window happens to
        be open right now (Part 2 of the task: the keyboard otherwise
        stays open across field switches, so "off" has to mean off, not
        just "stop reopening")."""
        self.keyboard_enabled = bool(checked)
        window_state.save_keyboard_enabled(self.keyboard_enabled)
        if not self.keyboard_enabled:
            self._keyboard_controller.hide_all()

    def _refresh_training_mode_action_visibility(self, *_):
        """Training Mode's Settings entry is Engineer-only - both invisible
        and disabled below that level (same belt-and-suspenders pattern as
        Kiosk Mode's own entry just below): hidden so it isn't
        discoverable, disabled so even a stale reference to the QAction
        can't trigger it. Unlike Kiosk Mode's entry, this one's checked
        state is never touched here - a level drop does not itself turn
        Training Mode off (Task says nothing about that, and doing so
        silently would be its own kind of surprise: an Engineer who
        dropped to Operator to test a permission and comes back up to
        Engineer should find the mode exactly as they left it)."""
        is_engineer = self.access_manager.has_access(AccessLevel.ENGINEER)
        self._act_training_mode.setVisible(is_engineer)
        self._act_training_mode.setEnabled(is_engineer)

    def _on_training_mode_toggled(self, checked: bool):
        """Re-verify access at click/toggle time, not just menu-open time -
        the 5-minute auto-logout could have fired in between (same
        re-verification pattern as every Force button and Kiosk Mode's own
        toggle in this app). If access was lost, the checkbox is put back
        to the actual state instead of trusting what the click implied -
        `checked` here is what the user just tried to set it to, which may
        not be what's really about to happen."""
        if self.training_mode is None:
            return
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.deny_access(AccessLevel.ENGINEER, "Training Mode")
            self._act_training_mode.blockSignals(True)
            self._act_training_mode.setChecked(self.training_mode.active)
            self._act_training_mode.blockSignals(False)
            self._refresh_training_mode_action_visibility()
            return
        self.training_mode.set_active(checked, actor=self.access_manager.level)
        self._refresh_training_mode_indicator()

    def _on_presentation_started(self, scenario_name):
        self._refresh_presentation_indicator()

    def _on_presentation_stopped(self):
        self._refresh_presentation_indicator()

    def _refresh_presentation_indicator(self, *_):
        """Task: "wyrazny wskaznik, ze trwa prezentacja - osobny od
        wskaznika Trybu cwiczebnego". A separate permanent status-bar
        widget, its own color (state_info - blue, distinct from
        Training Mode's amber state_caution above) and its own text -
        deliberately does NOT also touch the workspace border the way
        Training Mode's own indicator does: Presentation Mode can only
        ever be active while Training Mode already is too (GRANICE hard
        requirement), so that border is already Training Mode's alone
        to own: doubling it up here would just be two indicators
        fighting over the same border color for no added clarity."""
        active = self.presentation_mode is not None and self.presentation_mode.active
        theme_colors = self.theme_manager.current_colors()
        if active:
            color = theme_colors["state_info"]
            self.lbl_sb_presentation.setText(f" {tr('statusbar.presentation_mode_active')} ")
            self.lbl_sb_presentation.setStyleSheet(
                f"color: {theme_colors['window_bg']}; background-color: {color}; font-weight: bold; padding: 1px 6px;"
            )
            self.lbl_sb_presentation.setToolTip(tr("statusbar.tooltip_presentation_mode"))
            self.lbl_sb_presentation.setVisible(True)
        else:
            self.lbl_sb_presentation.setVisible(False)

    def _refresh_api_warning_indicator(self, *_):
        """Task: DODATKOWO - REST API exposed beyond localhost, signaled
        "w interfejsie" too (not just main.py's startup log). Static
        content (api_host doesn't change without a restart - no live
        reconfiguration UI exists for it), but the STYLING still needs
        to track theme changes like every other status-bar indicator,
        so this is a real refresh method, called once at construction
        and again from _on_theme_changed(), not inlined into __init__."""
        exposed = bool(self.api_host) and not is_local_host(self.api_host)
        if not exposed:
            self.lbl_sb_api_warning.setVisible(False)
            return
        theme_colors = self.theme_manager.current_colors()
        self.lbl_sb_api_warning.setText(f" {tr('statusbar.api_exposed', host=self.api_host)} ")
        self.lbl_sb_api_warning.setStyleSheet(
            f"color: {theme_colors['window_bg']}; background-color: {theme_colors['state_alarm']}; "
            f"font-weight: bold; padding: 1px 6px;"
        )
        self.lbl_sb_api_warning.setToolTip(tr("statusbar.tooltip_api_exposed", host=self.api_host))
        self.lbl_sb_api_warning.setVisible(True)

    def _refresh_db_size_warning_indicator(self, *_):
        """Task B3: "ostrzezenie, gdy baza przekroczy zadany rozmiar" -
        off by default (project_manager.get_db_size_warning_config()'s
        own "enabled": False default, GRANICE). Called once at
        construction, again from _on_theme_changed() (styling must track
        theme changes like every other status-bar indicator), and
        periodically from self.db_size_check_timer (unlike the static
        api_warning above, the database genuinely grows during a run)."""
        if self.project_manager is None:
            self.lbl_sb_db_warning.setVisible(False)
            return
        cfg = self.project_manager.get_db_size_warning_config()
        if not cfg.get("enabled"):
            self.lbl_sb_db_warning.setVisible(False)
            return
        try:
            from epw_os.db.database import get_db_stats
            size_bytes = get_db_stats()["file_size_bytes"]
        except Exception:
            self.lbl_sb_db_warning.setVisible(False)
            return
        threshold_bytes = int(cfg.get("threshold_mb", 500) or 500) * 1024 * 1024
        if size_bytes < threshold_bytes:
            self.lbl_sb_db_warning.setVisible(False)
            return
        size_mb = size_bytes / (1024 * 1024)
        theme_colors = self.theme_manager.current_colors()
        self.lbl_sb_db_warning.setText(f" {tr('statusbar.db_size_exceeded', size=f'{size_mb:.0f}')} ")
        self.lbl_sb_db_warning.setStyleSheet(
            f"color: {theme_colors['window_bg']}; background-color: {theme_colors['state_alarm']}; "
            f"font-weight: bold; padding: 1px 6px;"
        )
        self.lbl_sb_db_warning.setToolTip(tr("statusbar.tooltip_db_size_exceeded"))
        self.lbl_sb_db_warning.setVisible(True)

    def _refresh_training_mode_indicator(self, *_):
        """Task: "WYRAZNY, staly wskaznik... niemozliwe do przeoczenia -
        inny kolor paska statusu albo ramka wokol obszaru roboczego." Does
        both, deliberately redundant: a bordered workspace alone could be
        missed if a page's own content fills the frame edge to edge on a
        small screen, and a status-bar-only change could be missed if the
        operator's eyes are on the synoptic, not the bottom of the window.
        Together, whichever the operator happens to be looking at, the
        mode is unmistakable. This is the single place that reads
        self.training_mode.active for display purposes - called after
        every toggle and after every theme change (colors are
        theme-dependent), so it's always in sync with both."""
        active = self.training_mode is not None and self.training_mode.active
        theme_colors = self.theme_manager.current_colors()
        if active:
            color = theme_colors["state_caution"]
            self.lbl_sb_training.setText(f" {tr('statusbar.training_mode_active')} ")
            self.lbl_sb_training.setStyleSheet(
                f"color: {theme_colors['window_bg']}; background-color: {color}; font-weight: bold; padding: 1px 6px;"
            )
            # Task: podpowiedzi - "wskaznik trybu... tryb cwiczebny". Only
            # meaningful while visible (hidden entirely otherwise, below).
            self.lbl_sb_training.setToolTip(tr("statusbar.tooltip_training_mode"))
            self.lbl_sb_training.setVisible(True)
            self.stacked_widget.setStyleSheet(f"border: 3px solid {color};")
        else:
            self.lbl_sb_training.setVisible(False)
            self.stacked_widget.setStyleSheet("")

    def _on_intrusion_tag_changed(self, tag_name, value, quality):
        """Every zone/line/system state IntrusionManager exposes is a
        real TagManager "Security.*" tag (see intrusion_manager.py) -
        this piggybacks on the tag_changed bridge every other tag-driven
        widget in this app already uses, rather than adding a dedicated
        Qt signal for it. Calls refresh_live() (Task 6: "aktualizuj
        tylko to, co sie zmienilo"), NOT the full refresh() - this fires
        on every single violation/state/fault/lock/suspect change, often
        many times a second, and refresh_live() updates existing cells
        in place instead of tearing down and rebuilding both tables. May
        fire once more even after the feature was just disabled (a
        tag_removed's own tag_changed-shaped echo, if any is still in
        flight) - page_intrusion may already be None by then, same
        "feature toggle, not just a hidden page" tolerance every other
        conditionally-built page in this window now needs."""
        if isinstance(tag_name, str) and tag_name.startswith("Security."):
            if self.page_intrusion_overview is not None:
                self.page_intrusion_overview.refresh_live()
            self._refresh_intrusion_indicator()
            self._refresh_nav_attention_intrusion()

    def _refresh_intrusion_indicator(self, *_):
        """Task: "Stan uzbrojenia MA BYC WIDOCZNY z kazdej strony
        programu, nie tylko z tej jednej. Wykorzystaj pasek statusu albo
        gorny pasek." A permanent status-bar widget, hidden while every
        zone is DISARMED (nothing to announce), colored by the
        system-wide aggregate state (get_system_state()) - ARMED (calm/
        caution amber), EXIT_DELAY/ENTRY_DELAY (caution amber, with the
        remaining seconds - the same aggregate countdown
        EntryCountdownActive/ExitCountdownActive tags signal to logic),
        or ALARM (the same alarm-red used everywhere else in this app).
        Called after every "Security."-prefixed tag change and every
        theme change, same pattern as every other status indicator in
        this window."""
        if self.intrusion_manager is None:
            self.lbl_sb_intrusion.setVisible(False)
            return
        state = self.intrusion_manager.get_system_state()
        theme_colors = self.theme_manager.current_colors()
        if state == ZoneState.DISARMED:
            self.lbl_sb_intrusion.setVisible(False)
            return
        if state == ZoneState.ALARM:
            color = theme_colors["state_alarm"]
            text = tr("statusbar.intrusion_alarm")
            tooltip = tr("statusbar.tooltip_intrusion_status")
        elif state in (ZoneState.EXIT_DELAY, ZoneState.ENTRY_DELAY):
            color = theme_colors["state_caution"]
            # Any one zone's remaining seconds - a system-wide aggregate
            # has no single "the" countdown when more than one zone is
            # mid-delay at once; the Intrusion Alarm page shows every
            # zone's own countdown individually.
            zones = self.intrusion_manager.get_zones()
            remaining = next(
                (self.intrusion_manager.get_countdown_remaining(z["id"]) for z in zones
                 if self.intrusion_manager.get_zone_state(z["id"]) == state),
                0,
            )
            key = "statusbar.intrusion_exit_delay" if state == ZoneState.EXIT_DELAY else "statusbar.intrusion_entry_delay"
            text = tr(key, seconds=remaining)
            tooltip = tr("statusbar.tooltip_intrusion_status")
        else:  # ARMED
            color = theme_colors["state_caution"]
            text = tr("statusbar.intrusion_armed")
            tooltip = tr("statusbar.tooltip_intrusion_status")
        self.lbl_sb_intrusion.setText(f" {text} ")
        self.lbl_sb_intrusion.setStyleSheet(
            f"color: {theme_colors['window_bg']}; background-color: {color}; font-weight: bold; padding: 1px 6px;"
        )
        self.lbl_sb_intrusion.setToolTip(tooltip)
        self.lbl_sb_intrusion.setVisible(True)

    def _refresh_nav_attention_intrusion(self, *_):
        """Task 3: "jesli w grupie jest cos wymagajace uwagi
        (niepotwierdzone alarmy, AKTYWNY ALARM WLAMANIOWY, AWARIA LINII,
        PAMIEC ALARMU), grupa ma to sygnalizowac NAWET GDY JEST
        ZWINIETA" - ALARM (red) while any zone is actually in ALARM
        right now; WARNING (amber) if nothing is alarming THIS INSTANT
        but there's still something to look at (a line fault, or an
        unacknowledged alarm memory left over from an earlier one - see
        intr_alarm_memory.md); otherwise no marker at all."""
        if self.page_intrusion_overview is None or self.intrusion_manager is None:
            return
        from epw_os.gui.widgets.nav_tree import ATTENTION_NONE, ATTENTION_WARNING, ATTENTION_ALARM
        if self.intrusion_manager.get_system_state() == ZoneState.ALARM:
            level = ATTENTION_ALARM
        else:
            any_fault = bool(self.tag_manager.get_value("Security.System.LineFault"))
            any_memory = any(
                self.intrusion_manager.get_alarm_memory(z["id"])["active"]
                for z in self.intrusion_manager.get_zones()
            )
            level = ATTENTION_WARNING if (any_fault or any_memory) else ATTENTION_NONE
        self.nav_tree.set_leaf_attention("intrusion_overview", level)

    def _refresh_kiosk_action_visibility(self, *_):
        """Kiosk Mode's Settings entry is Engineer-only - both invisible
        and disabled below that level (belt and suspenders: hidden so it
        isn't discoverable, disabled so even a stale reference to the
        QAction can't trigger it).

        Bug 4: unlike before, this entry no longer disappears once
        already in kiosk - at Engineer level it stays visible/enabled and
        its label flips to the "exit" wording, so it becomes the way back
        out (see _on_kiosk_action_triggered()/exit_kiosk_mode()) instead
        of leaving "close the app" as the only option. Below Engineer
        it's hidden either way, kiosk or not."""
        is_engineer = self.access_manager.has_access(AccessLevel.ENGINEER)
        self._act_kiosk.setVisible(is_engineer)
        self._act_kiosk.setEnabled(is_engineer)
        self._act_kiosk.setText(
            tr("menu.settings_kiosk_mode_exit") if self.kiosk else tr("menu.settings_kiosk_mode")
        )

    def _refresh_kiosk_menubar_visibility(self, *_):
        """Bug 4: menu bar visibility while IN Kiosk Mode tracks the
        access level - visible at Engineer (so service work can happen
        without ever leaving the kiosk's fullscreen/frameless/PIN-gated
        state) and hidden below it, including after the 5-minute
        auto-logout (both reach here via access_manager.level_changed,
        no new timer). A no-op outside Kiosk Mode - the menu bar is
        always visible there regardless of level, unaffected by this.
        Deliberately does not touch self.kiosk, the frameless/fullscreen
        window flags, or the F11/Esc/double-click guards (all of those
        key off self.kiosk alone, not menu bar visibility) - see
        enter_kiosk_mode()/exit_kiosk_mode() for what actually owns
        those."""
        if not self.kiosk:
            return
        is_engineer = self.access_manager.has_access(AccessLevel.ENGINEER)
        self.menuBar().setVisible(is_engineer)

    def _on_kiosk_action_triggered(self):
        # Re-verify access at click time, not just menu-open time - the
        # 5-minute auto-logout could have fired in between (same
        # defense-in-depth pattern as every Force button in this app).
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.deny_access(AccessLevel.ENGINEER, "Kiosk Mode")
            self._refresh_kiosk_action_visibility()
            return
        if self.kiosk:
            # Bug 4: already in kiosk and Engineer-level (the only way
            # this action is visible/reachable in that state) - this
            # click means "exit", not "enter again".
            self.exit_kiosk_mode()
        else:
            self.enter_kiosk_mode()

    def enter_kiosk_mode(self):
        """Security: fullscreen, borderless, menu bar hidden (unless
        already Engineer - see below), exit gated by Engineer PIN
        (closeEvent()/_kiosk_authorize_exit(), or now also
        exit_kiosk_mode() via Settings > Kiosk Mode - see Bug 4 note
        there) - distinct from View > Fullscreen Mode
        (_on_fullscreen_toggled()), which is pure convenience with no PIN
        and stays exitable by anyone at any time. Kiosk Mode itself (the
        fullscreen/frameless/PIN-gated-exit state, i.e. self.kiosk) is
        still one-way for the lifetime of the process except through that
        one Engineer-gated exit - matches the task's "Kiosk Mode is not
        remembered between runs" requirement, since there is nothing to
        remember beyond this one already-running session, and a plain
        restart without --kiosk always comes back up normal.

        Callable from two places: main.py's --kiosk flag (self.kiosk is
        already True by the time this actually runs - set synchronously
        at construction - but the deferred call itself is still needed,
        since showFullScreen() has no effect before the window is first
        shown) and Settings > Kiosk Mode (called directly, the window is
        already visible - and the caller is necessarily already Engineer,
        since that's the only level the action is reachable at, so the
        menu bar below comes up visible immediately instead of hidden).
        Idempotent either way - re-applying the same flags/fullscreen
        state a second time is harmless."""
        self.kiosk = True
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        # Bug 4: was an unconditional hide - now tracks access level (see
        # _refresh_kiosk_menubar_visibility()), so entering kiosk while
        # already Engineer (the Settings > Kiosk Mode path) shows the bar
        # immediately instead of hiding it only to reveal it a moment
        # later on the next level_changed signal.
        self._refresh_kiosk_menubar_visibility()
        # Fullscreen Mode must not coexist with Kiosk Mode - it would be
        # a second, PIN-free way to alter Kiosk's window state. Disabling
        # the action also disables its F11 shortcut; explicitly
        # unchecking too in case it was already active from before this
        # Engineer logged in.
        self._fullscreen_action.setChecked(False)
        self._fullscreen_action.setEnabled(False)
        self._refresh_kiosk_action_visibility()
        self.showFullScreen()

    def exit_kiosk_mode(self):
        """Bug 4: the one path (besides closing the app, which still
        works exactly as before) that leaves an already-running Kiosk
        Mode session. Reachable only via Settings > Kiosk Mode, and only
        while at Engineer level (_refresh_kiosk_action_visibility() hides
        the action otherwise; _on_kiosk_action_triggered() re-checks
        access again immediately before calling this).

        Still funnels through _kiosk_authorize_exit() - the exact same
        Engineer-PIN gate closeEvent() uses - so this is not a second,
        weaker way out: since the caller here is already Engineer,
        request_access() inside it does not re-prompt, it just confirms
        the level and records KIOSK_EXIT to the audit log, same as it
        would for a close-triggered exit.

        Reverses exactly what enter_kiosk_mode() applied: windowed,
        framed, menu bar unconditionally visible again (no longer
        access-level-dependent - that dependency only applies while
        self.kiosk is True), Fullscreen Mode action re-enabled. Kiosk
        Mode itself stays off for the remainder of this run - a later
        re-entry via this same menu, or a restart with --kiosk, starts a
        fresh kiosk session."""
        if not self._kiosk_authorize_exit():
            return
        self.kiosk = False
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
        self.menuBar().setVisible(True)
        self._fullscreen_action.setEnabled(True)
        self._refresh_kiosk_action_visibility()
        self.showNormal()

    def _on_fullscreen_toggled(self, checked: bool):
        """View > Fullscreen Mode / F11 - convenience, available to every
        access level, no PIN. Menu bar and status bar stay visible
        (plain showFullScreen()/showNormal() never touch either) - unlike
        Kiosk Mode, which explicitly hides the menu bar and requires an
        Engineer PIN to ever get back out."""
        if self.kiosk:
            # Hard requirement: Kiosk Mode owns fullscreen/frameless
            # completely - this convenience toggle (and by extension its
            # F11 shortcut) must be a no-op while it's active, even if
            # something manages to trigger it. enter_kiosk_mode() already
            # disables the action so this path shouldn't normally run,
            # but the check stays here too as the authoritative guard.
            self._fullscreen_action.blockSignals(True)
            self._fullscreen_action.setChecked(False)
            self._fullscreen_action.blockSignals(False)
            return
        if checked:
            self._pre_fullscreen_maximized = self.isMaximized()
            self.showFullScreen()
        else:
            if getattr(self, "_pre_fullscreen_maximized", False):
                self.showMaximized()
            else:
                self.showNormal()

    # ------------------------------------------------------------------
    # File menu
    # ------------------------------------------------------------------

    def _testing(self) -> bool:
        return os.environ.get("EPW_TESTING") == "1"

    def _info(self, text):
        if self._testing():
            return
        QMessageBox.information(self, tr("dialog.info_title"), text)

    def _warn(self, text):
        if self._testing():
            return
        QMessageBox.warning(self, tr("dialog.info_title"), text)

    def deny_access(self, required_level: str, action: str = ""):
        """The one, shared way every page reports 'you can't do that at
        your current level' (Task: real, per-level permissions - User is
        view-only). Reached via self.window().deny_access(...) from any
        page - never a PIN prompt (GRANICE: the operator raises their own
        level deliberately, via the top-bar dropdown - request_access()
        stays reserved for that one flow and for Kiosk Mode's exit gate,
        neither of which this method touches).

        Always records the denial to the audit log, tested-or-not - the
        DOWÓD explicitly checks denials reach audit_log, and skipping
        that under EPW_TESTING would make it untestable. Only the
        informational popup itself is skipped under EPW_TESTING, same as
        _info()/_warn() above (a blocking QMessageBox.exec() would hang
        an automated test).

        `action` is a fixed, untranslated, short English identifier
        (e.g. "Force in Control Outputs") - it's audit-log content, which
        stays in one language regardless of the UI language setting,
        same policy as every other audit_logger.record() call in this
        codebase (see SESSION_REPORT.md's i18n task)."""
        level_name = tr(f"access.{str(required_level).lower()}", default=str(required_level))
        if not self._testing():
            QMessageBox.information(self, tr("access.denied_title"),
                                     tr("access.denied_message", level=level_name))
        if self.audit_logger is not None:
            self.audit_logger.record(
                "ACCESS_DENIED", self.access_manager.level,
                f"{action} requires {required_level}" if action else f"Requires {required_level}",
                success=False,
            )

    def _confirm_discard_changes(self) -> bool:
        """Return True if it is OK to abandon/replace the current project
        (nothing unsaved, or the operator chose Save/Discard). False means
        the operator cancelled and the calling action must abort."""
        if self.project_manager is None or not self.project_manager.is_dirty():
            return True
        if self._testing():
            return True
        resp = QMessageBox.question(
            self, tr("dialog.unsaved_title"), tr("dialog.unsaved_text"),
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if resp == QMessageBox.StandardButton.Cancel:
            return False
        if resp == QMessageBox.StandardButton.Save:
            self.project_manager.save_project()
        return True

    def _project_display_name(self) -> str:
        """Task: the top-bar label shows the operator-given project NAME
        (Project > Properties) once set, falling back to the technical
        project_id identifier (unchanged default: "DEFAULT_PROJECT")
        otherwise - never both, and never translated (it's operator
        data). hasattr() guard: a project_manager without get_metadata()
        (an older/minimal test double) just falls back to project_id,
        same as before this task."""
        if self.project_manager is None:
            return "SUBSTATION 1"
        if hasattr(self.project_manager, "get_metadata"):
            name = (self.project_manager.get_metadata().get("name") or "").strip()
            if name:
                return name
        return self.project_manager.config.get("project_id", "SUBSTATION 1")

    def _refresh_project_label(self):
        if self.project_manager is None:
            return
        self.lbl_project.setText(f"{tr('topbar.project')}: {self._project_display_name()}")

    def _open_project_properties_dialog(self):
        if self._no_project_manager():
            return
        from epw_os.gui.widgets.project_properties_dialog import ProjectPropertiesDialog
        dialog = ProjectPropertiesDialog(
            self.project_manager, self.tag_manager, self.access_manager, self.audit_logger, parent=self,
        )
        if dialog.exec():
            self._refresh_project_label()

    def _refresh_recent_projects_menu(self):
        menu = self._recent_projects_menu
        menu.clear()
        paths = window_state.load_recent_projects()
        if not paths:
            act_empty = menu.addAction(tr("menu.project_recent_empty"))
            act_empty.setEnabled(False)
        else:
            for path in paths:
                exists = os.path.exists(path)
                label = os.path.basename(path)
                if not exists:
                    # Task: a missing file must be shown clearly (grayed
                    # out AND marked), not just silently fail on click.
                    label = f"{label}{tr('menu.project_recent_missing_suffix')}"
                action = menu.addAction(label)
                action.setToolTip(path)
                action.setEnabled(exists)
                if exists:
                    action.triggered.connect(lambda checked=False, p=path: self._open_recent_project(p))
        menu.addSeparator()
        act_clear = menu.addAction(tr("menu.project_recent_clear"))
        act_clear.triggered.connect(self._clear_recent_projects)

    def _open_recent_project(self, path):
        if self._no_project_manager():
            return
        if not self._confirm_discard_changes():
            return
        if self.project_manager.load_from(path):
            window_state.add_recent_project(path)
            self._refresh_project_label()
        else:
            # Same failure path/message as File > Open hitting an invalid
            # project file - not a new error case, just a second way to
            # reach the existing one.
            self._warn(tr("dialog.invalid_project"))

    def _clear_recent_projects(self):
        window_state.clear_recent_projects()

    def _no_project_manager(self) -> bool:
        if self.project_manager is None:
            self._warn("Project manager unavailable in this context.")
            return True
        return False

    def _file_new_project(self):
        if self._no_project_manager():
            return
        if not self._confirm_discard_changes():
            return
        self.project_manager.new_project()
        self._refresh_project_label()
        self._info(tr("dialog.new_created"))

    def _file_open_project(self):
        if self._no_project_manager():
            return
        if not self._confirm_discard_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog.open_title"), "", tr("dialog.project_filter"))
        if not path:
            return
        if self.project_manager.load_from(path):
            window_state.add_recent_project(path)
            self._refresh_project_label()
        else:
            self._warn(tr("dialog.invalid_project"))

    def _file_save_project(self):
        if self._no_project_manager():
            return
        # Task: "Data ostatniej modyfikacji... aktualizowana przy
        # zapisie" - ANY save, not just an edit through Project >
        # Properties. Called here, not from inside ProjectManager.save_project()
        # itself (GRANICE: that method's own logic is unchanged).
        if hasattr(self.project_manager, "touch_metadata_modified"):
            self.project_manager.touch_metadata_modified()
        self.project_manager.save_project()
        self._info(tr("dialog.saved"))

    def _file_save_project_as(self):
        if self._no_project_manager():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dialog.save_as_title"), "project.json", tr("dialog.project_filter"))
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        if hasattr(self.project_manager, "touch_metadata_modified"):
            self.project_manager.touch_metadata_modified()
        self.project_manager.save_project_as(path)
        window_state.add_recent_project(path)
        self._refresh_project_label()
        self._info(tr("dialog.saved"))

    def _file_export_project(self):
        if self._no_project_manager():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dialog.export_title"), "epw_project_backup.json",
            tr("dialog.project_filter"))
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        self.project_manager.export_to(path)
        self._info(tr("dialog.exported"))

    def _file_import_project(self):
        if self._no_project_manager():
            return
        if not self._confirm_discard_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog.import_title"), "", tr("dialog.project_filter"))
        if not path:
            return
        if self.project_manager.import_from(path):
            self._refresh_project_label()
            self._info(tr("dialog.imported"))
        else:
            self._warn(tr("dialog.invalid_project"))

    def _persist_window_state(self):
        """Save size + maximized state for next launch. When maximized,
        normalGeometry() holds the size to restore to once un-maximized."""
        if self.isMaximized() or self.isFullScreen():
            g = self.normalGeometry()
            window_state.save(g.width(), g.height(), True)
        else:
            window_state.save(self.width(), self.height(), False)

    def closeEvent(self, event):
        """Exit confirmation (File > Exit and the window close button both
        land here). Offers to save unsaved work first, then confirms.
        Every event.accept() path below must run shutdown_gui() first -
        see its docstring for why (QApplication-level event filter
        cleanup, segfault fix).

        Kiosk mode (self.kiosk): closing additionally requires Engineer
        access - see _kiosk_authorize_exit(). This is the single funnel
        point for EVERY way a close can be requested (the window-close
        button - absent anyway once frameless, Alt+F4, File > Exit, a
        window-manager close request), because Qt turns all of them into
        this same closeEvent() call; there's no separate list of
        "closing shortcuts" to maintain. The kiosk check runs even under
        EPW_TESTING (unlike the confirmation dialogs below it), so it's
        exercised for real by automated tests instead of being silently
        bypassed the way those dialogs are."""
        if self.kiosk and not self._kiosk_authorize_exit():
            event.ignore()
            return
        if self._testing():
            self.shutdown_gui()
            event.accept()
            return
        if not self._confirm_discard_changes():
            event.ignore()
            return
        resp = QMessageBox.question(
            self, tr("dialog.exit_title"), tr("dialog.exit_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._persist_window_state()
            self.shutdown_gui()
            event.accept()
        else:
            event.ignore()

    def _kiosk_authorize_exit(self) -> bool:
        """Kiosk mode only, called from closeEvent(). Reuses the existing
        AccessManager PIN flow completely unchanged (request_access()
        only prompts if not already at Engineer level; a wrong or
        cancelled PIN returns False, leaving the window open). Records
        the outcome - success or failure - to the audit log under its
        own event type, separate from the "LOGIN" entry AccessManager/
        EPWCore already record for the PIN attempt itself (that one
        means "someone authenticated as Engineer"; this one specifically
        means "an attempt was made to close the kiosk" - not the same
        fact, e.g. an operator already logged in as Engineer for an
        unrelated reason closing the kiosk generates no fresh LOGIN
        attempt at all, since request_access() skips the prompt when
        already authorized)."""
        granted = self.request_access(AccessLevel.ENGINEER)
        if self.audit_logger is not None:
            self.audit_logger.record(
                "KIOSK_EXIT" if granted else "KIOSK_EXIT_DENIED",
                self.access_manager.level,
                "Kiosk mode exit authorized" if granted else "Kiosk mode exit denied - Engineer PIN required",
                success=granted,
            )
        return granted

    def setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Task: every one of these 5 used to be a value hardcoded once at
        # construction and never touched again ("User: Admin" regardless
        # of who was actually logged in, "DB: OK"/"FPS: 60"/"Latency: 12ms"/
        # "Scan: 45ms" with nothing behind any of them). Decision per
        # field, see SESSION_REPORT.md for the full justification:
        #   User  -> wired to the real access level (_update_status_user_label())
        #   DB    -> wired to a real, periodic Historian/DB health check (_check_db_health())
        #   FPS   -> REMOVED: this app has no continuous whole-window render
        #            loop to measure (a handful of pages redraw on their own
        #            QTimer, e.g. TopologyCanvas/WaveformWidget, but there is
        #            no single "the UI's frame rate" for a forms-based Qt
        #            app - any single number here would just be a
        #            differently-shaped fake, not an honest one)
        #   Latency -> wired to real command round-trip time (_on_command_status())
        #   Scan  -> wired to the real driver poll-cycle time (_on_driver_scan_cycle())
        # Text/color for User/DB/Latency/Scan are all set below by their
        # own update methods, not here - construction only creates the
        # widgets; each is seeded with a real (or explicit "no data")
        # value immediately after, same "seed now, don't rely solely on a
        # future signal" pattern as the time sync indicator further down.
        self.lbl_sb_user = QLabel()
        self.lbl_sb_db = QLabel()
        self.lbl_sb_lat = QLabel()
        # Task: podpowiedzi - static (what Latency/Scan actually measure
        # doesn't change; only the number does, via setText() elsewhere),
        # so set once here rather than repeated at every update.
        self.lbl_sb_lat.setToolTip(tr("statusbar.tooltip_latency"))
        self.lbl_sb_scan = QLabel()
        self.lbl_sb_scan.setToolTip(tr("statusbar.tooltip_scan"))
        self.lbl_sb_timesync = QLabel()
        self.lbl_sb_ver = QLabel(f" v{__version__} ")
        self.btn_sb_mode = QPushButton(f" {self._mode_label()} ")
        self.btn_sb_mode.clicked.connect(self.toggle_mode)
        self._refresh_mode_button_style()
        # Training Mode's persistent indicator (Task: "WYRAZNY, staly
        # wskaznik... niemozliwe do przeoczenia") - a permanent widget
        # (right side, never scrolled out of view by the scrolling
        # widgets on the left), hidden whenever the mode is off. Its
        # text/color/visibility are set once below by
        # _refresh_training_mode_indicator(), not here - this is just
        # the widget's construction.
        self.lbl_sb_training = QLabel()
        # Presentation Mode's own persistent indicator (Task: "wyrazny
        # wskaznik... osobny od wskaznika Trybu cwiczebnego") - same
        # permanent-widget/hidden-when-inactive shape as Training Mode's
        # above, but a distinct widget with its own text/color, so the
        # two are never visually confusable and can both show at once
        # (a presentation always runs WITH Training Mode active).
        self.lbl_sb_presentation = QLabel()
        self.lbl_sb_presentation.setVisible(False)
        # Task: DODATKOWO - REST API exposed beyond localhost, signaled
        # "w interfejsie" as well as the startup log (main.py). Static -
        # seeded once from self.api_host (no live reconfiguration UI
        # exists for it), shown only when non-local; a real security
        # exposure, so styled with the alarm color, not Training Mode's
        # milder caution amber.
        self.lbl_sb_api_warning = QLabel()
        self.lbl_sb_api_warning.setVisible(False)
        self._refresh_api_warning_indicator()
        # Database size warning (Task: feature/retention-and-test-fix,
        # B3 - "ostrzezenie, gdy baza przekroczy zadany rozmiar"). Unlike
        # api_warning above, this genuinely changes DURING a run (the
        # database keeps growing) - refreshed once here and again every
        # self.db_size_check_timer tick (see below), not just at
        # construction/theme-change time.
        self.lbl_sb_db_warning = QLabel()
        self.lbl_sb_db_warning.setVisible(False)
        self._refresh_db_size_warning_indicator()
        # Intrusion alarm system's aggregate status (Task: "Stan
        # uzbrojenia MA BYC WIDOCZNY z kazdej strony programu... Wykorzystaj
        # pasek statusu") - same permanent-widget/hidden-when-DISARMED
        # shape as Training Mode's own indicator above, but a distinct
        # widget/color per state (armed/counting down/alarm) - see
        # _refresh_intrusion_indicator().
        self.lbl_sb_intrusion = QLabel()
        self.lbl_sb_intrusion.setVisible(False)
        if self._presentation_started_signal is not None:
            self._presentation_started_signal.connect(self._on_presentation_started)
        if self._presentation_stopped_signal is not None:
            self._presentation_stopped_signal.connect(self._on_presentation_stopped)

        self.statusbar.addWidget(self.lbl_sb_user)
        self.statusbar.addWidget(QLabel(" | "))
        self.statusbar.addWidget(self.lbl_sb_db)
        self.statusbar.addWidget(QLabel(" | "))
        self.statusbar.addWidget(self.lbl_sb_lat)
        self.statusbar.addWidget(QLabel(" | "))
        self.statusbar.addWidget(self.lbl_sb_scan)
        self.statusbar.addWidget(QLabel(" | "))
        self.statusbar.addWidget(self.lbl_sb_timesync)
        self.statusbar.addWidget(QLabel(" | "))
        self.statusbar.addWidget(self.lbl_sb_ver)

        self.statusbar.addPermanentWidget(self.lbl_sb_api_warning)
        self.statusbar.addPermanentWidget(self.lbl_sb_db_warning)
        self.statusbar.addPermanentWidget(self.lbl_sb_presentation)
        self.statusbar.addPermanentWidget(self.lbl_sb_training)
        self.statusbar.addPermanentWidget(self.lbl_sb_intrusion)
        self.statusbar.addPermanentWidget(self.btn_sb_mode)
        self._refresh_training_mode_indicator()
        self._refresh_intrusion_indicator()
        self._refresh_nav_attention_intrusion()
        # Seeded from whatever's already true right now, not just future
        # signals - same "don't rely solely on a future signal" pattern
        # as every other status indicator in this method (a presentation
        # could conceivably already be active if this window is being
        # reconstructed while core.presentation_mode itself persists,
        # e.g. in a test harness).
        if self.presentation_mode is not None and self.presentation_mode.active:
            self._on_presentation_started(self.presentation_mode.scenario.name if self.presentation_mode.scenario else "")

        # Time sync indicator - seeded directly from whatever
        # time_sync_monitor already knows *right now* (not just future
        # signal emissions) for the same reason Task 1's Device Status fix
        # exists: a background poll can complete before this label is
        # wired up to the live signal, and a one-shot/edge-triggered value
        # would otherwise be missed forever. time_sync_monitor here is a
        # Qt-signal adapter (GUITimeSyncAdapter in main.py), not the core
        # TimeSyncMonitor directly - same pattern as tag_manager/access_manager.
        if self.time_sync_monitor is not None:
            self._update_time_sync_label(self.time_sync_monitor.status, self.time_sync_monitor.detail)
            self.time_sync_monitor.status_changed.connect(self._update_time_sync_label)
        else:
            self._update_time_sync_label("UNKNOWN", "No time sync monitor")

        # User - single source of truth is access_manager.level_changed,
        # the exact same signal _update_access_label() (top-bar dropdown)
        # already listens to, so both can never disagree - including on
        # automatic logout (on_access_timeout() -> access_manager.logout()
        # fires this same signal, no separate wiring needed for that case).
        self.access_manager.level_changed.connect(self._update_status_user_label)
        self._update_status_user_label()

        # DB - periodic, deliberately NOT in any hot path (tag_changed,
        # command dispatch, ...): a few dict/queue reads every few
        # seconds, decoupled from how often tags actually change.
        self._check_db_health()
        self.db_health_timer = QTimer(self)
        self.db_health_timer.timeout.connect(self._check_db_health)
        self.db_health_timer.start(4000)

        # Latency - event-driven (command_status), no polling at all.
        # No data yet until the first command completes.
        self.lbl_sb_lat.setText(f" {tr('statusbar.latency')}: {tr('statusbar.no_data')} ")
        if self._command_status_signal is not None:
            self._command_status_signal.connect(self._on_command_status)

        # Scan - event-driven (driver_scan_cycle), no polling at all.
        # No data yet until the first driver poll cycle completes.
        self.lbl_sb_scan.setText(f" {tr('statusbar.scan')}: {tr('statusbar.no_data')} ")
        if self._driver_scan_cycle_signal is not None:
            self._driver_scan_cycle_signal.connect(self._on_driver_scan_cycle)

    def _update_time_sync_label(self, status, detail):
        text_key = {
            "SYNCED": "statusbar.time_sync_synced",
            "NOT_SYNCED": "statusbar.time_sync_not_synced",
        }.get(status, "statusbar.time_sync_unknown")
        theme_colors = self.theme_manager.current_colors()
        color = {
            "SYNCED": theme_colors["state_ok_text"],
            "NOT_SYNCED": theme_colors["state_alarm"],
        }.get(status, theme_colors["state_indeterminate"])
        self.lbl_sb_timesync.setText(f" {tr('statusbar.time_sync')}: {tr(text_key)} ")
        self.lbl_sb_timesync.setStyleSheet(f"color: {color}; font-weight: bold;")
        # Task: podpowiedzi - "co znaczy kazdy stan i skad pochodzi
        # informacja". A general explanation of the mechanism (tr()'d,
        # same for every state) plus the dynamic `detail` this method
        # already receives (the OS time service's own current reading -
        # see time_sync_monitor.py) - not just the raw detail string
        # alone, which never explained what SYNCED/NOT_SYNCED/UNKNOWN
        # themselves mean or where they come from.
        tooltip = tr("statusbar.tooltip_time_sync")
        if detail:
            tooltip += "\n" + detail
        self.lbl_sb_timesync.setToolTip(tooltip)
        self._last_time_sync_status = status
        self._last_time_sync_detail = detail

    def _update_status_user_label(self, *_):
        """Task: 'User: Admin' was a static label - always showed Admin
        regardless of the real access level, the worst of the 5 facades
        (it misled about what the current operator can actually do).
        Called right after construction (seeded) and on every
        access_manager.level_changed - the same signal _update_access_label()
        (top-bar dropdown) listens to, so the two can never disagree,
        including on automatic logout (on_access_timeout() calls
        access_manager.logout(), which fires this same signal)."""
        level = self.access_manager.level
        level_name = tr(f"access.{str(level).lower()}", default=str(level))
        theme_colors = self.theme_manager.current_colors()
        color = {
            AccessLevel.USER: theme_colors["text"],
            AccessLevel.OPERATOR: theme_colors["state_info"],
            AccessLevel.ENGINEER: theme_colors["state_alarm"],
        }.get(level, theme_colors["text"])
        self.lbl_sb_user.setText(f" {tr('statusbar.user')}: {level_name.upper()} ")
        self.lbl_sb_user.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.lbl_sb_user.setToolTip(tr("statusbar.tooltip_user"))

    def _check_db_health(self):
        """Task: 'DB: OK' was a static label that never checked anything.
        Real checks, all cheap: is Historian's worker thread actually
        running, does HealthManager's own DATABASE/HISTORIAN subsystem
        state say FAULT, and is Historian's write queue backing up (a
        rising trend over the last few polls, or an outright large
        backlog) rather than draining normally - the SD-card write
        endurance concern this same task's Part 4 deadband addresses from
        the write-volume side; this is the operator-visible symptom side.
        Three states, color-differentiated: OK (green) / WARNING (queue
        growing or large, amber) / ERROR (historian stopped or a FAULT
        subsystem state, red)."""
        theme_colors = self.theme_manager.current_colors()
        if self.historian is None:
            self.lbl_sb_db.setText(f" {tr('statusbar.db')}: {tr('statusbar.no_data')} ")
            self.lbl_sb_db.setStyleSheet(f"color: {theme_colors['state_indeterminate']}; font-weight: bold;")
            self.lbl_sb_db.setToolTip(tr("statusbar.tooltip_db_no_data"))
            return

        error = not getattr(self.historian, "is_running", False)
        if self.health_manager is not None:
            health = self.health_manager.get_health()
            if health.get("DATABASE") == "FAULT" or health.get("HISTORIAN") == "FAULT":
                error = True

        qsize = 0
        try:
            qsize = self.historian.queue.qsize()
        except Exception:
            # Deliberate, not logged: runs on a fast periodic status-bar
            # timer (would flood the log if it ever fired every tick) -
            # self.historian can be a test double with no real queue, and
            # queue.Queue.qsize() is itself documented as
            # "not reliable" (NotImplementedError on some platforms).
            # qsize just stays 0 (the gauge briefly reads empty) either way.
            pass
        self._db_queue_history.append(qsize)
        self._db_queue_history = self._db_queue_history[-5:]
        growing = (
            len(self._db_queue_history) >= 3
            and all(b >= a for a, b in zip(self._db_queue_history, self._db_queue_history[1:]))
            and self._db_queue_history[-1] > self._db_queue_history[0]
        )
        warning = qsize > 200 or growing
        if qsize > 2000:
            error = True

        # Task: podpowiedzi - dynamic (current queue size, the same
        # number this method already just computed above), not a fixed
        # explanation set once at construction.
        if error:
            self.lbl_sb_db.setText(f" {tr('statusbar.db')}: {tr('statusbar.db_error')} ")
            self.lbl_sb_db.setStyleSheet(f"color: {theme_colors['state_alarm']}; font-weight: bold;")
            self.lbl_sb_db.setToolTip(tr("statusbar.tooltip_db_error", queue=qsize))
        elif warning:
            self.lbl_sb_db.setText(f" {tr('statusbar.db')}: {tr('statusbar.db_warning')} ")
            self.lbl_sb_db.setStyleSheet(f"color: {theme_colors['state_warning_dark']}; font-weight: bold;")
            self.lbl_sb_db.setToolTip(tr("statusbar.tooltip_db_warning", queue=qsize))
        else:
            self.lbl_sb_db.setText(f" {tr('statusbar.db')}: {tr('statusbar.db_ok')} ")
            self.lbl_sb_db.setStyleSheet(f"color: {theme_colors['state_ok_text']}; font-weight: bold;")
            self.lbl_sb_db.setToolTip(tr("statusbar.tooltip_db_ok"))

    def _on_command_status(self, command_id, state, reason):
        """Task: 'Latency: 12ms' was a static label. Real measurement:
        wall time from this command's REQUESTED event to whatever
        terminal state it reaches - SUCCESS is the common case, but
        TIMEOUT/FAILED/BLOCKED are real round trips too and worth
        showing rather than leaving the field stuck on the last
        successful command. No CommandManager changes needed - this
        tracks its existing command_status lifecycle (command_manager.py)
        purely client-side; command_status was already emitted on the
        core event bus but never bridged to the GUI before this task."""
        from epw_os.core.command_manager import CommandState
        if state == CommandState.REQUESTED:
            self._pending_command_times[command_id] = time.monotonic()
            return
        started = self._pending_command_times.pop(command_id, None)
        if started is None:
            return
        if state in (CommandState.SUCCESS, CommandState.TIMEOUT, CommandState.FAILED, CommandState.BLOCKED):
            elapsed_ms = (time.monotonic() - started) * 1000.0
            self.lbl_sb_lat.setText(f" {tr('statusbar.latency')}: {elapsed_ms:.0f}ms ")

    def _on_driver_scan_cycle(self, driver_id, elapsed_ms):
        """Task: 'Scan: 45ms' was a static label. Real measurement: the
        actual measured elapsed time of the driver's own poll loop (see
        simulator_driver.py's _run_loop()), emitted once per real cycle -
        purely event-driven, no polling added by this window."""
        self.lbl_sb_scan.setText(f" {tr('statusbar.scan')}: {elapsed_ms:.0f}ms ")

    def _mode_label(self, mode=None):
        """Translated label for the run-mode button. The raw mode string
        comes from tag_manager ("SIMULATION MODE" / "LIVE MODE", or just
        "SIMULATION" in some test mocks) - match on the LIVE keyword."""
        if mode is None:
            mode = getattr(self.tag_manager, "mode", "") or ""
        if "LIVE" in mode.upper():
            return tr("statusbar.live_mode")
        return tr("statusbar.simulation_mode")

    def toggle_mode(self):
        self.tag_manager.toggle_mode()
        self.btn_sb_mode.setText(f" {self._mode_label()} ")
        self._refresh_mode_button_style()

    def _refresh_mode_button_style(self):
        """LIVE MODE is flagged in alarm-red (a live-hardware mode is the
        one worth catching your eye) - SIMULATION MODE in the calmer
        info-blue. Shared by the initial style (setup_statusbar()),
        toggle_mode(), and a theme change, so all three ways this button
        can need recoloring go through one place."""
        theme_colors = self.theme_manager.current_colors()
        is_live = "LIVE" in (getattr(self.tag_manager, "mode", "") or "").upper()
        if is_live:
            color = theme_colors["state_alarm"]
        else:
            color = theme_colors["state_info"]
        self.btn_sb_mode.setStyleSheet(f"color: {color}; font-weight: bold; border: none; background: transparent;")
        # Task: podpowiedzi - "wskaznik trybu (symulacja / praca)".
        # Dynamic: explains whichever mode is CURRENTLY active, not a
        # generic "click to toggle" for both - shares this method's
        # trigger points (construction, toggle_mode(), theme change) with
        # the color above.
        self.btn_sb_mode.setToolTip(
            tr("statusbar.tooltip_mode_live") if is_live else tr("statusbar.tooltip_mode_simulation")
        )

    # Task: which Engineer-gated pages never prompt for a PIN on demand -
    # an insufficient level gets an informational denial instead, and
    # raises their own level via the top-bar dropdown if they want in.
    # Each such page's own refresh()-time inline gate (a locked, empty
    # view + message) stays as a second layer for any other path that
    # can land here (e.g. a level dropping below Engineer while already
    # on the page fires level_changed -> refresh() directly).
    _ENGINEER_GATED_PAGES = frozenset({"audit_log", "bus_diagnostics", "engineer_mode"})
    # Fixed, untranslated English identifiers for deny_access()'s audit-log
    # `action` text (see its own docstring) - same three strings the old,
    # now-removed _open_audit_log()/_open_bus_diagnostics()/
    # request_engineer_mode() methods used to pass literally.
    _GATED_PAGE_ACTION_NAMES = {
        "audit_log": "Audit Log",
        "bus_diagnostics": "Bus Diagnostics",
        "engineer_mode": "Engineer Mode",
    }

    def _navigate_to(self, page_id: str):
        """The one place a click - from the nav tree, or any other
        internal caller (on_access_timeout()'s "kick back to Main
        View", a deny-and-elsewhere flow) - actually switches the
        stacked widget. Replaces the old per-page _open_X()/
        request_engineer_mode() methods and their hardcoded
        setCurrentIndex(N) literals, which broke the moment a page
        could be conditionally absent - self._page_index (built once,
        in construction order, in __init__) is the only source of "what
        index is this page at" now."""
        if page_id in self._ENGINEER_GATED_PAGES and not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.deny_access(AccessLevel.ENGINEER, self._GATED_PAGE_ACTION_NAMES[page_id])
            self.nav_tree.set_current_page(self._current_page_id)  # undo the tree's own optimistic selection
            return
        index = self._page_index.get(page_id)
        if index is None:
            return  # feature disabled / page doesn't exist right now - nothing to switch to
        self.stacked_widget.setCurrentIndex(index)
        self._current_page_id = page_id
        if page_id == "alarms":
            self.page_alarms.refresh()
        elif page_id == "audit_log":
            self.page_audit.refresh()
        elif page_id == "bus_diagnostics":
            self.page_bus_diagnostics.refresh()

    def request_access(self, level: str) -> bool:
        """The one place that raises access_manager.level: if already at
        `level` or above, succeeds immediately; otherwise prompts for that
        level's PIN (with retry-on-wrong-PIN built into the popup) and
        returns whether the operator ended up authenticated at `level`.
        Other pages call this via self.window().request_access(...) before
        doing anything that needs Operator/Engineer access."""
        if self.access_manager.has_access(level):
            self.access_timeout_timer.start(5 * 60 * 1000)
            return True

        # No keyboard_enabled here (this task): PinPromptPopup's embedded
        # keypad is always present now, independent of the Settings
        # toggle - see PinPromptPopup's docstring and SESSION_REPORT.md.
        popup = PinPromptPopup(self.access_manager, level, self)
        if popup.exec():
            self.access_timeout_timer.start(5 * 60 * 1000)
            return True
        return False

    def on_access_timeout(self):
        if self.access_manager.level != AccessLevel.USER:
            self.access_manager.logout()
            self._navigate_to("main_view")  # Kick back to Main View
            AccessTimeoutPopup(self).exec()

    def _on_access_level_selected(self, level):
        """Handler for the top-bar access dropdown. Moving to a level at
        or below the current one is a plain demotion (no PIN); moving up
        goes through the existing PIN-prompt flow (request_access)."""
        if self.access_manager.has_access(level):
            self.access_manager.demote(level)
        else:
            self.request_access(level)

    def _update_alarm_counter(self, *_):
        if self.alarm_manager is None:
            return
        alarms = self.alarm_manager.get_active_alarms()
        unacked = sum(1 for a in alarms if a.state == AlarmState.ACTIVE_UNACK)
        self.lbl_alarm_cnt.setText(f"{tr('topbar.alarms')}: {len(alarms)}")
        # Task: podpowiedzi - dynamic (active/unacknowledged breakdown),
        # updated alongside the text every time this method runs, not set
        # once at construction.
        self.lbl_alarm_cnt.setToolTip(tr("topbar.tooltip_alarms", active=len(alarms), unacked=unacked))
        theme_colors = self.theme_manager.current_colors()
        if unacked > 0:
            # Unacknowledged - impossible to miss.
            self.lbl_alarm_cnt.setStyleSheet(
                f"color: {theme_colors['accent_text']}; background-color: {theme_colors['state_alarm_dark']}; "
                "font-weight: bold; padding: 1px 4px;"
            )
        elif alarms:
            # Active but every one already acknowledged - still worth
            # noticing, calmer than an unacked alarm.
            self.lbl_alarm_cnt.setStyleSheet(
                f"color: {theme_colors['text']}; background-color: {theme_colors['state_warning_badge']}; "
                "font-weight: bold; padding: 1px 4px;"
            )
        else:
            self.lbl_alarm_cnt.setStyleSheet("")
        # Task 3 (nav tree attention indicator): "niepotwierdzone alarmy"
        # is one of the Task's own explicit examples - same three-way
        # severity this label's own color just above already computed.
        from epw_os.gui.widgets.nav_tree import ATTENTION_NONE, ATTENTION_WARNING, ATTENTION_ALARM
        level = ATTENTION_ALARM if unacked > 0 else (ATTENTION_WARNING if alarms else ATTENTION_NONE)
        self.nav_tree.set_leaf_attention("alarms", level)

    def _update_access_label(self, *_):
        level = self.access_manager.level
        level_name = tr(f"access.{str(level).lower()}", default=str(level))
        self.btn_access_level.setText(f"{tr('topbar.access')}: {level_name.upper()} ▾")
        theme_colors = self.theme_manager.current_colors()
        color = {
            AccessLevel.USER: theme_colors["text"],
            AccessLevel.OPERATOR: theme_colors["state_info"],
            AccessLevel.ENGINEER: theme_colors["state_alarm"],
        }.get(level, theme_colors["text"])
        self.btn_access_level.setStyleSheet(
            f"QToolButton {{ border: 1px solid {theme_colors['bevel_shadow']}; padding: 2px 8px; "
            f"font-weight: bold; color: {color}; }}"
        )
        # Task: podpowiedzi - "co wolno na obecnym poziomie", dynamic
        # (changes with the level, same signal that already drives the
        # text/color above).
        tooltip_key = {
            AccessLevel.USER: "access.tooltip_user",
            AccessLevel.OPERATOR: "access.tooltip_operator",
            AccessLevel.ENGINEER: "access.tooltip_engineer",
        }.get(level, "access.tooltip_user")
        self.btn_access_level.setToolTip(tr(tooltip_key))

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress):
            if self.access_manager.level != AccessLevel.USER:
                # Restart the 5-minute inactivity timer on any user activity
                self.access_timeout_timer.start(5 * 60 * 1000)
            # Screen sleep applies regardless of access level (a plain
            # User's idle screen blanks too) - restart on any activity,
            # and wake immediately if currently asleep. The overlay's own
            # mouse/key handlers already emit woken (redundant with this,
            # both paths are idempotent - exit_screen_sleep() on an
            # already-hidden overlay is a harmless no-op).
            self._restart_screen_sleep_timer()
            if self.screen_sleep_overlay.isVisible():
                self.exit_screen_sleep()
        elif event.type() == QEvent.Type.MouseButtonDblClick:
            # Fullscreen Mode exit #1 of 3 (Esc and F11/menu are the other
            # two - see _on_fullscreen_toggled()) - a double-click
            # anywhere in the work area (the page/stacked_widget region,
            # not the menu bar or status bar). Hard-gated on `not
            # self.kiosk` even though _on_fullscreen_toggled() already
            # refuses to act during Kiosk Mode - this is the specific
            # mechanism the task calls out as a hard requirement to
            # verify independently, not just "covered transitively".
            if (not self.kiosk and self._fullscreen_action.isChecked()
                    and isinstance(obj, QWidget)
                    and (obj is self.stacked_widget or self.stacked_widget.isAncestorOf(obj))):
                self._fullscreen_action.setChecked(False)
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        # Fullscreen Mode exit #2 of 3 (Esc) - hard-gated on `not
        # self.kiosk`, same reasoning as the double-click handler above:
        # Kiosk Mode must swallow this outright, not rely solely on the
        # convenience toggle already being disabled.
        if (event.key() == Qt.Key.Key_Escape and not self.kiosk
                and self._fullscreen_action.isChecked()):
            self._fullscreen_action.setChecked(False)
            return
        super().keyPressEvent(event)

    def _restart_screen_sleep_timer(self):
        if self._screen_sleep_minutes > 0:
            self.screen_sleep_timer.start(self._screen_sleep_minutes * 60 * 1000)
        else:
            self.screen_sleep_timer.stop()

    def enter_screen_sleep(self):
        self.screen_sleep_overlay.show_asleep()

    def exit_screen_sleep(self):
        self.screen_sleep_overlay.hide()
        self._restart_screen_sleep_timer()

    def set_screen_sleep_minutes(self, minutes: int):
        """Called from Settings > Screen Sleep... - takes effect
        immediately, not just on next launch."""
        self._screen_sleep_minutes = max(0, int(minutes))
        window_state.save_screen_sleep_minutes(self._screen_sleep_minutes)
        self._restart_screen_sleep_timer()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.screen_sleep_overlay.isVisible():
            self.screen_sleep_overlay.setGeometry(self.rect())

    def update_clock(self):
        date_str = QDate.currentDate().toString("yyyy-MM-dd (ddd)")
        time_str = QTime.currentTime().toString("HH:mm:ss")
        self.lbl_clock.setText(f"{date_str} {time_str}")

    def on_comm_tag_changed(self, tag_name, new_value, quality):
        if tag_name in self._device_status_tags:
            self.update_comm_status()

    def update_comm_status(self):
        offline = [t for t in self._device_status_tags if self.tag_manager.get_value(t) != "ONLINE"]
        theme_colors = self.theme_manager.current_colors()
        # Task: podpowiedzi - dynamic (which devices are actually
        # offline), computed here rather than at construction since it's
        # exactly the list this method already builds every time it runs.
        if not offline:
            self.lbl_comm_status.setText(tr("topbar.comm_ok"))
            self.lbl_comm_status.setStyleSheet(f"color: {theme_colors['state_ok_text']}; font-weight: bold;")
            self.lbl_comm_status.setToolTip(tr("topbar.tooltip_comm_status_ok"))
        else:
            self.lbl_comm_status.setText(tr("topbar.comm_offline", n=len(offline)))
            self.lbl_comm_status.setStyleSheet(f"color: {theme_colors['state_alarm']}; font-weight: bold;")
            self.lbl_comm_status.setToolTip(
                tr("topbar.tooltip_comm_status_offline", devices=", ".join(offline))
            )

        # "Q: XX%" (top bar) - real percentage of registered devices
        # currently ONLINE, computed from the exact same tags/values just
        # read above - see the comment where lbl_comm_quality is
        # constructed for why this proxy metric was chosen over adding
        # new per-exchange counters to DeviceManager. Tooltip says
        # honestly what's actually measured (device-online ratio), not
        # the "% successful exchanges" framing the task's own example
        # used - see SESSION_REPORT.md.
        total = len(self._device_status_tags)
        online = total - len(offline)
        pct = 100 if total == 0 else round(100 * online / total)
        self.lbl_comm_quality.setText(tr("topbar.comm_quality", pct=pct))
        self.lbl_comm_quality.setToolTip(tr("topbar.tooltip_comm_quality", online=online, total=total))
        if pct >= 100:
            q_color = theme_colors["state_ok_text"]
        elif pct > 0:
            q_color = theme_colors["state_warning_dark"]
        else:
            q_color = theme_colors["state_alarm"]
        self.lbl_comm_quality.setStyleSheet(f"color: {q_color}; font-weight: bold;")
