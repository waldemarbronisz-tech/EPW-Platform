from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QSpacerItem, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt, QTimer
from epw_os.gui.widgets.synoptic_objects import Wire, Busbar, Breaker, Contactor, Lamp, DigitalIndicator, Transformer
from epw_os.gui.widgets.industrial_labels import StatusLabel
from epw_os.gui.widgets.popups import DeviceControlPopup, ConfirmationPopup, InterlockFailurePopup, CommandFailedPopup
from epw_os.gui.logger import ui_logger
from epw_os.core.logging import log
from epw_os.i18n import tr
from epw_os.core.access_manager import AccessLevel
from epw_os.core.tag_manager import TagQuality
from epw_os.gui.theme_manager import get_theme_manager, current_colors
import random
import time
from datetime import datetime

class MeasurementPanel(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("SunkenFrame")
        layout = QGridLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("SectionHeader")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl, 0, 0, 1, 4)

        self.vl1 = DigitalIndicator("V", tr("pages.entry_gate.meas_vl1"))
        self.vl2 = DigitalIndicator("V", tr("pages.entry_gate.meas_vl2"))
        self.vl3 = DigitalIndicator("V", tr("pages.entry_gate.meas_vl3"))
        self.freq = DigitalIndicator("Hz", tr("pages.entry_gate.meas_freq"))

        self.il1 = DigitalIndicator("A", tr("pages.entry_gate.meas_il1"))
        self.il2 = DigitalIndicator("A", tr("pages.entry_gate.meas_il2"))
        self.il3 = DigitalIndicator("A", tr("pages.entry_gate.meas_il3"))
        self.power = DigitalIndicator("kW", tr("pages.entry_gate.meas_power"))

        self.q = DigitalIndicator("kvar", tr("pages.entry_gate.meas_q"))
        self.s = DigitalIndicator("kVA", tr("pages.entry_gate.meas_s"))
        self.pf = DigitalIndicator("", tr("pages.entry_gate.meas_pf"))
        self.energy = DigitalIndicator("kWh", tr("pages.entry_gate.meas_energy"))

        # Task: podpowiedzi - "pelna nazwa wielkosci i jednostka" (the
        # tile face only has room for an abbreviation). Static, set once
        # here - see DigitalIndicator.set_base_tooltip()'s docstring for
        # why it survives every later update_value() call instead of
        # being wiped by the SIMULATED-quality note.
        self.vl1.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_vl1"))
        self.vl2.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_vl2"))
        self.vl3.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_vl3"))
        self.freq.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_freq"))
        self.il1.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_il1"))
        self.il2.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_il2"))
        self.il3.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_il3"))
        self.power.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_power"))
        self.q.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_q"))
        self.s.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_s"))
        self.pf.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_pf"))
        self.energy.set_base_tooltip(tr("pages.entry_gate.tooltip_meas_energy"))

        layout.addWidget(self.vl1, 1, 0)
        layout.addWidget(self.vl2, 1, 1)
        layout.addWidget(self.vl3, 1, 2)
        layout.addWidget(self.freq, 1, 3)

        layout.addWidget(self.il1, 2, 0)
        layout.addWidget(self.il2, 2, 1)
        layout.addWidget(self.il3, 2, 2)
        layout.addWidget(self.power, 2, 3)

        layout.addWidget(self.q, 3, 0)
        layout.addWidget(self.s, 3, 1)
        layout.addWidget(self.pf, 3, 2)
        layout.addWidget(self.energy, 3, 3)

class DeviceStatusPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("SunkenFrame")
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setVerticalSpacing(10)

        title_lbl = QLabel(tr("pages.entry_gate.device_status_title"))
        title_lbl.setObjectName("SectionHeader")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl, 0, 0, 1, 2)

        self.devices = {
            "Orange Pi": "Device.OrangePi.Status",
            "ELA-01": "Device.ELA01.Status",
            "ADA-01": "Device.ADA01.Status",
            "Modbus RTU": "Device.Modbus.Status"
        }
        self.labels = {}
        self._name_labels = []

        for i, (dev, tag) in enumerate(self.devices.items()):
            name_lbl = QLabel(dev)
            self._name_labels.append(name_lbl)
            layout.addWidget(name_lbl, i+1, 0)

            lbl = StatusLabel("---")
            self.labels[tag] = lbl
            layout.addWidget(lbl, i+1, 1)

        self._refresh_name_label_colors()
        get_theme_manager().theme_changed.connect(self._refresh_name_label_colors)

    def _refresh_name_label_colors(self, *_):
        # Was a hardcoded "color: black;" - correct for Industrial, but
        # would have stayed unreadably dark against Night/Cyberpunk/High
        # Contrast's dark panels instead of following the theme's normal
        # text color like every plain QLabel already does via the global
        # QSS (this explicit override was actually SHADOWING that).
        text_color = current_colors()["text"]
        for name_lbl in self._name_labels:
            name_lbl.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color};")

    def update_label(self, tag, value, quality):
        if tag in self.labels:
            if quality == "BAD" or value == "OFFLINE":
                self.labels[tag].update_status("OFFLINE")
            else:
                self.labels[tag].update_status(value)

