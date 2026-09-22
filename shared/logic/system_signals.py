"""Loader for the fixed system-signal catalog (feat/internal-bits §3) —
system_signals_catalog.json. Dependency-free (no PySide6), loaded once and
cached at module import — the catalog is a static platform contract, never
edited at runtime.

feat/multi-device-followups (closes ARCHITECTURE.md §9.2): the "Komunikacja"
category's per-device diagnostics (<dev>.ONLINE/<dev>.FAULT/
<dev>.SAFE_PATH_OK) are no longer hardcoded in the JSON file for ELA01/ADA01
only — they're generated in _device_signals() below, from the SAME
project.settings["ela_devices"]/["ada_devices"] DeviceModel already reads for
everything else device-related (feat/multi-device-io), so a project defining
ELA02/ADA02 gets their diagnostics too, without a second, independently-
maintained device list. Every public function below takes an OPTIONAL
`project` for exactly this reason — omitted (or None), or a project with no
ELA/ADA devices at all, correctly generates NO per-device diagnostics (task
"jedno źródło listy kart": DeviceModel.get_ela_devices()/get_ada_devices()
return [] rather than a silent "ELA01"/"ADA01" default, so there is no
device to generate a diagnostic signal FOR).

feat/signal-register §3.3: that idea is generalised. A catalog entry may
carry `instances` naming a project collection ("zones", "lines"), and
get_categories(project) then produces one signal per member -
SEC.ZONE.PARTER.ARMED rather than the pattern SEC.ZONE.<zone_id>.ARMED.
The platform genuinely fixes that every zone HAS an ARMED, what it means
and what type it is; only how many zones exist belongs to the
installation. Every consumer already calls get_categories(project), so
the picker, the Signals panel and the validator each see the concrete
signals without a change of their own.
"""
import json
import os
import re

_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "system_signals_catalog.json")

_COMMS_CATEGORY_ID = "SYS.COMMS"

# (id suffix, description template, label, safety_relevant) — description
# templates take the device name itself (e.g. "ELA02"), never a fixed
# "ELA01" literal, so the generated text scales to however many devices a
# project defines. Text/flags below are exactly what the catalog's own
# static ELA01/ADA01 entries used to say — this is a mechanical change of
# WHERE they're produced, not a change of what they say for the default
# single-device case.
_ELA_DEVICE_SIGNAL_TEMPLATES = [
    ("ONLINE", "Module {dev} is communicating correctly", "ELA OK", False),
    ("FAULT", "Module {dev} fault", "ELA FLT", True),
]
_ADA_DEVICE_SIGNAL_TEMPLATES = [
    ("ONLINE", "Module {dev} is communicating correctly", "ADA OK", False),
    ("FAULT", "Module {dev} fault", "ADA FLT", True),
    ("SAFE_PATH_OK", "Hardware shutdown path healthy", "PATH OK", True),
]

_catalog = None


def _load():
    global _catalog
    if _catalog is None:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            _catalog = json.load(f)
    return _catalog


def get_catalog_version() -> str:
    return _load()["catalog_version"]


def _device_signals(project) -> list:
    """Per-device "Komunikacja" signals for every ELA/ADA device `project`
    defines (project=None -> no devices at all, see below)."""
    # feat/logic-execution: DeviceModel is Logic Studio's, and this module
    # is imported by EPW-OS (which has no editor on its path) every time a
    # system.signal block resolves its own type. Behavior is unchanged:
    # DeviceModel.get_ela_devices(None)/get_ada_devices(None) already
    # return [] for project=None (a project is the ONLY source of a device
    # list) - so with no project there was never anything to import it for.
    if project is None:
        return []
    try:
        from logic_studio.core.device_model import DeviceModel
    except ImportError:
        # feat/signal-register 3.3: EPW-OS has no editor on its path. It
        # never passed a project here before, so this line was never
        # reached from the controller - but the per-instance patterns
        # give the runtime a real reason to ask the catalogue about a
        # project, and an ImportError mid-scan would be a poor way to
        # find that out. The device diagnostics come from the EDITOR's
        # device list, which the controller does not have, so none is
        # exactly the right answer here rather than a failure.
        return []

    signals = []
    for dev in DeviceModel.get_ela_devices(project):
        for suffix, desc_tpl, label, safety in _ELA_DEVICE_SIGNAL_TEMPLATES:
            signals.append({
                "id": f"{dev}.{suffix}", "description": desc_tpl.format(dev=dev),
                "label": label, "type": "BOOL", "source": "runtime",
                "safety_relevant": safety, "runtime": "served",
            })
    for dev in DeviceModel.get_ada_devices(project):
        for suffix, desc_tpl, label, safety in _ADA_DEVICE_SIGNAL_TEMPLATES:
            signals.append({
                "id": f"{dev}.{suffix}", "description": desc_tpl.format(dev=dev),
                "label": label, "type": "BOOL", "source": "runtime",
                "safety_relevant": safety, "runtime": "served",
            })
    return signals


