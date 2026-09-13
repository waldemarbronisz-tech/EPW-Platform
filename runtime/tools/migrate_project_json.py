"""One-off import of the old runtime/project.json (task "runtime czyta
projekt.epw", 5.1). After it, runtime reads projekt.epw and never the old
file again; the old file is only READ here - never written, renamed or
deleted (the task's own GRANICE: "NIE KASUJ pliku, zostaw jako kopię").

What goes where:

  analog_points          -> projekt.epw: an AI card (default id "AI1") and
                            its points <card>.AI.<n> - description,
                            technical note, signal type, raw/engineering
                            range, unit, decimals. The old "AI<n>" tag
                            becomes channel n; any other old tag name gets
                            the next free channel, and the report says
                            which. Every channel of the card gets a point
                            ("karty rodzą punkty").
  switching_counters     -> runtime_state.json (state, not project). A
                            record whose key already is a point address of
                            the project moves as is. The old flat "DI<n>"
                            names only move when --flat-di-card names the
                            DI card they were (DI<n> -> <card>.DI.<n>) -
                            which physical card a flat number meant is not
                            something this script may guess.
  controller settings    -> controller.local.json: UI language, REST
                            host/port, MQTT, historian and audit
                            retention, database size warning, alarm
                            history retention, service notes, .epwsyn and
                            .epwlogic paths.

Structure the old file may hold (zones, lines, process protections,
descriptions, device list) is NOT invented into the project: it belongs to
Studio (SPEC_PROJEKT_EPW.md "Trzy warstwy dostępu") and the report names
every such section left behind. A new projekt.epw gets every module the
old file had enabled - an old project with no "enabled_features" section
had them all, so the controller keeps behaving as before.

An existing projekt.epw (e.g. one from Studio) is extended, never
replaced: points already in it are left as they are.

Usage, from the repository root:
    python runtime/tools/migrate_project_json.py
    python runtime/tools/migrate_project_json.py --flat-di-card DI1
    python runtime/tools/migrate_project_json.py --source old.json --target new/projekt.epw
"""
import argparse
import json
import re
import sys
from pathlib import Path

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from epw_os.core import project_format as pf  # noqa: E402
from epw_os.core.addressing import is_address  # noqa: E402
from epw_os.core.analog_scaling import normalize_config  # noqa: E402
from epw_os.core.feature_config import TOGGLABLE_FEATURES, normalize_enabled_features  # noqa: E402
from epw_os.core.local_json import atomic_write_json, read_json_object  # noqa: E402
from epw_os.core.project_manager import (LEGACY_PROJECT_FILE, DEFAULT_PROJECT_FILE, SETTINGS_FILE_NAME,  # noqa: E402
                                         SETTINGS_FORMAT, STATE_FILE_NAME, ProjectManager)
from epw_os.core.runtime_state import RuntimeStateStore  # noqa: E402
from epw_os.i18n import set_language, tr  # noqa: E402

SETTINGS_KEYS = (
    "language", "api_host", "api_port", "mqtt", "historian_deadband", "historian_retention", "audit_retention",
    "db_size_warning", "intrusion_history_retention", "service_notes", "synoptic_project", "logic_project",
)
STRUCTURE_LEFT_TO_STUDIO = (
    "intrusion_zones", "intrusion_lines", "intrusion_power_supervision", "process_protections",
    "tag_descriptions", "output_descriptions", "devices", "commands",
)
ANALOG_FIELDS = ("signal_type", "raw_min", "raw_max", "eng_min", "eng_max", "unit", "decimals")
_OLD_AI_TAG = re.compile(r"^AI(\d+)$")
_OLD_DI_TAG = re.compile(r"^DI(\d+)$")


class MigrationError(Exception):
    pass


def _analog_point(address: str, record: dict) -> "pf.Point":
    config = normalize_config({key: record[key] for key in ANALOG_FIELDS if key in record})
    return pf.Point(
        address=address,
        description=str(record.get("description", "")),
        technical_note=str(record.get("technical_note", "")),
        signal_type=str(config["signal_type"]),
        raw_min=float(config["raw_min"]), raw_max=float(config["raw_max"]),
        eng_min=float(config["eng_min"]), eng_max=float(config["eng_max"]),
        unit=str(config["unit"]), decimals=int(config["decimals"]),
    )


