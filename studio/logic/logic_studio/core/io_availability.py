"""Whether this project actually HAS the physical I/O a block needs.

A DI block with no DI card in the project is not a syntax error - the
compiler catches it eventually ("Invalid DI Address: ''"), but only once
the engineer compiles, which can be a long time after the mistake. Until
then the block's Address dropdown is simply EMPTY, with nothing saying
why: the same blank list you get for "no cards defined" and for "cards
defined but none of this kind".

This module is the one place that knows which card kind each addressable
block type needs, and turns "there are none" into a sentence a person can
act on - naming where to add one, which differs depending on whether
Logic Studio runs inside EPW Studio (the card list is Studio's, bridged
in) or standalone (the project's own Devices/Analog points settings).

Used by the property grid (the Address editor) and by the canvas (when a
block is dropped). Both ask here rather than each deciding for itself
what counts as "missing".
"""
from logic_studio.core.device_model import DeviceModel

# type_id -> (kind, human name of what the block needs, how to get one in
# a STANDALONE project). The bridged (inside EPW Studio) hint is one
# sentence for all four - see _WHERE_IN_STUDIO below.
_REQUIREMENTS = {
    "input.di": ("DI", "a physical digital input",
                 'Add an ELA module in Settings -> Project Settings -> Devices.'),
    "output.do": ("DO", "a physical digital output",
                  'Add an ADA module in Settings -> Project Settings -> Devices.'),
    "input.ai": ("AI", "an analog input",
                 'Define one in Settings -> Project Settings -> General -> Analog points.'),
    "output.ao": ("AO", "an analog output",
                  'Define one in Settings -> Project Settings -> General -> Analog points.'),
}

_WHERE_IN_STUDIO = 'Add a card with {kind} channels in Configuration -> I/O Cards.'

_ADDRESS_GETTERS = {
    "input.di": DeviceModel.get_ela_addresses,
    "output.do": DeviceModel.get_ada_addresses,
    "input.ai": DeviceModel.get_analog_input_addresses,
    "output.ao": DeviceModel.get_analog_output_addresses,
}


def needs_physical_io(type_id: str) -> bool:
    """True for the four block types that address a real terminal."""
    return type_id in _REQUIREMENTS


def required_kind(type_id: str):
    """"DI"/"DO"/"AI"/"AO", or None for a block that addresses nothing."""
    requirement = _REQUIREMENTS.get(type_id)
    return requirement[0] if requirement else None


def available_addresses(project, type_id: str) -> list:
    """Every address this block type could be given in `project` - the
    exact list the Address dropdown offers, from the same getters the
    compiler's validator checks against."""
    getter = _ADDRESS_GETTERS.get(type_id)
    if getter is None or project is None:
        return []
    return list(getter(project))


def is_hosted_by_studio(project) -> bool:
    """True when the card list comes from EPW Studio (LogicPanel bridged
    it in) rather than from this project's own settings - which decides
    WHERE the engineer has to go to add one."""
    return getattr(project, "external_cards", None) is not None


def missing_io_message(project, type_id: str):
    """One sentence-pair explaining that `project` has nowhere to point
    this block, or None when it has at least one address to offer.

    None is also the answer for a block type that needs no address at all
    - callers can hand any type_id here without pre-filtering.
    """
    if not needs_physical_io(type_id) or project is None:
        return None
    if available_addresses(project, type_id):
        return None

    kind, needs, standalone_hint = _REQUIREMENTS[type_id]
    where = _WHERE_IN_STUDIO.format(kind=kind) if is_hosted_by_studio(project) else standalone_hint
    return (f"This block needs {needs}, but no {kind} channel is defined in this project. "
            f"{where}")


def empty_address_placeholder(type_id: str) -> str:
    """What the Address dropdown shows INSTEAD of an empty list - short
    enough for a combo box, explicit about which kind is missing."""
    kind = required_kind(type_id) or "I/O"
    return f"(no {kind} channels in this project)"
