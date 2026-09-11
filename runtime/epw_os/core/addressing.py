"""The one canonical point-address grammar for the whole EPW platform -
task "migracja adresacji: jedna gramatyka w całej platformie".

    <card>.<KIND>.<channel>

e.g. "ELA1.DI.5", "ADA1.DO.12", "ELA1.AI.3", "ADA1.AO.1".

THIS MODULE IS A THIN RE-EXPORT SHIM. Etap 1/2 of this task gave this
file and Logic Studio's logic_studio/core/addressing.py each their own
hand-copied mirror of the grammar - the etap-3 follow-up named that
directly as the disease this task exists to end ("trzecia kopia w
Studio to gwarantowany rozjazd za pół roku - dokładnie tak powstały te
trzy gramatyki, które właśnie likwidujemy"). The actual regex and every
function around it now live in exactly ONE file, shared/addressing.py -
this module loads it BY PATH (not `import shared.addressing`, so
runtime never needs the repo root on sys.path, and no global import
state is mutated) and re-exports its names, so every existing
`from epw_os.core.addressing import ...` call site in this codebase
keeps working unchanged.

Studio (studio/shell/project_panels.py) imports shared/addressing.py
the same way. Synoptic Editor is TypeScript, a different language
runtime - it cannot share this file, so its own mirror
(studio/synoptic/src/project/DeviceValidation.ts's `parseChannelAddress`)
is a genuine fourth implementation, proven to agree with this one only
by test_addressing_grammar_cross_platform.py (task's own ETAP 4), which
fails the moment either side drifts.
"""
import importlib.util
from pathlib import Path

_SHARED_ADDRESSING_PATH = Path(__file__).resolve().parents[3] / "shared" / "addressing.py"
_spec = importlib.util.spec_from_file_location("_epw_shared_addressing", _SHARED_ADDRESSING_PATH)
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

ADDRESS_PATTERN = _shared.ADDRESS_PATTERN
VALID_KINDS = _shared.VALID_KINDS
InvalidAddressError = _shared.InvalidAddressError
parse_address = _shared.parse_address
try_parse_address = _shared.try_parse_address
is_address = _shared.is_address
format_address = _shared.format_address