class PageEntryGate(QWidget):
    # Task "migracja adresacji", point 1.2 (Waldek's own doprecyzowanie,
    # wariant C): this page's own device_map used to duplicate what an
    # APARAT already is in the project (id, feedback, command) -
    # "the same class of error as Main View <-> System Topology: two
    # sources of truth about the same thing". Fixed by reading real
    # apparatuses from apparatus_registry (epw_os/core/apparatus.py)
    # instead of keeping a private DI1-4/DO01-04 literal table - but the
    # one-line diagram ITSELF (which symbol sits where, wired to which
    # neighbour) is a fixed drawing (GRANICE: "nie zmieniaj struktury
    # paneli"), not project data - these four ROLE ids are which SLOT
    # in that fixed drawing each apparatus binding fills, not apparatus
    # ids themselves. Same convention as protection_verifier.py's own
    # ROLE_TESTED_APPARATUS.
    ROLE_MAIN_BREAKER = "main_view.q1"
    ROLE_GENERATOR_CONTACTOR = "main_view.kmg"
    ROLE_FEEDER_1 = "main_view.km1"
    ROLE_FEEDER_2 = "main_view.km2"
    ROLE_VOLTAGE_RELAY = "main_view.voltage_relay"

    def __init__(self, tag_manager, switching_counters=None, service_notes=None,
                 apparatus_registry=None, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.switching_counters = switching_counters
        self.service_notes = service_notes
        # Injected, never hardcoded - None (today's real value from
        # main.py, until the "runtime czyta projekt.epw" task lands)
        # means every role below resolves to "not configured", not a
        # guessed DO01/DI1. See apparatus.py's own module docstring.
        self.apparatus_registry = apparatus_registry

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Left side: Synoptic Diagram
        left_col = QVBoxLayout()

        syn_frame = QFrame()
        syn_frame.setObjectName("SunkenFrame")
        syn_layout = QGridLayout(syn_frame)
        syn_layout.setSpacing(0)

        lbl_supply = QLabel(tr("pages.entry_gate.lbl_supply"))
        lbl_supply.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_supply.setStyleSheet("font-weight: bold;")

        self.w_supply = Wire("V", 40)
        self.w_supply.update_voltage(True)

        # Task "migracja adresacji": widget tag_name is the real
        # apparatus's own command address, read from apparatus_registry
        # by ROLE (which slot in this fixed drawing), not a literal
        # "DO0N". `feedback` (used below to build device_map) comes from
        # the SAME apparatus - one lookup, both addresses, matching
        # what an apparatus actually is (id + feedback + command), not
        # two independently-hardcoded literals. Unconfigured (no
        # apparatus bound to this role, or it's missing one side) shows
        # plainly as "not configured" - never a guessed DO01/DI1.
        q1_command, q1_description, q1_feedback = self._apparatus_binding(self.ROLE_MAIN_BREAKER)
        self.q1 = Breaker(q1_command or tr("pages.entry_gate.apparatus_not_configured_short"))
        self.q1.description = q1_description
        self.q1.is_configured = q1_command is not None
        self.w1 = Wire("V", 40)

        kmg_command, kmg_description, kmg_feedback = self._apparatus_binding(self.ROLE_GENERATOR_CONTACTOR)
        self.kmg = Contactor(tag_name=kmg_command or tr("pages.entry_gate.apparatus_not_configured_short"))
        self.kmg.description = kmg_description
        self.kmg.is_configured = kmg_command is not None
        self.w2 = Wire("V", 40)

        self.busbar = Busbar(400)

        self.w3_1 = Wire("V", 40)
        self.w3_2 = Wire("V", 40)

        km1_command, km1_description, km1_feedback = self._apparatus_binding(self.ROLE_FEEDER_1)
        self.km1 = Contactor(tag_name=km1_command or tr("pages.entry_gate.apparatus_not_configured_short"))
        self.km1.description = km1_description
        self.km1.is_configured = km1_command is not None

        km2_command, km2_description, km2_feedback = self._apparatus_binding(self.ROLE_FEEDER_2)
        self.km2 = Contactor(tag_name=km2_command or tr("pages.entry_gate.apparatus_not_configured_short"))
        self.km2.description = km2_description
        self.km2.is_configured = km2_command is not None

        self.w4_1 = Wire("V", 40)
        self.w4_2 = Wire("V", 40)

        lbl_house = QLabel(tr("pages.entry_gate.lbl_house"))
        lbl_house.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_workshop = QLabel(tr("pages.entry_gate.lbl_workshop"))
        lbl_workshop.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Assembly on Grid in parallel sequence
        syn_layout.addWidget(lbl_supply, 0, 1, Qt.AlignmentFlag.AlignHCenter)
        syn_layout.addWidget(self.w_supply, 1, 1, Qt.AlignmentFlag.AlignHCenter)
        syn_layout.addWidget(self.q1, 2, 1, Qt.AlignmentFlag.AlignHCenter)
        syn_layout.addWidget(self.w1, 3, 1, Qt.AlignmentFlag.AlignHCenter)
        syn_layout.addWidget(self.kmg, 4, 1, Qt.AlignmentFlag.AlignHCenter)
        syn_layout.addWidget(self.w2, 5, 1, Qt.AlignmentFlag.AlignHCenter)

        syn_layout.addWidget(self.busbar, 6, 0, 1, 3, Qt.AlignmentFlag.AlignHCenter)

        syn_layout.addWidget(self.w3_1, 7, 0, Qt.AlignmentFlag.AlignHCenter)
        syn_layout.addWidget(self.w3_2, 7, 2, Qt.AlignmentFlag.AlignHCenter)

        syn_layout.addWidget(self.km1, 8, 0, Qt.AlignmentFlag.AlignHCenter)
        syn_layout.addWidget(self.km2, 8, 2, Qt.AlignmentFlag.AlignHCenter)

        syn_layout.addWidget(self.w4_1, 9, 0, Qt.AlignmentFlag.AlignHCenter)
        syn_layout.addWidget(self.w4_2, 9, 2, Qt.AlignmentFlag.AlignHCenter)

        syn_layout.addWidget(lbl_house, 10, 0, Qt.AlignmentFlag.AlignHCenter)
        syn_layout.addWidget(lbl_workshop, 10, 2, Qt.AlignmentFlag.AlignHCenter)

        syn_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding), 11, 0)

        left_col.addWidget(syn_frame, stretch=3)

        layout.addLayout(left_col, stretch=2)

        # Right side: Panel
        panel_layout = QVBoxLayout()

        self.device_status = DeviceStatusPanel()
        panel_layout.addWidget(self.device_status)

        self.meas_panel = MeasurementPanel(tr("pages.entry_gate.meas_panel_title"))
        panel_layout.addWidget(self.meas_panel)

        panel_layout.addStretch()
        layout.addLayout(panel_layout, stretch=1)

        # Setup Command Manager connection
        # The legacy hard-coded InterlockEngine rules have been removed.
        # Interlocks will now be handled by the LogicRuntime via CommandManager.

        # Setup Connections
        self.q1.request_control.connect(self.handle_control_request)
        self.kmg.request_control.connect(self.handle_control_request)
        self.km1.request_control.connect(self.handle_control_request)
        self.km2.request_control.connect(self.handle_control_request)

        # Connect to DI tags
        self.tag_manager.tag_changed.connect(self.on_tag_changed)

        # Task "migracja adresacji": keyed by whichever apparatus
        # actually has a feedback address bound - a role with no
        # apparatus, or an apparatus missing its feedback side, has
        # NOTHING to react to and is correctly absent here entirely
        # (not present-but-wrong, per the task's own "absence is the
        # honest state" rule already applied throughout this migration).
        self.device_map = {}
        for feedback_tag, widget in (
            (q1_feedback, self.q1), (kmg_feedback, self.kmg),
            (km1_feedback, self.km1), (km2_feedback, self.km2),
        ):
            if feedback_tag:
                self.device_map[feedback_tag] = widget

        # Switching counters (Task: liczba przelaczen i czas w stanie
        # zamknietym per aparat) are keyed by the apparatus's own
        # feedback tag - the one that actually carries the device's
        # real open/close transitions. Each widget's OWN tag_name is
        # its command address instead (see the comment above self.q1) -
        # counter_tag is how popups.py's DeviceControlPopup/
        # DevicePropertiesPopup find the right counter for a device
        # without needing to know about device_map themselves.
        for feedback_tag, widget in self.device_map.items():
            widget.counter_tag = feedback_tag
            self._refresh_device_tooltip(widget, feedback_tag)

        # Task "migracja adresacji": was literal "DI14"/"DO21" - the
        # voltage-monitoring relay pair recalculate_electricity() below
        # drives has no dedicated widget of its own to show a "not
        # configured" state on, so when unconfigured this relay's logic
        # is simply skipped entirely (no phantom writes to made-up tag
        # names, no fabricated log lines) - see recalculate_electricity()
        # itself.
        self._voltage_relay_command, _description, self._voltage_relay_feedback = \
            self._apparatus_binding(self.ROLE_VOLTAGE_RELAY)

        # Load initial values
        self.init_cabinet_tags()

        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self.recalculate_electricity)
        self.sim_timer.start(250)

    def _resolve_role(self, role):
        """Apparatus bound to `role`, or None if apparatus_registry
        itself is None or the role has no binding - see
        apparatus_registry.get_by_role()'s own docstring."""
        if self.apparatus_registry is None:
            return None
        return self.apparatus_registry.get_by_role(role)

    def _apparatus_binding(self, role):
        """(command_tag, description, feedback_tag) for `role` -
        command_tag/feedback_tag are None when unconfigured (no
        apparatus bound, or it's missing that side) - description falls
        back to a plain "not configured" label (task's own explicit
        "moduł ma to powiedzieć wprost") instead of a synthetic
        "Digital Output Channel N" the way the old literal-tag code
        did."""
        apparatus = self._resolve_role(role)
        command_tag = apparatus.command[0] if apparatus and apparatus.command else None
        feedback_tag = apparatus.feedback[0] if apparatus and apparatus.feedback else None
        if command_tag:
            description = self.tag_manager.get_output_description(command_tag, command_tag)
        else:
            description = tr("pages.entry_gate.apparatus_not_configured")
        return command_tag, description, feedback_tag

    def init_cabinet_tags(self):
        tags = [
            "Cabinet.SystemHealth", "Cabinet.TempInside", "Cabinet.TempOutside",
            "Cabinet.Humidity", "Cabinet.Door", "Cabinet.Heater", "Cabinet.Fan",
            "Cabinet.Alarm", "Cabinet.Fault", "Device.OrangePi.Status",
            "Device.ELA01.Status", "Device.ADA01.Status", "Device.Modbus.Status"
        ]
        for k in tags:
            v = self.tag_manager.get_value(k)
            if v is not None:
                self.tag_manager.update_tag(k, v)

        # The write-back above re-triggers tag_changed for anything
        # listening *right now* - but by the time this page is constructed,
        # DeviceManager's SimulatorDriver has often already flipped
        # Device.*.Status to ONLINE once already (device_manager.py emits
        # that transition exactly once, edge-triggered). If that one-shot
        # event fired before main.py finished wiring the EventBus -> Qt
        # signal bridge (which only happens *after* MainWindow, and
        # therefore this page, is fully constructed), it's gone for good -
        # the tag itself is correctly ONLINE in tag_manager, but the panel
        # never heard about it and is stuck showing its "---" placeholder
        # forever, even though System Topology's diagram is doing fine
        # (it isn't reading live tags at all here - see SESSION_REPORT.md).
        # Read the current value directly instead of hoping a re-emitted
        # event survives the timing race.
        for tag in self.device_status.labels:
            v = self.tag_manager.get_value(tag)
            if v is not None:
                self.device_status.update_label(tag, v, "GOOD")

    def handle_control_request(self, args):
        device, pos = args
        main_window = self.window()

        # Task: device control from the synoptic requires Operator or
        # above - checked here (the actual click-to-control entry point),
        # not just by disabling/greying the drawn symbol (which would
        # need paintEvent changes in synoptic_objects.py - out of scope;
        # this is the real, execution-time gate the task asks for).
        if not main_window.access_manager.has_access(AccessLevel.OPERATOR):
            main_window.deny_access(AccessLevel.OPERATOR, "Device control from synoptic (Main View)")
            return

        # Task "migracja adresacji": no apparatus bound to this symbol's
        # role - refuse plainly instead of dispatching a command against
        # the placeholder text drawn on the symbol (never a real tag).
        if not getattr(device, "is_configured", True):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, tr("pages.entry_gate.apparatus_not_configured_title"),
                                     tr("pages.entry_gate.apparatus_not_configured"))
            return

        popup = DeviceControlPopup(device, self, switching_counters=self.switching_counters,
                                    service_notes=self.service_notes)
        popup.move(pos) # Show near cursor

        if popup.exec():
            cmd_str = popup.cmd_str
            state_str = tr("pages.common.state_closed") if device.state == 1 else tr("pages.common.state_open")

            ui_logger.log("INFO", "OPERATION", device.tag_name, f"Operator requested {cmd_str}", "Operator", self.tag_manager.mode, "")

            conf = ConfirmationPopup(device.tag_name, state_str, cmd_str, tr("access.operator"), self)
            conf.move(pos)
            if conf.exec():
                # Re-checked right before actual dispatch, not just at the
                # top of this method - access could have timed out in the
                # seconds the two confirmation popups were open (same
                # pattern as Control Outputs' Force button).
                if not main_window.access_manager.has_access(AccessLevel.OPERATOR):
                    main_window.deny_access(AccessLevel.OPERATOR, "Device control from synoptic (Main View)")
                    return

                ui_logger.log("INFO", "OPERATION", device.tag_name, "Confirmation accepted", "Operator", self.tag_manager.mode, "")

                # Route to CommandManager instead of hard-coded InterlockEngine
                permitted, reasons = main_window.command_manager.request_command(device.tag_name, cmd_str)
                
                if not permitted:
                    from PySide6.QtWidgets import QMessageBox
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.setWindowTitle(tr("pages.entry_gate.command_rejected_title"))
                    msg.setText(tr("pages.entry_gate.command_rejected_text", reason=reasons[0]))
                    msg.exec()
                    return

                # Setup mapping
                di_tag = None
                for t, dev in self.device_map.items():
                    if dev == device:
                        di_tag = t
                        break

                if not di_tag:
                    ui_logger.log("FAULT", "SYSTEM", device.tag_name, "No DI mapping", "SYSTEM", self.tag_manager.mode, "")
                    return

                ui_logger.log("INFO", "OPERATION", device.tag_name, "DO Pulse Started", "SYSTEM", self.tag_manager.mode, "")

                target_state = 1 if cmd_str == "CLOSE" else 0
                

                device.command_pending = True
                device.update()

                # Bistable pulse 500ms
                QTimer.singleShot(500, lambda: self.set_feedback_waiting(device))
                # Bug 3 fix: `delay` was never defined anywhere in this
                # method - every permitted command hit a NameError right
                # here (previously masked because Bug 2's fail-safe block
                # meant `permitted` was never True in the default setup,
                # so this line was never reached). There is no per-device
                # pulse-time configuration yet, so this is a placeholder
                # constant, not a real fix of the underlying gap: pick a
                # sensible fixed delay for the simulated hardware feedback
                # to arrive after the pulse ends, loosely matching the
                # 1500ms feedback timeout used elsewhere (command_manager
                # definitions' default timeout_ms). Revisit and replace
                # with a real per-device value once device/pulse
                # configuration exists (see SESSION_REPORT.md).
                delay = 1000
                QTimer.singleShot(delay, lambda: self.simulate_hardware_feedback(di_tag, target_state, pos))
            else:
                ui_logger.log("INFO", "OPERATION", device.tag_name, "Command rejected", "Operator", self.tag_manager.mode, "")

    def set_feedback_waiting(self, device):
        device.command_pending = False
        device.feedback_waiting = True
        device.update()
        ui_logger.log("INFO", "OPERATION", device.tag_name, "DO Pulse Ended", "SYSTEM", self.tag_manager.mode, "")
        ui_logger.log("INFO", "OPERATION", device.tag_name, "Waiting for DI feedback", "SYSTEM", self.tag_manager.mode, "")

    def simulate_hardware_feedback(self, di_tag, target_state, pos):

        # We simulate 95% success rate for real feel
        if random.random() < 0.95:
            self.tag_manager.update_tag(di_tag, target_state)
        else:
            log.debug(f"Simulated communication failure on {self.device_map[di_tag].tag_name}")
            dev = self.device_map[di_tag]
            dev.feedback_waiting = False
            dev.update()
            ui_logger.log("ALARM", "PROTECTION", dev.tag_name, "Operation Failed", "SYSTEM", self.tag_manager.mode, "Timeout")
            cf = CommandFailedPopup(dev.tag_name, self)
            cf.move(pos)
            cf.exec()

    def on_tag_changed(self, tag_name, new_value, quality):
        if tag_name in self.device_map:
            device = self.device_map[tag_name]
            log.debug(f"Synoptic '{device.tag_name}' received tag update for {tag_name} = {new_value}")
            if device.state != new_value:
                device.start_transition_animation(new_value)
                device.op_counter += 1
                device.last_op_time = datetime.now().strftime("%H:%M:%S")

                device.feedback_waiting = False
                device.update()

                state_str = "CLOSED" if new_value == 1 else "OPEN"
                old_str = "OPEN" if new_value == 1 else "CLOSED"

                ui_logger.log("INFO", "OPERATION", device.tag_name, "DI Feedback received", "SYSTEM", self.tag_manager.mode, state_str)
                ui_logger.log("INFO", "OPERATION", device.tag_name, "Synoptic updated", "SYSTEM", self.tag_manager.mode, state_str)
                ui_logger.log("INFO", "OPERATION", device.tag_name, "Operation successful", "SYSTEM", self.tag_manager.mode, state_str)
                # Task: podpowiedzi - state changed, so the tooltip's own
                # state text needs refreshing along with it.
                self._refresh_device_tooltip(device, tag_name)

        elif tag_name in self.device_status.labels:
            self.device_status.update_label(tag_name, new_value, quality)

    def _refresh_device_tooltip(self, widget, di_tag):
        """Task: podpowiedzi - "symbole aparatow (nazwa, stan, powiazane
        wejscia i wyjscia)". Name/DO/DI tag are fixed at construction;
        state is dynamic - called again from on_tag_changed() above every
        time this device's feedback actually changes."""
        state_str = tr("pages.common.state_closed") if widget.state == 1 else tr("pages.common.state_open")
        widget.setToolTip(tr(
            "pages.entry_gate.tooltip_synoptic_device",
            name=widget.description, do_tag=widget.tag_name, di_tag=di_tag, state=state_str,
        ))

    def recalculate_electricity(self):
        # Task: this whole method invents voltage/current/power readings
        # with no physical power meter behind them (see EPM-01 in System
        # Topology, which is likewise entirely fabricated) - the Boolean
        # relay logic further down (DI14/DO21) is real signal simulation,
        # kept as-is, but Meas.L1/L2/L3 and the widget quality passed to
        # MeasurementPanel are honestly SIMULATED, not "GOOD" (there was
        # never a real health check here - "GOOD" was a hardcoded lie of
        # exactly the kind this task exists to remove). The simulation
        # itself stays - GRANICE forbids removing it - only the pretense
        # that it's a real measurement is gone: DigitalIndicator.update_value()
        # now renders SIMULATED in a distinct color (see synoptic_objects.py),
        # and every Meas.L1/L2/L3 tag write below carries
        # quality=TagQuality.SIMULATED, which flows unchanged through
        # tag_changed -> Historian.record_tag_change() into TagHistory's
        # own quality column - marked and filterable, not indistinguishable
        # from a real reading.
        health_quality = "SIMULATED"

        # Supply
        supply_on = True
        self.w_supply.update_voltage(supply_on)
        self.w_supply.current_flow = 120.0

        # Q1
        q1_out = supply_on and (self.q1.state == 1)
        self.w1.update_voltage(q1_out)
        self.w1.current_flow = 120.0 if q1_out else 0.0

        # KMG
        kmg_out = q1_out and (self.kmg.state == 1)
        self.w2.update_voltage(kmg_out)
        self.w2.current_flow = 120.0 if kmg_out else 0.0
        self.busbar.update_voltage(kmg_out)
        self.w3_1.update_voltage(kmg_out)
        self.w3_1.current_flow = 40.0 if kmg_out else 0.0
        self.w3_2.update_voltage(kmg_out)
        self.w3_2.current_flow = 80.0 if kmg_out else 0.0

        # KM1
        km1_out = kmg_out and (self.km1.state == 1)
        self.w4_1.update_voltage(km1_out)
        self.w4_1.current_flow = 40.0 if km1_out else 0.0

        # KM2
        km2_out = kmg_out and (self.km2.state == 1)
        self.w4_2.update_voltage(km2_out)
        self.w4_2.current_flow = 80.0 if km2_out else 0.0

        # Update Measurements
        if q1_out:
            v_val = 230.1
            self.meas_panel.vl1.update_value(v_val, health_quality)
            self.meas_panel.vl2.update_value(229.8, health_quality)
            self.meas_panel.vl3.update_value(230.5, health_quality)
            self.meas_panel.freq.update_value(50.01, health_quality)
            
            # Positional quality (not quality=...): self.tag_manager here is
            # main.py's GUITagManagerAdapter, whose update_tag() names this
            # parameter `q`, not `quality` - passing positionally works with
            # both that adapter and the plain core TagManager.
            self.tag_manager.update_tag("Meas.L1", v_val, TagQuality.SIMULATED)
            self.tag_manager.update_tag("Meas.L2", 229.8, TagQuality.SIMULATED)
            self.tag_manager.update_tag("Meas.L3", 230.5, TagQuality.SIMULATED)

            p_val = 0
            if km1_out: p_val += 15.4
            if km2_out: p_val += 42.1

            self.meas_panel.power.update_value(p_val, health_quality)
            if p_val > 0:
                self.meas_panel.il1.update_value((p_val*1000)/(3*230), health_quality)
                self.meas_panel.pf.update_value(0.96, health_quality)
            else:
                self.meas_panel.il1.update_value(0, health_quality)
                self.meas_panel.pf.update_value(0, health_quality)
                
            # Voltage Monitoring Relay logic - task "migracja adresacji":
            # skipped entirely when unconfigured (no dedicated widget of
            # its own to show "not configured" on - see this widget's
            # own resolution comment above self.init_cabinet_tags()).
            if self._voltage_relay_feedback and self._voltage_relay_command \
                    and self.tag_manager.get_value(self._voltage_relay_feedback) != 1:
                self.tag_manager.update_tag(self._voltage_relay_feedback, 1)
                self.tag_manager.update_tag(self._voltage_relay_command, 1)
                ui_logger.log("INFO", "OPERATION", "KVG1", "Bus voltage detected", "SYSTEM", self.tag_manager.mode, "")
        else:
            self.meas_panel.vl1.update_value(0, health_quality)
            self.meas_panel.vl2.update_value(0, health_quality)
            self.meas_panel.vl3.update_value(0, health_quality)
            self.meas_panel.freq.update_value(0, health_quality)
            self.meas_panel.power.update_value(0, health_quality)
            self.meas_panel.il1.update_value(0, health_quality)
            self.meas_panel.pf.update_value(0, health_quality)
            
            self.tag_manager.update_tag("Meas.L1", 0.0, TagQuality.SIMULATED)
            self.tag_manager.update_tag("Meas.L2", 0.0, TagQuality.SIMULATED)
            self.tag_manager.update_tag("Meas.L3", 0.0, TagQuality.SIMULATED)
            
            # Voltage Monitoring Relay logic - see the identical comment
            # above (bus-energized branch) for why this is skipped
            # entirely when unconfigured.
            if self._voltage_relay_feedback and self._voltage_relay_command \
                    and self.tag_manager.get_value(self._voltage_relay_feedback) != 0:
                self.tag_manager.update_tag(self._voltage_relay_feedback, 0)
                self.tag_manager.update_tag(self._voltage_relay_command, 0)
                ui_logger.log("WARNING", "OPERATION", "KVG1", "Bus voltage lost", "SYSTEM", self.tag_manager.mode, "")
