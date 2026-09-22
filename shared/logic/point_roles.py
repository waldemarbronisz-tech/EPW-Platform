"""Point roles - a contact on an ELA input that carries a register
signal (etap 4 of the signal register).

Part of the register's PWR, UPS and PROT groups does not arrive over
Modbus but as a dry contact wired to a digital input: the trip contact
of an external protection relay, the status contacts of a UPS, a 24 V
supervision relay, a mains-present relay. Studio's point registry gives
such a DI point a ROLE (which register signal the contact carries) and
a CONTACT type (NO/NC), and the controller exposes the bit under the
same name it would have had from an ADA01 or an EPM. The logic never
learns where it came from (4.3).

The list of roles is not invented here: it is the catalogue's own
PWR/UPS/PROT entries that a single contact can carry. Left out on
purpose: the per-stage patterns (a stage word comes from ADA01 only),
the two negations the controller derives (PWR.MAINS_LOST from
PWR.MAINS_OK, PWR.POWER_24V_FAULT from PWR.POWER_24V_OK - assign the OK
role and pick the contact type), and PROT.SETTINGS_MISMATCH (a
comparison of checksums, not a contact).

Polarity (4.2): the platform rule is that a supervision signal reads
TRUE when the state is healthy. A relay's NO contact CLOSES when its
condition holds, so with NO the bit equals the input; an NC contact
OPENS when the condition holds, so with NC the bit is the input
negated. "Mains OK" on the NC contact of a mains relay therefore reads
TRUE while the input is open - the correct sense.

Rule Z4: when the input's quality is not GOOD (the card is silent, not
yet read, forced bad) the bit takes the catalogue's safe value and
COMM.<card>.ONLINE says why.
"""
from shared.logic import system_signals

ROLE_CATEGORIES = ("PWR", "UPS", "PROT")

CONTACT_NO = "NO"
CONTACT_NC = "NC"
CONTACTS = (CONTACT_NO, CONTACT_NC)

# The bit the controller derives from another: never a role of its own.
DERIVED = {"PWR.MAINS_LOST": "PWR.MAINS_OK", "PWR.POWER_24V_FAULT": "PWR.POWER_24V_OK"}

# Not a contact: a checksum comparison the controller makes, and the
# self-test flags of ADA01's own firmware.
_NOT_A_CONTACT = frozenset({"PROT.SETTINGS_MISMATCH", "PROT.TEST_ACTIVE", "PROT.TEST_OK"})

# Which device block also serves the group, for the "two sources of
# one bit" warning (4.4): the card-model prefix of that device.
DEVICE_SOURCE = {"PWR": "EPM", "PROT": "ADA"}

# TRUE = the healthy state (rule 4.2). With more than one point on the
# same role (Studio warns about it) a healthy-type bit needs EVERY
# contact to say healthy, an event-type bit needs ANY contact to say so.
HEALTHY_TRUE = frozenset({
    "PWR.MAINS_OK", "PWR.L1_OK", "PWR.L2_OK", "PWR.L3_OK", "PWR.NEUTRAL_OK", "PWR.PHASE_SEQUENCE_OK",
    "PWR.POWER_24V_OK", "PWR.DC_BUS_OK", "PWR.AUX_POWER_OK", "PWR.BACKUP_AVAILABLE",
    "UPS.ONLINE", "UPS.MAINS_PRESENT",
    "PROT.READY", "PROT.ACTIVE",
})


def roles() -> list:
    """[{id, description, label, category}] - every catalogue signal a
    contact can carry, in catalogue order."""
    out = []
    for signal in system_signals.raw_signals():
        signal_id = signal.get("id", "")
        category = signal_id.split(".", 1)[0]
        if category not in ROLE_CATEGORIES or "<" in signal_id:
            continue
        if signal_id in DERIVED or signal_id in _NOT_A_CONTACT:
            continue
        out.append({"id": signal_id, "description": signal.get("description", ""),
                    "label": signal.get("label", ""), "category": category})
    return out


def role_ids() -> list:
    return [r["id"] for r in roles()]


def is_role(signal_id) -> bool:
    return bool(signal_id) and signal_id in set(role_ids())


def safe_value(signal_id: str) -> bool:
    """The catalogue's safe value (rule Z4) - False unless the entry says otherwise."""
    for signal in system_signals.raw_signals():
        if signal.get("id") == signal_id:
            return bool(signal.get("safe_value", False))
    return False


def bit_from_contact(contact: str, input_value) -> bool:
    """The register bit from the input's raw value and the contact type."""
    value = bool(input_value)
    return (not value) if contact == CONTACT_NC else value


def combine(signal_id: str, values: list) -> bool:
    """Several contacts on one role into one bit (see HEALTHY_TRUE)."""
    if not values:
        return safe_value(signal_id)
    return all(values) if signal_id in HEALTHY_TRUE else any(values)


def device_source_for(signal_id: str):
    """The card-model prefix of the device that also serves this signal's
    group over Modbus, or None (UPS has no device source)."""
    return DEVICE_SOURCE.get(signal_id.split(".", 1)[0])
