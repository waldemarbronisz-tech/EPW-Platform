"""Presentation Mode (Task: "przygotowany scenariusz demonstracyjny
uruchamiany jednym poleceniem"). Headless (no PyQt import), same rule
as every other core/ module - EPWCore is "Headless by design... NO
PyQt references" (its own docstring), so this lives here as a plain
runtime state machine using threading.Timer for step scheduling (the
same primitive CommandManager's own command-timeout handling already
uses), not QTimer. main.py bridges this module's event_bus events to
Qt signals for the GUI, the same pattern every other core-to-GUI
notification in this app already uses.

HARD REQUIREMENT (GRANICE): "Prezentacja NIE MOZE dzialac przy
wylaczonym Trybie cwiczebnym." can_start()/start() both refuse unless
training_mode.active is True - nothing in this module can turn Training
Mode on by itself; the task explicitly reserves that decision for the
GUI ("jesli nie jest wlaczony - zaproponuj wlaczenie, NIE wlaczaj po
cichu" - see presentation_dialog.py).

Scenario steps run through the exact same paths a human operator would
use, never a shortcut around them (GRANICE: "scenariusz nie moze omijac
uprawnien ani blokad"):
  - "command" steps call command_manager.request_command_ex() - full,
    unmodified safety_kernel + logic_engine validation, then
    driver_manager.route_command() - the same boundary Training Mode's
    own cutoff already lives at (driver_manager.py), reused exactly
    as-is here, not reimplemented. That existing cutoff is *why* this
    feature is safe to run without touching real hardware, not
    something this module adds a second copy of.
  - "tag" steps call tag_manager.update_tag() - no different from what
    SimulatorDriver already does every second; there was never an
    access check on a raw tag write to bypass.
  - "alarm"/"alarm_clear" steps call the same public
    AlarmManager.trigger_alarm()/clear_alarm() the real device-comm-
    failure/EMERGENCY_STOP alarm sources already use.
  - "device_comm" steps (Task: 4 more scenarios, scenario 2 - utrata
    komunikacji) call BaseDriver.set_comm_suspended() - a device
    genuinely stops reporting its comm heartbeat, so SafetyKernel's
    real 3-missed-cycle detection thread fires on its own, unmodified
    (safety_kernel.py is never touched by this task).
  - "counter_threshold" steps (scenario 5 - zuzycie mechaniczne) call
    the same public SwitchingCounterManager.set_warning_threshold() the
    Digital Inputs page's own Engineer-only control already uses.
  - a scenario's own optional "command_definitions" (scenario 4 -
    aparat nie potwierdza wykonania) are merged in via
    CommandManager.load_definitions() - the exact same public loader
    epw_core.py's own default command set already goes through, under
    non-colliding demo-only keys, never overwriting a real device's
    definition.

Stopping (Task: "zatrzymanie przywraca stan sprzed uruchomienia")
restores every tag whose value actually changed during the run back to
its pre-start snapshot - see _restore_snapshot()'s docstring for why
only *changed* tags are written back (Historian/deadband hygiene, not
a correctness requirement) - EXCEPT SafetyKernel's own Safety.* fault-
latch tags, which are never reverted (see PROTECTED_TAG_PREFIXES) - and
restores every DI switching-counter record touched during the run,
including a temporarily-lowered warning_threshold (see
_restore_counters()) - and clears every alarm this scenario itself
triggered. A scenario that runs to completion goes through this exact
same restore path (_finish() calls stop()), not a special case -
"stopped by clicking Stop" and "finished on its own" leave the system
in the same place either way.
"""
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from epw_os.core.logging import log

