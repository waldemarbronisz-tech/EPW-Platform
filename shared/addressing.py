"""The ONE canonical point-address grammar for the whole EPW platform -
task "migracja adresacji: jedna gramatyka w całej platformie", point 2 of
the etap-3 follow-up ("JEDNA FUNKCJA WALIDUJĄCA, NIE TRZY KOPIE").

    <card>.<KIND>.<channel>

e.g. "ELA1.DI.5", "ADA1.DO.12", "ELA1.AI.3", "ADA1.AO.1". Three segments,
dot-separated. `card` is free-form, user-chosen text (no assumed prefix
like "ELA"/"ADA" - those are just this codebase's own example device
types, not a naming rule). `KIND` is exactly one of DI/DO/AI/AO.
`channel` is a positive integer with NO leading zero (`DI.5`, never
`DI.05`) - a zero-padded channel number is what capped the old flat
scheme at 64 slots per kind (shared/docs/ADDRESSING_INVENTORY.md §3.5);
this grammar has no such ceiling.

WHY THIS FILE EXISTS, AND WHERE IT LIVES
-----------------------------------------
Etap 1/2 of this task gave runtime (epw_os/core/addressing.py) and Logic
Studio (logic_studio/core/addressing.py) each their OWN hand-copied
mirror of this grammar, cross-referenced in each other's docstrings "so
a change to one prompts checking the other". The etap-3 follow-up named
this directly: two verbatim copies is EXACTLY the disease this task
exists to end - it's how the platform ended up with three disagreeing
address grammars in the first place.

Both runtime and Logic Studio are Python and both already live in this
one repository (checked out whole for CI and for the Orange Pi
deployment alike - runtime/ORANGE_PI_DEPLOYMENT.md's own install steps
`git clone` the full repo, not just runtime/), so for these two there is
no real obstacle to a genuine single source of truth: this file. Their
own `core/addressing.py` modules are now thin re-export shims that load
THIS file by path (see either shim's own comment for why by-path, not a
`shared` import) - the regex, and every function around it, is defined
here exactly once.

Studio (studio/shell/project_panels.py's `_card_channel_addresses`) is
also Python and imports this file directly, the same way.

Synoptic Editor is TypeScript, a different language runtime - this file
cannot be imported there. Its own mirror (studio/synoptic/src/project/
DeviceValidation.ts's `parseChannelAddress`) is therefore a REAL fourth
implementation, not avoidable the way the three Python copies were.
This is the case task's own etap-3 instructions anticipated ("jeśli się
nie da [...] to test porównujący implementacje i padający, gdy się
rozjadą") - test_addressing_grammar_cross_platform.py (etap 4) drives
both this module and DeviceValidation.ts's parseChannelAddress with the
same address strings and fails the moment either accepts/rejects/parses
one differently, which is the strongest guarantee two different
language runtimes can give each other.

STRICT VS. PERMISSIVE PARSING
------------------------------
`parse_address()` RAISES `InvalidAddressError` on anything that isn't a
well-formed address. This is deliberate, not an oversight: a caller
that calls parse_address() already believes its input IS an address (an
apparatus's own `feedback`/`command` field, a DeviceModel-generated
string) - silently returning a placeholder there is the exact bug class
that broke command_manager.load_definitions() for DO05-64 in this same
task (a `k.split(".")[0] + "." + k.split(".")[1]` that assumed exactly
three segments and quietly misparsed anything else, discovered only by
someone reading the flat scheme's DO05-64 by hand). A malformed address
reaching parse_address() is a real bug and must say so loudly.

For the OTHER, equally real use - sifting a MIXED list of tag names
where most entries are correctly not channel addresses at all (e.g.
"System.Mode" and "Cabinet.TempInside" living alongside "ELA1.DI.5" in
the same TagManager) - `is_address()`/`try_parse_address()` are the
right tools: "not an address" is the expected, valid answer there, not
an error.
"""
import re

# Documents the grammar's SHAPE (used by is_old_style_address() and as a
# quick reference) - parse_address() itself does NOT match against this
# directly, see its own docstring for why.
ADDRESS_PATTERN = re.compile(r"^(?P<card>[^.]+)\.(?P<kind>DI|DO|AI|AO)\.(?P<channel>[1-9][0-9]*)$")

_CHANNEL_PATTERN = re.compile(r"^[1-9][0-9]*$")

VALID_KINDS = ("DI", "DO", "AI", "AO")


