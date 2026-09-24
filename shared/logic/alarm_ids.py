"""The alarms a controller raises, by id - what ALM.<alarm_id>.* ranges
over (owner's decision 2026-09-24: "rozbij te alarmy" - one instance per
real AlarmManager alarm, not only the process protections).

The ids are the AlarmManager's own, exactly as the controller raises
them, so a logic block reading ALM.DEVICE_COMM_ELA1.ACTIVE reads the
alarm the panel shows under that id:

    DEVICE_COMM_<card>              a card's communication failure (EPWCore)
    DEVICE_HEALTH_<card>            a card unhealthy (SafetyKernel)
    PROT_SETTINGS_MISMATCH_<card>   an ADA card's settings differ from the project (DeviceSignals)
    PROCESS_<protection>            a process protection tripped (ProcessProtectionManager)
    EMERGENCY_STOP, SYSTEM_HEALTH, REMOTE_COMMAND_REFUSED, ALM_TEST   fixed platform alarms

Studio mirrors this list into the embedded Logic Studio as
`external_alarms` from the project's cards and process protections; the
controller answers any alarm id by shape, so an alarm outside this list
(raised by a future module) still reads truthfully.
"""

# (id, Polish name) - the alarms every controller has regardless of the project.
FIXED_ALARMS = (
    ("EMERGENCY_STOP", "Zatrzymanie awaryjne"),
    ("SYSTEM_HEALTH", "Stan systemu"),
    ("REMOTE_COMMAND_REFUSED", "Odrzucona komenda zdalna"),
    ("ALM_TEST", "Alarm testowy"),
)

DEVICE_COMM_PREFIX = "DEVICE_COMM_"
DEVICE_HEALTH_PREFIX = "DEVICE_HEALTH_"
PROT_SETTINGS_MISMATCH_PREFIX = "PROT_SETTINGS_MISMATCH_"
PROCESS_PREFIX = "PROCESS_"


def _field(obj, name, default=""):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def alarm_instances(cards, process_protections) -> list:
    """[{"id", "name"}] in a stable order: the fixed alarms, then per card
    (communication, health, and settings mismatch for an ADA card), then
    per process protection. `cards` / `process_protections` may be
    Studio's dataclasses or plain dicts with id / model / name."""
    out = [{"id": alarm_id, "name": name} for alarm_id, name in FIXED_ALARMS]
    seen = {entry["id"] for entry in out}

    def add(alarm_id, name):
        if alarm_id and alarm_id not in seen:
            seen.add(alarm_id)
            out.append({"id": alarm_id, "name": name})

    for card in cards or []:
        card_id = str(_field(card, "id") or "")
        if not card_id:
            continue
        add(DEVICE_COMM_PREFIX + card_id, f"Komunikacja z {card_id}")
        add(DEVICE_HEALTH_PREFIX + card_id, f"Stan karty {card_id}")
        if str(_field(card, "model") or "").upper().startswith("ADA"):
            add(PROT_SETTINGS_MISMATCH_PREFIX + card_id, f"Nastawy zabezpieczeń {card_id} różne od projektu")
    for protection in process_protections or []:
        protection_id = str(_field(protection, "id") or "")
        if protection_id:
            add(PROCESS_PREFIX + protection_id, str(_field(protection, "name") or protection_id))
    return out
