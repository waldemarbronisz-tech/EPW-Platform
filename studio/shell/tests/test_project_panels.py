"""Task "edytor DI/DO/AI" - project_panels.py's pure data-logic
functions (sync_points_for_card/remove_points_for_card/points_for_card),
exercised without Qt - same reasoning as test_project_format.py's own
header: no widget needs to exist for "karty rodzą punkty" itself to be
correct. The QWidget classes (ProjectInfoPanel/CardsPanel/
PointRegistryPanel) are covered indirectly by main_window.py's own
smoke path (constructed, clicked through, screenshotted - see this
task's own chat report), not unit-tested here.
"""
from studio.shell.project_format import (
    Card, Device, ElectricalProtectionStage, Line, Location, Point, ProcessProtection, Zone, new_project,
)
from studio.shell.project_panels import (
    ELECTRICAL_PROTECTION_CATALOG,
    MODULE_CATALOG,
    MODULE_IDS,
    card_from_synoptic_dict,
    card_to_synoptic_dict,
    ensure_electrical_protection_seeded,
    find_point_owner,
    location_from_synoptic_dict,
    location_to_synoptic_dict,
    point_owner_map,
    points_for_card,
    points_of_kind,
    remove_points_for_card,
    sync_points_for_card,
    _module_has_data,
    _module_entry,
)


def _project():
    return new_project("Test")


def test_sync_points_for_card_creates_one_point_per_channel():
    project = _project()
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=4)
    project.cards.append(card)
    sync_points_for_card(project, card)
    addresses = [p.address for p in project.points]
    assert addresses == ["ELA1.DI.1", "ELA1.DI.2", "ELA1.DI.3", "ELA1.DI.4"]


def test_sync_points_for_card_preserves_existing_descriptions():
    """"Karty rodzą punkty [...] Nie wpisujesz ich ręcznie" - but
    re-syncing (e.g. after editing the card's model, which doesn't
    change its address space) must never wipe out a name a user already
    typed into an existing point."""
    project = _project()
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    project.cards.append(card)
    sync_points_for_card(project, card)
    project.points[0].description = "Wylacznik glowny"

    card.model = "ELA01-rev2"
    sync_points_for_card(project, card)

    assert project.points[0].description == "Wylacznik glowny"


def test_sync_points_for_card_drops_points_beyond_shrunk_channel_count():
    project = _project()
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=4)
    project.cards.append(card)
    sync_points_for_card(project, card)
    project.points[3].description = "Doomed"

    card.channels = 2
    sync_points_for_card(project, card)

    addresses = [p.address for p in project.points]
    assert addresses == ["ELA1.DI.1", "ELA1.DI.2"]


def test_sync_points_for_card_grows_without_touching_existing_ones():
    project = _project()
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    project.cards.append(card)
    sync_points_for_card(project, card)
    project.points[0].description = "Named"

    card.channels = 3
    sync_points_for_card(project, card)

    assert [p.address for p in project.points] == ["ELA1.DI.1", "ELA1.DI.2", "ELA1.DI.3"]
    assert project.points[0].description == "Named"
    assert project.points[2].description == ""


def test_sync_points_for_card_does_not_touch_other_cards():
    project = _project()
    card_a = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    card_b = Card(id="ADA1", model="ADA01", kind="DO", channels=2)
    project.cards.extend([card_a, card_b])
    sync_points_for_card(project, card_a)
    sync_points_for_card(project, card_b)
    next(p for p in project.points if p.address == "ADA1.DO.1").description = "Untouched"

    card_a.channels = 3
    sync_points_for_card(project, card_a)

    by_address = {p.address: p.description for p in project.points}
    assert by_address["ADA1.DO.1"] == "Untouched"
    assert "ELA1.DI.3" in by_address


