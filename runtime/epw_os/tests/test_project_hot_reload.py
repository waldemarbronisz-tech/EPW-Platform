"""Owner's instruction, on reinstalling a project live: "dzialaj z tym".

Until now only the logic PROGRAM could be swapped without a restart.
Everything else - cards, points, apparatuses, the alarm system, the
pages - was built once at startup, so installing a project from Studio
meant "restart EPW OS". EPWCore.reload_project() rebuilds all of it in
place.

The things worth proving here are the ones a merge-and-hope
implementation gets wrong: a card DELETED in Studio has to take its
channel tags with it, a deleted apparatus has to stop being operable,
and nothing that outlives projects (the database, the drivers, the audit
log, the access level) may be torn down with them.
"""
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf
from epw_os.core.access_manager import AccessLevel
from epw_os.core.epw_core import EPWCore
from epw_os.core.feature_config import TOGGLABLE_FEATURES


def _write_project(path, cards, apparatus_id=None, zone_name=None, sounder=None):
    """A real projekt.epw, written with the same shared writer Studio
    uses - not a hand-built dict, so what the controller reloads is
    exactly what an engineer would send it."""
    project = pf.new_project("Hot reload test")
    # Which modules this controller is composed of - the device's own
    # composition, exactly as Studio writes it.
    project.modules = list(TOGGLABLE_FEATURES)
    for card_id, kinds in cards.items():
        project.cards.append(pf.Card(id=card_id, model="ELA01", channel_kinds=dict(kinds)))
        for kind, count in kinds.items():
            for channel in range(1, count + 1):
                project.points.append(pf.Point(address=f"{card_id}.{kind}.{channel}"))
    if apparatus_id is not None:
        card_id = next(iter(cards))
        project.devices.append(pf.Device(id=apparatus_id, behavior="SWITCHED", kind="BREAKER",
                                          feedback=[f"{card_id}.DI.1"], command=[f"{card_id}.DI.2"]))
    if zone_name is not None:
        project.zones.append(pf.Zone(id="Z1", name=zone_name))
    if sounder is not None:
        project.sounder = sounder
    pf.save_project(project, path)
    return project


@pytest.fixture
def core(tmp_path, db):
    path = tmp_path / "projekt.epw"
    _write_project(path, {"ELA1": {"DI": 4}}, apparatus_id="Q1", zone_name="Hall")
    c = EPWCore()
    c.project_manager.project_file = str(path)
    c.startup()
    yield c
    c.shutdown()


def _install(core, tmp_path, **kwargs):
    """What Studio does: write a new file, install it over the
    controller's own, then ask the controller to take it up."""
    incoming = tmp_path / "incoming.epw"
    _write_project(incoming, **kwargs)
    ok, error = core.project_manager.install_project_file(str(incoming), actor="test")
    assert ok, error
    return core.reload_project(actor="test", level=AccessLevel.ENGINEER)


# --- the point of the whole thing -------------------------------------------

def test_a_new_project_takes_effect_without_a_restart(core, tmp_path):
    assert core.tag_manager.get_tag("ELA1.DI.4") is not None

    result = _install(core, tmp_path, cards={"ELA2": {"DI": 8}}, zone_name="Warehouse")

    assert result["success"] is True
    assert core.tag_manager.get_tag("ELA2.DI.8") is not None, "the new card's channels are live"
    assert core.restart_requested in (None, False, ""), "nothing asked the process to go down"
    assert core.is_running is True


def test_a_card_deleted_in_studio_takes_its_channel_tags_with_it(core, tmp_path):
    """The failure mode a merge-only reload would have: a channel that
    exists nowhere in the device, still readable, still nameable by
    logic, for ever."""
    assert core.tag_manager.get_tag("ELA1.DI.1") is not None

    result = _install(core, tmp_path, cards={"ELA2": {"DI": 2}})

    assert core.tag_manager.get_tag("ELA1.DI.1") is None
    assert "ELA1.DI.1" in result["removed_tags"], "and the register says which ones went"


