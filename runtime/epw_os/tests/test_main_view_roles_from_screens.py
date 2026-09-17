"""Punkt 2 / luka 4 ("Main View po deviceId"): the Main View symbols take
their apparatus from the screens embedded in projekt.epw - a screen object's
deviceId, resolved through the screens' own device registry to a
designation - and only fall back to the naming rule of
MAIN_VIEW_ROLE_DESIGNATIONS for what the screens do not draw."""
import pytest

from epw_os.core.apparatus import (MAIN_VIEW_ROLE_DESIGNATIONS, Apparatus, ApparatusRegistry,
                                   bind_roles_by_designation, bind_roles_from_screens)


def _registry(*ids):
    registry = ApparatusRegistry()
    registry.set_apparatuses([Apparatus(id=i, feedback=["DI1.DI.1"], command=["DO1.DO.1"]) for i in ids])
    return registry


def _screens(objects, devices):
    return {"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "S"},
            "canvas": {"width": 1920, "height": 1080},
            "objects": [{"id": f"o{n}", "type": "electrical.circuit_breaker", **o} for n, o in enumerate(objects)],
            "devices": [{"id": i, "designation": d, "name": i, "behavior": "SWITCHED", "kind": "contactor"}
                        for i, d in devices]}


def test_the_drawn_device_wins_over_the_naming_rule():
    # Two locations both have a KM1; the naming rule alone would leave the
    # symbol unconfigured. The engineer drew MH_KM1 on the screen.
    registry = _registry("KOT_KM1", "MH_KM1", "KOT_Q1")
    assert bind_roles_by_designation(registry, MAIN_VIEW_ROLE_DESIGNATIONS)["main_view.km1"] is None

    screens = _screens([{"deviceId": "MH_KM1"}, {"deviceId": "KOT_Q1"}],
                       [("KOT_KM1", "-KM1"), ("MH_KM1", "-KM1"), ("KOT_Q1", "-Q1")])
    outcome = bind_roles_from_screens(registry, screens, MAIN_VIEW_ROLE_DESIGNATIONS)

    assert outcome["main_view.km1"] == "MH_KM1"
    assert registry.get_by_role("main_view.km1").id == "MH_KM1"
    assert outcome["main_view.q1"] == "KOT_Q1"


def test_the_screens_designation_binds_even_when_the_id_does_not_follow_the_naming_rule():
    # The apparatus is called "FEEDER_A" in the project; the screens say its
    # designation is -KM1. The naming rule could never find it.
    registry = _registry("FEEDER_A")
    screens = _screens([{"deviceId": "FEEDER_A"}], [("FEEDER_A", "-KM1")])
    assert bind_roles_by_designation(registry, MAIN_VIEW_ROLE_DESIGNATIONS)["main_view.km1"] is None

    outcome = bind_roles_from_screens(registry, screens, MAIN_VIEW_ROLE_DESIGNATIONS)

    assert outcome["main_view.km1"] == "FEEDER_A"


def test_roles_the_screens_do_not_draw_fall_back_to_the_naming_rule():
    registry = _registry("KOT_Q1", "KOT_KM1", "KOT_KVG1")
    screens = _screens([{"deviceId": "KOT_Q1"}], [("KOT_Q1", "-Q1")])

    outcome = bind_roles_from_screens(registry, screens, MAIN_VIEW_ROLE_DESIGNATIONS)

    assert outcome == {"main_view.q1": "KOT_Q1", "main_view.km1": "KOT_KM1", "main_view.voltage_relay": "KOT_KVG1",
                       "main_view.kmg": None, "main_view.km2": None}


@pytest.mark.parametrize("screens", [None, {}, {"objects": "no", "devices": 3}])
def test_no_screens_means_the_naming_rule_for_every_role(screens):
    registry = _registry("KOT_Q1", "MH_KM2")
    outcome = bind_roles_from_screens(registry, screens, MAIN_VIEW_ROLE_DESIGNATIONS)
    assert outcome == bind_roles_by_designation(_registry("KOT_Q1", "MH_KM2"), MAIN_VIEW_ROLE_DESIGNATIONS)
    assert registry.get_by_role("main_view.km2").id == "MH_KM2"


