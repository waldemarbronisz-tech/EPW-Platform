"""Task "migracja adresacji", etap 4: the platform-wide proof.

runtime and Logic Studio share the exact same grammar implementation
(both epw_os/core/addressing.py and logic_studio/core/addressing.py are
thin shims loading shared/addressing.py by path - see either shim's own
module docstring) - so, on the Python side, "do they agree" is a
tautology once both files load correctly. The actual platform-wide
question is whether a THIRD implementation, in a different language,
agrees too: Synoptic Editor is TypeScript and cannot import
shared/addressing.py at all, so its own mirror
(studio/synoptic/src/project/DeviceValidation.ts's `parseChannelAddress`)
is a genuine, independently-maintained fourth copy of this grammar.

shared/addressing_grammar_vectors.json is the one fixture BOTH sides are
driven by - this file exercises it against Python's
epw_os.core.addressing (== shared/addressing.py), and
addressing-grammar-cross-platform.test.ts exercises the identical list
against parseChannelAddress. Neither file has ever seen the other's
source - agreement is proven by both indepedently matching the same
ground truth, not by one importing the other.

To see this test actually catch a divergence (not just pass because
nothing is currently broken): temporarily edit either
shared/addressing.py's channel pattern or DeviceValidation.ts's
`channelRaw` regex to accept a leading zero again (reverting the etap-3
fix) and re-run the corresponding suite - the "ELA1.DI.05" case below
fails immediately. This was done once, by hand, while writing this
test, specifically to confirm it actually would catch it, then reverted.
"""
import json
from pathlib import Path

import pytest

from epw_os.core.addressing import is_address, parse_address, InvalidAddressError

_VECTORS_PATH = Path(__file__).resolve().parents[3] / "shared" / "addressing_grammar_vectors.json"
_CASES = json.loads(_VECTORS_PATH.read_text(encoding="utf-8"))["cases"]


def _case_id(case):
    return repr(case["input"])


@pytest.mark.parametrize("case", _CASES, ids=_case_id)
def test_matches_the_shared_cross_platform_vector(case):
    address = case["input"]
    if case["valid"]:
        card, kind, channel = parse_address(address)
        assert (card, kind, channel) == (case["card"], case["kind"], case["channel"])
        assert is_address(address, kind) is True
    else:
        with pytest.raises(InvalidAddressError):
            parse_address(address)
        assert is_address(address) is False


def test_vector_file_has_both_valid_and_invalid_cases():
    """A guard against an accidentally-empty or one-sided fixture silently
    making the parametrized test above pass trivially."""
    assert any(c["valid"] for c in _CASES)
    assert any(not c["valid"] for c in _CASES)