# Which project collection an `instances` pattern ranges over, and where
# to read it from. A logic project embedded in Studio has these mirrored
# onto it (studio/shell/logic_panel.py), exactly as it already has the
# card list - a standalone Logic Studio has none, and then a pattern
# simply produces nothing, which is the correct answer rather than a
# placeholder nobody can use.
_INSTANCE_ATTRIBUTES = {
    "zones": "external_zones",
    "lines": "external_lines",
    # The project's cards (Studio mirrors them as one entry per channel
    # KIND - {"id", "kind", "channels"} - so a card appears once per kind
    # there and exactly once here).
    "devices": "external_cards",
}

_PLACEHOLDER = re.compile(r"<[^>]+>")


def _instances(project, kind: str) -> list:
    attribute = _INSTANCE_ATTRIBUTES.get(kind)
    if project is None or attribute is None:
        return []
    values = getattr(project, attribute, None) or []
    seen, instances = set(), []
    for value in values:
        if isinstance(value, dict) and value.get("id") and value["id"] not in seen:
            seen.add(value["id"])
            instances.append(value)
    return instances


def _expand(signal: dict, project) -> list:
    """One catalog entry into the signals it actually stands for.

    A plain entry is itself. A pattern entry becomes one signal per
    instance, with the placeholder replaced by the instance's stable ID
    and its NAME appended to the description - the id is what the logic
    binds to and must not follow a rename, while the name is what an
    engineer recognises in the picker ("Strefa uzbrojona - Parter").
    """
    kind = signal.get("instances")
    if not kind:
        return [signal]
    expanded = []
    for instance in _instances(project, kind):
        instance_id = str(instance["id"])
        name = (instance.get("name") or "").strip()
        concrete = dict(signal)
        concrete.pop("instances", None)
        concrete["id"] = _PLACEHOLDER.sub(instance_id, signal["id"], count=1)
        concrete["instance_of"] = signal["id"]
        concrete["instance_id"] = instance_id
        if name:
            concrete["description"] = f"{signal.get('description', '')} - {name}"
        expanded.append(concrete)
    return expanded


def get_categories(project=None) -> list:
    """List of {"id", "name", "signals"} dicts, in catalog order (§3.2's
    "Stan systemu" -> "Komunikacja" -> "Poziom dostępu" -> "Generatory
    czasu" — the order the signal picker's top-level sections use). The
    "Komunikacja" category's signal list is extended with this project's own
    per-device diagnostics (_device_signals above); every other category —
    and "Komunikacja"'s own two non-device-specific signals — comes back
    exactly as the static catalog has it. Returns fresh category dicts and a
    fresh signals list each call; the static per-category signal dicts
    themselves are shared, never mutated, with the cached catalog."""
    categories = []
    for raw in _load()["categories"]:
        cat = dict(raw)
        signals = []
        for signal in cat["signals"]:
            signals.extend(_expand(signal, project))
        if cat["id"] == _COMMS_CATEGORY_ID:
            signals = signals + _device_signals(project)
        cat["signals"] = signals
        categories.append(cat)
    return categories


def raw_signals() -> list:
    """Every catalog entry AS WRITTEN, patterns unexpanded.

    get_all_signals() answers "what can this project use", which for a
    pattern with no instances is nothing at all - correct there, and
    exactly wrong for anything asking "what does the catalog cover". The
    status report compares the register against the catalog's coverage,
    and without this it reported every per-zone signal as missing on the
    very commit that added it.
    """
    return [signal for cat in _load()["categories"] for signal in cat["signals"]]


def get_all_signals(project=None) -> list:
    """Every signal across every category, flattened."""
    return [s for cat in get_categories(project) for s in cat["signals"]]


RUNTIME_SERVED = "served"
RUNTIME_PLANNED = "planned"


def runtime_status(signal_id: str, project=None) -> str:
    """Whether the controller actually answers for this signal.

    "served" - EPW-OS computes it from something real. "planned" - the
    name is agreed and the id is stable, but nothing produces a value
    yet, so logic reading it sees the safe default and nothing else,
    for ever.

    An unknown signal is reported as planned rather than served: the
    honest answer for a name this build has never heard of is "not from
    here". Per-device diagnostics generated for this project's own
    ELA/ADA modules are served - they come from the device manager that
    generated them.
    """
    entry = get_signal(signal_id, project)
    if entry is None:
        return RUNTIME_PLANNED
    return entry.get("runtime", RUNTIME_SERVED)


def get_signal(signal_id: str, project=None):
    """A single signal's catalog entry (id/description/label/type/source/
    safety_relevant), or None if signal_id isn't in the catalog (this
    project's own ELA/ADA device list included) — the "spoza katalogu" case
    §3.4's migration and validator §4 both need to detect."""
    for signal in get_all_signals(project):
        if signal["id"] == signal_id:
            return signal
    return None
