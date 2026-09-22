"""Emulated ADA01 / EPM / card diagnostics on the virtual Modbus bus
(tools/modbus_sim.py), implementing the SAME register maps the driver
reads (drivers/device_blocks.py, shared/docs/*_REGISTER_MAP.md).

The bits live from today, with no boards: an emulated ADA01 declares a
stage tripped, the driver reads the stage word, the controller exposes
PROT.UV_STAGE1.TRIP, the logic acts. A real card later is a swap at the
end of the bus - map, driver, bits and logic unchanged.

Each emulator owns one unit of a VirtualBus: it writes the input
registers the master reads, and acts on the holding-register commands
the master writes (the bus reports every write through on_write; the
dispatcher below routes it to the unit's emulator). The state - trips,
latches, blocks - is the emulator's, not the controller's: it survives a
controller restart exactly like a card's own memory would.

Everything here is a test/bench tool, never imported by the controller.
"""
import threading

from epw_os.drivers import device_blocks as B
from shared.logic.protection_stages import STAGE_IDS, STAGE_INDEX, settings_checksum


class EmulationDispatcher:
    """Routes the bus's on_write to the emulator owning the unit."""

    def __init__(self, bus):
        self.bus = bus
        self.emulators = {}
        bus.on_write = self._on_write

    def attach(self, emulator):
        self.emulators.setdefault(emulator.unit, []).append(emulator)

    def _on_write(self, unit, kind, address_1based, value):
        for emulator in self.emulators.get(int(unit), []):
            emulator.on_write(kind, address_1based - 1, value)


class _UnitEmulator:
    def __init__(self, bus, unit: int):
        self.bus = bus
        self.unit = int(unit)
        self._lock = threading.RLock()
        registers = bus.units[self.unit].input_registers
        if len(registers) < B.EMULATED_INPUT_REGISTERS:
            registers.extend([0] * (B.EMULATED_INPUT_REGISTERS - len(registers)))
        holding = bus.units[self.unit].holding
        if len(holding) < B.EMULATED_HOLDING_REGISTERS:
            holding.extend([0] * (B.EMULATED_HOLDING_REGISTERS - len(holding)))

    def _set(self, address: int, value: int):
        with self.bus._lock:
            self.bus.units[self.unit].input_registers[address] = int(value) & 0xFFFF

    def _get(self, address: int) -> int:
        return self.bus.units[self.unit].input_registers[address]

    def on_write(self, kind, address, value):
        pass


class CardDiagEmulator(_UnitEmulator):
    """Every card's DIAG block: healthy by default, SIMULATION set (it
    is an emulation and says so), firmware 1.0, 35.0 C, 24.00 V."""

    def __init__(self, bus, unit, firmware=(1, 0), temperature_c=35.0, supply_v=24.0):
        super().__init__(bus, unit)
        self.status = (B.DIAG_BIT_READY | B.DIAG_BIT_RUNNING | B.DIAG_BIT_WATCHDOG_OK | B.DIAG_BIT_POWER_OK
                       | B.DIAG_BIT_CONFIG_OK | B.DIAG_BIT_SIMULATION)
        self.errors = 0
        self.resets = 0
        self.resyncs = 0
        self._set(B.DIAG_FIRMWARE, (firmware[0] << 8) | firmware[1])
        self.set_temperature(temperature_c)
        self.set_supply(supply_v)
        self._publish()

    def _publish(self):
        self._set(B.DIAG_STATUS, self.status)
        self._set(B.DIAG_ERRORS, self.errors)

    def set_flag(self, bit: int, on: bool):
        with self._lock:
            self.status = (self.status | bit) if on else (self.status & ~bit)
            self._publish()

    def set_temperature(self, celsius: float):
        self._set(B.DIAG_TEMPERATURE, int(round(celsius * 10)))

    def set_supply(self, volts: float):
        self._set(B.DIAG_SUPPLY, int(round(volts * 100)))

    def fault(self, on: bool = True):
        self.set_flag(B.DIAG_BIT_FAULT, on)
        if on:
            self.errors += 1
            self._publish()

    def on_write(self, kind, address, value):
        if kind != "register" or address != B.DIAG_CMD:
            return
        if value == B.DIAG_CMD_RESET:
            self.resets += 1
            with self._lock:
                self.status &= ~(B.DIAG_BIT_FAULT | B.DIAG_BIT_IO_FAULT)
                self.status |= B.DIAG_BIT_READY | B.DIAG_BIT_RUNNING | B.DIAG_BIT_WATCHDOG_OK
                self.errors = 0
                self._publish()
        elif value == B.DIAG_CMD_RESYNC:
            self.resyncs += 1
            self.set_flag(B.DIAG_BIT_CONFIG_OK, True)


