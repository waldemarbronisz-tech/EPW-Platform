"""shared/docs/SPEC_PROJEKT_EPW.md's own contract, exercised against the
real save_project()/load_project() round trip - no Qt, no mocks, plain
files on tmp_path. project_format.py has zero PySide6 dependency, so
this suite needs none of studio/logic/tests's own qapp/qsettings
fixtures.
"""
import gzip
import json

import pytest

from studio.shell.project_format import (
    Card,
    Device,
    Line,
    LineInputMode,
    LineParametrization,
    LineType,
    Location,
    NORMAL_STATE_NC,
    Point,
    PowerSupervision,
    Project,
    ProjectFormatError,
    SCHEMA_VERSION,
    Zone,
    default_value_windows,
    load_project,
    new_project,
    save_project,
)


def test_new_project_starts_dirty():
    """An unsaved new project IS unsaved work - main_window.py's close
    handler must not treat it as nothing-to-lose."""
    p = new_project("Rozdzielnica A")
    assert p.is_dirty is True
    assert p.metadata.name == "Rozdzielnica A"
    assert p.revision == 0


def test_save_clears_dirty_and_bumps_revision(tmp_path):
    p = new_project("Test")
    path = tmp_path / "projekt.epw"
    save_project(p, path)
    assert p.is_dirty is False
    assert p.revision == 1

    p.touch()
    assert p.is_dirty is True
    save_project(p, path)
    assert p.is_dirty is False
    assert p.revision == 2


def test_round_trip_preserves_metadata(tmp_path):
    p = new_project("Rozdzielnica A", author="Waldek")
    p.metadata.description = "Sterowanie kotłownią"
    path = tmp_path / "projekt.epw"
    save_project(p, path)

    loaded = load_project(path)
    assert loaded.metadata.name == "Rozdzielnica A"
    assert loaded.metadata.author == "Waldek"
    assert loaded.metadata.description == "Sterowanie kotłownią"
    assert loaded.revision == 1
    assert loaded.is_dirty is False


def test_round_trip_preserves_structural_collections(tmp_path):
    p = new_project("Test")
    p.modules = ["ELA01", "ADA01"]
    p.cards = [Card(id="DI1", model="ELA01", kind="DI", channels=32)]
    p.locations = [Location(code="KOT", description="Kotłownia")]
    p.points = [
        Point(address="DI1.DI.1", description="Czujka", location="KOT"),
        Point(
            address="DI1.AI.1", description="Temperatura", location="KOT",
            signal_type="4-20mA", raw_min=4, raw_max=20, eng_min=0, eng_max=100,
            unit="°C", decimals=1,
        ),
    ]
    p.devices = [
        Device(
            id="KOT_KMG1", behavior="SWITCHED", kind="Stycznik",
            feedback=["DI1.DI.1"], command=["DI1.DO.1"],
            supervision={"maxCloseSeconds": 5},
            safe_state={"onStartup": "OFF", "onLinkLoss": "OFF"},
        )
    ]
    path = tmp_path / "projekt.epw"
    save_project(p, path)

    loaded = load_project(path)
    assert loaded.modules == ["ELA01", "ADA01"]
    assert loaded.cards == [Card(id="DI1", model="ELA01", kind="DI", channels=32)]
    assert loaded.locations == [Location(code="KOT", description="Kotłownia")]
    assert len(loaded.points) == 2
    assert loaded.points[1].signal_type == "4-20mA"
    assert loaded.points[1].unit == "°C"
    assert len(loaded.devices) == 1
    assert loaded.devices[0].id == "KOT_KMG1"
    assert loaded.devices[0].feedback == ["DI1.DI.1"]
    assert loaded.devices[0].safe_state == {"onStartup": "OFF", "onLinkLoss": "OFF"}


def test_empty_collections_are_omitted_from_the_file(tmp_path):
    """Module docstring's own rule, ported from the old spec's "katalogi
    nieużywane [...] mogą nie istnieć": a bare project writes only
    format/schema_version/project/revision/modified_by - not five empty
    arrays pretending to be real content."""
    p = new_project("Bare")
    path = tmp_path / "projekt.epw"
    save_project(p, path)

    with gzip.open(path, "rb") as f:
        data = json.loads(f.read().decode("utf-8"))

    assert set(data.keys()) == {"format", "schema_version", "project", "revision", "modified_by"}


def test_file_is_gzip_compressed_utf8_json(tmp_path):
    """Confirms the module's own stated physical format choice, not
    just its round-trip behavior via the same functions that wrote it -
    reads the bytes independently, the way a human "unzip -l" style
    sanity check would."""
    p = new_project("Test")
    path = tmp_path / "projekt.epw"
    save_project(p, path)

    raw = path.read_bytes()
    assert raw[:2] == b"\x1f\x8b"  # gzip magic number
    decompressed = gzip.decompress(raw)
    data = json.loads(decompressed.decode("utf-8"))
    assert data["format"] == "EPW_PROJECT_FILE"


def test_missing_optional_fields_load_without_error(tmp_path):
    """A minimal, hand-written file with only the required header -
    load_project() must not require cards/locations/points/devices to
    be present at all."""
    path = tmp_path / "minimal.epw"
    minimal = {
        "format": "EPW_PROJECT_FILE",
        "schema_version": 1,
        "project": {"name": "Minimal"},
    }
    with gzip.open(path, "wb") as f:
        f.write(json.dumps(minimal).encode("utf-8"))

    loaded = load_project(path)
    assert loaded.metadata.name == "Minimal"
    assert loaded.cards == []
    assert loaded.points == []
    assert loaded.devices == []
    assert loaded.is_dirty is False