def test_remove_points_for_card_removes_only_its_own_points():
    project = _project()
    card_a = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    card_b = Card(id="ADA1", model="ADA01", kind="DO", channels=2)
    project.cards.extend([card_a, card_b])
    sync_points_for_card(project, card_a)
    sync_points_for_card(project, card_b)

    remove_points_for_card(project, card_a)

    addresses = [p.address for p in project.points]
    assert addresses == ["ADA1.DO.1", "ADA1.DO.2"]


def test_points_for_card_filters_by_address_prefix():
    project = _project()
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    project.cards.append(card)
    sync_points_for_card(project, card)
    project.points.append(Point(address="ADA1.DO.1"))

    result = points_for_card(project, card)

    assert {p.address for p in result} == {"ELA1.DI.1", "ELA1.DI.2"}


def test_find_point_owner_returns_none_for_free_point():
    project = _project()
    assert find_point_owner(project, "ELA1.DI.1") is None


def test_find_point_owner_returns_the_owning_device():
    project = _project()
    device = Device(id="KOT_KMG1", behavior="SIGNAL", feedback=["ELA1.DI.1"])
    project.devices.append(device)
    owner = find_point_owner(project, "ELA1.DI.1")
    assert owner is device


def test_find_point_owner_checks_command_list_too():
    project = _project()
    device = Device(id="KOT_KMG1", behavior="SWITCHED", command=["ADA1.DO.1"])
    project.devices.append(device)
    assert find_point_owner(project, "ADA1.DO.1") is device


def test_find_point_owner_excludes_the_given_device_id():
    """A device re-checking its OWN existing assignment must not be
    told it conflicts with itself."""
    project = _project()
    device = Device(id="KOT_KMG1", behavior="SIGNAL", feedback=["ELA1.DI.1"])
    project.devices.append(device)
    assert find_point_owner(project, "ELA1.DI.1", exclude_device_id="KOT_KMG1") is None


def test_point_owner_map_covers_feedback_and_command():
    project = _project()
    project.devices.append(
        Device(id="KOT_KMG1", behavior="SWITCHED", feedback=["ELA1.DI.1"], command=["ADA1.DO.1"])
    )
    owners = point_owner_map(project)
    assert owners == {"ELA1.DI.1": "KOT_KMG1", "ADA1.DO.1": "KOT_KMG1"}


def test_point_owner_map_omits_unassigned_points():
    project = _project()
    assert point_owner_map(project) == {}


def test_card_synoptic_dict_round_trip():
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=32)
    data = card_to_synoptic_dict(card)
    assert data == {"id": "ELA1", "model": "ELA01", "channelKind": "DI", "channelCount": 32}
    restored = card_from_synoptic_dict(data)
    assert restored == card


def test_location_synoptic_dict_round_trip():
    location = Location(code="KOT", description="Kotlownia")
    data = location_to_synoptic_dict(location)
    assert data == {"code": "KOT", "description": "Kotlownia"}
    restored = location_from_synoptic_dict(data)
    assert restored == location


def test_points_of_kind_filters_by_the_owning_cards_kind():
    """LineConfigDialog's own point picker (Task "Alarmówka: na maksa
    dużo opcji") relies on this to offer only DI points for a CONTACT
    line and only AI points for a PARAMETRIZED one - the same
    impossible-to-assign-the-wrong-type stance
    intrusion_manager.py's own picker has on the runtime side."""
    project = _project()
    di_card = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    ai_card = Card(id="ELA1B", model="ELA01B", kind="AI", channels=2)
    project.cards.extend([di_card, ai_card])
    sync_points_for_card(project, di_card)
    sync_points_for_card(project, ai_card)

    di_points = points_of_kind(project, "DI")
    ai_points = points_of_kind(project, "AI")

    assert {p.address for p in di_points} == {"ELA1.DI.1", "ELA1.DI.2"}
    assert {p.address for p in ai_points} == {"ELA1B.AI.1", "ELA1B.AI.2"}


def test_points_of_kind_empty_when_no_matching_card():
    project = _project()
    assert points_of_kind(project, "AI") == []


