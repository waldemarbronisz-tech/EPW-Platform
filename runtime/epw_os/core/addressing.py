"""The one canonical point-address grammar for the whole EPW platform -
task "migracja adresacji: jedna gramatyka w całej platformie".

    <card>.<KIND>.<channel>

e.g. "ELA1.DI.5", "ADA1.DO.12", "ELA1.AI.3", "ADA1.AO.1". Three segments,
dot-separated. `card` is free-form, user-chosen text (no assumed prefix
like "ELA"/"ADA" - those are just this codebase's own example device
types, not a naming rule). `KIND` is exactly one of DI/DO/AI/AO.
`channel` is a positive integer with NO leading zero (`DI.5`, never
`DI.05`) - a zero-padded channel number is what capped the old flat
scheme at 64 slots per kind (shared/docs/ADDRESSING_INVENTORY.md §3.5);
this grammar has no such ceiling.

Before this task, three subsystems (switching_counters.py,
presentation_mode.py, intrusion_manager.py) each kept their own,
DISAGREEING opinion of "what counts as a DI tag" (measured in
ADDRESSING_INVENTORY.md §3.2c - two plain `startswith("DI")` checks that
never matched this codebase's own multi-device tag shape at all, and a
regex tuned for a two-segment `{dev}.DIvNN` shape that doesn't match
this three-segment grammar either). This module exists so there is
exactly ONE parser/validator, imported everywhere a tag name needs to be
recognized as an address - not a fourth independent opinion.

Studio (studio/shell/project_format.py's `Point.address`) and Logic
Studio (logic_studio/core/device_model.py) each keep their OWN mirror of
this exact grammar - GRANICE forbids importing runtime/ from studio/,
the same reasoning project_panels.py's own ELECTRICAL_PROTECTION_CATALOG
already documents for the electrical-protection catalog. The three
mirrors are proven to agree by test_addressing_grammar_cross_platform.py
(runtime) plus its Studio/Logic-side counterparts (task's own ETAP 4) -
change this pattern, and update those too, or the cross-platform test
fails on purpose.
"""
import re

ADDRESS_PATTERN = re.compile(r"^(?P<card>[^.]+)\.(?P<kind>DI|DO|AI|AO)\.(?P<channel>[1-9][0-9]*)$")

VALID_KINDS = ("DI", "DO", "AI", "AO")


def parse_address(tag_name: str):
    """(card, kind, channel:int), or None if `tag_name` doesn't match
    the grammar at all - most tags in this system (e.g. "System.Mode",
    "Cabinet.TempInside", "EPM01.UL1.RMS") are not channel addresses and
    correctly return None here, not a false match."""
    if not isinstance(tag_name, str):
        return None
    m = ADDRESS_PATTERN.match(tag_name)
    if not m:
        return None
    return m.group("card"), m.group("kind"), int(m.group("channel"))


def is_address(tag_name: str, kind: str = None) -> bool:
    """True if `tag_name` matches the grammar - `kind` (one of
    VALID_KINDS), if given, additionally requires that exact channel
    kind. This is the replacement for every ad-hoc `startswith("DI")`/
    bespoke regex this task's own inventory found disagreeing with each
    other."""
    parsed = parse_address(tag_name)
    if parsed is None:
        return False
    return kind is None or parsed[1] == kind


def format_address(card: str, kind: str, channel: int) -> str:
    """The one place that ASSEMBLES an address string, mirroring
    parse_address()'s own grammar exactly - used by tag_manager.configure()
    instead of an inline f-string, so the two can never independently
    drift apart."""
    if kind not in VALID_KINDS:
        raise ValueError(f"Unknown address kind {kind!r} - must be one of {VALID_KINDS}")
    if not isinstance(channel, int) or channel < 1:
        raise ValueError(f"channel must be a positive integer, got {channel!r}")
    return f"{card}.{kind}.{channel}"