def migrate(source, target, state_file=None, settings_file=None, analog_card="AI1", flat_di_card=None) -> dict:
    source, target = Path(source), Path(target)
    state_file = Path(state_file) if state_file else target.with_name(STATE_FILE_NAME)
    settings_file = Path(settings_file) if settings_file else target.with_name(SETTINGS_FILE_NAME)
    report = {"target_created": False, "modules": [], "points_added": [], "points_kept": [],
              "counters_migrated": [], "counters_not_migrated": [], "settings": [], "left_to_studio": []}

    try:
        legacy = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise MigrationError(tr("migration.source_unreadable", "Cannot read {path}: {detail}",
                                path=source, detail=e)) from e
    if not isinstance(legacy, dict) or legacy.get("format") != "EPW_OS_PROJECT":
        raise MigrationError(tr("migration.source_not_legacy", "{path} is not an old runtime project.json.",
                                path=source))

    if target.exists():
        result = pf.read_project(target)
        if not result.ok:
            raise MigrationError(tr("migration.target_unreadable",
                                    "{path} exists but cannot be read ({reason}) - it is left untouched.",
                                    path=target, reason=result.error))
        project = result.project
    else:
        name = (legacy.get("metadata") or {}).get("name") or legacy.get("project_id") or "EPW"
        project = pf.new_project(name)
        enabled = normalize_enabled_features(legacy.get("enabled_features"))
        project.modules = [feature for feature in TOGGLABLE_FEATURES if enabled.get(feature)]
        report["target_created"] = True
        report["modules"] = list(project.modules)

    # --- analog points -> AI card + points ------------------------------------
    old_points = legacy.get("analog_points")
    if old_points is None:
        # A project.json from before the dynamic points list: the same
        # synthesis ProjectManager itself used, without saving anything back.
        reader = ProjectManager(project_file=str(source))
        reader.config = dict(legacy)
        old_points = reader._migrate_legacy_analog_points()
    numbered, named = [], []
    for record in old_points:
        match = _OLD_AI_TAG.match(str(record.get("tag", "")))
        (numbered if match else named).append((int(match.group(1)) if match else None, record))
    assignments = sorted(numbered, key=lambda item: item[0])
    next_channel = max((channel for channel, _ in assignments), default=0) + 1
    for _, record in named:
        assignments.append((next_channel, record))
        next_channel += 1

    if assignments:
        channels = max(channel for channel, _ in assignments)
        card = next((c for c in project.cards if c.id == analog_card), None)
        if card is None:
            card = pf.Card(id=analog_card, model="", kind="AI", channels=channels)
            project.cards.append(card)
        elif card.kind != "AI":
            raise MigrationError(tr("migration.card_not_ai", "Card {card} already exists and is not an AI card.",
                                    card=analog_card))
        else:
            card.channels = max(card.channels, channels)
        existing = {p.address for p in project.points}
        for channel, record in assignments:
            address = f"{analog_card}.AI.{channel}"
            if address in existing:
                report["points_kept"].append(address)
                continue
            project.points.append(_analog_point(address, record))
            existing.add(address)
            report["points_added"].append((str(record.get("tag", "")), address))
        for channel in range(1, card.channels + 1):
            address = f"{analog_card}.AI.{channel}"
            if address not in existing:
                project.points.append(pf.Point(address=address))
                existing.add(address)

    # --- switching counters -> runtime_state.json --------------------------------
    addresses = {p.address for p in project.points}
    store = RuntimeStateStore(state_file)
    state = store.load()
    counters = dict(state.get("switching_counters") or {})
    for key, record in (legacy.get("switching_counters") or {}).items():
        new_key = key if (is_address(key, "DI") and key in addresses) else None
        match = _OLD_DI_TAG.match(key)
        if new_key is None and match and flat_di_card:
            candidate = f"{flat_di_card}.DI.{int(match.group(1))}"
            new_key = candidate if candidate in addresses else None
        if new_key is None or new_key in counters:
            report["counters_not_migrated"].append(key)
            continue
        counters[new_key] = record
        report["counters_migrated"].append((key, new_key))
    state["switching_counters"] = counters

    # --- controller settings -> controller.local.json ---------------------------
    settings, _problem = read_json_object(settings_file)
    settings = {k: v for k, v in (settings or {}).items() if k not in ("format", "schema_version")}
    for key in SETTINGS_KEYS:
        if key in legacy and key not in settings:
            settings[key] = legacy[key]
            report["settings"].append(key)

    for key in STRUCTURE_LEFT_TO_STUDIO:
        if legacy.get(key):
            report["left_to_studio"].append(key)

    pf.save_project(project, target, modified_by="panel")
    if not store.save(state):
        raise MigrationError(tr("migration.state_write_failed", "Could not write {path}.", path=state_file))
    atomic_write_json(settings_file, {"format": SETTINGS_FORMAT, "schema_version": 1, **settings})
    report["revision"] = project.revision
    return report


def _print_report(report, source, target):
    print(tr("migration.done", "Imported {source} into {target} (revision {revision}).",
             source=source, target=target, revision=report["revision"]))
    if report["target_created"]:
        print(tr("migration.modules", "New project, modules: {modules}", modules=", ".join(report["modules"])))
    print(tr("migration.points_added", "Analog points added: {count}", count=len(report["points_added"])))
    for old, new in report["points_added"]:
        print(f"  {old} -> {new}")
    if report["points_kept"]:
        print(tr("migration.points_kept", "Already in the project, left unchanged: {addresses}",
                 addresses=", ".join(report["points_kept"])))
    print(tr("migration.counters_migrated", "Switching counters moved to the state file: {count}",
             count=len(report["counters_migrated"])))
    if report["counters_not_migrated"]:
        print(tr("migration.counters_not_migrated",
                 "Switching counters not moved (no such point in the project - use --flat-di-card for the old "
                 "DI<n> names once the DI card exists): {names}",
                 names=", ".join(report["counters_not_migrated"])))
    print(tr("migration.settings", "Controller settings moved: {keys}", keys=", ".join(report["settings"]) or "-"))
    if report["left_to_studio"]:
        print(tr("migration.left_to_studio", "Left for Studio (structure, not imported): {keys}",
                 keys=", ".join(report["left_to_studio"])))
    print(tr("migration.source_kept", "{source} was not changed and stays as a copy.", source=source))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import the old runtime project.json into projekt.epw.")
    parser.add_argument("--source", default=LEGACY_PROJECT_FILE)
    parser.add_argument("--target", default=DEFAULT_PROJECT_FILE)
    parser.add_argument("--state-file")
    parser.add_argument("--settings-file")
    parser.add_argument("--analog-card", default="AI1")
    parser.add_argument("--flat-di-card")
    parser.add_argument("--language", default="en")
    args = parser.parse_args(argv)
    set_language(args.language)
    try:
        report = migrate(args.source, args.target, args.state_file, args.settings_file, args.analog_card,
                         args.flat_di_card)
    except MigrationError as e:
        print(e, file=sys.stderr)
        return 1
    _print_report(report, args.source, args.target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
