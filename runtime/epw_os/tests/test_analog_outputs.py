"""Task „runtime czyta projekt.epw", punkt 2: analog outputs exist in
runtime.

A card's AO channels used to be skipped outright ("AO has no runtime
support yet") - the project could declare eight of them and nothing in
the controller knew. Now they are tags like DI/DO, the point's own
scaling is read the other way round on the way out (engineering value ->
raw register), and the write leaves through the same driver-layer
boundary a digital command does.
"""
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf
from epw_os.core.access_manager import AccessLevel
from epw_os.core.analog_scaling import (SIGNAL_TYPE_READY, compute_raw_value, scale_to_engineering, scale_to_raw)
from epw_os.core.epw_core import EPWCore
from epw_os.core.events import EventBus
from epw_os.core.tag_manager import TagManager


def _project(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    project = pf.new_project("Analog outputs")
    project.modules = ["analog_inputs"]
    project.cards = [pf.Card(id="ELA1", model="ELA", channel_kinds={"DI": 2, "AI": 2}, modbus_unit_id=1),
                     pf.Card(id="ADA1", model="ADA", channel_kinds={"DO": 2, "AO": 3}, modbus_unit_id=2)]
    project.points = [pf.Point(address="ELA1.DI.1"), pf.Point(address="ELA1.DI.2"),
                      pf.Point(address="ELA1.AI.1"), pf.Point(address="ELA1.AI.2"),
                      pf.Point(address="ADA1.DO.1"), pf.Point(address="ADA1.DO.2"),
                      pf.Point(address="ADA1.AO.1", description="Zawór mieszający", signal_type="4-20mA",
                               raw_min=4.0, raw_max=20.0, eng_min=0.0, eng_max=100.0, unit="%", decimals=0),
                      pf.Point(address="ADA1.AO.2", description="Zadana temperatura", signal_type=SIGNAL_TYPE_READY),
                      pf.Point(address="ADA1.AO.3")]
    path = directory / "projekt.epw"
    pf.save_project(project, path)
    return path


@pytest.fixture
def core(tmp_path, db):
    instance = EPWCore()
    instance.project_manager.project_file = str(_project(tmp_path))
    instance.startup()
    yield instance
    if instance.is_running:
        instance.shutdown()


def _writes(core) -> list:
    """What actually reached the driver layer."""
    return core.sim_driver.written


@pytest.fixture(autouse=True)
def _record_driver_writes(monkeypatch):
    from epw_os.drivers.simulator_driver import SimulatorDriver
    original = SimulatorDriver.write_tag
    recorded = []

    def recording(self, tag_name, value):
        recorded.append((tag_name, value))
        return original(self, tag_name, value)

    monkeypatch.setattr(SimulatorDriver, "write_tag", recording, raising=True)
    monkeypatch.setattr(SimulatorDriver, "written", recorded, raising=False)


def test_a_cards_analog_output_channels_become_tags():
    tag_manager = TagManager(EventBus())
    tag_manager.configure([{"id": "ADA1", "kind": "DO", "channels": 2},
                           {"id": "ADA1", "kind": "AO", "channels": 3},
                           {"id": "ELA1", "kind": "AI", "channels": 4}])

    from epw_os.core.addressing import is_address
    names = sorted(t.name for t in tag_manager.list_tags()
                   if any(is_address(t.name, kind) for kind in ("DI", "DO", "AI", "AO")))
    assert names == ["ADA1.AO.1", "ADA1.AO.2", "ADA1.AO.3", "ADA1.DO.1", "ADA1.DO.2"]
    # AI channels stay the Analog Inputs module's own points, not plain channels
    assert not any(name.startswith("ELA1.AI") for name in names)
    assert tag_manager.get_tag("ADA1.AO.1").quality.value == "NOT_INITIALIZED"


def test_scaling_runs_both_ways_and_passes_a_ready_value_through():
    # 4-20 mA carrying 0-100 %: half scale is 12 mA
    assert scale_to_raw(50.0, 4.0, 20.0, 0.0, 100.0) == 12.0
    assert scale_to_engineering(12.0, 4.0, 20.0, 0.0, 100.0) == 50.0

    config = {"signal_type": "4-20mA", "raw_min": 4.0, "raw_max": 20.0, "eng_min": 0.0, "eng_max": 100.0}
    assert compute_raw_value(25, config) == 8.0
    assert compute_raw_value("nie liczba", config) is None
    # a "ready value" point is written as given
    assert compute_raw_value(42.5, {"signal_type": SIGNAL_TYPE_READY}) == 42.5
    # a degenerate engineering span does not raise
    assert scale_to_raw(5.0, 4.0, 20.0, 7.0, 7.0) == 4.0


def test_the_project_carries_the_scaling_of_every_analog_output(core):
    outputs = {point["tag"]: point for point in core.project_manager.get_analog_output_points()}

    assert sorted(outputs) == ["ADA1.AO.1", "ADA1.AO.2", "ADA1.AO.3"]
    valve = outputs["ADA1.AO.1"]
    assert (valve["signal_type"], valve["raw_min"], valve["raw_max"], valve["eng_max"], valve["unit"]) == (
        "4-20mA", 4.0, 20.0, 100.0, "%")
    assert core.tag_manager.get_tag("ADA1.AO.1").description == "Zawór mieszający"


def test_setting_an_analog_output_writes_the_raw_value_through_the_driver_and_is_audited(core):
    result = core.write_analog_output("ADA1.AO.1", 75.0, actor="Engineer", level=AccessLevel.ENGINEER)

    assert result["success"] is True
    assert result["raw"] == 16.0  # 75 % of 0-100 on a 4-20 mA output
    assert ("ADA1.AO.1", 16.0) in _writes(core)
    assert core.tag_manager.get_value("ADA1.AO.1") == 16.0

    from epw_os.db.database import SessionLocal
    from epw_os.db.models import AuditLog
    session = SessionLocal()
    try:
        details = [row.detail for row in session.query(AuditLog).filter(AuditLog.event_type == "ANALOG_OUTPUT_SET")]
    finally:
        session.close()
    assert any("ADA1.AO.1 set to 75.0 % (16.0 raw)" == detail for detail in details)


def test_a_ready_value_output_is_written_as_given(core):
    result = core.write_analog_output("ADA1.AO.2", 42.5, actor="Engineer", level=AccessLevel.ENGINEER)

    assert result["success"] is True and result["raw"] == 42.5
    assert ("ADA1.AO.2", 42.5) in _writes(core)


def test_below_engineer_an_unknown_tag_and_a_non_number_are_all_refused(core):
    before = list(_writes(core))

    denied = core.write_analog_output("ADA1.AO.1", 10.0, actor="Operator", level=AccessLevel.OPERATOR)
    assert denied["success"] is False and "Engineer" in denied["reason"]

    not_an_output = core.write_analog_output("ELA1.DI.1", 10.0, level=AccessLevel.ENGINEER)
    assert not_an_output["success"] is False and "analog output" in not_an_output["reason"]

    missing = core.write_analog_output("ADA9.AO.1", 10.0, level=AccessLevel.ENGINEER)
    assert missing["success"] is False

    rubbish = core.write_analog_output("ADA1.AO.1", "dużo", level=AccessLevel.ENGINEER)
    assert rubbish["success"] is False and "number" in rubbish["reason"]

    assert _writes(core) == before  # nothing reached the driver