class InvalidAddressError(ValueError):
    """Raised by parse_address() when a string that is asserted to BE an
    address doesn't match the grammar. See this module's own docstring
    ("STRICT VS. PERMISSIVE PARSING") for when to catch this vs. when to
    use try_parse_address()/is_address() instead."""


def parse_address(tag_name):
    """(card, kind, channel:int). Raises InvalidAddressError if
    `tag_name` is not a string or does not match `<card>.<KIND>.<channel>`.

    Use this ONLY when the caller already expects `tag_name` to be a
    valid address. To sift a mixed list where "not an address" is a
    normal, expected outcome, use try_parse_address()/is_address().

    Tolerates surrounding whitespace around the whole string and around
    each of the three dotted parts (" ELA1 . DI . 5 " parses the same as
    "ELA1.DI.5") - deliberately mirrored from Synoptic's own
    parseChannelAddress (studio/synoptic/src/project/DeviceValidation.ts),
    which trims for exactly this reason ("a stray leading/trailing space
    must not surface as unknown card"): a human typing into a text field
    is the one real path a stray space can enter through, and normalizing
    it here means every one of the platform's three consumers agrees on
    it too, per test_addressing_grammar_cross_platform.py (etap 4)."""
    if not isinstance(tag_name, str):
        raise InvalidAddressError(f"address must be a string, got {tag_name!r}")
    parts = tag_name.strip().split(".")
    if len(parts) != 3:
        raise InvalidAddressError(
            f"{tag_name!r} is not a valid point address - expected "
            f'"<card>.<KIND>.<channel>" e.g. "ELA1.DI.5" (KIND one of {VALID_KINDS})'
        )
    card, kind, channel_raw = (p.strip() for p in parts)
    if not card or kind not in VALID_KINDS or not _CHANNEL_PATTERN.match(channel_raw):
        raise InvalidAddressError(
            f"{tag_name!r} is not a valid point address - expected "
            f'"<card>.<KIND>.<channel>" e.g. "ELA1.DI.5" (KIND one of {VALID_KINDS})'
        )
    return card, kind, int(channel_raw)


def try_parse_address(tag_name):
    """(card, kind, channel:int), or None if `tag_name` isn't a string or
    doesn't match the grammar - the non-raising counterpart to
    parse_address(), for sifting a list where most tags are legitimately
    not channel addresses at all."""
    try:
        return parse_address(tag_name)
    except InvalidAddressError:
        return None


def is_address(tag_name, kind: str = None) -> bool:
    """True if `tag_name` matches the grammar - `kind` (one of
    VALID_KINDS), if given, additionally requires that exact channel
    kind. This is the replacement for every ad-hoc `startswith("DI")`/
    bespoke regex ADDRESSING_INVENTORY.md found disagreeing with each
    other."""
    parsed = try_parse_address(tag_name)
    if parsed is None:
        return False
    return kind is None or parsed[1] == kind


def format_address(card: str, kind: str, channel: int) -> str:
    """The one place that ASSEMBLES an address string, mirroring
    parse_address()'s own grammar exactly - used instead of an inline
    f-string wherever an address is generated, so generation and parsing
    can never independently drift apart."""
    if kind not in VALID_KINDS:
        raise ValueError(f"Unknown address kind {kind!r} - must be one of {VALID_KINDS}")
    if not isinstance(channel, int) or channel < 1:
        raise ValueError(f"channel must be a positive integer, got {channel!r}")
    return f"{card}.{kind}.{channel}"


# The OLD, now-unsupported shape this platform used before "migracja
# adresacji" - a single dot, kind and channel concatenated with no
# separator and a zero-padded (2-digit) channel number ("ELA01.DI01",
# never "ELA01.DI1" or "ELA01.DI.1"). Matched deliberately narrowly (an
# exact 2-digit-or-more run) so it only flags the ACTUAL old convention,
# never a coincidentally DI/DO-prefixed name from something else
# entirely. Used by loaders (e.g. Logic Studio's core/project.py
# deserialize()) to refuse a stale-format file loudly instead of
# silently converting or dropping the address.
OLD_ADDRESS_PATTERN = re.compile(r"^[^.]+\.(DI|DO)[0-9]{2,}$")


def is_old_style_address(value) -> bool:
    return isinstance(value, str) and bool(OLD_ADDRESS_PATTERN.match(value)) and not is_address(value)
