"""Runtime's side of projekt.epw (task "runtime czyta projekt.epw").

Two jobs, both headless (no Qt):

1. build_project_view(): turn the Project that shared/project_format.py
   read into the flat sections the rest of runtime already consumes
   through ProjectManager.config - "devices" for TagManager.configure(),
   "analog_points" for the Analog Inputs page and scaling,
   "intrusion_zones"/"intrusion_lines" for IntrusionManager,
   "process_protections", "enabled_features" (the device composition),
   the point registry (descriptions, locations, technical notes) and the
   apparatus list. Every one of those modules keeps reading the same
   section it always read; only where the section comes from changed.

2. diff_settings(): when a module writes a section back, decide what may
   reach projekt.epw. SPEC_PROJEKT_EPW.md's three layers:
     Struktura - what exists (cards, points, apparatuses, zones, lines,
                 names, bindings): Studio only.
     Nastawa   - a number in something that exists (a threshold, a delay,
                 a scaling range): Studio AND the panel, Engineer level,
                 with an audit entry.
     Obsługa   - arming, bypass, walk test: runtime only, never the
                 project (runtime_state.json).
   The *_SETTINGS tuples below are the whole list of what the panel may
   change; anything else that differs from the project is reported as a
   structural change and refused.

The comparison is always made against build_project_view() of the
project as loaded - never against the raw dataclasses - so a module
filling in its own defaults (IntrusionManager adds value windows to a
contact line, scaling fills an unset range) is not mistaken for an edit.
"""
import json
import typing
from dataclasses import asdict, dataclass
from typing import Optional

from epw_os.core import project_format as pf
from epw_os.core.addressing import InvalidAddressError, parse_address
from epw_os.core.analog_scaling import normalize_config
from epw_os.core.feature_config import TOGGLABLE_FEATURES

# ProjectManager.config keys that come from projekt.epw.
PROJECT_KEYS = (
    "format", "schema_version", "project_id", "metadata", "modules", "enabled_features",
    "devices", "point_registry", "tag_descriptions", "output_descriptions", "analog_points",
    "apparatuses", "intrusion_zones", "intrusion_lines", "intrusion_power_supervision",
    "process_protections", "electrical_protection_stages",
)

# --- what the panel may change (Nastawa) ----------------------------------
ZONE_SETTINGS = ("exit_delay_seconds", "entry_delay_seconds")
ZONE_STRUCTURE = ("name",)
LINE_SETTINGS = ("min_violation_seconds", "multiplicity_count", "multiplicity_window_seconds",
                 "lockout_after_count", "alarm_hold_seconds", "silence_threshold_seconds", "value_windows")
LINE_STRUCTURE = ("name", "zone_id", "tag", "normal_state", "line_type", "input_mode", "parametrization")
PROCESS_SETTINGS = ("upper_threshold", "lower_threshold", "hysteresis", "delay_seconds", "enabled")
PROCESS_STRUCTURE = ("name", "analog_tag")
ELECTRICAL_SETTINGS = ("enabled", "setting", "hysteresis", "delay_ms", "action")
ANALOG_SETTINGS = ("signal_type", "raw_min", "raw_max", "eng_min", "eng_max", "unit", "decimals")
ANALOG_STRUCTURE = ("description", "technical_note")
POWER_SUPERVISION_KEYS = ("mains_tag", "mains_ok_state", "battery_tag", "battery_ok_state")

# Sections where any difference at all is structure.
_WHOLLY_STRUCTURAL = ("project_id", "metadata", "modules", "enabled_features", "devices", "point_registry",
                      "tag_descriptions", "output_descriptions", "apparatuses")


def point_kind(address: str) -> Optional[str]:
    try:
        return parse_address(address)[1]
    except (InvalidAddressError, ValueError, TypeError):
        return None


def _analog_record(point) -> dict:
    configured = {name: getattr(point, name) for name in ANALOG_SETTINGS if getattr(point, name) is not None}
    return {"tag": point.address, "description": point.description,
            "technical_note": point.technical_note, **normalize_config(configured)}


def _power_supervision_view(supervision) -> dict:
    if supervision.mains_tag is None and supervision.battery_tag is None:
        return {}
    return asdict(supervision)