STEP_TAG = "tag"
STEP_COMMAND = "command"
STEP_ALARM = "alarm"
STEP_ALARM_CLEAR = "alarm_clear"
# Task: cztery/piec nowych scenariuszy - GRANICE: "jesli ktorys wymaga
# rozszerzenia formatu scenariusza - rozszerz format, ale nie zaszywaj
# konkretnego scenariusza w kodzie". Both new types below are generic,
# reusable capabilities any scenario file can use - nothing about
# either one names a specific scenario.
#
# "device_comm": target=device_id, action="SUSPEND"/"RESUME" - see
# BaseDriver.set_comm_suspended()'s docstring (scenario 2, communication
# loss).
STEP_DEVICE_COMM = "device_comm"
# "counter_threshold": target=DI tag name, value=new warning_threshold
# (or null to clear it) - see SwitchingCounterManager.set_warning_threshold()
# (scenario 5, mechanical wear - a short demo can't wait for a real
# installation's real threshold, so a scenario may temporarily lower it;
# the whole counter record, threshold included, is restored on stop -
# see _restore_counters()).
STEP_COUNTER_THRESHOLD = "counter_threshold"

# Where the sample scenario (and any others an Engineer drops in) lives -
# a real, versioned repo file (Task: "scenariusz jako plik
# konfiguracyjny, nie zaszyty w kodzie"), not a machine-local config/
# path the way access.local.json/window_state.local.json are.
DEFAULT_SCENARIOS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "presentation_scenarios"
)


class PresentationModeError(Exception):
    pass


@dataclass
class PresentationStep:
    time_s: float
    type: str
    description: str = ""
    # "tag" steps
    tag: Optional[str] = None
    value: Any = None
    quality: Optional[str] = None  # defaults to SIMULATED if omitted - see _run_step()
    # "command" steps
    target: Optional[str] = None
    action: Optional[str] = None
    # "alarm" / "alarm_clear" steps
    alarm_id: Optional[str] = None
    message: str = ""
    priority: int = 2
    source_tag: str = ""
    # "device_comm" steps: target=device_id, action="SUSPEND"/"RESUME"
    # "counter_threshold" steps: target=DI tag name, value=new threshold


@dataclass
class PresentationScenario:
    name: str
    description: str = ""
    steps: List[PresentationStep] = field(default_factory=list)
    path: str = ""
    # Optional, scenario-scoped command definitions (Task: scenariusz 4 -
    # "aparat nie potwierdza wykonania") - same shape
    # CommandManager.load_definitions() already takes, merged in at
    # start() under their own non-colliding keys (a fictional target
    # name, never a real DO01-64), never overwriting a real device's
    # definition. See _register_scenario_tags()'s docstring for why any
    # output_tag/feedback_tag named here that doesn't exist yet is
    # auto-registered as a scratch tag rather than requiring a scenario
    # author to also edit epw_core.py's default tag set.
    command_definitions: dict = field(default_factory=dict)


