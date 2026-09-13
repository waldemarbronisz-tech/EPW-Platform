"""Device composition against what logic and screens refer to (task
"runtime czyta projekt.epw", 3.3; SPEC_PROJEKT_EPW.md, "Skład urządzenia":
"przy wczytaniu projektu sprawdzić, czy logika albo ekrany nie odwołują się
do sygnałów modułu, którego nie ma w składzie. Rozjazd = jasny komunikat
przy starcie").

WHAT THIS CHECK READS - stated plainly, because it has to move later.
projekt.epw does not carry screens or logic yet: Studio keeps them in their
own .epwlogic / .epwsyn files (separate task "Studio osadza ekrany, logikę
i settings_hash w projekt.epw", shared/docs/PROJEKT_EPW_ZADANIA.md). So the
check reads the two files runtime itself works with today, both named in
controller.local.json:

  logic_project     the compiled logic (EPW_RUNTIME_LOGIC JSON) that
                    LogicEngine.load_program() loads at every start;
  synoptic_project  a .epwsyn screen file.

When screens and logic are embedded in projekt.epw, _sources() is the one
place to change: read the project's `screens` and `logic` sections instead
of these two paths. The signal rules below stay as they are.

WHICH SIGNALS BELONG TO WHICH MODULE - only the tags a module creates
itself, so a match is certain, never a guess:

  intrusion           Security.*                  IntrusionManager
  protection_process  Process.<id>.Exceeded       ProcessProtectionManager
  analog_inputs       <card>.AI.<n> addresses     Analog Inputs tags

Modules that create no named tags (trends, power_quality, ...) cannot be
referred to by name, so they cannot mismatch. Every string anywhere in the
file is checked (values and keys), which finds a reference wherever the
format keeps it - block properties, io_labels, a screen object's tag or an
apparatus binding.

Headless, never raises: an unreadable file is not this check's to report
(LogicEngine and the .epwsyn loader already do).
"""
import json
from dataclasses import dataclass, field

from epw_os.core.addressing import is_address
from epw_os.core.feature_config import is_feature_enabled

MODULE_SIGNAL_RULES = (
    ("intrusion", lambda s: s.startswith("Security.")),
    ("protection_process", lambda s: s.startswith("Process.") and s.endswith(".Exceeded")),
    ("analog_inputs", lambda s: is_address(s, "AI")),
)


@dataclass
class CompositionIssue:
    module: str        # feature id, e.g. "intrusion"
    source_kind: str   # "logic" | "screen"
    path: str
    signals: list = field(default_factory=list)


def _sources(logic_file, synoptic_file):
    return [("logic", logic_file), ("screen", synoptic_file)]


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _collect_strings(node, out: set):
    if isinstance(node, str):
        out.add(node)
    elif isinstance(node, dict):
        for key, value in node.items():
            out.add(str(key))
            _collect_strings(value, out)
    elif isinstance(node, list):
        for value in node:
            _collect_strings(value, out)


def find_signals_outside_composition(enabled_features: dict, logic_file=None, synoptic_file=None) -> list:
    issues = []
    for source_kind, path in _sources(logic_file, synoptic_file):
        if not path:
            continue
        data = _read_json(path)
        if data is None:
            continue
        strings = set()
        _collect_strings(data, strings)
        for module, belongs_to_module in MODULE_SIGNAL_RULES:
            if is_feature_enabled(enabled_features, module):
                continue
            signals = sorted(s for s in strings if belongs_to_module(s))
            if signals:
                issues.append(CompositionIssue(module=module, source_kind=source_kind, path=str(path), signals=signals))
    return issues
