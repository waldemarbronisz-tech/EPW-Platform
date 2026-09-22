"""PROT.*, PWR.*, DEV.*, DIAG.* and the REQ.PROT.* / REQ.DEV.* requests -
the register's device groups, exposed by the controller from what the
DEVICES report (signal-register etap 3, owner's decisions: the
protection bits come from ADA01, the supply bits from EPM, a card's own
diagnostics from the card).

Rule Z3: the controller EXPOSES, it does not decide. Every PROT bit is
a bit of a status word ADA01 wrote (shared/docs/ADA01_REGISTER_MAP.md,
drivers/device_blocks.py); nothing here compares a measurement with a
setting. Rule Z4: a device that does not answer gives the catalogue's
safe value - and COMM.<device>.ONLINE says why.

The blocks arrive as `device_block_read` events from the Modbus driver
(one per card and block per poll); the last one per card is kept here.
The project's own protection settings (Studio's stage records, in
projekt.epw) are compared with what ADA01 reports - per stage ENABLED
and the settings checksum: ADA01 wins (it is the device that trips),
the difference is an alarm and PROT.SETTINGS_MISMATCH, never silently
one or the other.

Requests write ADA01's command registers through the driver and are
audited executed or refused; a stage that has no bus behind it (no
ADA card, card offline, write failed) refuses with the reason.
"""
import os
import shutil
import time

from epw_os.core.access_manager import AccessLevel
from epw_os.core.device_manager import DeviceStatus
from epw_os.core.logging import log
from epw_os.drivers import device_blocks as B
from shared.logic.protection_stages import (STAGE_IDS, STAGE_INDEX, SUMMARY_SIGNALS, settings_checksum,
                                            stage_of_setting, stages_of_summary)

DISK_WARNING_PCT = 90.0
DISK_FULL_PCT = 98.0
HIGH_TEMP_C = 70.0
HIGH_CPU_LOAD_PER_CORE = 0.9
SOC_THERMAL_PATHS = ("/sys/class/thermal/thermal_zone0/temp",)

_PROT_SYSTEM = ("PROT.READY", "PROT.ACTIVE", "PROT.ANY_START", "PROT.ANY_TRIP", "PROT.BLOCKED", "PROT.FAIL",
                "PROT.SETTINGS_MISMATCH", "PROT.TEST_ACTIVE", "PROT.TEST_OK") + SUMMARY_SIGNALS
_STAGE_SUFFIXES = ("ENABLED", "START", "TRIP", "BLOCKED", "LATCHED")
_PWR = {
    "PWR.MAINS_OK": B.POWER_BIT_MAINS_OK, "PWR.L1_OK": B.POWER_BIT_L1_OK, "PWR.L2_OK": B.POWER_BIT_L2_OK,
    "PWR.L3_OK": B.POWER_BIT_L3_OK, "PWR.NEUTRAL_OK": B.POWER_BIT_NEUTRAL_OK,
    "PWR.PHASE_SEQUENCE_OK": B.POWER_BIT_PHASE_SEQUENCE_OK, "PWR.POWER_24V_OK": B.POWER_BIT_POWER_24V_OK,
    "PWR.DC_BUS_OK": B.POWER_BIT_DC_BUS_OK, "PWR.AUX_POWER_OK": B.POWER_BIT_AUX_POWER_OK,
    "PWR.BACKUP_AVAILABLE": B.POWER_BIT_BACKUP_AVAILABLE, "PWR.BACKUP_ACTIVE": B.POWER_BIT_BACKUP_ACTIVE,
}
_PWR_NEGATED = {"PWR.MAINS_LOST": "PWR.MAINS_OK", "PWR.POWER_24V_FAULT": "PWR.POWER_24V_OK"}
_DEV = {
    "READY": B.DIAG_BIT_READY, "RUNNING": B.DIAG_BIT_RUNNING, "FAULT": B.DIAG_BIT_FAULT,
    "WATCHDOG_OK": B.DIAG_BIT_WATCHDOG_OK, "POWER_OK": B.DIAG_BIT_POWER_OK, "CONFIG_OK": B.DIAG_BIT_CONFIG_OK,
    "MAINTENANCE": B.DIAG_BIT_MAINTENANCE, "SIMULATION": B.DIAG_BIT_SIMULATION,
}
_DEV_SUFFIXES = tuple(_DEV) + ("WATCHDOG_FAULT",)
_DIAG = ("DIAG.ANY_FAULT", "DIAG.IO_FAULT", "DIAG.DRIVER_FAULT", "DIAG.CONFIG_FAULT", "DIAG.LOGIC_FAULT",
         "DIAG.SYNOPTIC_FAULT", "DIAG.DATABASE_FAULT", "DIAG.HISTORIAN_FAULT", "DIAG.API_FAULT", "DIAG.TIME_FAULT",
         "DIAG.WATCHDOG_FAULT", "DIAG.DISK_WARNING", "DIAG.DISK_FULL", "DIAG.HIGH_CPU", "DIAG.HIGH_TEMP")
