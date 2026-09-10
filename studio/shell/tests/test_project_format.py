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
    Location,
    Point,
    Project,
    ProjectFormatError,
    SCHEMA_VERSION,
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