class Ada01Emulator(_UnitEmulator):
    """ADA01's PROT block: 22 stages, each with ENABLED/START/TRIP/
    BLOCKED/LATCHED; the summary word; firmware and settings checksum;
    RESET / RESET_LATCH / SELFTEST / BLOCK / UNBLOCK commands.

    A trip is LATCHED (a tripped stage keeps TRIP and LATCHED until
    RESET_LATCH) - the way a protection relay remembers what it did,
    which is why the information lives in the device and not in the
    controller. `settings` (Studio's stage records) decide ENABLED and
    the checksum the card reports."""

    def __init__(self, bus, unit, settings=None, firmware=(1, 0)):
        super().__init__(bus, unit)
        self.words = {sid: B.STAGE_BIT_ENABLED for sid in STAGE_IDS}
        self.failed = False
        self.test_active = False
        self.test_ok = False
        self.commands = []
        self._set(B.PROT_FIRMWARE, (firmware[0] << 8) | firmware[1])
        self._set(B.PROT_FIRMWARE_BUILD, 1)
        self.apply_settings(settings or [])
        self._publish()

    # -- state -------------------------------------------------------------------------

    def apply_settings(self, settings: list):
        """The card's own settings - ENABLED per stage and the checksum
        it reports (shared/logic/protection_stages.settings_checksum)."""
        from shared.logic.protection_stages import stage_of_setting
        with self._lock:
            enabled = {sid: True for sid in STAGE_IDS}
            for record in settings:
                sid = stage_of_setting(record.get("function_id", ""), record.get("stage_name", ""))
                if sid is not None:
                    enabled[sid] = bool(record.get("enabled", True))
            for sid, on in enabled.items():
                self._flag(sid, B.STAGE_BIT_ENABLED, on)
            checksum = settings_checksum(settings)
            self._set(B.PROT_CHECKSUM_LO, checksum & 0xFFFF)
            self._set(B.PROT_CHECKSUM_HI, 0)
            self._publish()

    def set_checksum(self, value: int):
        """A card whose settings differ from the project's (the mismatch alarm)."""
        self._set(B.PROT_CHECKSUM_LO, value & 0xFFFF)

    def _flag(self, sid, bit, on):
        self.words[sid] = (self.words[sid] | bit) if on else (self.words[sid] & ~bit)

    def _publish(self):
        any_start = any(w & B.STAGE_BIT_START for w in self.words.values())
        any_trip = any(w & B.STAGE_BIT_TRIP for w in self.words.values())
        any_latched = any(w & B.STAGE_BIT_LATCHED for w in self.words.values())
        any_blocked = any(w & B.STAGE_BIT_BLOCKED for w in self.words.values())
        status = 0
        if not self.failed:
            status |= B.PROT_BIT_READY | B.PROT_BIT_ACTIVE
        else:
            status |= B.PROT_BIT_FAIL
        status |= (B.PROT_BIT_ANY_START if any_start else 0) | (B.PROT_BIT_ANY_TRIP if any_trip else 0)
        status |= (B.PROT_BIT_ANY_LATCHED if any_latched else 0) | (B.PROT_BIT_BLOCKED if any_blocked else 0)
        status |= (B.PROT_BIT_TEST_ACTIVE if self.test_active else 0) | (B.PROT_BIT_TEST_OK if self.test_ok else 0)
        self._set(B.PROT_STATUS, status)
        for sid in STAGE_IDS:
            self._set(B.PROT_STAGE_BASE + STAGE_INDEX[sid], self.words[sid])

    def pickup(self, stage_id: str, on: bool = True):
        with self._lock:
            self._flag(stage_id, B.STAGE_BIT_START, on)
            self._publish()

    def trip(self, stage_id: str):
        """The stage operated: TRIP and LATCHED, START cleared."""
        with self._lock:
            if not (self.words[stage_id] & B.STAGE_BIT_ENABLED) or self.words[stage_id] & B.STAGE_BIT_BLOCKED:
                return False
            self._flag(stage_id, B.STAGE_BIT_START, False)
            self._flag(stage_id, B.STAGE_BIT_TRIP, True)
            self._flag(stage_id, B.STAGE_BIT_LATCHED, True)
            self._publish()
            return True

    def set_failed(self, failed: bool = True):
        with self._lock:
            self.failed = failed
            self._publish()

    def stage_word(self, stage_id: str) -> int:
        return self.words[stage_id]

    # -- commands from the master ------------------------------------------------------

    def on_write(self, kind, address, value):
        if kind != "register":
            return
        with self._lock:
            if address == B.PROT_CMD:
                self.commands.append(("CMD", value))
                if value == B.PROT_CMD_RESET:
                    for sid in STAGE_IDS:
                        self._flag(sid, B.STAGE_BIT_START, False)
                        self._flag(sid, B.STAGE_BIT_TRIP, False)
                elif value == B.PROT_CMD_RESET_LATCH:
                    for sid in STAGE_IDS:
                        self._flag(sid, B.STAGE_BIT_TRIP, False)
                        self._flag(sid, B.STAGE_BIT_LATCHED, False)
                elif value == B.PROT_CMD_SELFTEST:
                    self.test_active, self.test_ok = True, False
                    threading.Timer(0.3, self._finish_selftest).start()
            elif address == B.PROT_BLOCK_STAGE and 1 <= value <= len(STAGE_IDS):
                self.commands.append(("BLOCK", STAGE_IDS[value - 1]))
                self._flag(STAGE_IDS[value - 1], B.STAGE_BIT_BLOCKED, True)
            elif address == B.PROT_UNBLOCK_STAGE and 1 <= value <= len(STAGE_IDS):
                self.commands.append(("UNBLOCK", STAGE_IDS[value - 1]))
                self._flag(STAGE_IDS[value - 1], B.STAGE_BIT_BLOCKED, False)
            self._publish()

    def _finish_selftest(self):
        with self._lock:
            self.test_active, self.test_ok = False, not self.failed
            self._publish()