_DEV_REQUESTS = ("RESET", "RECONNECT", "RESYNC")

# Rule Z4 - what a bit reads when its device does not answer. Everything
# else reads False (the catalogue's default safe value).
SAFE_TRUE = frozenset({"PROT.FAIL", "PWR.MAINS_LOST", "PWR.POWER_24V_FAULT"})
SAFE_TRUE_DEV_SUFFIXES = frozenset({"FAULT", "WATCHDOG_FAULT"})


def _split(signal_id: str):
    return signal_id.split(".")


class DeviceSignals:
    def __init__(self, core):
        self.core = core
        self.blocks = {}                 # card_id -> {block: (values, time)}
        self._mismatch_alarms = set()
        self._warned_stages = set()
        bus = getattr(core, "event_bus", None) if core is not None else None
        if bus is not None:
            bus.subscribe("device_block_read", self._on_block)

    # --- what the driver delivered ---------------------------------------------------------

    def _on_block(self, card_id, block, values):
        self.blocks.setdefault(card_id, {})[block] = (list(values), time.time())
        if block == "PROT":
            self._check_settings(card_id, values)

    def _get(self, name, default=None):
        return getattr(self.core, name, default) if self.core is not None else default

    def _cards(self) -> dict:
        """{card_id: model} for the project's cards."""
        pm = self._get("project_manager")
        config = getattr(pm, "config", None)
        if not isinstance(config, dict):
            return {}
        cards = {}
        for dev in config.get("devices", []):
            if dev.get("id"):
                cards.setdefault(dev["id"], dev.get("model") or "")
        return cards

    def _cards_with(self, block: str) -> list:
        return [card for card, model in self._cards().items() if block in B.blocks_for_model(model)]

    def _online(self, card_id: str) -> bool:
        manager = self._get("device_manager")
        info = getattr(manager, "devices", {}).get(card_id) if manager is not None else None
        return bool(info) and info.get("status") == DeviceStatus.ONLINE

    def _block(self, card_id: str, block: str):
        """The last values of a block, or None when the card is not
        answering (rule Z4) or never delivered it."""
        if not self._online(card_id):
            return None
        entry = self.blocks.get(card_id, {}).get(block)
        return entry[0] if entry else None

    # --- PROT -------------------------------------------------------------------------------

    def _prot_words(self) -> list:
        """(card_id, status word, {stage: word}) per ADA card answering."""
        out = []
        for card in self._cards_with("PROT"):
            values = self._block(card, "PROT")
            if values is None:
                continue
            status = values[B.PROT_STATUS - B.PROT_BLOCK[0]]
            base = B.PROT_STAGE_BASE - B.PROT_BLOCK[0]
            stages = {sid: values[base + i] for sid, i in STAGE_INDEX.items() if base + i < len(values)}
            out.append((card, status, stages))
        return out

    def _prot_available(self) -> bool:
        ada = self._cards_with("PROT")
        return bool(ada) and all(self._block(card, "PROT") is not None for card in ada)

    def _read_prot(self, signal_id: str):
        parts = _split(signal_id)
        words = self._prot_words()
        available = self._prot_available()
        if len(parts) == 3 and parts[1] in STAGE_INDEX and parts[2] in _STAGE_SUFFIXES:
            if not available:
                return self._safe(signal_id)
            bit = {"ENABLED": B.STAGE_BIT_ENABLED, "START": B.STAGE_BIT_START, "TRIP": B.STAGE_BIT_TRIP,
                   "BLOCKED": B.STAGE_BIT_BLOCKED, "LATCHED": B.STAGE_BIT_LATCHED}[parts[2]]
            flags = [bool(stages.get(parts[1], 0) & bit) for _c, _s, stages in words]
            return all(flags) if parts[2] == "ENABLED" else any(flags)
        if signal_id in SUMMARY_SIGNALS:
            if not available:
                return self._safe(signal_id)
            return any(stages.get(sid, 0) & B.STAGE_BIT_TRIP for _c, _s, stages in words
                       for sid in stages_of_summary(signal_id))
        if signal_id == "PROT.SETTINGS_MISMATCH":
            return bool(self._mismatch_alarms)
        if not available:
            return self._safe(signal_id)
        statuses = [status for _c, status, _st in words]
        if signal_id == "PROT.READY":
            return all(status & B.PROT_BIT_READY for status in statuses)
        if signal_id == "PROT.FAIL":
            return any(status & B.PROT_BIT_FAIL for status in statuses)
        bit = {"PROT.ACTIVE": B.PROT_BIT_ACTIVE, "PROT.ANY_START": B.PROT_BIT_ANY_START,
               "PROT.ANY_TRIP": B.PROT_BIT_ANY_TRIP, "PROT.BLOCKED": B.PROT_BIT_BLOCKED,
               "PROT.TEST_ACTIVE": B.PROT_BIT_TEST_ACTIVE, "PROT.TEST_OK": B.PROT_BIT_TEST_OK}[signal_id]
        return any(status & bit for status in statuses)

    def _project_settings(self) -> list:
        pm = self._get("project_manager")
        getter = getattr(pm, "get_electrical_protection_stages", None)
        try:
            return list(getter()) if callable(getter) else []
        except Exception:  # noqa: BLE001
            return []

    def _check_settings(self, card_id: str, values):
        """ADA01 wins; the difference is said out loud - per stage
        ENABLED (once per stage, in the log) and the checksum (an alarm
        and PROT.SETTINGS_MISMATCH while it lasts)."""
        settings = self._project_settings()
        if not settings:
            return
        base = B.PROT_STAGE_BASE - B.PROT_BLOCK[0]
        for record in settings:
            sid = stage_of_setting(record.get("function_id", ""), record.get("stage_name", ""))
            if sid is None or base + STAGE_INDEX[sid] >= len(values):
                continue
            device_enabled = bool(values[base + STAGE_INDEX[sid]] & B.STAGE_BIT_ENABLED)
            project_enabled = bool(record.get("enabled", True))
            key = (card_id, sid)
            if device_enabled != project_enabled and key not in self._warned_stages:
                self._warned_stages.add(key)
                log.warning(f"Protection stage {sid}: the project says enabled={project_enabled}, {card_id} reports "
                            f"enabled={device_enabled} - the card decides; the project is out of date.")
            elif device_enabled == project_enabled:
                self._warned_stages.discard(key)
        expected = settings_checksum(settings)
        reported = values[B.PROT_CHECKSUM_LO - B.PROT_BLOCK[0]]
        alarm_id = f"PROT_SETTINGS_MISMATCH_{card_id}"
        alarms = self._get("alarm_manager")
        if reported != expected and card_id not in self._mismatch_alarms:
            self._mismatch_alarms.add(card_id)
            text = (f"Protection settings on {card_id} differ from the project (checksum {reported:#06x} on the card, "
                    f"{expected:#06x} in projekt.epw) - the card's settings are the ones that trip.")
            log.warning(text)
            if alarms is not None:
                alarms.trigger_alarm(alarm_id, text, source_tag="", priority=3)
        elif reported == expected and card_id in self._mismatch_alarms:
            self._mismatch_alarms.discard(card_id)
            if alarms is not None:
                alarms.clear_alarm(alarm_id)

    # --- PWR --------------------------------------------------------------------------------

    def _power_status(self):
        for card in self._cards_with("POWER"):
            values = self._block(card, "POWER")
            if values is not None:
                return values[B.POWER_STATUS - B.POWER_BLOCK[0]]
        return None

    def _read_pwr(self, signal_id: str):
        status = self._power_status()
        if status is None:
            return self._safe(signal_id)
        if signal_id in _PWR_NEGATED:
            return not bool(status & _PWR[_PWR_NEGATED[signal_id]])
        return bool(status & _PWR[signal_id])

    # --- DEV / DIAG -------------------------------------------------------------------------

    def _diag_status(self, card_id: str):
        values = self._block(card_id, "DIAG")
        return values[B.DIAG_STATUS - B.DIAG_BLOCK[0]] if values else None

    def _read_dev(self, card_id: str, suffix: str):
        status = self._diag_status(card_id)
        if status is None:
            return self._safe(f"DEV.{card_id}.{suffix}")
        if suffix == "WATCHDOG_FAULT":
            return not bool(status & B.DIAG_BIT_WATCHDOG_OK)
        return bool(status & _DEV[suffix])

    def _card_temperatures(self) -> list:
        temps = []
        for card in self._cards():
            values = self._block(card, "DIAG")
            if values:
                temps.append(B.signed16(values[B.DIAG_TEMPERATURE - B.DIAG_BLOCK[0]]) / 10.0)
        return temps

    def _soc_temperature(self):
        for path in SOC_THERMAL_PATHS:
            try:
                with open(path, "r", encoding="ascii") as f:
                    return int(f.read().strip()) / 1000.0
            except (OSError, ValueError):
                continue
        return None

    def _disk_pct(self):
        try:
            usage = shutil.disk_usage(self._get("runtime_root", os.getcwd()) or os.getcwd())
        except OSError:
            return None
        return 100.0 * usage.used / usage.total if usage.total else None

    def _cpu_load_per_core(self):
        getter = getattr(os, "getloadavg", None)
        if not callable(getter):
            return None
        try:
            return getter()[0] / max(1, os.cpu_count() or 1)
        except OSError:
            return None

    def _health(self, subsystem: str):
        manager = self._get("health_manager")
        try:
            return manager.get_health().get(subsystem) if manager is not None else None
        except Exception:  # noqa: BLE001
            return None

    def _other(self, signal_id: str) -> bool:
        """Another source's bit, read through the attached system source."""
        system = getattr(self, "system", None)
        return bool(system.read(signal_id)) if system is not None else False

    def _read_diag(self, signal_id: str):
        cards = self._cards()
        if signal_id == "DIAG.IO_FAULT":
            return any(self._read_dev(card, "FAULT") is True for card in cards) or self._other("COMM.ANY_DEVICE_FAULT")
        if signal_id == "DIAG.WATCHDOG_FAULT":
            return any(self._read_dev(card, "WATCHDOG_FAULT") is True for card in cards)
        if signal_id == "DIAG.DRIVER_FAULT":
            return self._other("COMM.BUS_FAULT") or self._health("DRIVERS") == "FAULT"
        if signal_id == "DIAG.CONFIG_FAULT":
            return self._other("SYS.CONFIG_FAULT") or any(self._read_dev(card, "CONFIG_OK") is False
                                                           and self._diag_status(card) is not None for card in cards)
        if signal_id == "DIAG.LOGIC_FAULT":
            return self._other("RT.LOGIC.FAIL") or self._other("RT.LOGIC.PROJECT_FAULT")
        if signal_id == "DIAG.SYNOPTIC_FAULT":
            return self._other("RT.SYNOPTIC.FAIL") or self._other("RT.SYNOPTIC.BINDING_FAULT")
        if signal_id == "DIAG.DATABASE_FAULT":
            return self._health("DATABASE") == "FAULT"
        if signal_id == "DIAG.HISTORIAN_FAULT":
            return self._health("HISTORIAN") in ("FAULT", "DEGRADED")
        if signal_id == "DIAG.API_FAULT":
            return self._health("API") == "FAULT" or (self._other("SYS.RUNNING") and self._health("API") != "RUNNING")
        if signal_id == "DIAG.TIME_FAULT":
            return self._other("SYS.TIME_SYNC_FAULT")
        if signal_id in ("DIAG.DISK_WARNING", "DIAG.DISK_FULL"):
            pct = self._disk_pct()
            if pct is None:
                return False
            return pct >= (DISK_FULL_PCT if signal_id == "DIAG.DISK_FULL" else DISK_WARNING_PCT)
        if signal_id == "DIAG.HIGH_CPU":
            load = self._cpu_load_per_core()
            return load is not None and load > HIGH_CPU_LOAD_PER_CORE
        if signal_id == "DIAG.HIGH_TEMP":
            soc = self._soc_temperature()
            return any(t > HIGH_TEMP_C for t in self._card_temperatures()) or (soc is not None and soc > HIGH_TEMP_C + 5)
        if signal_id == "DIAG.ANY_FAULT":
            return any(self._read_diag(other) for other in _DIAG if other != "DIAG.ANY_FAULT")
        return False

    # --- safe values (rule Z4) --------------------------------------------------------------

    @staticmethod
    def _safe(signal_id: str) -> bool:
        if signal_id in SAFE_TRUE:
            return True
        parts = _split(signal_id)
        return len(parts) == 3 and parts[0] == "DEV" and parts[2] in SAFE_TRUE_DEV_SUFFIXES

    # --- the interface ----------------------------------------------------------------------

    def attach(self, system_source):
        self.system = system_source

    def serves(self, signal_id: str) -> bool:
        parts = _split(signal_id)
        if signal_id in _PROT_SYSTEM or signal_id in _PWR or signal_id in _PWR_NEGATED or signal_id in _DIAG:
            return True
        if len(parts) == 3 and parts[0] == "PROT" and parts[1] in STAGE_INDEX and parts[2] in _STAGE_SUFFIXES:
            return True
        if len(parts) == 3 and parts[0] == "DEV" and parts[1] and parts[2] in _DEV_SUFFIXES:
            return True
        if len(parts) == 3 and parts[:2] == ["REQ", "PROT"] and parts[2] in ("RESET", "RESET_LATCH", "TEST"):
            return True
        if len(parts) == 4 and parts[:2] == ["REQ", "PROT"] and parts[2] in STAGE_INDEX and parts[3] in ("BLOCK", "UNBLOCK"):
            return True
        return len(parts) == 4 and parts[:2] == ["REQ", "DEV"] and parts[2] and parts[3] in _DEV_REQUESTS

    def read(self, signal_id: str):
        parts = _split(signal_id)
        if parts[0] == "PROT":
            return self._read_prot(signal_id)
        if parts[0] == "PWR":
            return self._read_pwr(signal_id)
        if parts[0] == "DEV" and len(parts) == 3:
            return self._read_dev(parts[1], parts[2])
        if parts[0] == "DIAG":
            return self._read_diag(signal_id)
        return None

    # --- the requests -----------------------------------------------------------------------

    def required_level(self, signal_id: str):
        parts = _split(signal_id)
        if parts[:2] == ["REQ", "PROT"]:
            return AccessLevel.ENGINEER if len(parts) == 4 else AccessLevel.OPERATOR
        if parts[:2] == ["REQ", "DEV"]:
            return AccessLevel.ENGINEER
        return None

    def _audit(self, event, actor, detail, success=True):
        audit = self._get("audit_logger")
        if audit is not None:
            audit.record(event, actor, detail, success=success)

    def _write(self, card_id: str, address: int, value: int) -> tuple:
        driver = self._get("modbus_driver")
        writer = getattr(driver, "write_device_register", None)
        if not callable(writer):
            return False, f"{card_id} is not on the Modbus bus"
        if not self._online(card_id):
            return False, f"{card_id} is not answering"
        ok = writer(card_id, address, value)
        return (True, "") if ok else (False, f"write to {card_id} register {address} failed")

    def execute(self, signal_id: str, actor: str, level: str = None) -> bool:
        parts = _split(signal_id)
        results = []
        if parts[:2] == ["REQ", "PROT"]:
            targets = self._cards_with("PROT")
            if not targets:
                self._audit("PROTECTION_REQUEST_REFUSED", actor, f"{signal_id}: no ADA card in the project", success=False)
                log.warning(f"{signal_id} from {actor} refused: no ADA card in the project.")
                return False
            for card in targets:
                if len(parts) == 3:
                    code = {"RESET": B.PROT_CMD_RESET, "RESET_LATCH": B.PROT_CMD_RESET_LATCH, "TEST": B.PROT_CMD_SELFTEST}[parts[2]]
                    results.append((card, self._write(card, B.PROT_CMD, code)))
                else:
                    register = B.PROT_BLOCK_STAGE if parts[3] == "BLOCK" else B.PROT_UNBLOCK_STAGE
                    results.append((card, self._write(card, register, STAGE_INDEX[parts[2]] + 1)))
            event = "PROTECTION_REQUEST"
        elif parts[:2] == ["REQ", "DEV"]:
            card = parts[2]
            if parts[3] == "RECONNECT":
                results.append((card, self._reconnect(card)))
            else:
                code = B.DIAG_CMD_RESET if parts[3] == "RESET" else B.DIAG_CMD_RESYNC
                results.append((card, self._write(card, B.DIAG_CMD, code)))
            event = "DEVICE_REQUEST"
        else:
            return False
        ok = all(result[0] for _card, result in results)
        detail = "; ".join(f"{card}: {'ok' if result[0] else result[1]}" for card, result in results)
        self._audit(event if ok else event + "_REFUSED", actor, f"{signal_id} -> {detail}", success=ok)
        if not ok:
            log.warning(f"{signal_id} from {actor}: {detail}")
        return ok

    def _reconnect(self, card_id: str) -> tuple:
        driver = self._get("modbus_driver")
        if driver is None or card_id not in (self._get("_modbus_card_ids") or ()):
            return False, f"{card_id} is not on the Modbus bus"
        reset = getattr(driver, "reset_comm_stats", None)
        if callable(reset):
            reset(card_id)
        reconnect = getattr(driver, "reconnect", None)
        if callable(reconnect):
            return (True, "") if reconnect() else (False, "the bus could not be reopened")
        return True, ""
