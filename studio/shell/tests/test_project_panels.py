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
    export_points_csv,
    export_points_html,
    find_point_owner,
    load_help_topic_markdown,
    location_from_synoptic_dict,
    location_to_synoptic_dict,
    point_owner_map,
    points_for_card,
    points_of_kind,
    remove_points_for_card,
    sync_points_for_card,
    validate_project,
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


# Task point 5.1/5.2 - load_help_topic_markdown() is the pure (non-Qt)
# half of both HelpPanel and AboutDialog; AboutDialog itself, like
# every other QWidget in this file, is exercised by main_window.py's
# own smoke path (constructed, screenshotted), not unit-tested here -
# see this file's own module docstring.
def test_load_help_topic_markdown_substitutes_the_real_studio_version():
    from studio.shell.version import STUDIO_VERSION

    text = load_help_topic_markdown("about", "pl")
    assert "{version}" not in text
    assert STUDIO_VERSION in text


def test_load_help_topic_markdown_both_languages_have_the_new_topics():
    for key in ("devices", "about"):
        for lang in ("pl", "en"):
            text = load_help_topic_markdown(key, lang)
            assert "brak pliku pomocy" not in text


def test_load_help_topic_markdown_missing_topic_is_reported_not_raised():
    text = load_help_topic_markdown("this_topic_does_not_exist", "pl")
    assert "brak pliku pomocy" in text


# Task point 6 - "Sprawdź projekt": validate_project()'s seven checks,
# each proven with a REAL inconsistency (not just "returns something"),
# per this session's own "a generic mechanism is proven by a synthetic
# failing case" habit (see test_project_format_field_survival.py's own
# _Forgetful class). A clean, brand-new project must report nothing.
def test_validate_project_reports_nothing_for_a_fresh_project():
    assert validate_project(new_project("Test")) == []


def test_validate_project_flags_device_pointing_at_a_missing_point():
    project = new_project("Test")
    project.devices.append(Device(id="D1", behavior="SWITCHED", feedback=["ELA1.DI.1"]))
    issues = validate_project(project)
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].target == "devices" and issues[0].selector == "select_device" and issues[0].arg == "D1"


def test_validate_project_flags_device_point_whose_card_was_deleted():
    project = new_project("Test")
    project.points.append(Point(address="ELA1.DI.1"))  # point survives, card does not
    project.devices.append(Device(id="D1", behavior="SWITCHED", feedback=["ELA1.DI.1"]))
    issues = validate_project(project)
    assert len(issues) == 1 and issues[0].severity == "error"
    assert "ELA1" in issues[0].message


def test_validate_project_flags_two_devices_on_the_same_point():
    project = new_project("Test")
    project.cards.append(Card(id="ELA1", model="ELA01", kind="DI", channels=4))
    project.points.append(Point(address="ELA1.DI.1"))
    project.devices.append(Device(id="D1", behavior="SWITCHED", feedback=["ELA1.DI.1"]))
    project.devices.append(Device(id="D2", behavior="SWITCHED", feedback=["ELA1.DI.1"]))
    issues = validate_project(project)
    double_owned = [i for i in issues if "D1" in i.message and "D2" in i.message]
    assert len(double_owned) == 1 and double_owned[0].severity == "error"


def test_validate_project_flags_point_with_unknown_location_as_a_warning():
    project = new_project("Test")
    project.points.append(Point(address="ELA1.DI.1", location="NO_SUCH_LOCATION"))
    issues = validate_project(project)
    assert len(issues) == 1
    assert issues[0].severity == "warning"
    assert issues[0].target == "points" and issues[0].selector == "select_address"


def test_validate_project_flags_line_pointing_at_a_missing_point():
    # "intrusion" already in composition - isolates this test to the
    # ONE check under test, not also the (separately, correctly)
    # co-triggered check-7 orphan-data warning (own test below).
    project = new_project("Test")
    project.modules.append("intrusion")
    project.zones.append(Zone(id="Z1", name="Parter"))
    project.lines.append(Line(id="L1", name="Czujka", zone_id="Z1", tag="ELA1.DI.1"))
    issues = validate_project(project)
    assert len(issues) == 1 and issues[0].severity == "error"
    assert issues[0].target == "lines" and issues[0].selector == "select_line" and issues[0].arg == "L1"


def test_validate_project_flags_process_protection_missing_point():
    project = new_project("Test")
    project.modules.append("protection_process")
    project.process_protections.append(ProcessProtection(id="PP1", name="Temp", analog_tag="ADA1.AI.1"))
    issues = validate_project(project)
    assert len(issues) == 1 and issues[0].severity == "error"
    assert issues[0].target == "process_protection" and issues[0].arg == "PP1"


