"""Task "migracja adresacji", etap 4: the platform-wide proof.

See runtime/epw_os/tests/test_addressing_grammar_cross_platform.py's own
docstring for the full explanation. Studio (project_panels.py's
`_card_channel_addresses`) imports shared/addressing.py directly (it is
already a regular package rooted at the repo root, unlike runtime/Logic
Studio which need the by-path shim - see shared/addressing.py's own
module docstring) - this file drives that same import against the
identical vector list runtime/Logic Studio (Python) and Synoptic
(TypeScript) are each checked against.

NOTE: no CI job currently runs studio/shell's test suite at all (a
pre-existing gap, not something this task introduced or was asked to
fix) - this file is real and passes locally, but until that gap is
closed it isn't yet part of the automated platform-wide guarantee the
other three copies of this test provide.
"""
import json
from pathlib import Path

import pytest

from shared.addressing import is_address, parse_address, InvalidAddressError

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