def load_scenario(path: str) -> PresentationScenario:
    """Never lets one malformed step abort loading the whole file - a
    demo failing to run at all over one bad step in a config file would
    be worse than that one step being skipped (logged, not silent)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    steps = []
    for raw in data.get("steps", []):
        try:
            step = PresentationStep(
                time_s=float(raw["time_s"]),
                type=str(raw["type"]),
                description=str(raw.get("description", "")),
                tag=raw.get("tag"),
                value=raw.get("value"),
                quality=raw.get("quality"),
                target=raw.get("target"),
                action=raw.get("action"),
                alarm_id=raw.get("alarm_id"),
                message=str(raw.get("message", "")),
                priority=int(raw.get("priority", 2)),
                source_tag=str(raw.get("source_tag", "")),
            )
        except (KeyError, TypeError, ValueError) as e:
            log.warning(f"Presentation scenario {path}: skipping malformed step {raw!r}: {e}")
            continue
        steps.append(step)
    steps.sort(key=lambda s: s.time_s)  # always execute in time order, regardless of file order
    return PresentationScenario(
        name=data.get("name", os.path.splitext(os.path.basename(path))[0]),
        description=data.get("description", ""),
        steps=steps,
        path=path,
        command_definitions=data.get("command_definitions", {}) or {},
    )


def list_scenarios(directory: str = DEFAULT_SCENARIOS_DIR) -> List[str]:
    """Absolute paths of every *.json file in `directory`, sorted. A
    missing/empty directory just means no scenarios yet, not an error."""
    if not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, name) for name in os.listdir(directory) if name.lower().endswith(".json")
    )


class PresentationMode:
    # Tags never restored on stop, even if they changed while a scenario
    # ran - namespaces owned by a REAL, independently-latched mechanism
    # this module must never silently override. Concretely:
    # "Safety." - SafetyKernel's Safety.<id>.Healthy/.Fault tags (Task:
    # scenariusz 2 - "zatrzask kasuje sie WYLACZNIE przez reczne
    # potwierdzenie", safety_kernel.py's own docstring). Scenario 2
    # deliberately lets a REAL SafetyKernel fault latch during the demo;
    # silently reverting it on Stop would fake an acknowledgement that
    # never happened, defeating the scenario's entire point and the
    # latch's own hard invariant. Nothing in this module ever writes a
    # Safety.* tag itself, so this exclusion never hides anything a
    # scenario actually authored.
    PROTECTED_TAG_PREFIXES = ("Safety.",)

    def __init__(self, event_bus, tag_manager, command_manager, alarm_manager, training_mode, audit_logger=None,
                 driver_manager=None, device_manager=None, switching_counter_manager=None):
        self.event_bus = event_bus
        self.tag_manager = tag_manager
        self.command_manager = command_manager
        self.alarm_manager = alarm_manager
        self.training_mode = training_mode
        self.audit_logger = audit_logger
        # All three optional (Task: 4/5 new scenarios) - None simply
        # means the corresponding step types (device_comm,
        # counter_threshold) and switching-counter restore become no-ops
        # instead of crashing, the same defensive stance every optional
        # collaborator in this codebase already takes (e.g. audit_logger
        # above, already optional before this task).
        self.driver_manager = driver_manager
        self.device_manager = device_manager
        self.switching_counter_manager = switching_counter_manager

        self.active = False
        self.paused = False
        self.scenario: Optional[PresentationScenario] = None
        self.step_index = 0

        self._lock = threading.RLock()
        self._timer: Optional[threading.Timer] = None
        self._remaining_s = 0.0       # time left on the current wait
        self._wait_started_at = None  # time.monotonic() when the current wait was (re)armed
        self._snapshot = {}
        self._counter_snapshot = {}   # DI tag name -> pre-start switching-counter record
        self._triggered_alarm_ids = []

    def can_start(self) -> bool:
        """Task: hard requirement - Presentation Mode simply has no
        code path that runs a scenario while Training Mode is off."""
        return self.training_mode is not None and self.training_mode.active

    def start(self, scenario: PresentationScenario, actor: str = "Engineer"):
        """Raises PresentationModeError if Training Mode isn't active -
        the GUI is expected to have already offered to enable it (Task:
        never silently) before ever calling this. A no-op (not an
        error) if a presentation is already running - start() isn't a
        restart."""
        with self._lock:
            if not self.can_start():
                raise PresentationModeError(
                    "Presentation Mode requires Training Mode to be active first."
                )
            if self.active:
                return
            # Scenario-scoped command definitions (Task: scenariusz 4) -
            # registered BEFORE the tag snapshot below, so any scratch
            # tag this creates is itself captured at its just-created
            # (unwritten) value and correctly restored on stop like any
            # other tag the scenario touches - no special-casing needed.
            if scenario.command_definitions:
                self._register_scenario_tags(scenario.command_definitions)
                self.command_manager.load_definitions(scenario.command_definitions)
            self._snapshot = {t.name: (t.value, t.quality) for t in self.tag_manager.list_tags()}
            self._counter_snapshot = self._snapshot_counters()
            self._triggered_alarm_ids = []
            self.scenario = scenario
            self.step_index = 0
            self.active = True
            self.paused = False

        log.info(f"Presentation Mode started by {actor}: {scenario.name} ({len(scenario.steps)} steps)")
        if self.audit_logger is not None:
            self.audit_logger.record(
                "PRESENTATION_START", actor,
                f"Scenario: {scenario.name} ({len(scenario.steps)} steps)", success=True,
            )
        if self.event_bus is not None:
            self.event_bus.emit("presentation_started", scenario.name)
        self._schedule_next(scenario.steps[0].time_s if scenario.steps else 0.0)

    def stop(self, actor: str = "Engineer"):
        """Task: "zatrzymanie przywraca stan sprzed uruchomienia" - see
        module docstring. Safe to call when nothing is running (no-op)."""
        with self._lock:
            if not self.active:
                return
            scenario_name = self.scenario.name if self.scenario else ""
            stopped_at = self.step_index
            total = len(self.scenario.steps) if self.scenario else 0
            self.active = False
            self.paused = False

        self._cancel_timer()
        self._restore_snapshot()
        self._restore_counters()
        self._clear_triggered_alarms()

        log.info(f"Presentation Mode stopped by {actor} (step {stopped_at}/{total})")
        if self.audit_logger is not None:
            self.audit_logger.record(
                "PRESENTATION_STOP", actor,
                f"Scenario: {scenario_name} (stopped at step {stopped_at}/{total})", success=True,
            )
        if self.event_bus is not None:
            self.event_bus.emit("presentation_stopped")

    def pause(self):
        with self._lock:
            if not self.active or self.paused:
                return
            elapsed = (time.monotonic() - self._wait_started_at) if self._wait_started_at is not None else 0.0
            self._remaining_s = max(0.0, self._remaining_s - elapsed)
            self.paused = True
        self._cancel_timer()
        if self.event_bus is not None:
            self.event_bus.emit("presentation_paused")

    def resume(self):
        with self._lock:
            if not self.active or not self.paused:
                return
            self.paused = False
            remaining = self._remaining_s
        self._schedule_next(remaining)
        if self.event_bus is not None:
            self.event_bus.emit("presentation_resumed")

    def step_forward(self):
        """Executes the current pending step immediately, regardless of
        its scheduled time - works the same whether currently running
        or paused. If it was paused, stays paused afterward (one step
        closer, still waiting for a Resume/another Step) - see
        _schedule_next()'s own pause check for how that's enforced."""
        with self._lock:
            if not self.active:
                return
        self._cancel_timer()
        self._execute_current_step()

    def _schedule_next(self, delay_s: float):
        self._cancel_timer()
        delay_s = max(0.0, delay_s)
        with self._lock:
            self._remaining_s = delay_s
            self._wait_started_at = time.monotonic()
            if self.paused:
                # Recorded for the next resume()/step_forward(), but
                # deliberately not armed as a real timer - a paused
                # presentation must not advance on its own.
                return
        timer = threading.Timer(delay_s, self._on_timer_fire)
        timer.daemon = True
        with self._lock:
            self._timer = timer
        timer.start()

    def _cancel_timer(self):
        with self._lock:
            timer, self._timer = self._timer, None
        if timer is not None:
            timer.cancel()

    def _on_timer_fire(self):
        with self._lock:
            if not self.active or self.paused:
                return
        self._execute_current_step()

    def _execute_current_step(self):
        with self._lock:
            if not self.active or self.scenario is None or self.step_index >= len(self.scenario.steps):
                return
            step = self.scenario.steps[self.step_index]
            current_index = self.step_index

        self._run_step(step)

        if self.event_bus is not None:
            self.event_bus.emit("presentation_step", current_index, len(self.scenario.steps), step.description)

        with self._lock:
            if not self.active:
                return
            self.step_index += 1
            finished = self.step_index >= len(self.scenario.steps)
            next_delay = None if finished else (self.scenario.steps[self.step_index].time_s - step.time_s)

        if finished:
            self._finish()
        else:
            self._schedule_next(next_delay)

    def _run_step(self, step: PresentationStep):
        try:
            if step.type == STEP_TAG:
                from epw_os.core.tag_manager import TagQuality
                quality = TagQuality(step.quality) if step.quality else TagQuality.SIMULATED
                self.tag_manager.update_tag(step.tag, step.value, quality)
            elif step.type == STEP_COMMAND:
                record = self.command_manager.request_command_ex(
                    step.target, step.action, user="Engineer", source="Presentation"
                )
                # GRANICE: "scenariusz nie moze omijac uprawnien ani
                # blokad" - request_command_ex() above already ran the
                # exact same safety_kernel/logic_engine validation a
                # real Force button would; a BLOCKED/FAILED result here
                # is that validation genuinely refusing the step, not a
                # bug - logged so it's visible during rehearsal, but the
                # scenario continues to its next step rather than
                # aborting the whole demo over one rejected command.
                if record.state in ("BLOCKED", "FAILED"):
                    log.warning(
                        f"Presentation Mode: command {step.target}.{step.action} was "
                        f"{record.state} ({record.reason}) - continuing to the next step"
                    )
            elif step.type == STEP_ALARM:
                self.alarm_manager.trigger_alarm(step.alarm_id, step.message, source_tag=step.source_tag, priority=step.priority)
                self._triggered_alarm_ids.append(step.alarm_id)
            elif step.type == STEP_ALARM_CLEAR:
                self.alarm_manager.clear_alarm(step.alarm_id)
            elif step.type == STEP_DEVICE_COMM:
                self._run_device_comm_step(step)
            elif step.type == STEP_COUNTER_THRESHOLD:
                if self.switching_counter_manager is not None:
                    self.switching_counter_manager.set_warning_threshold(step.target, step.value)
                else:
                    log.warning("Presentation Mode: counter_threshold step skipped - no switching_counter_manager wired")
            else:
                log.warning(f"Presentation Mode: unknown step type {step.type!r} at t={step.time_s}s, skipped")
        except Exception as e:
            # A single bad step must not kill the rest of the demo -
            # logged, scenario continues at its next step.
            log.error(f"Presentation Mode: step failed ({step.type} @ {step.time_s}s): {e}")

    def _finish(self):
        """A scenario that runs to completion on its own restores state
        exactly the same way an operator-clicked Stop does - see module
        docstring."""
        self.stop(actor="System (scenario complete)")

    def _restore_snapshot(self):
        """Only writes back tags whose value or quality actually
        differ from the pre-start snapshot - restoring all ~150
        registered tags unconditionally would fire a tag_changed event
        (and, for every BOOL/STRING tag, an unconditional Historian
        write - see historian.py's deadband) for tags the scenario
        never touched, polluting history with no-op transitions. This
        is an efficiency/hygiene choice, not a correctness one: the
        actual restore guarantee (every tag ends at its pre-start
        value) holds either way."""
        for name, (old_value, old_quality) in self._snapshot.items():
            if name.startswith(self.PROTECTED_TAG_PREFIXES):
                continue
            tag = self.tag_manager.get_tag(name)
            if tag is None:
                continue
            if tag.value == old_value and tag.quality == old_quality:
                continue
            self.tag_manager.update_tag(name, old_value, old_quality)
        self._snapshot = {}

    def _clear_triggered_alarms(self):
        for alarm_id in self._triggered_alarm_ids:
            self.alarm_manager.clear_alarm(alarm_id)
        self._triggered_alarm_ids = []

    # --- scenario 2: device_comm steps ---------------------------------

    def _run_device_comm_step(self, step: PresentationStep):
        """target=device_id, action="SUSPEND"/"RESUME" - routes to
        whichever driver device_manager says actually services this
        device (same lookup Bus Diagnostics already uses - never
        assumes SIM_DRIVER specifically), then calls the neutral
        set_comm_suspended() interface on it (see BaseDriver). Missing
        device_manager/driver_manager, an unknown device, or a driver
        that doesn't implement the interface are all logged and
        skipped - same "one bad step doesn't kill the demo" stance as
        every other step type."""
        if self.device_manager is None or self.driver_manager is None:
            log.warning("Presentation Mode: device_comm step skipped - no device_manager/driver_manager wired")
            return
        info = self.device_manager.devices.get(step.target)
        if info is None:
            log.warning(f"Presentation Mode: device_comm step skipped - unknown device {step.target!r}")
            return
        driver = self.driver_manager.get_driver(info.get("driver_id"))
        if driver is None:
            log.warning(f"Presentation Mode: device_comm step skipped - no driver for {step.target!r}")
            return
        driver.set_comm_suspended(step.target, step.action == "SUSPEND")

    # --- scenario 4: scenario-scoped command definitions ----------------

    def _register_scenario_tags(self, definitions: dict):
        """A scenario's own command_definitions (Task: scenariusz 4 -
        "aparat nie potwierdza wykonania") may reference output_tag/
        feedback_tag names that don't exist yet - a demo-only command
        needs its own output/feedback tags, distinct from any real
        device's self-referential default (output_tag == feedback_tag),
        for CommandManager's real FEEDBACK_PENDING/timeout_ms path to
        ever actually elapse instead of resolving synchronously. Rather
        than requiring a scenario author to also edit epw_core.py's
        default tag set for a tag nothing else in the app ever reads,
        auto-register anything missing as a plain BOOL scratch tag
        (SIMULATED quality, matching every other presentation-authored
        value). A tag name that already exists (a real device tag) is
        left completely alone."""
        from epw_os.core.tag_manager import TagType, TagQuality
        for definition in definitions.values():
            for tag_name in (definition.get("output_tag"), definition.get("feedback_tag")):
                if tag_name and self.tag_manager.get_tag(tag_name) is None:
                    self.tag_manager.add_tag(
                        tag_name, False, TagType.BOOL,
                        description="Presentation Mode scratch tag", source="PRESENTATION",
                        quality=TagQuality.SIMULATED,
                    )

    # --- scenario 5: switching-counter snapshot/restore -----------------

    def _snapshot_counters(self) -> dict:
        """Every currently-registered DI<n> tag's switching-counter
        record, taken at start() the same way the general tag snapshot
        is - see _restore_counters() for why this is unconditional
        rather than scoped to only the tags this scenario's own steps
        touch."""
        if self.switching_counter_manager is None:
            return {}
        snapshot = {}
        for t in self.tag_manager.list_tags():
            if t.name.startswith("DI") and t.name[2:].isdigit():
                snapshot[t.name] = self.switching_counter_manager.get_snapshot(t.name)
        return snapshot

    def _restore_counters(self):
        """Task: scenariusz 5 - "liczniki NIE MOGA byc trwale
        zafalszowane... po zatrzymaniu wartosci maja wrocic do stanu
        sprzed uruchomienia". Unconditionally overwrites every
        snapshotted DI tag's counter record (not just ones that
        differ): get_snapshot()'s own closed_seconds already accrues
        real elapsed time for a currently-closed device (see its
        docstring), so a straight equality check against the pre-start
        snapshot would almost always see a difference anyway, even with
        zero actual switching during the run - restoring unconditionally
        is simpler and exactly as correct. This runs AFTER
        _restore_snapshot() above, whose own DI/DO tag writes can
        themselves fire a spurious tag_changed the counters would
        otherwise (briefly, correctly) count - restore_record()'s
        wholesale overwrite here is what makes the final state correct
        regardless of that ordering, since it discards any such
        intermediate artifact rather than adjusting from it."""
        if self.switching_counter_manager is None:
            self._counter_snapshot = {}
            return
        for tag_name, old_record in self._counter_snapshot.items():
            self.switching_counter_manager.restore_record(tag_name, old_record)
        self._counter_snapshot = {}