def _catalog_stage_count():
    return sum(len(stages) for *_rest, stages in ELECTRICAL_PROTECTION_CATALOG)


def test_ensure_electrical_protection_seeded_creates_one_per_catalog_stage():
    project = _project()
    changed = ensure_electrical_protection_seeded(project)
    assert changed is True
    assert len(project.electrical_protection_stages) == _catalog_stage_count()


def test_ensure_electrical_protection_seeded_is_idempotent():
    project = _project()
    ensure_electrical_protection_seeded(project)
    project.electrical_protection_stages[0].setting = 12345.0
    changed_again = ensure_electrical_protection_seeded(project)
    assert changed_again is False
    assert len(project.electrical_protection_stages) == _catalog_stage_count()
    assert project.electrical_protection_stages[0].setting == 12345.0


# -- "Skład urządzenia" (task "fix/project-format-integrity", points
# 2/3) - MODULE_CATALOG/_module_has_data() pure logic. The widget
# itself (ModuleCompositionPanel, the [0][I] switch, the QMessageBox
# warning flow) is covered indirectly - constructed, clicked through
# (including both the "No" and "Yes" branches of the disable warning,
# via a mocked QMessageBox.question), and screenshotted - see this
# task's own chat report, not unit-tested here, same stance this
# file's own module docstring already takes for every other panel.

def test_module_catalog_only_lists_ids_feature_config_calls_togglable():
    """Mirrors runtime/epw_os/core/feature_config.py's own
    TOGGLABLE_FEATURES - not ALWAYS_ON_FEATURES (those "cannot be
    disabled by this dialog" on the runtime side either, so they have
    no business in a table whose point is choosing)."""
    always_on_that_leaked_in = {
        "main_view", "digital_inputs", "control_outputs", "alarms", "events", "audit_log",
    } & set(MODULE_IDS)
    assert always_on_that_leaked_in == set()


def test_module_catalog_entries_have_both_languages_and_a_group_marker():
    for entry in MODULE_CATALOG:
        feature_id, name_pl, name_en, desc_pl, desc_en, tree_group = entry
        assert name_pl and name_en and desc_pl and desc_en
        assert tree_group in ("alarm", "protection", None)


def test_module_entry_looks_up_by_id():
    entry = _module_entry("intrusion")
    assert entry is not None
    assert entry[0] == "intrusion"
    assert _module_entry("not_a_real_module") is None


def test_module_has_data_false_for_an_empty_project():
    project = new_project("Test")
    for feature_id in MODULE_IDS:
        assert _module_has_data(project, feature_id) is False


def test_module_has_data_true_for_intrusion_with_a_zone_or_a_line():
    project = new_project("Test")
    project.zones.append(Zone(id="Z1", name="Parter"))
    assert _module_has_data(project, "intrusion") is True

    project2 = new_project("Test")
    project2.lines.append(Line(id="L1", name="Czujka", zone_id="Z1"))
    assert _module_has_data(project2, "intrusion") is True


def test_module_has_data_true_for_electrical_protection_with_stages():
    project = new_project("Test")
    project.electrical_protection_stages.append(
        ElectricalProtectionStage(function_id="27 Under Voltage", stage_name="Stage 1")
    )
    assert _module_has_data(project, "protection_settings") is True


def test_module_has_data_true_for_process_protection_with_entries():
    project = new_project("Test")
    project.process_protections.append(ProcessProtection(id="PP1", name="Temp"))
    assert _module_has_data(project, "protection_process") is True


def test_module_has_data_false_for_modules_without_a_studio_panel():
    """"trends"/"engineer_mode"/etc have no Studio-side data concept
    yet - _module_has_data() must say so plainly (False), never guess."""
    project = new_project("Test")
    for feature_id in ("trends", "power_quality", "engineer_mode", "service_notes"):
        assert _module_has_data(project, feature_id) is False
