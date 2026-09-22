"""The electrical protection stages of ADA01 - the platform contract
behind PROT.<stage_id>.* and REQ.PROT.<stage_id>.* (signal-register etap
3, owner's format: PROT.UV_STAGE1.TRIP).

The list is FIXED: it is the stage table of ADA01's firmware
(shared/docs/ADA01_REGISTER_MAP.md, one status word per stage at
PROT_STAGE_BASE + index) and, on the other side, the catalogue of the
panel's own ProtectionManager.init_defaults() and Studio's
ELECTRICAL_PROTECTION_CATALOG - the same functions and stage names, so a
setting edited in Studio, a status word read from the card and a bit
read by the logic all speak of the same stage. Order matters: it IS the
register index.

Short codes (the owner's table to accept): 27 UV, 59 OV, 59N OVN, 47
PHSEQ (one function for phase sequence AND phase loss - the register
names PROT.PHASE_LOSS and PROT.PHASE_SEQUENCE_FAULT separately, both
come from this stage), 81U UF, 81O OF, 50 IOC, 51 TOC, 46 NEGSEQ, 49
THERMAL, 50N IEF, 51N TEF, and the three supply-loss functions the
panel has and the register does not: CTRLV, TECHV, UPSV. Function 32
(reverse power, PROT.POWER_REVERSE in the register) has no stage on
ADA01 nor in the panel - not here, not faked.

Dependency-free (no PySide6): imported by the catalogue loader
(shared/logic/system_signals.py), the controller and the device
emulation.
"""

# (stage id, ANSI/function code, function id as ProtectionManager/Studio name it,
#  stage name there, the register's summary bit(s) it feeds)
STAGES = [
    ("UV_STAGE1", "27", "27 Under Voltage", "Stage 1", ("PROT.UNDERVOLTAGE",)),
    ("UV_STAGE2", "27", "27 Under Voltage", "Stage 2", ("PROT.UNDERVOLTAGE",)),
    ("OV_STAGE1", "59", "59 Over Voltage", "Stage 1", ("PROT.OVERVOLTAGE",)),
    ("OV_STAGE2", "59", "59 Over Voltage", "Stage 2", ("PROT.OVERVOLTAGE",)),
    ("OVN_STAGE1", "59N", "59N Neutral Overvoltage", "Stage 1", ("PROT.NEUTRAL_FAULT",)),
    ("PHSEQ_STAGE1", "47", "47 Phase Sequence / Phase Loss", "Stage 1", ("PROT.PHASE_LOSS", "PROT.PHASE_SEQUENCE_FAULT")),
    ("UF_STAGE1", "81U", "81U Under Frequency", "Stage 1", ("PROT.UNDERFREQUENCY",)),
    ("UF_STAGE2", "81U", "81U Under Frequency", "Stage 2", ("PROT.UNDERFREQUENCY",)),
    ("OF_STAGE1", "81O", "81O Over Frequency", "Stage 1", ("PROT.OVERFREQUENCY",)),
    ("OF_STAGE2", "81O", "81O Over Frequency", "Stage 2", ("PROT.OVERFREQUENCY",)),
    ("IOC_STAGE1", "50", "50 Instantaneous Overcurrent", "Stage 1", ("PROT.OVERCURRENT",)),
    ("IOC_STAGE2", "50", "50 Instantaneous Overcurrent", "Stage 2", ("PROT.OVERCURRENT",)),
    ("TOC_STAGE1", "51", "51 Time Overcurrent", "Stage 1", ("PROT.OVERCURRENT",)),
    ("TOC_STAGE2", "51", "51 Time Overcurrent", "Stage 2", ("PROT.OVERCURRENT",)),
    ("NEGSEQ_STAGE1", "46", "46 Negative Sequence Current", "Stage 1", ("PROT.UNBALANCE",)),
    ("THERMAL_STAGE1", "49", "49 Thermal Overload", "Stage 1", ()),
    ("THERMAL_STAGE2", "49", "49 Thermal Overload", "Stage 2", ()),
    ("IEF_STAGE1", "50N", "50N Earth Fault Instantaneous", "Stage 1", ("PROT.EARTH_FAULT",)),
    ("TEF_STAGE1", "51N", "51N Earth Fault Time", "Stage 1", ("PROT.EARTH_FAULT",)),
    ("CTRLV_STAGE1", "-", "Control Voltage Loss", "Stage 1", ()),
    ("TECHV_STAGE1", "-", "Technical Supply Loss", "Stage 1", ()),
    ("UPSV_STAGE1", "-", "UPS Supply Loss", "Stage 1", ()),
]

STAGE_IDS = tuple(s[0] for s in STAGES)
STAGE_INDEX = {s[0]: i for i, s in enumerate(STAGES)}
SUMMARY_SIGNALS = ("PROT.UNDERVOLTAGE", "PROT.OVERVOLTAGE", "PROT.OVERCURRENT", "PROT.PHASE_LOSS",
                   "PROT.PHASE_SEQUENCE_FAULT", "PROT.UNBALANCE", "PROT.UNDERFREQUENCY", "PROT.OVERFREQUENCY",
                   "PROT.EARTH_FAULT", "PROT.NEUTRAL_FAULT")


def stage_instances() -> list:
    """The catalogue's instance list: {"id", "name"} per stage."""
    return [{"id": sid, "name": f"{function} {stage}"} for sid, _ansi, function, stage, _summary in STAGES]


def stages_of_summary(signal_id: str) -> list:
    return [sid for sid, _ansi, _f, _s, summary in STAGES if signal_id in summary]


def stage_of_setting(function_id: str, stage_name: str):
    """The stage id a Studio/panel setting record refers to, or None."""
    for sid, _ansi, function, stage, _summary in STAGES:
        if function == function_id and stage == stage_name:
            return sid
    return None


def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def settings_checksum(settings: list) -> int:
    """CRC-16 (Modbus polynomial) of the stage settings in stage order -
    what ADA01 reports in PROT_CHECKSUM and what the controller computes
    from the project, so a mismatch between them is one number to
    compare (ADA01 concept: mismatch = alarm). `settings` is a list of
    dicts with function_id/stage_name/enabled/setting/hysteresis/
    delay_ms/action (Studio's ElectricalProtectionStage); stages the
    list does not mention are taken at their defaults."""
    by_stage = {}
    for record in settings or []:
        sid = stage_of_setting(record.get("function_id", ""), record.get("stage_name", ""))
        if sid is not None:
            by_stage[sid] = record
    parts = []
    for sid in STAGE_IDS:
        record = by_stage.get(sid, {})
        parts.append("%s:%d:%.3f:%.3f:%d:%s" % (
            sid, 1 if record.get("enabled", True) else 0, float(record.get("setting", 0.0) or 0.0),
            float(record.get("hysteresis", 0.0) or 0.0), int(record.get("delay_ms", 0) or 0),
            str(record.get("action", "Trip"))))
    return _crc16(";".join(parts).encode("utf-8"))
