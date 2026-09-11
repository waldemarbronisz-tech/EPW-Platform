from epw_os.core.events import EventBus
from epw_os.core.tag_manager import TagManager
from epw_os.core.alarm_manager import AlarmManager
from epw_os.core.project_manager import ProjectManager
from epw_os.core.logic_engine import LogicEngine
from epw_os.core.safety_kernel import SafetyKernel
from epw_os.core.command_manager import CommandManager
from epw_os.core.access_manager import AccessManager
from epw_os.core.api_auth import ApiAuth
from epw_os.core.time_sync_monitor import TimeSyncMonitor
from epw_os.core.audit_logger import AuditLogger
from epw_os.core.mqtt_manager import MqttManager
from epw_os.core.logging import log

class EPWCore:
    """
    The composition root and lifecycle manager for EPW OS.
    Headless by design. Contains NO PyQt references.
    """
    def __init__(self):
        self.is_running = False
        self.event_bus = EventBus()
        
        log.info("Initializing EPWCore services...")
        self.tag_manager = TagManager(self.event_bus)
        self.alarm_manager = AlarmManager(self.event_bus)
        
        self.project_manager = ProjectManager()
        self.logic_engine = LogicEngine(self.tag_manager)
        self.safety_kernel = SafetyKernel(self.tag_manager)
        # Always starts at User, regardless of who was logged in on a
        # previous run - there is no persisted session, only persisted PIN
        # hashes (epw_os/config/access.local.json, gitignored).
        self.access_manager = AccessManager(self.event_bus)
        # REST API bearer-token auth (Task: zamkniecie luki bezpieczenstwa
        # w REST API - see epw_os/backend/api.py and api_auth.py's own
        # docstring for why this is a separate module, not an extension
        # of AccessManager above). Same "no persisted state but the
        # token hashes themselves" stance as access_manager - constructed
        # unconditionally here, no project data needed.
        self.api_auth = ApiAuth()

        # Time sync indicator (Windows Time service, not a direct NTP
        # query - see time_sync_monitor.py's module docstring) and the
        # independent security/config audit trail (separate from the
        # operational Event Recorder - see audit_logger.py).
        self.time_sync_monitor = TimeSyncMonitor(self.event_bus)
        self.audit_logger = AuditLogger(self.event_bus)
        self.event_bus.subscribe("login_attempt", self._on_login_attempt)
        self.event_bus.subscribe("pin_changed", self._on_pin_changed)
        self.event_bus.subscribe("login_lockout", self._on_login_lockout)

        # MQTT integration (Task: "integracja MQTT") - constructed
        # unconditionally, same "always exists, decides for itself
        # whether it's actually active" stance as ApiAuth/AccessManager
        # above: MqttManager.start() (called from startup() below, after
        # load_project()) is the one place that reads whether the
        # integration is enabled at all, whether paho-mqtt is even
        # installed, and every connection setting - constructing the
        # object here costs nothing and needs no project data yet (its
        # own __init__ never touches the network). GRANICE: "Integracja
        # MQTT domyslnie WYLACZONA" - see project_manager.get_mqtt_config()'s
        # own "enabled": False default.
        self.mqtt_manager = MqttManager(self.event_bus, self.tag_manager, self.project_manager, self.audit_logger)

        from epw_os.core.health_manager import HealthManager
        from epw_os.core.historian import Historian
        from epw_os.drivers.simulator_driver import SimulatorDriver
        from epw_os.core.driver_manager import DriverManager
        from epw_os.core.device_manager import DeviceManager
        from epw_os.simulation.simulated_plant import SimulatedPlant
        self.health_manager = HealthManager(self.event_bus)
        # audit_logger (Task: retention) - already constructed above,
        # passed straight through so a retention config change/purge can
        # be recorded to the audit trail (see historian.py's own
        # configure_retention()/_enforce_retention()).
        self.historian = Historian(self.event_bus, audit_logger=self.audit_logger)
        # switching_counters/service_notes are NOT constructed here like
        # the managers above - unlike them, their constructors read
        # persisted project data immediately, and self.project_manager
        # is still empty at this point (ProjectManager() only loads its
        # config later, in startup()). Constructed in startup() instead,
        # right after load_project() - see there.
        self.switching_counters = None
        self.service_notes = None
        # Intrusion (burglar) alarm system (Task: "system alarmowy...
        # konfigurowalne linie dozorowe i strefy") - same "waits for
        # load_project()" reason as switching_counters/service_notes
        # above, PLUS it needs the DI/device tags its own lines
        # reference to already exist (so it can seed each line's live
        # violated state at construction, not just react to future
        # tag_changed events) - constructed later in startup() than
        # those two, right after DI/device registration. See there.
        self.intrusion_manager = None
        # Process protections (page-split task, part 1 - "Zabezpieczenia
        # procesowe") - same "waits for load_project(), and for the
        # analog input tags it references to already exist" reason as
        # intrusion_manager above. See _start_process_protection().
        self.process_protection_manager = None
        # Feature configuration (Task: "okno konfiguracji funkcji") -
        # same deferred-to-startup() reason as everything else on this
        # page: needs load_project() to have populated the persisted
        # section first. An empty dict here is never actually consulted
        # for anything (is_feature_enabled() would read every togglable
        # feature as its own fail-open default anyway) - startup()
        # always overwrites this with normalize_enabled_features()'s
        # real result before anything else checks it.
        self.enabled_features = {}
        # Alarm event history for the intrusion module (Task: "historia
        # zdarzen alarmowych") - same deferred-to-startup() reason as
        # intrusion_manager itself just above (needs load_project() to
        # have populated the persisted retention config), constructed
        # right before it so IntrusionManager can be handed a real
        # reference instead of None.
        self.intrusion_alarm_history = None
        # Training Mode (Task: tryb cwiczebny) - unlike switching_counters/
        # service_notes above, this has no persisted data to wait for
        # (it's never persisted at all, by design - see
        # training_mode.py), so it's constructed here in __init__ like
        # the other plain headless managers rather than deferred to
        # startup(). Needs audit_logger (already constructed above) and
        # needs to exist before DriverManager, which reads it in
        # route_command() - the actual cutoff point.
        from epw_os.core.training_mode import TrainingModeManager
        self.training_mode = TrainingModeManager(self.event_bus, self.audit_logger)
        self.driver_manager = DriverManager(self.event_bus, training_mode=self.training_mode)
        self.device_manager = DeviceManager(self.event_bus)
        
        self.sim_driver = SimulatorDriver(self.event_bus)
        self.driver_manager.register_driver("SIM_DRIVER", self.sim_driver)

        # SafetyKernel was constructed above with only tag_manager (before
        # device_manager/driver_manager/alarm_manager/audit_logger
        # existed) - wire the rest of what its health checks read/signal
        # through in now, the same set_driver_manager()-style pattern
        # CommandManager already uses a few lines below.
        self.safety_kernel.set_device_manager(self.device_manager)
        self.safety_kernel.set_driver_manager(self.driver_manager)
        self.safety_kernel.set_alarm_manager(self.alarm_manager)
        self.safety_kernel.set_audit_logger(self.audit_logger)

        # Simulated Plant mappings
        plant_mappings = {
            "ADA01.DO01": {
                "trigger_value": True,
                "delay_ms": 50,
                "feedback_tag": "ELA01.DI03",
                "feedback_value": True
            }
        }
        self.simulated_plant = SimulatedPlant(self.event_bus, mappings=plant_mappings)
        
        self.command_manager = CommandManager(self.tag_manager, self.logic_engine, self.safety_kernel, self.event_bus)
        self.command_manager.set_driver_manager(self.driver_manager)

        # Presentation Mode (Task: scenariusz demonstracyjny uruchamiany
        # jednym poleceniem) - constructed here like every other
        # runtime-only manager (TrainingModeManager, SwitchingCounterManager)
        # rather than in the GUI layer: it's system-wide state (one
        # source of truth for "is a demo running right now"), not a
        # page-scoped tool. Needs command_manager, so built right after
        # it. Requires Training Mode active to ever run a scenario - see
        # presentation_mode.py's own docstring for the full reasoning.
        # driver_manager/device_manager (Task: 4 more scenarios - scenario
        # 2's device_comm steps) are already constructed above this
        # point, wired in now the same way command_manager/alarm_manager/
        # training_mode already are. switching_counters is NOT ready yet
        # here (it needs project_manager, only built in startup() below)
        # - see set_switching_counter_manager() call in startup(), the
        # same deferred-wiring pattern safety_kernel's
        # set_device_manager()/set_driver_manager() already use for
        # exactly this ordering reason.
        from epw_os.core.presentation_mode import PresentationMode
        self.presentation_mode = PresentationMode(
            self.event_bus, self.tag_manager, self.command_manager, self.alarm_manager,
            self.training_mode, self.audit_logger,
            driver_manager=self.driver_manager, device_manager=self.device_manager,
        )

        self.event_bus.subscribe("driver_to_tag", self._bridge_driver_to_tag)
        self.event_bus.subscribe("mode_change_request", self._handle_mode_request)
        self.event_bus.subscribe("driver_comm_ok", self._on_driver_comm_ok)
        self.event_bus.subscribe("device_status_changed", self._on_device_status_changed)
        # Real alarm sources for AlarmManager (see _on_device_status_changed
        # and _on_tag_changed_for_alarms below) - purely observational
        # (read a tag, raise/clear a UI alarm), no safety decision and no
        # command dispatch, so this is safe to wire here rather than in
        # safety_kernel.py/interlock_engine.py.
        self.event_bus.subscribe("tag_changed", self._on_tag_changed_for_alarms)
        # SafetyKernel's Fault latches clear ONLY via manual acknowledgement
        # on the existing Alarms page (task requirement) - AlarmManager
        # already emits this event from acknowledge_alarm(), so this is
        # purely a bridge, not a new acknowledgement mechanism.
        self.event_bus.subscribe("alarm_acknowledged", self._on_alarm_acknowledged)

    def _bridge_driver_to_tag(self, tag_name, value, quality):
        from epw_os.core.tag_manager import TagQuality
        q = TagQuality(quality) if isinstance(quality, str) else quality
        self.tag_manager.update_tag(tag_name, value, q)

    def _handle_mode_request(self, new_mode: str):
        log.info(f"System mode transitioning to {new_mode}")
        self.tag_manager.set_mode(new_mode)

    def _on_login_attempt(self, level: str, success: bool):
        detail = f"Login attempt at {level} level" if success else f"Failed login attempt at {level} level"
        self.audit_logger.record("LOGIN", level, detail, success=success)

    def _on_pin_changed(self, level: str):
        self.audit_logger.record("PIN_CHANGE", level, f"{level} PIN changed", success=True)

    def _on_login_lockout(self, level: str, duration_seconds: float):
        self.audit_logger.record(
            "LOGIN_LOCKOUT", level,
            f"{level} locked out for {duration_seconds:.0f}s after repeated failed PIN attempts",
            success=False,
        )

    def _on_driver_comm_ok(self, device_id: str):
        """A driver reported a successful poll cycle for device_id - mark it
        alive and re-check every device's watchdog (cheap: a handful of
        devices) so a driver that later stalls still flips to COMM_FAILURE."""
        self.device_manager.update_comm(device_id)
        self.device_manager.check_watchdogs()

    def _on_device_status_changed(self, device_id: str, status: str):
        """Bridge DeviceManager's internal status to the GUI-facing
        Device.<id>.Status tag - created the first time this fires for a
        given device_id, updated on every later change. Also raises/
        clears a real AlarmManager alarm on COMM_FAILURE - the only
        device-status transition genuinely live in this system today
        (see SESSION_REPORT.md for why COMM_FAILURE and EMERGENCY_STOP
        were chosen as the alarm-acknowledgement feature's real triggers
        instead of inventing one).

        Bug fix (Task: "luka w blokadzie komend przy awarii komunikacji
        dla urzadzen skonfigurowanych w projekcie"): this tag used to
        exist ONLY for the four hardcoded default devices (registered
        directly in TagManager.init_default_tags()'s cabinet_tags) - any
        project-configured device (TagManager.configure()'s multi-device
        path) never got one at all, silently defeating
        SafetyKernel.validate_command_safety()'s per-device
        communication-health check for every such device. Now created
        lazily here instead, for ANY device_id (default or
        project-configured), the first time its status is actually
        known - the same "create on first real signal" pattern
        SafetyKernel._ensure_bool_tag() already uses for
        Safety.<id>.Healthy/.Fault."""
        tag_name = f"Device.{device_id}.Status"
        if self.tag_manager.get_tag(tag_name) is None:
            from epw_os.core.tag_manager import TagType
            self.tag_manager.add_tag(
                tag_name, status, TagType.STRING,
                description=f"Communication status (ONLINE/OFFLINE/COMM_FAILURE) of device '{device_id}', "
                            f"as tracked by DeviceManager's poll-cycle watchdog.",
                source="SYSTEM",
            )
        else:
            self.tag_manager.update_tag(tag_name, status)

        alarm_id = f"DEVICE_COMM_{device_id}"
        if status == "COMM_FAILURE":
            self.alarm_manager.trigger_alarm(
                alarm_id, f"{device_id} communication failure", source_tag=tag_name, priority=3
            )
        else:
            self.alarm_manager.clear_alarm(alarm_id)

    def _on_alarm_acknowledged(self, alarm):
        """Bridges AlarmManager's existing acknowledgement event to
        SafetyKernel's Fault-latch clearing - see
        SafetyKernel.on_alarm_acknowledged()'s docstring. A no-op for any
        alarm_id SafetyKernel didn't itself raise (DEVICE_COMM_*,
        EMERGENCY_STOP, or anything else - on_alarm_acknowledged() checks
        the id itself and ignores what it doesn't recognize)."""
        self.safety_kernel.on_alarm_acknowledged(alarm.id, alarm.ack_user)

    def _on_tag_changed_for_alarms(self, tag_name, value, quality):
        """EMERGENCY_STOP is a registered tag nothing currently writes in
        this simulated environment, but it's the one other genuinely
        safety-relevant real tag in the system (read by safety_kernel.py/
        interlock_engine.py, both untouched here) - alarming on it is
        purely observational, not a safety decision."""
        if tag_name == "EMERGENCY_STOP":
            if value:
                self.alarm_manager.trigger_alarm(
                    "EMERGENCY_STOP", "EMERGENCY STOP active", source_tag="EMERGENCY_STOP", priority=4
                )
            else:
                self.alarm_manager.clear_alarm("EMERGENCY_STOP")

    def startup(self):
        """
        Executes controlled startup lifecycle.
        """
        log.info("EPWCore Startup Sequence Initiated.")
        from epw_os.core.health_manager import SubsystemState
        
        # 1. Initialize configuration / project
        self.project_manager.load_project()

        # Feature configuration (Task: "okno konfiguracji, w ktorym
        # wlacza i wylacza sie poszczegolne funkcje sterownika") - read
        # right after load_project() so every conditional construction
        # below (switching_counters/service_notes/intrusion/analog
        # inputs) already knows the real, persisted answer. GRANICE:
        # "Domyslnie WSZYSTKIE funkcje wlaczone... bez migracji" -
        # normalize_enabled_features() backfills a missing/old-format
        # section to all-True, so an existing project behaves exactly
        # as it always did.
        from epw_os.core.feature_config import normalize_enabled_features, is_feature_enabled
        self.enabled_features = normalize_enabled_features(self.project_manager.get_enabled_features())

        # Switching counters (Task: liczba przelaczen i czas w stanie
        # zamknietym per aparat) - constructed here, not in __init__,
        # specifically because it must load persisted data
        # (project_manager.get_switching_counters()) AFTER
        # load_project() above has actually populated project_manager's
        # config, not before. Subscribes to tag_changed immediately on
        # construction, well before any DI tag can change below. Only
        # constructed at all when the feature is enabled - see
        # _start_switching_counters()/_stop_switching_counters() for the
        # same pair of steps run again later at runtime, from
        # set_feature_enabled().
        if is_feature_enabled(self.enabled_features, "switching_counters"):
            self._start_switching_counters()

        # Service notes (Task: historia serwisowa przypisana do aparatu)
        # - same "must load persisted data after load_project()" reason
        # as switching_counters above. No start()/stop() lifecycle at
        # all (unlike switching_counters/historian): notes are added one
        # at a time by a person, synchronously, and saved immediately -
        # there is no background thread or buffered state to run/flush.
        # Only constructed at all when the feature is enabled.
        if is_feature_enabled(self.enabled_features, "service_notes"):
            self._start_service_notes()

        # Configure dynamically from project config (task "migracja
        # adresacji" - configure() is now the ONLY path, called
        # unconditionally; an empty `devices` list correctly produces
        # zero DI/DO tags - see configure()'s own docstring).
        devices = self.project_manager.config.get("devices", [])
        self.tag_manager.configure(devices)
        for dev in devices:
            self.device_manager.register_device(dev.get("id"), dev.get("driver", "SIM_DRIVER"), dev.get("timeout", 5.0))
        sim_device_ids = [dev.get("id") for dev in devices if dev.get("driver", "SIM_DRIVER") == "SIM_DRIVER"]

        # Main View's cabinet-status panel and electricity-simulation
        # tags (Cabinet.*, Device.*.Status, Sim.*, Meas.*) - unconditional,
        # same as before this task (previously bundled into
        # init_default_tags(), which only ran in the "no devices" branch
        # this if/else used to have - see tag_manager.py's own docstring
        # for why splitting them apart rather than also making them
        # conditional preserves EXACTLY the same behavior for both cases,
        # not a new one).
        self.tag_manager.init_simulation_and_cabinet_tags()
        # The four legacy simulated cabinet-status devices (Device.OrangePi.
        # Status / .ELA01. / .ADA01. / .Modbus., just seeded above) still
        # expect live comm status - registered here, unconditionally, same
        # as init_simulation_and_cabinet_tags() itself, so the status
        # pipeline is real instead of a permanently-stale hardcoded default.
        # A real project device sharing one of these four ids is registered
        # twice (register_device()/set_devices() below are both idempotent
        # on id) - harmless, not a new collision this task introduces.
        default_devices = ["OrangePi", "ELA01", "ADA01", "Modbus"]
        for dev_id in default_devices:
            self.device_manager.register_device(dev_id, "SIM_DRIVER", timeout=5.0)
        sim_device_ids = sim_device_ids + [d for d in default_devices if d not in sim_device_ids]

        # SimulatorDriver polls these device IDs on its own cycle and reports
        # comm-ok heartbeats for each, which _on_driver_comm_ok() turns into
        # real ONLINE/OFFLINE transitions instead of a static default.
        self.sim_driver.set_devices(sim_device_ids)

        # Intrusion alarm system (Task: "system alarmowy") - constructed
        # here, not earlier: needs load_project() (above) to have
        # actually populated project_manager's config so
        # get_intrusion_zones()/get_intrusion_lines() return real
        # persisted data, AND needs the DI/device tags just registered
        # above to already exist so it can seed each supervision line's
        # live violated state right now instead of only from a future
        # tag_changed event (same "don't rely solely on a future signal"
        # reasoning as the time sync indicator / training mode / alarms
        # status-bar widgets). GRANICE: does not touch safety_kernel.py,
        # the permission matrix, Kiosk/Training Mode, or the API/auth -
        # see intrusion_manager.py's own module docstring for the full
        # scope boundary (never writes to any driver/output tag).
        # Only constructed at all when the feature is enabled.
        if is_feature_enabled(self.enabled_features, "intrusion"):
            self._start_intrusion()

        # Analog Inputs: a dynamic, operator-managed points collection, not
        # part of the devices/init_default_tags split above - registered
        # from ProjectManager's own persisted list regardless of which
        # device-config path was taken (a point isn't tied to a physical
        # device slot the way DI/DO are). See add_analog_point()/
        # remove_analog_point() for how the set changes at runtime, and
        # ProjectManager.get_analog_points() for the one-time migration
        # from the old fixed-AI1..AI16 format. Only registered at all
        # when the feature is enabled - the persisted points list itself
        # is untouched either way (Task: "wylaczenie nigdy nie kasuje
        # danych"), only whether their TAGS exist right now.
        if is_feature_enabled(self.enabled_features, "analog_inputs"):
            self._register_analog_input_tags()

        # Process protections (page-split task, part 1 - "Zabezpieczenia
        # procesowe") - constructed here, AFTER analog input tags are
        # registered just above, for the same "seed from a live tag,
        # not just a future event" reason intrusion is constructed after
        # DI/device tags exist. Independent of "protection_settings"
        # (Elektryczne) - see nav_model.py's own module docstring on why
        # this dependency is deliberately NOT wired the way engineer_mode/
        # protection_settings is. Only constructed at all when enabled.
        if is_feature_enabled(self.enabled_features, "protection_process"):
            self._start_process_protection()

        # System.Theme: writable, drives the GUI's visual theme (Task:
        # przelaczane motywy wizualne) - registered unconditionally here,
        # same reasoning as analog_points above (not tied to which
        # devices/init_default_tags branch ran). Always seeded to the
        # Industrial default: Core knows nothing about the GUI's
        # persisted, machine-local theme preference (epw_os/gui/
        # window_state.py, not project data) - the GUI applies the
        # operator's actual saved theme on startup by writing through
        # this exact same tag right after MainWindow exists (see
        # ThemeManager.bind_tag_manager()), so "restored on restart" and
        # "changed via logic" are provably the same code path.
        from epw_os.core.themes import DEFAULT_THEME_INDEX
        from epw_os.core.tag_manager import TagType
        self.tag_manager.add_tag(
            "System.Theme", DEFAULT_THEME_INDEX, TagType.INT,
            description="Active visual theme (0=Industrial, 1=Night, 2=High Contrast, "
                        "3=Cyberpunk, 4=SimCity 2000)",
            source="SYSTEM",
        )

        # Apply any persisted operator-edited tag descriptions on top of the
        # defaults (e.g. custom DI labels saved from the GUI).
        for tag_name, desc in self.project_manager.get_tag_descriptions().items():
            self.tag_manager.set_description(tag_name, desc)

        commands = self.project_manager.config.get("commands", {})
        if commands:
            self.command_manager.load_definitions(commands)
        else:
            # Task "migracja adresacji": the old DO01-DO04-wired-to-DI1-DI4
            # special case is GONE along with the flat scheme itself - it
            # had no natural generalization to a real, multi-device ADA
            # card (there is no structural "first four channels are
            # special" concept once channel numbers aren't project-wide
            # slots anymore, only per-card). Every real DO channel
            # configure() just created is now self-contained instead -
            # each tag is both the command output and its own feedback -
            # the same pattern the old flat scheme already used for its
            # OWN majority case (DO05-DO64). Built from whatever DO tags
            # actually exist (addressing.is_address(), not a range()), so
            # this scales to any number of ADA cards/channels a project
            # has, or none at all (an empty `devices` project correctly
            # gets zero default command definitions - nothing to route to).
            from epw_os.core.addressing import is_address
            default_commands = {}
            for tag in self.tag_manager.list_tags():
                if not is_address(tag.name, "DO"):
                    continue
                default_commands[f"{tag.name}.CLOSE"] = {
                    "driver_id": "SIM_DRIVER", "output_tag": tag.name, "output_value": True,
                    "feedback_tag": tag.name, "feedback_value": True, "timeout_ms": 1500
                }
                default_commands[f"{tag.name}.OPEN"] = {
                    "driver_id": "SIM_DRIVER", "output_tag": tag.name, "output_value": False,
                    "feedback_tag": tag.name, "feedback_value": False, "timeout_ms": 1500
                }
            self.command_manager.load_definitions(default_commands)

        logic_file = self.project_manager.get_logic_file()
        if logic_file:
            if not self.logic_engine.load_program(logic_file):
                self.health_manager.update_subsystem("LOGIC_RUNTIME", SubsystemState.FAULT)
            else:
                self.logic_engine.is_running = True
                self.health_manager.update_subsystem("LOGIC_RUNTIME", SubsystemState.RUNNING)
        else:
            self.health_manager.update_subsystem("LOGIC_RUNTIME", SubsystemState.DEGRADED)
        
        # 2. Database & Historian
        # *.db files are gitignored, so a fresh checkout (or a clean CI
        # runner) has no database at all until migrations create it. Apply
        # them now, before the Historian worker starts writing.
        from epw_os.db.database import run_migrations
        run_migrations()
        # Deadband config (Task: ograniczenie zapisow na karcie SD) applied
        # before start() - see project_manager.py's get_deadband_config()/
        # historian.py's configure_deadband() for the optional
        # project.json section and the sensible built-in defaults used
        # when it's absent.
        self.historian.configure_deadband(self.project_manager.get_deadband_config())
        # Retention (Task: feature/retention-and-test-fix) - same "read
        # the persisted, optional section, apply before start()" pattern
        # as the deadband config just above. GRANICE: "Retencja domyslnie
        # WYLACZONA" - get_historian_retention_config() returns 0/0 (off)
        # for a project that never configured this, so this call is a
        # no-op for every existing installation until an Engineer
        # explicitly sets a limit.
        _hist_retention = self.project_manager.get_historian_retention_config()
        self.historian.configure_retention(
            max_days=_hist_retention.get("max_days", 0), max_rows=_hist_retention.get("max_rows", 0))
        # Same pattern for the audit log's own retention (B2) - archive_dir
        # left as "" (project has no override) falls back to
        # AuditLogger's own built-in default location.
        _audit_retention = self.project_manager.get_audit_retention_config()
        self.audit_logger.configure_retention(
            max_days=_audit_retention.get("max_days", 0), max_rows=_audit_retention.get("max_rows", 0),
            archive_dir=_audit_retention.get("archive_dir") or None)
        self.historian.start()
        self.health_manager.update_subsystem("HISTORIAN", SubsystemState.RUNNING)
        # Periodic background save only (GRANICE: "zapisuj okresowo oraz
        # przy zamykaniu programu", never on every state change) - the
        # manager itself has already been counting since it was
        # constructed above, immediately after load_project(). May be
        # None (feature disabled) - same tolerance shutdown()'s own
        # stop() call already has.
        if self.switching_counters is not None:
            self.switching_counters.start()
        # Same "periodic background save only" reasoning as
        # switching_counters.start() above - intrusion_manager.py's own
        # line-life supervision (part 3: violation counters/timestamps)
        # and silence/suspect check both run off this one periodic tick.
        if self.intrusion_manager is not None:
            self.intrusion_manager.start()
        self.health_manager.update_subsystem("DATABASE", SubsystemState.RUNNING)
        
        # 3. Initialize Drivers & Devices
        self.driver_manager.start_all()
        if not self.driver_manager.all_required_running():
            log.error("Required driver startup failed")
            
        self.health_manager.update_subsystem("DRIVERS", SubsystemState.RUNNING)

        # 4. Time sync monitor - check once synchronously right away so the
        # status bar indicator has a real reading immediately, then keep
        # polling in the background.
        self.time_sync_monitor.check_once()
        self.time_sync_monitor.start()

        # 5. SafetyKernel health monitor - starts only after devices are
        # registered and drivers are running above, on its own background
        # thread (see safety_kernel.py) so the once-per-second check never
        # runs on, or blocks, the GUI thread.
        self.safety_kernel.start()

        # 6. MQTT integration - last, deliberately: publishes a full
        # retained snapshot of every tag registered above the moment it
        # connects (see MqttManager._publish_controller_status()), so
        # starting it only once everything else is fully configured
        # means that very first snapshot is already complete rather than
        # a partial one a moment before more tags get registered. A
        # no-op call when disabled/unavailable - see its own module
        # docstring (A2/A6: "brak biblioteki albo brak brokera NIE MOZE
        # uniemozliwic uruchomienia programu").
        self.mqtt_manager.start()

        self.is_running = True
        self.health_manager.update_subsystem("API", SubsystemState.RUNNING)
        log.info("EPWCore Startup Sequence Complete.")

    # --- Analog Inputs: dynamic points -----------------------------
    # (see startup()'s registration above and page_analog_inputs.py's
    # Add Point / Remove Point buttons for the GUI side)

    def add_analog_point(self, point: dict) -> bool:
        """Registers a brand-new Analog Inputs point: a real TagManager
        tag (the live value source), persisted into project.json's
        analog_points list, and told to the simulator so it starts
        producing values for it on the next poll cycle. Returns False
        (no-op, nothing registered or persisted) if the tag name is
        already taken - by another analog point or any other tag
        (DI/DO/Cabinet/...) - tag names are a single flat namespace."""
        from epw_os.core.tag_manager import TagType
        tag_name = point["tag"]
        if self.tag_manager.get_tag(tag_name) is not None:
            return False
        self.tag_manager.add_tag(
            tag_name, 0.0, TagType.REAL,
            description=point.get("description", ""), source="HARDWARE"
        )
        points = self.project_manager.get_analog_points()
        points.append(dict(point))
        self.project_manager.save_project()
        self.sim_driver.set_analog_tags([p["tag"] for p in points])
        return True

    def remove_analog_point(self, tag_name: str) -> bool:
        """Unregisters an existing point - removes the live tag, drops
        its persisted record, and stops the simulator from producing
        values for it. Returns False if tag_name isn't a currently
        registered tag at all."""
        if not self.tag_manager.remove_tag(tag_name):
            return False
        points = [p for p in self.project_manager.get_analog_points() if p["tag"] != tag_name]
        self.project_manager.set_analog_points(points)
        self.project_manager.save_project()
        self.sim_driver.set_analog_tags([p["tag"] for p in points])
        return True

    def update_analog_point(self, tag_name: str, point: dict):
        """Updates an existing point's description/signal config/
        technical note - not its tag name. Renaming a live tag isn't
        supported (same as every other tag in this system); remove and
        re-add under the new name instead."""
        self.tag_manager.set_description(tag_name, point.get("description", ""))
        points = self.project_manager.get_analog_points()
        for p in points:
            if p["tag"] == tag_name:
                p.update(point)
                p["tag"] = tag_name
                break
        self.project_manager.save_project()

    # --- Feature configuration (Task: "okno konfiguracji funkcji") ---------
    #
    # Two kinds of helper below: a start_X()/stop_X() pair per feature that
    # actually HAS something to start/stop (switching_counters, service_notes,
    # intrusion, analog_inputs' tag registration), and set_feature_enabled()
    # itself, the one entry point that persists the change, audits it, and
    # calls the right pair - used both by startup() above (the initial
    # construction) and live, from the GUI's Feature Configuration dialog,
    # with no program restart either way (GRANICE: "zmiana ma dzialac BEZ
    # RESTARTU programu"). Features with nothing of their own to start/stop
    # (trends, power_quality, protection_settings, bus_diagnostics,
    # system_topology, engineer_mode - see SESSION_REPORT.md for the survey
    # behind that list) still go through set_feature_enabled() for the
    # persistence/audit step; there's just no corresponding helper pair to
    # call for them.

    def _start_switching_counters(self):
        from epw_os.core.switching_counters import SwitchingCounterManager
        self.switching_counters = SwitchingCounterManager(self.event_bus, self.project_manager)
        # Deferred wiring (Task: scenariusz 5 - zuzycie mechaniczne) -
        # presentation_mode already exists by the time this ever runs
        # (constructed in __init__(), before switching_counters could
        # exist even at startup) - see its own constructor comment.
        self.presentation_mode.switching_counter_manager = self.switching_counters
        if self.is_running:
            # A live (post-startup) enable - startup() itself calls
            # .start() once, later, alongside the historian/intrusion
            # start() calls, not here (self.is_running is only True
            # once startup() has already gotten that far).
            self.switching_counters.start()

    def _stop_switching_counters(self):
        if self.switching_counters is None:
            return
        self.switching_counters.stop()  # flushes pending counts, detaches from tag_changed - see its own docstring
        self.switching_counters = None
        if self.presentation_mode is not None:
            self.presentation_mode.switching_counter_manager = None

    def _start_service_notes(self):
        from epw_os.core.service_notes import ServiceNoteManager
        self.service_notes = ServiceNoteManager(self.project_manager)

    def _stop_service_notes(self):
        # No thread, no subscription, no tags - see the module survey in
        # SESSION_REPORT.md. Dropping the reference is the whole thing;
        # already-saved notes are untouched (ServiceNoteManager never
        # deletes anything it wrote).
        self.service_notes = None

    def _start_intrusion(self):
        from epw_os.core.intrusion_manager import IntrusionManager
        from epw_os.core.intrusion_history import IntrusionAlarmHistoryLogger
        self.intrusion_alarm_history = IntrusionAlarmHistoryLogger(self.project_manager, self.event_bus)
        self.intrusion_manager = IntrusionManager(self.event_bus, self.tag_manager, self.project_manager,
                                                   self.audit_logger, self.intrusion_alarm_history)
        if self.is_running:
            self.intrusion_manager.start()

    def _stop_intrusion(self):
        if self.intrusion_manager is None:
            return
        self.intrusion_manager.teardown()  # stops its thread/timers, detaches from tag_changed, removes every Security.* tag
        self.intrusion_manager = None
        self.intrusion_alarm_history = None

    def _start_process_protection(self):
        from epw_os.core.process_protection_manager import ProcessProtectionManager
        self.process_protection_manager = ProcessProtectionManager(
            self.event_bus, self.tag_manager, self.project_manager, self.audit_logger)
        # No is_running-gated .start() call, unlike switching_counters/
        # intrusion above - this module has no background thread of its
        # own (only short-lived per-protection threading.Timer delay
        # confirmations), so construction alone is already "running".

    def _stop_process_protection(self):
        if self.process_protection_manager is None:
            return
        self.process_protection_manager.teardown()  # cancels pending timers, detaches from tag_changed, removes tags
        self.process_protection_manager = None

    def _register_analog_input_tags(self):
        from epw_os.core.tag_manager import TagType
        analog_points = self.project_manager.get_analog_points()
        for point in analog_points:
            self.tag_manager.add_tag(
                point["tag"], 0.0, TagType.REAL,
                description=point.get("description", ""), source="HARDWARE"
            )
        self.sim_driver.set_analog_tags([p["tag"] for p in analog_points])

    def _unregister_analog_input_tags(self):
        # Deliberately does NOT touch project_manager's persisted points
        # list (unlike remove_analog_point() above, which is a real
        # delete) - only the live tags disappear; re-enabling replays
        # _register_analog_input_tags() against the same, untouched
        # list (Task: "wylaczenie nigdy nie kasuje danych").
        for point in self.project_manager.get_analog_points():
            self.tag_manager.remove_tag(point["tag"])
        self.sim_driver.set_analog_tags([])

    # Which feature each helper pair above belongs to - the only place
    # this mapping is spelled out, so set_feature_enabled() below stays
    # a plain lookup instead of a chain of if/elif.
    _FEATURE_START_STOP = {
        "switching_counters": ("_start_switching_counters", "_stop_switching_counters"),
        "service_notes": ("_start_service_notes", "_stop_service_notes"),
        "intrusion": ("_start_intrusion", "_stop_intrusion"),
        "analog_inputs": ("_register_analog_input_tags", "_unregister_analog_input_tags"),
        "protection_process": ("_start_process_protection", "_stop_process_protection"),
    }

    def get_feature_tag_names(self, feature: str) -> list:
        """Which TagManager tag names `feature` currently owns and would
        remove if disabled right now - used both to actually remove them
        (via the stop_X() helpers above, which recompute this
        themselves rather than trusting a possibly-stale list) and to
        warn beforehand if logic references any of them (see
        feature_referenced_by_logic()). Every feature not listed here
        owns no tags of its own (see the module survey in an earlier
        SESSION_REPORT.md revision) - trends/power_quality/
        protection_settings/bus_diagnostics/system_topology/
        engineer_mode all return []. "intrusion_history"/"intrusion_
        config" (page-split task) also return [] deliberately - they
        are pure page-visibility toggles for viewing/configuring
        "intrusion"'s OWN tags, not owners of any tag themselves."""
        if feature == "intrusion" and self.intrusion_manager is not None:
            names = []
            for zone in self.intrusion_manager.get_zones():
                for suffix in ("State", "ArmRequest", "CountdownRemaining", "AlarmMemoryActive",
                               "AlarmMemoryFirstCauseLine", "WalkTestActive"):
                    names.append(f"Security.Zone.{zone['id']}.{suffix}")
            for line in self.intrusion_manager.get_lines():
                for suffix in ("Violated", "Locked", "MultiplicityCounting", "State", "Fault", "Suspect"):
                    names.append(f"Security.Line.{line['id']}.{suffix}")
            names.extend([
                "Security.System.State", "Security.System.Alarm", "Security.System.EntryCountdownActive",
                "Security.System.ExitCountdownActive", "Security.Supervisory.Violated", "Security.System.LineFault",
                "Security.Power.MainsOk", "Security.Power.BatteryOk", "Security.System.TechnicalAlarm",
            ])
            return names
        if feature == "analog_inputs":
            return [p["tag"] for p in self.project_manager.get_analog_points()]
        if feature == "protection_process" and self.process_protection_manager is not None:
            return [f"Process.{p['id']}.Exceeded" for p in self.process_protection_manager.get_protections()]
        return []

    def feature_referenced_by_logic(self, feature: str) -> bool:
        """Best-effort check for the Task's own required warning ("jesli
        logika uzytkownika uzywa tagow tej funkcji"): True if any tag
        `feature` owns appears anywhere in the currently-loaded logic
        project. LogicEngine (Task's own placeholder engine - see its
        module docstring) exposes no dedicated "which tags does this
        program reference" API, so this reads its raw loaded JSON
        directly rather than adding one just for this - logic_engine.py
        itself is untouched. A tag name appearing as a substring of some
        unrelated JSON value would be a false positive; there are no
        false negatives, which is the direction that actually matters
        for a warning."""
        tag_names = self.get_feature_tag_names(feature)
        if not tag_names:
            return False
        project = getattr(self.logic_engine, "_project", None)
        if not project:
            return False
        import json as _json
        text = _json.dumps(project)
        return any(name in text for name in tag_names)

    def set_feature_enabled(self, feature: str, enabled: bool, actor: str, level: str = None) -> dict:
        """The one entry point for turning a controller function on/off,
        used by both the GUI dialog and (for tests) direct calls. Always
        refuses for an ALWAYS_ON feature, REGARDLESS of level or of
        being called directly instead of through the dialog (Task's own
        DOWOD requirement: "funkcji z listy zabronionej NIE da sie
        wylaczyc, takze przez bezposrednie wywolanie z pominieciem
        interfejsu"). `level`, if given, must be Engineer - same
        defense-in-depth stance every other Engineer-gated core method
        in this codebase already has (e.g. IntrusionManager.add_zone()).
        Persists immediately, audits immediately, then runs the actual
        start/stop for features that have one - live, no restart.
        Returns {"success": bool, "reason": str}."""
        from epw_os.core.access_manager import AccessLevel
        from epw_os.core.feature_config import ALWAYS_ON_FEATURES, TOGGLABLE_FEATURES, is_feature_enabled
        if feature in ALWAYS_ON_FEATURES:
            log.warning(f"Refused to disable feature {feature!r}: it is always-on.")
            return {"success": False, "reason": f"'{feature}' cannot be disabled."}
        if feature not in TOGGLABLE_FEATURES:
            log.warning(f"Refused to change unknown feature {feature!r}.")
            return {"success": False, "reason": f"Unknown feature '{feature}'."}
        if level is not None:
            order = AccessLevel._ORDER
            try:
                if order.index(level) < order.index(AccessLevel.ENGINEER):
                    log.warning(f"Refused to change feature {feature!r}: level {level!r} is below Engineer.")
                    return {"success": False, "reason": "Access denied - Engineer level required."}
            except ValueError:
                # `level` is caller-supplied; unrecognized -> denied (kept
                # unchanged), but worth a log line - same "polykane
                # wyjatki" pattern as System.Mode.
                log.warning(f"Refused to change feature {feature!r}: unrecognized level {level!r} - denying.")
                return {"success": False, "reason": "Access denied - Engineer level required."}

        enabled = bool(enabled)
        was_enabled = is_feature_enabled(self.enabled_features, feature)
        if was_enabled == enabled:
            return {"success": True, "reason": "unchanged"}  # idempotent, no duplicate audit entry

        self.enabled_features[feature] = enabled
        self.project_manager.set_enabled_features(self.enabled_features)
        self.project_manager.save_project()

        start_stop = self._FEATURE_START_STOP.get(feature)
        if start_stop is not None:
            start_name, stop_name = start_stop
            getattr(self, start_name if enabled else stop_name)()

        if self.audit_logger is not None:
            self.audit_logger.record(
                "FEATURE_ENABLED" if enabled else "FEATURE_DISABLED", actor,
                f"Feature '{feature}' {'enabled' if enabled else 'disabled'}", success=True,
            )
        return {"success": True, "reason": ""}

    def shutdown(self):
        """
        Executes controlled graceful shutdown.
        """
        log.info("EPWCore Shutdown Sequence Initiated.")
        self.is_running = False

        # Publishes a clean, retained "offline" and joins its worker
        # thread before anything else stops - see MqttManager.stop()'s
        # own docstring. A no-op if it was never actually connected
        # (disabled/library missing/no broker configured).
        if self.mqtt_manager is not None:
            self.mqtt_manager.stop()

        # A running presentation leaves a threading.Timer scheduled for
        # its next step - stop() cancels it (and restores state) before
        # anything else shuts down, same "don't leave a dangling
        # background callback past process exit" concern as every other
        # explicit stop() in this method.
        if self.presentation_mode is not None:
            self.presentation_mode.stop(actor="System (shutdown)")

        # Same "don't leave a dangling background callback past process
        # exit" concern as Presentation Mode above - a zone mid-exit- or
        # entry-delay leaves its own threading.Timer scheduled.
        if self.intrusion_manager is not None:
            self.intrusion_manager.shutdown()

        # Same "don't leave a dangling background callback past process
        # exit" concern - a process protection mid-delay leaves its own
        # threading.Timer scheduled. teardown() is the same method
        # set_feature_enabled() uses to turn this module off live - this
        # module has no separate "leave tags in place, TagManager is
        # about to disappear anyway" shutdown() variant to bother with
        # (see process_protection_manager.py's own docstring on why one
        # method covers both cases here).
        if self.process_protection_manager is not None:
            self.process_protection_manager.teardown()

        # Stop runtimes
        from epw_os.core.health_manager import SubsystemState
        self.logic_engine.is_running = False
        self.health_manager.update_subsystem("LOGIC_RUNTIME", SubsystemState.STOPPING)
        
        # Flush Historian & Stop Drivers
        self.historian.stop()
        if self.switching_counters is not None:
            # stop() itself does a final flush_to_project() (GRANICE:
            # "zapisuj... przy zamykaniu programu") - see
            # switching_counters.py.
            self.switching_counters.stop()
        self.driver_manager.stop_all()
        self.time_sync_monitor.stop()
        self.safety_kernel.stop()
        
        log.info("EPWCore Shutdown Sequence Complete.")