def build_project_view(project) -> dict:
    cards = {card.id: card for card in project.cards}
    registry = []
    for point in project.points:
        kind = point_kind(point.address)
        card = cards.get(point.address.split(".", 1)[0])
        registry.append({
            "address": point.address,
            "kind": kind,
            "description": point.description,
            "location": pf.effective_location(point, card),
            "technical_note": point.technical_note,
        })
    return {
        "format": pf.FORMAT_MARKER,
        "schema_version": pf.SCHEMA_VERSION,
        "project_id": project.metadata.name,
        "metadata": {
            "name": project.metadata.name,
            "description": project.metadata.description,
            "author": project.metadata.author,
            "created": project.metadata.created_at,
            "modified": project.metadata.modified_at,
        },
        "modules": list(project.modules),
        "enabled_features": {feature: feature in project.modules for feature in TOGGLABLE_FEATURES},
        # A Card can now have more than one channel kind (task follow-up,
        # user report: "karta ELA1 ma DI oraz AI") - TagManager.configure()
        # (the sole consumer of this list) still expects the flat, one-
        # kind-per-entry shape it always has, so one Card flattens to one
        # entry per kind here rather than TagManager needing to change.
        "devices": [
            {"id": c.id, "kind": kind, "model": c.model, "channels": channels}
            for c in project.cards
            for kind, channels in c.channel_kinds.items()
        ],
        "point_registry": registry,
        "tag_descriptions": {p["address"]: p["description"] for p in registry if p["description"]},
        "output_descriptions": {p["address"]: p["description"] for p in registry
                                if p["description"] and p["kind"] == "DO"},
        "analog_points": [_analog_record(p) for p in project.points if point_kind(p.address) == "AI"],
        "apparatuses": [{"id": d.id, "behavior": d.behavior, "kind": d.kind,
                         "feedback": list(d.feedback), "command": list(d.command),
                         "command_style": d.command_style, "pulse_ms": d.pulse_ms} for d in project.devices],
        "intrusion_zones": [asdict(z) for z in project.zones],
        "intrusion_lines": [asdict(l) for l in project.lines],
        "intrusion_power_supervision": _power_supervision_view(project.power_supervision),
        "process_protections": [asdict(p) for p in project.process_protections],
        "electrical_protection_stages": [asdict(s) for s in project.electrical_protection_stages],
    }


@dataclass
class SettingChange:
    section: str      # "intrusion_zones", "analog_points", ...
    record_id: str    # zone/line/protection id, point address, "function_id / stage_name"
    field: str
    old: object
    new: object

    def describe(self) -> str:
        return f"{self.section}[{self.record_id}].{self.field}: {self.old!r} -> {self.new!r}"


@dataclass
class SettingsDiff:
    changes: list
    structural: list  # human-readable names of what differs structurally


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _same(a, b) -> bool:
    numeric = (int, float)
    if isinstance(a, numeric) and isinstance(b, numeric) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(float(a) - float(b)) <= 1e-9
    return _canonical(a) == _canonical(b)


def _stage_key(record) -> str:
    return f"{record.get('function_id')} / {record.get('stage_name')}"


def _diff_records(section, current, baseline, key, settings, structure, diff, allow_new=False, skip=None):
    base_by_id = {key(r): r for r in baseline}
    current_by_id = {}
    for record in current if isinstance(current, list) else []:
        if isinstance(record, dict):
            current_by_id[key(record)] = record
    if not isinstance(current, list):
        diff.structural.append(section)
        return
    for rid in sorted(set(base_by_id) - set(current_by_id)):
        diff.structural.append(f"{section}[{rid}] removed")
    for rid, record in current_by_id.items():
        base = base_by_id.get(rid)
        if base is None:
            if not allow_new:
                diff.structural.append(f"{section}[{rid}] added")
                continue
            base = {}
        for name in structure:
            if skip and skip(record, name):
                continue
            if name in record and base and not _same(record[name], base.get(name)):
                diff.structural.append(f"{section}[{rid}].{name}")
        for name in settings:
            if skip and skip(record, name):
                continue
            if name in record and not _same(record[name], base.get(name)):
                diff.changes.append(SettingChange(section, rid, name, base.get(name), record[name]))