def test_a_card_that_shrank_loses_only_the_channels_it_lost(core, tmp_path):
    _install(core, tmp_path, cards={"ELA1": {"DI": 2}})

    assert core.tag_manager.get_tag("ELA1.DI.2") is not None
    assert core.tag_manager.get_tag("ELA1.DI.3") is None
    assert core.tag_manager.get_tag("ELA1.DI.4") is None


def test_an_apparatus_deleted_in_studio_stops_being_operable(core, tmp_path):
    """Commands merge by key, which is right at startup and wrong here."""
    assert "Q1.CLOSE" in core.command_manager._definitions

    _install(core, tmp_path, cards={"ELA1": {"DI": 4}})

    assert "Q1.CLOSE" not in core.command_manager._definitions
    assert core.apparatus_registry.list_ids() == []


def test_the_alarm_system_comes_back_on_the_new_projects_zones(core, tmp_path):
    assert [z["name"] for z in core.intrusion_manager.get_zones()] == ["Hall"]

    _install(core, tmp_path, cards={"ELA1": {"DI": 4}}, zone_name="Warehouse")

    assert core.intrusion_manager is not None, "a new manager, but there is one"
    assert [z["name"] for z in core.intrusion_manager.get_zones()] == ["Warehouse"]
    assert core.tag_manager.get_tag("Security.System.Alarm") is not None


def test_the_sounder_settings_come_from_the_reloaded_project(core, tmp_path):
    _install(core, tmp_path, cards={"ELA1": {"DI": 4}}, zone_name="Hall",
             sounder=pf.Sounder(siren_seconds=45.0, panic_silent=False))

    assert core.intrusion_manager._sounder_cfg["siren_seconds"] == 45.0
    assert core.intrusion_manager._sounder_cfg["panic_silent"] is False


def test_forces_do_not_survive_a_project_change(core, tmp_path):
    """A force pins a tag the new project may not even have."""
    forced, reason = core.force_manager.force("ELA1.DI.3", True, actor="Engineer")
    assert forced is True, reason

    _install(core, tmp_path, cards={"ELA1": {"DI": 4}})

    assert core.force_manager.is_forced("ELA1.DI.3") is False


def test_a_card_removed_from_the_project_leaves_the_device_register(core, tmp_path):
    assert "ELA1" in core.device_manager.devices

    _install(core, tmp_path, cards={"ELA2": {"DI": 2}})

    assert "ELA1" not in core.device_manager.devices
    assert "ELA2" in core.device_manager.devices


# --- what a project does NOT own --------------------------------------------

def test_everything_that_outlives_projects_keeps_running(core, tmp_path):
    core.access_manager.level = AccessLevel.ENGINEER

    _install(core, tmp_path, cards={"ELA2": {"DI": 2}})

    assert core.historian.is_running is not False
    assert core.driver_manager.all_required_running() is True
    assert core.access_manager.level == AccessLevel.ENGINEER, "nobody was signed out by a file arriving"
    assert core.audit_logger is not None


def test_the_gui_is_told_so_it_can_rebuild_its_pages(core, tmp_path):
    """Pages and nav entries are built from the project too; main.py
    listens for this and rebuilds the window."""
    seen = []
    core.event_bus.subscribe("project_reloaded", lambda success: seen.append(success))

    _install(core, tmp_path, cards={"ELA2": {"DI": 2}})

    assert seen == [True]


def test_the_reload_is_engineer_only(core, tmp_path):
    result = core.reload_project(actor="test", level=AccessLevel.OPERATOR)

    assert result["success"] is False
    assert "Engineer" in result["reason"]
    assert core.tag_manager.get_tag("ELA1.DI.1") is not None, "nothing was taken apart"


def test_it_is_written_down(core, tmp_path):
    from epw_os.db.database import SessionLocal
    from epw_os.db.models import AuditLog

    _install(core, tmp_path, cards={"ELA2": {"DI": 2}})

    session = SessionLocal()
    try:
        entries = session.query(AuditLog).filter(AuditLog.event_type == "PROJECT_RELOADED").all()
        assert len(entries) == 1
        assert entries[0].actor == "test"
    finally:
        session.close()