def test_validate_project_flags_process_protection_pointing_at_a_non_ai_point():
    project = new_project("Test")
    project.modules.append("protection_process")
    project.cards.append(Card(id="ELA1", model="ELA01", kind="DI", channels=4))
    project.points.append(Point(address="ELA1.DI.1"))
    project.process_protections.append(ProcessProtection(id="PP1", name="Temp", analog_tag="ELA1.DI.1"))
    issues = validate_project(project)
    assert len(issues) == 1 and issues[0].severity == "error"
    assert "AI" in issues[0].message


def test_validate_project_flags_module_with_orphaned_data_as_a_warning():
    project = new_project("Test")
    project.zones.append(Zone(id="Z1", name="Parter"))  # intrusion data, "intrusion" not in modules
    issues = validate_project(project)
    assert len(issues) == 1
    assert issues[0].severity == "warning"
    assert issues[0].target == "modules" and issues[0].selector == "select_module" and issues[0].arg == "intrusion"


def test_validate_project_no_orphan_warning_once_the_module_is_in_composition():
    project = new_project("Test")
    project.modules.append("intrusion")
    project.zones.append(Zone(id="Z1", name="Parter"))
    assert validate_project(project) == []


# Task point 7 - "Eksportuj listę punktów": export_points_csv()/
# export_points_html() are pure functions (no Qt, no file I/O) -
# main_window._export_point_list() itself (the file-picker/write) is
# covered by main_window.py's own smoke path, not here, same division
# this file's module docstring already draws everywhere else.
def _export_demo_project():
    project = new_project("Test")
    project.cards.append(Card(id="ELA1", model="ELA01", kind="DI", channels=2))
    project.cards.append(Card(id="ADA1", model="ADA01", kind="AI", channels=1))
    project.locations.append(Location(code="KOT", description="Kotlownia"))
    project.points.append(Point(
        address="ELA1.DI.1", description="Czujnik drzwi", location="KOT",
        technical_note="NC, 2-przewodowy",
    ))
    project.points.append(Point(address="ELA1.DI.2", description="Bez lokalizacji"))
    project.points.append(Point(
        address="ADA1.AI.1", description="Temperatura kotla", location="KOT",
        raw_min=4.0, raw_max=20.0, eng_min=0.0, eng_max=100.0, unit="degC",
    ))
    project.devices.append(Device(id="APARAT1", behavior="SIGNAL", feedback=["ELA1.DI.1"]))
    return project


def test_export_points_csv_has_the_tasks_own_columns_in_order():
    import csv
    import io

    text = export_points_csv(_export_demo_project())
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == [
        "Adres", "Opis", "Lokalizacja", "Notatka techniczna", "Aparat",
        "Zakres surowy", "Zakres inżynieryjny", "Jednostka",
    ]


def test_export_points_csv_rows_have_the_right_values():
    import csv
    import io

    text = export_points_csv(_export_demo_project())
    by_address = {row[0]: row for row in list(csv.reader(io.StringIO(text)))[1:]}
    assert by_address["ELA1.DI.1"] == [
        "ELA1.DI.1", "Czujnik drzwi", "KOT", "NC, 2-przewodowy", "APARAT1", "", "", "",
    ]
    assert by_address["ELA1.DI.2"][2] == "(bez lokalizacji)"
    assert by_address["ADA1.AI.1"][5:8] == ["4…20", "0…100", "degC"]


def test_export_points_csv_orders_rows_by_card_then_location():
    import csv
    import io

    addresses = [row[0] for row in list(csv.reader(io.StringIO(export_points_csv(_export_demo_project()))))[1:]]
    assert addresses.index("ELA1.DI.1") < addresses.index("ELA1.DI.2") < addresses.index("ADA1.AI.1")


def test_export_points_csv_of_an_empty_project_is_header_only():
    import csv
    import io

    rows = list(csv.reader(io.StringIO(export_points_csv(new_project("Test")))))
    assert len(rows) == 1


def test_export_points_html_groups_by_card_then_location():
    text = export_points_html(_export_demo_project())
    assert "<h2>ELA1" in text and "<h2>ADA1" in text
    assert "<h3>KOT</h3>" in text
    assert "<h3>(bez lokalizacji)</h3>" in text
    assert text.index("<h2>ELA1") < text.index("<h2>ADA1")


def test_export_points_html_escapes_user_supplied_text():
    project = new_project("Test")
    project.cards.append(Card(id="ELA1", model="ELA01", kind="DI", channels=1))
    project.points.append(Point(address="ELA1.DI.1", description="<script>alert(1)</script>"))
    text = export_points_html(project)
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;" in text


def test_export_points_html_of_an_empty_project_has_no_group_headers():
    assert "<h2>" not in export_points_html(new_project("Test"))