class EpmEmulator(_UnitEmulator):
    """EPM's POWER block: three phases, neutral, frequency, and the
    supply status word; MAINS_OK is every phase present."""

    def __init__(self, bus, unit, voltage=230.0, frequency=50.0):
        super().__init__(bus, unit)
        self.phases = {1: True, 2: True, 3: True}
        self.neutral_ok = True
        self.sequence_ok = True
        self.backup_available = True
        self.backup_active = False
        self.dc_bus_ok = True
        self.aux_ok = True
        self.v24_ok = True
        self.voltage = voltage
        self.frequency = frequency
        self._publish()

    def _publish(self):
        for phase, address in ((1, B.POWER_UL1), (2, B.POWER_UL2), (3, B.POWER_UL3)):
            self._set(address, int(round(self.voltage * 10)) if self.phases[phase] else 0)
        self._set(B.POWER_FREQ, int(round(self.frequency * 100)))
        self._set(B.POWER_UN, 0 if self.neutral_ok else 500)
        status = 0
        if all(self.phases.values()):
            status |= B.POWER_BIT_MAINS_OK
        status |= (B.POWER_BIT_L1_OK if self.phases[1] else 0) | (B.POWER_BIT_L2_OK if self.phases[2] else 0)
        status |= (B.POWER_BIT_L3_OK if self.phases[3] else 0)
        status |= (B.POWER_BIT_NEUTRAL_OK if self.neutral_ok else 0) | (B.POWER_BIT_PHASE_SEQUENCE_OK if self.sequence_ok else 0)
        status |= (B.POWER_BIT_BACKUP_AVAILABLE if self.backup_available else 0) | (B.POWER_BIT_BACKUP_ACTIVE if self.backup_active else 0)
        status |= (B.POWER_BIT_DC_BUS_OK if self.dc_bus_ok else 0) | (B.POWER_BIT_AUX_POWER_OK if self.aux_ok else 0)
        status |= (B.POWER_BIT_POWER_24V_OK if self.v24_ok else 0)
        self._set(B.POWER_STATUS, status)

    def set_phase(self, phase: int, ok: bool):
        with self._lock:
            self.phases[int(phase)] = bool(ok)
            self._publish()

    def mains_lost(self, backup_active: bool = True):
        with self._lock:
            self.phases = {1: False, 2: False, 3: False}
            self.backup_active = backup_active
            self._publish()

    def mains_back(self):
        with self._lock:
            self.phases = {1: True, 2: True, 3: True}
            self.backup_active = False
            self._publish()

    def set_flags(self, **flags):
        with self._lock:
            for name, value in flags.items():
                setattr(self, name, bool(value))
            self._publish()
