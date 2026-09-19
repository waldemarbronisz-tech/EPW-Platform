"""Executes the user's logic on the controller.

Until this task this class only HELD the compiled document (it checked
the format marker and answered "is anything configured?"); the actual
interlock graph was never evaluated - its own comment said so: "In a
real engine, we'd evaluate the interlock graph."

It does now, and deliberately not with a second engine written here: the
scan runs on the SAME ExecutionEngine and the SAME block library Logic
Studio simulates with (shared/logic/), fed by the same compiled
EPW_RUNTIME_LOGIC document Studio embeds in projekt.epw. What the
engineer tested on the canvas is literally what the controller executes -
a controller-side reimplementation would only be a promise that the two
agree.

Three things this class owns on top of the shared engine, because they
are the controller's and not the editor's:

  * the scan thread, at the program's own cycle_time_ms;
  * the fail-safe posture: a program that was configured but cannot run
    blocks operator commands, exactly as before, and stopping the scan
    drives every output the program ever touched to its safe state
    (ExecutionEngine.stop());
  * the interlock rule that makes an output belong to the logic: a
    manual command to an output the running program drives is refused,
    so an operator and the scan can never fight over the same coil.
"""
import json
import threading
from typing import Tuple, List

from epw_os.core.logging import log
# Importing this module is also what puts the repository root on sys.path
# for `shared.logic` - see its docstring.
from epw_os.core.logic_runtime import TagIOProvider  # noqa: F401  (re-exported for callers)
from shared.logic.blocks import register_builtin_blocks
from shared.logic.engine.execution import ExecutionEngine, ExecutionState
from shared.logic.engine.time_provider import SystemTimeProvider
from shared.logic.program_loader import ProgramLoadError, load_program

# The block types whose "Address" property names a physical output this
# program drives - see driven_outputs().
_OUTPUT_TYPE_IDS = ("output.do", "output.ao")