def test_rejects_a_file_without_the_format_marker(tmp_path):
    path = tmp_path / "not_a_project.epw"
    with gzip.open(path, "wb") as f:
        f.write(json.dumps({"schema_version": 1, "project": {"name": "x"}}).encode("utf-8"))

    with pytest.raises(ProjectFormatError, match="nie jest projektem EPW"):
        load_project(path)


def test_rejects_a_newer_schema_version_explicitly(tmp_path):
    """SPEC_PROJEKT_EPW.md, "Wersjonowanie i zgodność": "Aplikacja
    odmawia wczytania pliku o wersji formatu nowszej niż obsługiwana.
    Odmawia jawnie, z komunikatem - nie próbuje zgadywać." - the error
    must exist and must name the problem, not silently misread the file
    or crash on an unexpected key shape."""
    path = tmp_path / "future.epw"
    with gzip.open(path, "wb") as f:
        f.write(json.dumps({
            "format": "EPW_PROJECT_FILE",
            "schema_version": SCHEMA_VERSION + 1,
            "project": {"name": "From the future"},
        }).encode("utf-8"))

    with pytest.raises(ProjectFormatError, match="nowszą niż obsługiwana"):
        load_project(path)


def test_rejects_a_corrupt_non_gzip_file(tmp_path):
    path = tmp_path / "corrupt.epw"
    path.write_bytes(b"this is not gzip data at all")

    with pytest.raises(ProjectFormatError):
        load_project(path)


def test_touch_does_not_bump_revision():
    """SPEC_PROJEKT_EPW.md: "revision, rosnąca przy KAŻDYM zapisie" -
    at every SAVE, not at every in-memory edit."""
    p = new_project("Test")
    p.revision = 0
    p.is_dirty = False
    p.touch()
    assert p.revision == 0
    assert p.is_dirty is True


# -- Alarmówka (Zone/Line/PowerSupervision) --------------------------------
# Task "Alarmówka: na maksa dużo opcji" - field-for-field match to
# runtime/epw_os/core/intrusion_manager.py's own real parameter set (see
# Zone/Line/PowerSupervision's own docstrings).

def test_intrusion_section_omitted_when_module_not_in_composition():
    """"Sterownik podlewania nie ma alarmówki" - a project with no
    zones, no lines, and unconfigured power supervision writes no
    "intrusion" key at all, same "absent section = module not present"
    reading every other collection already gets."""
    p = new_project("Test")
    data = json.loads(_decompress_saved(p))
    assert "intrusion" not in data


def test_zone_line_power_supervision_round_trip(tmp_path):
    p = new_project("Test")
    p.zones.append(Zone(id="Z1", name="Parter", exit_delay_seconds=45.0, entry_delay_seconds=30.0))
    line = Line(
        id="L1", name="Kontaktron 2EOL okno", zone_id="Z1", tag="ELA1.AI.1",
        normal_state=NORMAL_STATE_NC, line_type=LineType.INSTANT,
        input_mode=LineInputMode.PARAMETRIZED, parametrization=LineParametrization.DEOL,
        value_windows=default_value_windows(LineParametrization.DEOL),
        min_violation_seconds=0.5, multiplicity_count=2, multiplicity_window_seconds=5.0,
        lockout_after_count=3, alarm_hold_seconds=10.0, silence_threshold_seconds=3600.0,
    )
    p.lines.append(line)
    p.power_supervision = PowerSupervision(mains_tag="ELA1.AI.2", battery_tag="ELA1.AI.3", battery_ok_state=False)

    path = tmp_path / "projekt.epw"
    save_project(p, path)
    loaded = load_project(path)

    assert loaded.zones == [Zone(id="Z1", name="Parter", exit_delay_seconds=45.0, entry_delay_seconds=30.0)]
    assert loaded.lines == [line]
    assert loaded.power_supervision == PowerSupervision(
        mains_tag="ELA1.AI.2", battery_tag="ELA1.AI.3", battery_ok_state=False
    )


def test_intrusion_section_present_with_only_power_supervision_configured():
    """Power supervision is system-wide, not per-zone/line - configuring
    ONLY it (no zones/lines at all yet) must still round-trip, not get
    silently dropped by the "omit when empty" rule above."""
    p = new_project("Test")
    p.power_supervision = PowerSupervision(mains_tag="ELA1.AI.1")
    data = json.loads(_decompress_saved(p))
    assert "intrusion" in data
    assert data["intrusion"]["power_supervision"]["mains_tag"] == "ELA1.AI.1"


def test_default_value_windows_eol_has_three_states():
    windows = default_value_windows(LineParametrization.EOL)
    assert set(windows.keys()) == {"VIOLATED", "SECURE", "FAULT_OPEN"}


def test_default_value_windows_deol_has_five_states():
    windows = default_value_windows(LineParametrization.DEOL)
    assert set(windows.keys()) == {"SHORT", "VIOLATED", "SECURE", "TAMPER", "FAULT_OPEN"}


def _decompress_saved(project) -> str:
    """Saves `project` to a throwaway in-memory-ish path and returns the
    raw JSON text - a lighter-weight check than a full load_project()
    round trip for tests that only care about the WRITTEN shape."""
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "p.epw"
        save_project(project, path)
        with gzip.open(path, "rb") as f:
            return f.read().decode("utf-8")
