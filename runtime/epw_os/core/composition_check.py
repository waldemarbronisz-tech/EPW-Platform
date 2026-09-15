"""Device composition against what logic and screens refer to (task
"runtime czyta projekt.epw", 3.3; SPEC_PROJEKT_EPW.md, "Skład urządzenia":
"przy wczytaniu projektu sprawdzić, czy logika albo ekrany nie odwołują się
do sygnałów modułu, którego nie ma w składzie. Rozjazd = jasny komunikat
przy starcie").

WHAT THIS CHECK READS. Task "Studio osadza ekrany i logikę w
projekt.epw": the project's own embedded sections come first -

  logic_runtime  the compiled logic (EPW_RUNTIME_LOGIC) Studio embeds on
                 every save, the same document LogicEngine executes;
  screens        the EPW_SYNOPTIC document (identical to a .epwsyn file).

For a project saved before that task (no embedded sections) the check
falls back to the two files named in controller.local.json - the compiled
.epwlogic.runtime.json (`logic_project`) and a .epwsyn (`synoptic_project`).
_sources() is the one place that decides; the signal rules below stay as
they are whichever source they read.

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


def _sources(logic_file, synoptic_file, logic_data=None, screens_data=None):
    """[(kind, path-or-label, data-or-None)] - an embedded document wins
    over the file of the same kind; a kind with neither is skipped."""
    result = []
    if logic_data:
        result.append(("logic", "projekt.epw#logic_runtime", logic_data))
    elif logic_file:
        result.append(("logic", logic_file, None))
    if screens_data:
        result.append(("screen", "projekt.epw#screens", screens_data))
    elif synoptic_file:
        result.append(("screen", synoptic_file, None))
    return result


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


def find_signals_outside_composition(enabled_features: dict, logic_file=None, synoptic_file=None,
                                     logic_data=None, screens_data=None) -> list:
    issues = []
    for source_kind, path, data in _sources(logic_file, synoptic_file, logic_data, screens_data):
        if data is None:
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