class LogicEngine:
    def __init__(self, tag_manager):
        self.tag_manager = tag_manager
        self.is_running = False
        self._project = None
        # Bug 2 fix: set to True only when load_program() is actually
        # called - i.e. project.json's "logic_project" pointed at a file
        # at all. This is deliberately a separate flag from self._project
        # (which reflects a config that actually loaded successfully):
        # before this flag existed, "no logic project was ever
        # configured" and "a project WAS configured but failed to load"
        # were indistinguishable inside this class - self._project was
        # None either way, so validate_command() below fail-safe-blocked
        # both cases identically. Only the second one is a real fault.
        self._configured = False

        # The compiled, runnable program - None whenever the document on
        # hand could not be turned into one. self._project (the raw
        # document) and this are NOT the same thing: a document can be
        # present and unrunnable, which is precisely the fault case
        # validate_command() below must keep blocking.
        self._program = None
        self._engine = None
        self._io = None
        self._driven_outputs = frozenset()

        self._scan_thread = None
        self._stop_event = threading.Event()
        self._first_scan = True
        self.last_error = ""

    # --- configuration ------------------------------------------------------

    def is_configured(self) -> bool:
        """True once a logic program was ever handed to load_program()/
        load_program_data() (whether or not it actually loaded). Used by
        the GUI (widgets/popups.py) to show a neutral "no logic
        configured" message instead of implying an interlock graph was
        evaluated."""
        return self._configured

    def attach_io(self, io_provider):
        """The IOProvider the scan runs against - EPWCore builds it
        (epw_os/core/logic_runtime.py's TagIOProvider) once the driver
        layer exists, which is later than this object is constructed.
        Without one, a loaded program still compiles and reports, but
        start() refuses to scan: a scan with no way to read an input or
        drive an output would be a program running blind."""
        self._io = io_provider

    def load_program(self, filepath: str) -> bool:
        self._configured = True
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            log.warning(f"Logic runtime artifact {filepath} not found.")
            self.last_error = f"{filepath} not found."
            return False
        except Exception as e:
            log.error(f"Failed to load logic runtime: {e}")
            self.last_error = str(e)
            return False
        return self.load_program_data(data)

    def load_program_data(self, data) -> bool:
        """The compiled EPW_RUNTIME_LOGIC document itself - task "Studio
        osadza ekrany i logikę w projekt.epw": runtime takes the logic
        from projekt.epw's own `logic_runtime` section (Studio embeds the
        compiled program on every save), the .epwlogic.runtime.json path
        in controller.local.json stays as the fallback for an older
        project.

        Returns True only when the document actually became a RUNNABLE
        program - the checksum matched, every block type is one this
        controller's library knows, and every block's pins line up with
        it (shared/logic/program_loader.py refuses each of those). The
        raw document is kept either way, so a rejected one can still be
        inspected/reported; what it never becomes is something this
        controller pretends to execute.
        """
        self._configured = True
        # A program replaced while the scan is running would leave the
        # thread scanning the OLD one - stopped first, which also drives
        # its outputs safe rather than leaving them wherever the last
        # scan of a program that no longer exists happened to put them.
        if self.is_running:
            self.stop()
        self._program = None
        self._driven_outputs = frozenset()
        if not isinstance(data, dict) or data.get("format") != "EPW_RUNTIME_LOGIC":
            log.error("Invalid logic runtime schema")
            self.last_error = "Invalid logic runtime schema."
            self._project = None
            return False
        self._project = data

        # Idempotent, and needed before any block type can be resolved -
        # the controller has no editor startup to have done it already.
        register_builtin_blocks()
        try:
            self._program = load_program(data)
        except ProgramLoadError as e:
            log.error(f"Refusing to run the logic program: {e}")
            self.last_error = str(e)
            return False

        self._driven_outputs = self._collect_driven_outputs(self._program)
        self.last_error = ""
        log.info(f"Logic program loaded: {len(self._program.execution_order)} blocks in the scan, "
                 f"cycle time {self._program.cycle_time_ms} ms, "
                 f"{len(self._driven_outputs)} output(s) driven by logic.")
        return True

    @staticmethod
    def _collect_driven_outputs(program) -> frozenset:
        """Every physical output address the program writes. Taken from
        the blocks that are actually IN the scan (execution_order) - a
        block the compiler left out drives nothing."""
        addresses = set()
        for uuid in program.execution_order:
            block = program.get_block(uuid)
            if block is None or block.type_id not in _OUTPUT_TYPE_IDS:
                continue
            address = (block.properties.get("Address") or "").strip()
            if address:
                addresses.add(address)
        return frozenset(addresses)

    def driven_outputs(self) -> frozenset:
        """The output addresses the running program owns - see
        validate_command()."""
        return self._driven_outputs

    # --- the scan -----------------------------------------------------------

    def start(self) -> bool:
        """Starts scanning. False (and no thread) when there is nothing
        runnable or no IOProvider - never a thread that spins doing
        nothing."""
        if self.is_running:
            return True
        if self._program is None:
            return False
        if self._io is None:
            log.error("Logic scan not started: no IOProvider is attached.")
            self.last_error = "No IOProvider attached."
            return False

        self._engine = ExecutionEngine(self._program, self._io, SystemTimeProvider())
        self._engine.start()
        if self._engine.state != ExecutionState.RUNNING:
            log.error("Logic scan not started: the execution engine refused the program.")
            self.last_error = "The execution engine refused the program."
            self._engine = None
            return False

        self._first_scan = True
        self._stop_event.clear()
        self.is_running = True
        self._set_signal("ready", True)
        self._scan_thread = threading.Thread(target=self._scan_loop, daemon=True, name="EPW-LogicScan")
        self._scan_thread.start()
        log.info(f"Logic scan started ({self._program.cycle_time_ms} ms).")
        return True

    def stop(self):
        """Stops scanning and leaves the outputs safe: ExecutionEngine.
        stop() drives every output the program ever touched to its safe
        state (digital False, analog 0.0) rather than latching it at its
        last value."""
        self.is_running = False
        self._set_signal("ready", False)
        self._stop_event.set()
        thread, self._scan_thread = self._scan_thread, None
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            # Two scan periods plus a margin: long enough for a scan in
            # progress to finish, short enough that shutdown never hangs
            # on a program that misbehaves.
            thread.join(timeout=self._join_timeout_s())
        if self._engine is not None:
            self._engine.stop()

    def _join_timeout_s(self) -> float:
        cycle_ms = self._program.cycle_time_ms if self._program else 100
        return max(1.0, (float(cycle_ms) * 2.0) / 1000.0)

    def _scan_loop(self):
        interval_s = max(0.001, float(self._program.cycle_time_ms) / 1000.0)
        while True:
            self._run_one_scan()
            if self._stop_event.wait(interval_s):
                return

    def _run_one_scan(self):
        """One scan, plus the diagnostics the SYS.* signals report. A
        block that raises must never take the scan thread down with it:
        that would stop every interlock in the program silently. The
        engine is faulted instead, which stops the scan through the same
        path stop() uses - outputs fail safe - and leaves the reason
        where the health/diagnostics can see it."""
        try:
            self._set_signal("first_scan", self._first_scan)
            self._engine.step()
            self._first_scan = False
            scan_ms = self._engine.last_scan_duration_ms
            self._set_signal("scan_overrun", scan_ms > self._program.cycle_time_ms)
        except Exception as e:  # noqa: BLE001 - see the docstring above
            log.error(f"Logic scan failed, stopping the program: {e}")
            self.last_error = str(e)
            self.is_running = False
            self._stop_event.set()
            self._set_signal("ready", False)
            if self._engine is not None:
                self._engine.stop()

    def _set_signal(self, name: str, value):
        source = getattr(self._io, "system_signals", None)
        if source is not None:
            setattr(source, name, value)

    def get_status(self) -> dict:
        """What the program is doing right now, for diagnostics/the API."""
        engine = self._engine
        return {
            "configured": self._configured,
            "loaded": self._program is not None,
            "running": self.is_running,
            "block_count": len(self._program.execution_order) if self._program else 0,
            "cycle_time_ms": self._program.cycle_time_ms if self._program else 0,
            "scan_count": engine.cycle_counter if engine else 0,
            "last_scan_ms": round(engine.last_scan_duration_ms, 3) if engine else 0.0,
            "max_scan_ms": round(engine.max_scan_duration_ms, 3) if engine else 0.0,
            "driven_outputs": sorted(self._driven_outputs),
            "last_error": self.last_error,
        }

    # --- the interlock ------------------------------------------------------

    def validate_command(self, device_tag: str, command: str) -> Tuple[bool, List[str]]:
        # Bug 2 fix: distinguish "no logic project configured at all"
        # (normal, expected - project.json's logic_project is null) from
        # "a project WAS configured but never loaded successfully, or -
        # in the future - stopped responding" (a genuine fault). Only
        # the second one fail-safe-blocks. Every OTHER gate that runs
        # around this method (access level in the calling page, and
        # safety_kernel.validate_command_safety() in command_manager.py)
        # is completely independent of this check and is unchanged.
        if not self._configured:
            return True, []
        if self._program is None:
            return False, ["Logic Runtime Unavailable - Commands Blocked (Fail Safe)"]

        # An output the running program drives belongs to the program.
        # Letting a manual command through would put the operator and the
        # scan in a race the operator always loses - the next scan
        # overwrites the command a few milliseconds later, which looks
        # exactly like a command that "didn't work" and is far more
        # dangerous than a refusal that says why. Only enforced while the
        # scan is actually RUNNING: a stopped program drives nothing, and
        # manual control is then the only control there is.
        if self.is_running and device_tag in self._driven_outputs:
            return False, [f"{device_tag} is driven by the logic program - manual control is blocked"]

        return True, []