def _line_field_not_applicable(record, name) -> bool:
    """Value windows and the EOL/DEOL choice only mean something for a
    PARAMETRIZED line - IntrusionManager fills placeholders in for contact
    lines, which are not edits."""
    return name in ("value_windows", "parametrization") and record.get("input_mode") != pf.LineInputMode.PARAMETRIZED


def diff_settings(project, config: dict) -> SettingsDiff:
    baseline = build_project_view(project)
    diff = SettingsDiff(changes=[], structural=[])

    for key in _WHOLLY_STRUCTURAL:
        if key in config and not _same(config[key], baseline[key]):
            diff.structural.append(key)

    _diff_records("intrusion_zones", config.get("intrusion_zones", baseline["intrusion_zones"]),
                  baseline["intrusion_zones"], lambda r: r.get("id"), ZONE_SETTINGS, ZONE_STRUCTURE, diff)
    _diff_records("intrusion_lines", config.get("intrusion_lines", baseline["intrusion_lines"]),
                  baseline["intrusion_lines"], lambda r: r.get("id"), LINE_SETTINGS, LINE_STRUCTURE, diff,
                  skip=_line_field_not_applicable)
    _diff_records("process_protections", config.get("process_protections", baseline["process_protections"]),
                  baseline["process_protections"], lambda r: r.get("id"), PROCESS_SETTINGS, PROCESS_STRUCTURE, diff)
    # Electrical stages: the catalog of functions/stages is fixed by ADA01
    # itself (see project_format.py), so a value for a catalog stage the
    # project did not list yet is a setting, not a new thing.
    _diff_records("electrical_protection_stages",
                  config.get("electrical_protection_stages", baseline["electrical_protection_stages"]),
                  baseline["electrical_protection_stages"], _stage_key, ELECTRICAL_SETTINGS, (), diff,
                  allow_new=True)
    _diff_records("analog_points", config.get("analog_points", baseline["analog_points"]),
                  baseline["analog_points"], lambda r: r.get("tag"), ANALOG_SETTINGS, ANALOG_STRUCTURE, diff)

    power = config.get("intrusion_power_supervision", baseline["intrusion_power_supervision"])
    normalized = {k: power.get(k) for k in POWER_SUPERVISION_KEYS} if isinstance(power, dict) and power else {}
    if normalized and normalized["mains_tag"] is None and normalized["battery_tag"] is None:
        normalized = {}
    if not _same(normalized, baseline["intrusion_power_supervision"]):
        diff.structural.append("intrusion_power_supervision")
    return diff


def _coerce_to_field(record, name, value):
    hint = typing.get_type_hints(type(record))[name]
    targets = [a for a in typing.get_args(hint) if a is not type(None)] or [hint]
    target = targets[0]
    if value is None:
        return None
    if target is bool:
        return bool(value)
    if target is int:
        return int(value)
    if target is float:
        return float(value)
    if target is str:
        return str(value)
    if target is dict or typing.get_origin(target) is dict:
        return {k: list(v) if isinstance(v, (list, tuple)) else v for k, v in dict(value).items()}
    return value


def apply_changes(project, changes) -> None:
    """Writes each SettingChange into the Project dataclasses (the caller
    then saves the file). Only ever called with a diff that had no
    structural part."""
    zones = {z.id: z for z in project.zones}
    lines = {l.id: l for l in project.lines}
    processes = {p.id: p for p in project.process_protections}
    points = {p.address: p for p in project.points}
    stages = {f"{s.function_id} / {s.stage_name}": s for s in project.electrical_protection_stages}
    for change in changes:
        if change.section == "electrical_protection_stages" and change.record_id not in stages:
            function_id, stage_name = change.record_id.split(" / ", 1)
            stage = pf.ElectricalProtectionStage(function_id=function_id, stage_name=stage_name)
            project.electrical_protection_stages.append(stage)
            stages[change.record_id] = stage
        target = {
            "intrusion_zones": zones, "intrusion_lines": lines, "process_protections": processes,
            "analog_points": points, "electrical_protection_stages": stages,
        }[change.section][change.record_id]
        setattr(target, change.field, _coerce_to_field(target, change.field, change.new))