def test_two_different_apparatuses_drawn_for_one_symbol_leave_it_unconfigured():
    registry = _registry("KOT_KM1", "MH_KM1")
    screens = _screens([{"deviceId": "KOT_KM1"}, {"deviceId": "MH_KM1"}],
                       [("KOT_KM1", "-KM1"), ("MH_KM1", "-KM1")])

    outcome = bind_roles_from_screens(registry, screens, MAIN_VIEW_ROLE_DESIGNATIONS)

    assert outcome["main_view.km1"] is None
    assert registry.get_by_role("main_view.km1") is None


def test_the_same_apparatus_drawn_twice_is_one_binding():
    registry = _registry("KOT_KM1")
    screens = _screens([{"deviceId": "KOT_KM1"}, {"deviceId": "KOT_KM1"}], [("KOT_KM1", "-KM1")])
    assert bind_roles_from_screens(registry, screens, MAIN_VIEW_ROLE_DESIGNATIONS)["main_view.km1"] == "KOT_KM1"


def test_a_drawn_device_missing_from_the_apparatus_register_is_ignored_with_the_naming_rule_next():
    # The screens were drawn against a device the project no longer has;
    # the register still has KOT_KM1 under its own name.
    registry = _registry("KOT_KM1")
    screens = _screens([{"deviceId": "OLD_KM1"}], [("OLD_KM1", "-KM1")])

    outcome = bind_roles_from_screens(registry, screens, MAIN_VIEW_ROLE_DESIGNATIONS)

    assert outcome["main_view.km1"] == "KOT_KM1"


def test_an_object_whose_device_is_not_in_the_screens_registry_uses_the_id_suffix():
    registry = _registry("KOT_KVG1")
    screens = _screens([{"deviceId": "KOT_KVG1"}], [])
    assert bind_roles_from_screens(registry, screens, MAIN_VIEW_ROLE_DESIGNATIONS)["main_view.voltage_relay"] == "KOT_KVG1"


def test_designations_compare_without_the_iec_minus_and_case():
    registry = _registry("X1")
    screens = _screens([{"deviceId": "X1"}], [("X1", " -q1 ")])
    assert bind_roles_from_screens(registry, screens, MAIN_VIEW_ROLE_DESIGNATIONS)["main_view.q1"] == "X1"


# --- through EPWCore.startup() --------------------------------------------------------

@pytest.fixture
def start_core(db):
    cores = []

    def _start(project_path):
        from epw_os.core.epw_core import EPWCore
        core = EPWCore()
        core.project_manager.project_file = str(project_path)
        core.startup()
        cores.append(core)
        return core

    yield _start
    for core in cores:
        if core.is_running:
            core.shutdown()


def test_core_binds_the_main_view_from_the_embedded_screens(tmp_path, start_core):
    from epw_os.core import project_format as pf
    project = pf.new_project("Screens bind", author="Test")
    project.locations = [pf.Location("KOT", "Kotlownia"), pf.Location("MH", "Maszynownia")]
    card_di = pf.Card("DI1", "ELA01", channel_kinds={"DI": 4}, location="KOT")
    card_do = pf.Card("DO1", "ADA01", channel_kinds={"DO": 4}, location="KOT")
    project.cards = [card_di, card_do]
    project.points = [pf.Point(address=f"DI1.DI.{n}") for n in range(1, 5)] + \
                     [pf.Point(address=f"DO1.DO.{n}") for n in range(1, 5)]
    project.devices = [
        pf.Device(id="KOT_KM1", behavior="SWITCHED", feedback=["DI1.DI.1"], command=["DO1.DO.1"]),
        pf.Device(id="MH_KM1", behavior="SWITCHED", feedback=["DI1.DI.2"], command=["DO1.DO.2"]),
        pf.Device(id="KOT_Q1", behavior="SWITCHED", feedback=["DI1.DI.3"], command=["DO1.DO.3"]),
    ]
    project.screens = _screens([{"deviceId": "MH_KM1"}], [("KOT_KM1", "-KM1"), ("MH_KM1", "-KM1"), ("KOT_Q1", "-Q1")])
    path = tmp_path / "projekt.epw"
    pf.save_project(project, path)

    core = start_core(path)

    # Drawn: MH_KM1 (the naming rule alone would have left KM1 unconfigured).
    assert core.apparatus_registry.get_by_role("main_view.km1").id == "MH_KM1"
    # Not drawn: Q1 still comes from the naming rule.
    assert core.apparatus_registry.get_by_role("main_view.q1").id == "KOT_Q1"
    assert core.apparatus_registry.get_by_role("main_view.kmg") is None
