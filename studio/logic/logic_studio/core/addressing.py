"""The one canonical point-address grammar for the whole EPW platform -
task "migracja adresacji: jedna gramatyka w całej platformie".

    <card>.<KIND>.<channel>

e.g. "ELA01.DI.5", "ADA01.DO.12". Three segments, dot-separated. `card`
is free-form, user-chosen text (this build's own convention happens to
be "<PREFIX><NN>", enforced by DeviceModel.is_valid_device_name() - a
LOCAL naming convention, not something this grammar itself requires).
`KIND` is exactly one of DI/DO/AI/AO. `channel` is a positive integer
with NO leading zero - a zero-padded channel number is what capped the
old flat/two-segment scheme at a fixed digit width; this grammar has no
such ceiling.

This is Logic Studio's OWN mirror of runtime's epw_os/core/addressing.py
- GRANICE forbids importing runtime/ from studio/, so the grammar is
hand-copied here, verbatim, the same "cross-referenced in each other's
docstring so a change to one prompts checking the other" convention
project_format.py's own module docstring already uses for the
electrical-protection catalog. The two are proven to agree by this
task's own cross-platform test (test_addressing_grammar_cross_platform.py)
rather than trusted to coincidentally match - change this pattern, and
update runtime's copy too, or that test fails on purpose."""
import re

ADDRESS_PATTERN = re.compile(r"^(?P<card>[^.]+)\.(?P<kind>DI|DO|AI|AO)\.(?P<channel>[1-9][0-9]*)$")

VALID_KINDS = ("DI", "DO", "AI", "AO")


def parse_address(tag_name: str):
    """(card, kind, channel:int), or None if `tag_name` doesn't match
    the grammar at all."""
    if not isinstance(tag_name, str):
        return None
    m = ADDRESS_PATTERN.match(tag_name)
    if not m:
        return None
    return m.group("card"), m.group("kind"), int(m.group("channel"))


def is_address(tag_name: str, kind: str = None) -> bool:
    """True if `tag_name` matches the grammar - `kind` (one of
    VALID_KINDS), if given, additionally requires that exact channel
    kind."""
    parsed = parse_address(tag_name)
    if parsed is None:
        return False
    return kind is None or parsed[1] == kind


def format_address(card: str, kind: str, channel: int) -> str:
    """The one place that ASSEMBLES an address string, mirroring
    parse_address()'s own grammar exactly - used by DeviceModel instead
    of an inline f-string, so the two can never independently drift
    apart."""
    if kind not in VALID_KINDS:
        raise ValueError(f"Unknown address kind {kind!r} - must be one of {VALID_KINDS}")
    if not isinstance(channel, int) or channel < 1:
        raise ValueError(f"channel must be a positive integer, got {channel!r}")
    return f"{card}.{kind}.{channel}"


# The OLD, now-unsupported shape this platform used before "migracja
# adresacji" - a single dot, kind and channel concatenated with no
# separator and a zero-padded (2-digit) channel number ("ELA01.DI01",
# never "ELA01.DI1" or "ELA01.DI.1"). Matched deliberately narrowly (an
# exact 2-digit run) so it only flags the ACTUAL old convention, never a
# coincidentally DI/DO-prefixed name from something else entirely.
# See core/project.py's own deserialize() - "existing .epwlogic files
# have stale addresses" (task's own GRANICE) must refuse to load with a
# clear message, never silently guess or drop the address.
OLD_ADDRESS_PATTERN = re.compile(r"^[^.]+\.(DI|DO)[0-9]{2,}$")


def is_old_style_address(value) -> bool:
    return isinstance(value, str) and bool(OLD_ADDRESS_PATTERN.match(value)) and not is_address(value)
