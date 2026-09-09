import sys
import threading
import uvicorn
import time
from epw_os.core.epw_core import EPWCore
from epw_os.core.logging import log
from epw_os.core.tag_manager import TagQuality

def run_backend(core: EPWCore):
    log.info("Starting FastAPI backend...")
    from epw_os.backend.api import app as fastapi_app
    # Inject EPWCore into FastAPI state
    fastapi_app.state.core = core
    
    # Typed accessors (ProjectManager.get_api_host()/get_api_port()) -
    # default host 127.0.0.1 stays the single source of truth there,
    # not duplicated here.
    host = core.project_manager.get_api_host()
    port = core.project_manager.get_api_port()
    
    config = uvicorn.Config(fastapi_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())

def main():
    log.info("Starting EPW OS...")

    # Kiosk mode: opt-in only, via a plain argv check (no argparse - one
    # boolean flag doesn't need a new dependency or to reshape how this
    # script is invoked). Off by default so a developer running
    # `python main.py` on a normal desktop sees exactly today's behavior;
    # Orange Pi's autostart service is the one place that passes it - see
    # ORANGE_PI_DEPLOYMENT.md.
    kiosk = "--kiosk" in sys.argv[1:]
    if kiosk:
        log.info("Kiosk mode enabled (--kiosk): fullscreen, borderless, Engineer PIN required to exit.")

    # 1. Initialize Headless Core
    core = EPWCore()
    core.startup()

    # Task: DODATKOWO - a non-local api_host must be loudly signaled at
    # startup, not just quietly honored. Checked here (not inside
    # run_backend()'s own thread) so it appears at the top of the
    # startup log, not interleaved with uvicorn's own log lines.
    from epw_os.core.api_auth import is_local_host
    _api_host = core.project_manager.get_api_host()
    if not is_local_host(_api_host):
        log.warning("=" * 70)
        log.warning(f"REST API is bound to {_api_host}:{core.project_manager.get_api_port()} - "
                     f"NOT localhost-only. This exposes command/tag/alarm access to the network.")
        log.warning("Set api_host back to 127.0.0.1 in project.json unless this is intentional.")
        log.warning("=" * 70)

    # 2. Start API Backend Thread
    backend_thread = threading.Thread(target=run_backend, args=(core,), daemon=True)
    backend_thread.start()

    # 3. Optional GUI Boot (if in GUI environment)
    # We will wrap GUI inside a try/except to allow truly headless server boot
    gui_enabled = True
    if gui_enabled:
        try:
            from PySide6.QtWidgets import QApplication
            from epw_os.gui.main_window import MainWindow
            from epw_os.i18n import set_language

            # Apply the project's saved UI language before any widget is
            # built. This is the only unconditional apply point (process
            # startup) - the other one, rebuild_window()
            # below, only runs later if the operator actually changes it
            # from Settings > Language, so the whole GUI never needs a
            # real restart just to switch language (Task: kiosk on Orange
            # Pi shouldn't need Engineer PIN + a relaunch just to change
            # languages).
            set_language(core.project_manager.get_language())

            app = QApplication(sys.argv)

            # Task: podpowiedzi (tooltips) - app-wide ~500ms delay before
            # one appears, tuned centrally instead of relying on whatever
            # the platform default happens to be. Wraps app.style()
            # rather than replacing it - every other timing/rendering
            # behavior is untouched (see tooltip_style.py).
            from epw_os.gui.tooltip_style import TooltipTimingStyle
            app.setStyle(TooltipTimingStyle(app.style()))

            # PySide6 silently aborts the whole process (no traceback at all) when an
            # exception escapes a Qt slot (QTimer callbacks, button clicks, etc.).
            # Install a global excepthook so such errors are logged instead of
            # crashing EPW OS without any diagnostic output.
            def _qt_excepthook(exc_type, exc_value, exc_tb):
                import traceback
                log.error(
                    "Unhandled exception in Qt event loop:\n"
                    + "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                )
            sys.excepthook = _qt_excepthook

            font = app.font()
            font.setFamily("MS Sans Serif")
            font.setPointSize(9)
            app.setFont(font)
            
            # Qt Event Bridge to completely decouple Core from PySide6
            from PySide6.QtCore import QObject, Signal
            class QtEventBridge(QObject):
                tag_changed = Signal(str, object, str)
                command_status = Signal(str, str, str)
                access_level_changed = Signal(str)
                time_sync_status_changed = Signal(str, str)
                alarms_changed = Signal()
                # Task: status bar "Scan" field - real driver poll-cycle time.
                driver_scan_cycle = Signal(str, float)
                # Task: Presentation Mode - presentation_mode.py's own
                # event_bus events, bridged the same way every other
                # core-to-GUI notification in this app already is.
                presentation_started = Signal(str)
                presentation_stopped = Signal()
                presentation_paused = Signal()
                presentation_resumed = Signal()
                presentation_step = Signal(int, int, str)
                # Task: integracja MQTT - the connection-state changes
                # happen on MqttManager's own background thread, so this
                # gets the same "wrap only what crosses a thread
                # boundary" treatment as time_sync_status_changed above.
                mqtt_status_changed = Signal(str)

            bridge = QtEventBridge()
            
            # Wrap core managers for the GUI
            class GUITagManagerAdapter:
                def __init__(self, core_tm, qt_bridge, project_manager, epw_core):
                    self._core_tm = core_tm
                    self._project_manager = project_manager
                    # Needed for the Analog Inputs dynamic-points methods
                    # below - adding/removing a point is more than a
                    # project.json edit, it also (un)registers a live
                    # TagManager tag and updates the simulator, which only
                    # EPWCore can orchestrate together (see
                    # add_analog_point()/remove_analog_point() there).
                    self._epw_core = epw_core
                    self.tag_changed = qt_bridge.tag_changed
                def get_value(self, name): return self._core_tm.get_value(name)
                def get_tag(self, name): return self._core_tm.get_tag(name)
                def update_tag(self, name, val, q=TagQuality.GOOD): self._core_tm.update_tag(name, val, q)
                # Bug fix ("program nie uruchamia sie"): ProtectionVerifier's
                # constructor (epw_os/core/protection_verifier.py, the
                # System.PendingCommand/System.ActiveTrip fix) now calls
                # tag_manager.add_tag() - this adapter never had that
                # method, so PageEngineerMode's construction raised
                # AttributeError, caught by this file's own broad
                # "GUI failed, run headless" except block below, silently
                # falling back to headless every launch. Passed straight
                # through, same shape as get_value()/update_tag() above.
                def add_tag(self, name, value, data_type, description="", timeout=5.0, source="SYSTEM",
                            quality=TagQuality.GOOD):
                    return self._core_tm.add_tag(name, value, data_type, description=description,
                                                  timeout=timeout, source=source, quality=quality)
                def set_description(self, name, desc):
                    self._core_tm.set_description(name, desc)
                    self._project_manager.set_tag_description(name, desc)
                    self._project_manager.save_project()
                def get_output_description(self, name, default=""):
                    return self._project_manager.get_output_descriptions().get(name, default)
                def set_output_description(self, name, desc):
                    self._project_manager.set_output_description(name, desc)
                    self._project_manager.save_project()
                def get_analog_points(self):
                    return self._project_manager.get_analog_points()
                def list_tags(self):
                    # Task: signal-list export (Tools > Export Signal
                    # List..., epw_os.core.tag_export.build_tag_list_export())
                    # needs every registered Tag object, not just a single
                    # value/description lookup - same passthrough shape
                    # every other method on this adapter already uses.
                    return self._core_tm.list_tags()
                def add_analog_point(self, point):
                    return self._epw_core.add_analog_point(point)
                def remove_analog_point(self, tag_name):
                    return self._epw_core.remove_analog_point(tag_name)
                def update_analog_point(self, tag_name, point):
                    return self._epw_core.update_analog_point(tag_name, point)
                @property
                def mode(self): return self._core_tm.mode
                def toggle_mode(self): self._core_tm.toggle_mode()

            gui_tm = GUITagManagerAdapter(core.tag_manager, bridge, core.project_manager, core)

            class GUIAccessManagerAdapter:
                def __init__(self, core_am, qt_bridge):
                    self._core_am = core_am
                    self.level_changed = qt_bridge.access_level_changed
                @property
                def level(self): return self._core_am.level
                def has_access(self, required_level): return self._core_am.has_access(required_level)
                def attempt_login(self, level, pin): return self._core_am.attempt_login(level, pin)
                def logout(self): self._core_am.logout()
                def demote(self, level): return self._core_am.demote(level)
                def verify_pin(self, level, pin): return self._core_am.verify_pin(level, pin)
                def set_pin(self, level, new_pin): return self._core_am.set_pin(level, new_pin)

            gui_am = GUIAccessManagerAdapter(core.access_manager, bridge)

            class GUITimeSyncAdapter:
                def __init__(self, core_tsm, qt_bridge):
                    self._core_tsm = core_tsm
                    self.status_changed = qt_bridge.time_sync_status_changed
                @property
                def status(self): return self._core_tsm.status
                @property
                def detail(self): return self._core_tsm.detail

            gui_tsm = GUITimeSyncAdapter(core.time_sync_monitor, bridge)

            class GUIAlarmAdapter:
                def __init__(self, core_alarm_mgr, qt_bridge):
                    self._core_am = core_alarm_mgr
                    self.alarms_changed = qt_bridge.alarms_changed
                def get_active_alarms(self): return self._core_am.get_active_alarms()
                def get_all_alarms(self): return self._core_am.get_all_alarms()
                def acknowledge_alarm(self, alarm_id, user=""): return self._core_am.acknowledge_alarm(alarm_id, user)

            gui_alarms = GUIAlarmAdapter(core.alarm_manager, bridge)

            class GUIFeatureConfigAdapter:
                """Task ("okno konfiguracji funkcji") - no Qt signal to
                bridge (unlike the adapters above): a feature change only
                ever reaches the GUI through the SAME explicit window-
                rebuild callback the caller (FeatureConfigDialog, via
                MainWindow._open_feature_config_dialog()) already drives
                itself - see rebuild_window() below."""
                def __init__(self, epw_core):
                    self._core = epw_core
                def get_enabled_features(self):
                    return dict(self._core.enabled_features)
                def set_feature_enabled(self, feature, enabled, actor, level=None):
                    return self._core.set_feature_enabled(feature, enabled, actor, level=level)
                def feature_referenced_by_logic(self, feature):
                    return self._core.feature_referenced_by_logic(feature)
                def get_feature_tag_names(self, feature):
                    return self._core.get_feature_tag_names(feature)

            gui_feature_config = GUIFeatureConfigAdapter(core)

            class GUIMqttAdapter:
                """Task ("integracja MQTT") - Qt-free like
                GUIFeatureConfigAdapter above (get_config()/configure()/
                get_state()/get_stats() are all plain sync calls onto
                the headless MqttManager); the dialog gets the live
                connection-state signal separately, via bridge.
                mqtt_status_changed (see MqttConfigDialog's own
                `status_changed_signal` parameter)."""
                def __init__(self, core_mqtt):
                    self._core = core_mqtt
                def get_config(self):
                    return self._core.get_config()
                def configure(self, config, password=None, actor="", level=None):
                    return self._core.configure(config, password=password, actor=actor, level=level)
                def get_state(self):
                    return self._core.get_state()
                def get_stats(self):
                    return self._core.get_stats()

            gui_mqtt = GUIMqttAdapter(core.mqtt_manager)

            # Bridge EventBus -> Qt signals. Registered *before* MainWindow
            # is constructed (unlike the other subscriptions below, which
            # is a known, harmless-so-far gap - see Task 1's SESSION_REPORT
            # entry): time_sync_status_changed and the 3 alarm_* events are
            # background-thread/infrequent-edge-triggered exactly like the
            # one that caused the Device Status panel bug, so these get the
            # careful ordering from the start instead of relying only on
            # main_window.py's construction-time seed read.
            def on_time_sync_status_changed(status, detail):
                bridge.time_sync_status_changed.emit(status, detail)
            core.event_bus.subscribe("time_sync_status_changed", on_time_sync_status_changed)

            def on_alarm_event(_alarm):
                bridge.alarms_changed.emit()
            core.event_bus.subscribe("alarm_triggered", on_alarm_event)
            core.event_bus.subscribe("alarm_cleared", on_alarm_event)
            core.event_bus.subscribe("alarm_acknowledged", on_alarm_event)

            def on_mqtt_status_changed(state):
                bridge.mqtt_status_changed.emit(state)
            core.event_bus.subscribe("mqtt_status_changed", on_mqtt_status_changed)

            # Map core managers to GUI expectations. project_manager and
            # audit_logger are passed straight through (no Qt) so the File
            # menu / Protection Settings / Language dialog can drive them
            # directly against the real project / DB.
            #
            # Task: switch interface language without restarting the
            # kiosk. Wrapped in a function, not a single inline
            # construction, so the exact same MainWindow(...) call can run
            # again later - rebuild_window() below
            # calls this a second time once the operator actually changes
            # the language, tearing down and replacing the window while
            # core/bridge/every adapter above keep running untouched
            # (EPWCore, the drivers, the DB, the REST API thread never
            # restart - only the GUI layer does). `current_window` is a
            # one-element list, not a bare variable, so the callback below
            # (a closure) can update which window is "current" and this
            # function's own final cleanup (after app.exec() returns) sees
            # that update too - a bare `window = ...` reassigned only
            # inside the closure would rebind the closure's own local, not
            # this function's.
            def build_window():
                return MainWindow(gui_tm, core.command_manager, gui_am, core.project_manager,
                                   core.audit_logger, gui_tsm, gui_alarms, core.historian, kiosk=kiosk,
                                   switching_counters=core.switching_counters, training_mode=core.training_mode,
                                   service_notes=core.service_notes, health_manager=core.health_manager,
                                   command_status_signal=bridge.command_status,
                                   driver_scan_cycle_signal=bridge.driver_scan_cycle,
                                   device_manager=core.device_manager, driver_manager=core.driver_manager,
                                   presentation_mode=core.presentation_mode,
                                   presentation_started_signal=bridge.presentation_started,
                                   presentation_stopped_signal=bridge.presentation_stopped,
                                   presentation_paused_signal=bridge.presentation_paused,
                                   presentation_resumed_signal=bridge.presentation_resumed,
                                   presentation_step_signal=bridge.presentation_step,
                                   api_host=_api_host, intrusion_manager=core.intrusion_manager,
                                   process_protection_manager=core.process_protection_manager,
                                   language_changed_callback=rebuild_window,
                                   feature_config=gui_feature_config,
                                   feature_config_changed_callback=rebuild_window,
                                   mqtt_manager=gui_mqtt, mqtt_status_changed_signal=bridge.mqtt_status_changed)

            def rebuild_window():
                """Tears down and reconstructs the GUI window in place,
                core/bridge/every adapter above kept running untouched -
                originally built for the language-switch task (Task:
                switch without restarting the kiosk), reused as-is for
                the feature-configuration task (Task: "zmiana ma dzialac
                BEZ RESTARTU programu") - a feature toggle can add/remove
                pages and nav entries, which needs exactly the same full
                reconstruction a language change already needed, for the
                same reason: neither is safely patchable into a running
                window piecemeal."""
                old_window = current_window[0]
                # Same geometry the operator was just looking at, not
                # whatever was last saved on a real close - closeEvent()
                # (where this normally runs) is deliberately NOT used for
                # this teardown, see below, so nothing else will have
                # persisted it.
                old_window._persist_window_state()
                set_language(core.project_manager.get_language())
                new_window = build_window()
                current_window[0] = new_window
                new_window.show()
                # shutdown_gui() only - NOT old_window.close(): that would
                # run closeEvent(), which under --kiosk demands the
                # Engineer PIN and otherwise offers to save unsaved
                # changes, exactly the friction this whole task exists to
                # remove for a plain language switch. shutdown_gui() is
                # the same self-contained cleanup closeEvent() itself
                # calls before accepting (event-filter/keyboard-controller
                # teardown, page_trends/page_bus_diagnostics' own
                # timers) - see its own docstring - independent of that
                # confirmation/kiosk-authorization logic entirely.
                old_window.shutdown_gui()
                old_window.hide()
                old_window.deleteLater()
                log.info("EPW OS GUI rebuilt in place (language or feature-configuration change, no restart).")

            current_window = [build_window()]

            # Bridge EventBus -> Qt signals
            def on_tag_changed(tag_name, value, quality):
                bridge.tag_changed.emit(tag_name, value, quality)
            core.event_bus.subscribe("tag_changed", on_tag_changed)

            def on_access_level_changed(level):
                bridge.access_level_changed.emit(level)
            core.event_bus.subscribe("access_level_changed", on_access_level_changed)

            # Task: status bar "Latency" field - real command round-trip
            # time. command_status already carries the full REQUESTED ->
            # .../SUCCESS/TIMEOUT/FAILED/BLOCKED lifecycle for every
            # command (see command_manager.py) but was never bridged to
            # the GUI at all before this task - MainWindow itself tracks
            # REQUESTED timestamps per command_id and computes the elapsed
            # time on a terminal state (see main_window.py's
            # _on_command_status()), so this bridge is the only change
            # needed here.
            def on_command_status(command_id, state, reason):
                bridge.command_status.emit(command_id, state, reason)
            core.event_bus.subscribe("command_status", on_command_status)

            # Task: status bar "Scan" field - real driver poll-cycle time,
            # emitted once/second by SimulatorDriver's own loop (see
            # simulator_driver.py).
            def on_driver_scan_cycle(driver_id, elapsed_ms):
                bridge.driver_scan_cycle.emit(driver_id, elapsed_ms)
            core.event_bus.subscribe("driver_scan_cycle", on_driver_scan_cycle)

            # Task: Presentation Mode - see presentation_mode.py's own
            # event_bus.emit() calls for exactly what each of these
            # carries.
            def on_presentation_started(name):
                bridge.presentation_started.emit(name)
            core.event_bus.subscribe("presentation_started", on_presentation_started)

            def on_presentation_stopped():
                bridge.presentation_stopped.emit()
            core.event_bus.subscribe("presentation_stopped", on_presentation_stopped)

            def on_presentation_paused():
                bridge.presentation_paused.emit()
            core.event_bus.subscribe("presentation_paused", on_presentation_paused)

            def on_presentation_resumed():
                bridge.presentation_resumed.emit()
            core.event_bus.subscribe("presentation_resumed", on_presentation_resumed)

            def on_presentation_step(index, total, description):
                bridge.presentation_step.emit(index, total, description)
            core.event_bus.subscribe("presentation_step", on_presentation_step)

            current_window[0].show()
            log.info("EPW OS GUI Running.")
            exit_code = app.exec()
            # Defense in depth: closeEvent() already calls this on a normal
            # window close, but app.exec() can also return via app.quit()
            # or a termination signal without closeEvent ever firing.
            # shutdown_gui() is idempotent - safe to call again either way.
            # See MainWindow.shutdown_gui()'s docstring for why this
            # matters (QApplication-level event filter cleanup, segfault
            # fix - SESSION_REPORT.md). current_window[0] - not the
            # `window` this block started with - in case a language
            # change rebuilt it in the meantime (see
            # rebuild_window() above).
            current_window[0].shutdown_gui()
        except Exception as e:
            log.warning(f"Could not start GUI: {e}. Running Headless.")
            exit_code = 0
            while core.is_running:
                time.sleep(1.0)
    else:
        while core.is_running:
            time.sleep(1.0)
        exit_code = 0
        
    core.shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
