"""Task "migracja adresacji", etap 4: the platform-wide proof.

See runtime/epw_os/tests/test_addressing_grammar_cross_platform.py's own
docstring for the full explanation of why this file exists (Logic
Studio's logic_studio.core.addressing is the SAME shared/addressing.py,
loaded by path - agreement between the two Python programs is a
tautology; the real cross-language question is Synoptic Editor's own
TypeScript mirror, checked against the identical vector list by
addressing-grammar-cross-platform.test.ts).
"""
import json
from pathlib import Path

import pytest

from logic_studio.core.addressing import is_address, parse_address, InvalidAddressError

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
    assert any(c["valid"] for c in _CASES)
    assert any(not c["valid"] for c in _CASES)
