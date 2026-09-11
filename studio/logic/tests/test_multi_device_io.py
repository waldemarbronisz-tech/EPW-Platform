"""feat/multi-device-io — DeviceModel's ELA/ADA module list is now
project-defined (project.settings["ela_devices"]/["ada_devices"]),
previously permanently fixed at one of each. Covers the core model,
schema migration, and the design/compile-time consumers (Validator,
core/crossref.py, property_grid's Address combobox). The live Simulation
panel grid and per-device system diagnostic signals (ELA01.ONLINE etc.)
were a deliberately separate, tracked follow-up (ARCHITECTURE.md
§9.1/§9.2) — closed by feat/multi-device-followups, covered in
tests/test_simulation_panel.py and the "system-signal catalog, per
device" section at the end of this file, respectively.
"""
import pytest
from PySide6.QtWidgets import QApplication

from logic_studio.blocks import register_builtin_blocks
from logic_studio.blocks.registry import BlockRegistry
from logic_studio.core.project import Project
from logic_studio.core.device_model import DeviceModel

register_builtin_blocks()


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---- DeviceModel: defaults, project-awareness ----------------------------

def test_no_project_defaults_to_empty():
    """Task "jedno źródło listy kart": no project handy (the bare,
    argument-less call) must NOT invent "ELA01"/"ADA01" - that silent
    default is exactly the bug this task's own report described (Logic
    Studio offering addresses for a card the project doesn't have)."""
    assert DeviceModel.get_ela_devices() == []
    assert DeviceModel.get_ada_devices() == []
    assert DeviceModel.get_ela_addresses() == []
    assert DeviceModel.get_ada_addresses() == []

def test_new_project_starts_with_zero_devices():
    """A brand-new Project() (no bridge, nothing configured yet) starts
    with NO ELA/ADA devices at all - the old "always exactly one of
    each" default is the bug this task fixes, not a regression test to
    preserve."""
    p = Project()
    assert DeviceModel.get_ela_devices(p) == []
    assert DeviceModel.get_ada_devices(p) == []
    assert DeviceModel.get_ela_addresses(p) == []
    assert DeviceModel.get_ada_addresses(p) == []

def test_addresses_span_every_defined_device():
    p = Project()
    p.settings["ela_devices"] = ["ELA01", "ELA02"]
    addrs = DeviceModel.get_ela_addresses(p)
    assert len(addrs) == 64
    assert "ELA01.DI.1" in addrs and "ELA01.DI.32" in addrs
    assert "ELA02.DI.1" in addrs and "ELA02.DI.32" in addrs

def test_devices_setting_survives_serialize_deserialize():
    p = Project()
    p.settings["ela_devices"] = ["ELA01", "ELA02", "ELA03"]
    p.settings["ada_devices"] = ["ADA01", "ADA02"]
    data = p.serialize()
    p2 = Project.deserialize(data)
    assert p2.settings["ela_devices"] == ["ELA01", "ELA02", "ELA03"]
    assert p2.settings["ada_devices"] == ["ADA01", "ADA02"]


# ---- device name validation / add / suggestion ----------------------------

def test_is_valid_device_name():
    assert DeviceModel.is_valid_device_name("ELA", "ELA01") is True
    assert DeviceModel.is_valid_device_name("ELA", "ELA99") is True
    assert DeviceModel.is_valid_device_name("ELA", "ADA01") is False  # wrong prefix
    assert DeviceModel.is_valid_device_name("ELA", "ELA1") is False  # not zero-padded
    assert DeviceModel.is_valid_device_name("ELA", "ELA001") is False  # too many digits
    assert DeviceModel.is_valid_device_name("ELA", "") is False
    assert DeviceModel.is_valid_device_name("ELA", None) is False

def test_next_device_name_fills_the_first_gap_and_extends():
    assert DeviceModel.next_device_name("ELA", []) == "ELA01"
    assert DeviceModel.next_device_name("ELA", ["ELA01"]) == "ELA02"
    assert DeviceModel.next_device_name("ELA", ["ELA01", "ELA02"]) == "ELA03"
    assert DeviceModel.next_device_name("ELA", ["ELA02"]) == "ELA01"  # fills the gap, doesn't just append

def test_set_ela_devices_validates_dedupes_and_normalizes(qsettings=None):
    p = Project()
    result = DeviceModel.set_ela_devices(p, ["ela01", " ELA02 ", "ELA01", "not-valid", ""])
    # lowercased/whitespace normalized to uppercase/stripped, duplicate
    # dropped, invalid entry dropped, order of first occurrence kept
    assert result == ["ELA01", "ELA02"]
    assert p.settings["ela_devices"] == ["ELA01", "ELA02"]

def test_set_ela_devices_becomes_empty_when_everything_invalid():
    """Task "jedno źródło listy kart": rejecting every invalid entry
    must leave an honest empty list, not invent "ELA01" from nothing."""
    p = Project()
    result = DeviceModel.set_ela_devices(p, ["", "garbage", "ADA01"])
    assert result == []


# ---- schema migration -----------------------------------------------------

def test_v4_project_migrates_with_default_single_device():
    old_data = {
        "format": "EPW_LOGIC",
        "schema_version": 4,
        "settings": {
            "name": "Old Project", "version": "1.0", "cycle_time_ms": 100,
            "analog_points": [], "internal_bits": [], "io_labels": {},
        },
        "blocks": [],
    }
    p = Project.deserialize(old_data)
    assert p.settings["ela_devices"] == ["ELA01"]
    assert p.settings["ada_devices"] == ["ADA01"]

def test_v1_project_migrates_all_the_way_through_to_ela_ada_devices():
    """The full v1->v5 migration chain in one load — the earliest format
    still ends up with the exact same default device list a brand-new
    project gets."""
    old_data = {
        "format": "EPW_LOGIC",
        "schema_version": 1,
        "settings": {"name": "Ancient Project", "version": "1.0", "cycle_time_ms": 100},
        "blocks": [],
    }
    p = Project.deserialize(old_data)
    assert p.settings["ela_devices"] == ["ELA01"]
    assert p.settings["ada_devices"] == ["ADA01"]


# ---- Validator: accepts an address only on a device the project defines --

def test_validator_rejects_address_on_an_undefined_device():
    from logic_studio.compiler.validator import Validator
    p = Project()
    di = BlockRegistry.create_block("input.di")
    di.properties["Address"] = "ELA02.DI.1"  # ELA02 doesn't exist yet
    p.add_block(di)

    errors, warnings = [], []
    Validator(p).run(errors, warnings)
    assert any("ELA02.DI.1" in e for e in errors)

def test_validator_accepts_address_once_the_device_is_defined():
    from logic_studio.compiler.validator import Validator
    p = Project()
    p.settings["ela_devices"] = ["ELA01", "ELA02"]
    di = BlockRegistry.create_block("input.di")
    di.properties["Address"] = "ELA02.DI.1"
    p.add_block(di)

    errors, warnings = [], []
    Validator(p).run(errors, warnings)
    assert not any("ELA02.DI.1" in e for e in errors)

def test_validator_names_the_card_when_it_gets_removed():
    """Task "jedno źródło listy kart" 1.2: a block whose card was
    REMOVED (not merely never defined - the far more common real
    scenario, a user deleting a card in Studio while a Logic block still
    points at it) must fail loudly at compile time, NAMING the missing
    card - never silently dropped, never its Address rewritten."""
    from logic_studio.compiler.validator import Validator
    p = Project()
    DeviceModel.set_ela_devices(p, ["ELA01", "ELA02"])
    di = BlockRegistry.create_block("input.di")
    di.properties["Address"] = "ELA02.DI.1"
    p.add_block(di)

    errors, warnings = [], []
    Validator(p).run(errors, warnings)
    assert not any("ELA02" in e and "nie istnieje" in e for e in errors)

    DeviceModel.set_ela_devices(p, ["ELA01"])  # ELA02 removed from the project
    di.properties["Address"] = "ELA02.DI.1"  # the block's own Address is untouched

    errors, warnings = [], []
    Validator(p).run(errors, warnings)
    assert di.properties["Address"] == "ELA02.DI.1"  # never silently rewritten
    assert any("ELA02" in e and "nie istnieje" in e for e in errors), errors


# ---- core/crossref.py: classifies an address on any defined device --------

def test_crossref_classifies_second_device_address_as_physical_di():
    from logic_studio.core.crossref import build_crossref, KIND_PHYSICAL_DI
    p = Project()
    p.settings["ela_devices"] = ["ELA01", "ELA02"]
    di = BlockRegistry.create_block("input.di")
    di.properties["Address"] = "ELA02.DI.5"
    p.add_block(di)

    crossref = build_crossref(p)
    assert crossref["ELA02.DI.5"].kind == KIND_PHYSICAL_DI
    assert crossref["ELA02.DI.5"].defined is True


# ---- property_grid.py: Address combobox spans every defined device --------

def test_property_grid_address_combobox_includes_every_device(qsettings):
    _app()
    from logic_studio.ui.panels.property_grid import PropertyGridPanel

    p = Project()
    p.settings["ela_devices"] = ["ELA01", "ELA02"]
    di = BlockRegistry.create_block("input.di")
    panel = PropertyGridPanel(settings=qsettings)
    panel.load_block_properties(di, p)

    combo = panel.field_widget("Address")
    items = [combo.itemText(i) for i in range(combo.count())]
    assert "ELA01.DI.1" in items
    assert "ELA02.DI.1" in items
    assert len(items) == 64


# ---- Project Settings dialog: device list editing (ui/dialogs.py) ---------

def test_dialog_starts_with_the_projects_current_devices(qsettings):
    _app()
    from logic_studio.ui.dialogs import ProjectSettingsDialog
    p = Project()
    p.settings["ela_devices"] = ["ELA01", "ELA02"]
    dialog = ProjectSettingsDialog(p)
    assert [dialog.ela_list.item(i).text() for i in range(dialog.ela_list.count())] == ["ELA01", "ELA02"]

def test_add_device_button_suggests_the_next_free_name(qsettings):
    """Task "jedno źródło listy kart": a brand-new project starts with
    ZERO devices now (not the old silent "ELA01" default) - the first
    Add press suggests "ELA01" itself, the second "ELA02"."""
    _app()
    from logic_studio.ui.dialogs import ProjectSettingsDialog
    p = Project()
    dialog = ProjectSettingsDialog(p)
    dialog._add_device(dialog.ela_list, "ELA")
    dialog._add_device(dialog.ela_list, "ELA")
    assert [dialog.ela_list.item(i).text() for i in range(dialog.ela_list.count())] == ["ELA01", "ELA02"]

def test_removing_the_last_remaining_device_is_now_allowed(qsettings):
    """Task "jedno źródło listy kart": the old "must keep at least one
    device" floor is gone - a project with zero ELA/ADA devices is a
    real, correct state (DeviceModel.get_ela_devices() == []), the same
    way Studio's own Cards panel lets a user remove its last card."""
    _app()
    from logic_studio.ui.dialogs import ProjectSettingsDialog
    p = Project()
    dialog = ProjectSettingsDialog(p)
    dialog._add_device(dialog.ela_list, "ELA")
    dialog.ela_list.item(0).setSelected(True)
    dialog._remove_selected_devices(dialog.ela_list)
    assert dialog.ela_list.count() == 0

def test_removing_a_non_last_device_works(qsettings):
    _app()
    from logic_studio.ui.dialogs import ProjectSettingsDialog
    p = Project()
    dialog = ProjectSettingsDialog(p)
    dialog._add_device(dialog.ela_list, "ELA")  # ELA01
    dialog._add_device(dialog.ela_list, "ELA")  # ELA01, ELA02
    dialog.ela_list.item(1).setSelected(True)
    dialog._remove_selected_devices(dialog.ela_list)
    assert [dialog.ela_list.item(i).text() for i in range(dialog.ela_list.count())] == ["ELA01"]

def test_apply_to_project_stores_the_edited_device_lists(qsettings):
    _app()
    from logic_studio.ui.dialogs import ProjectSettingsDialog
    p = Project()
    dialog = ProjectSettingsDialog(p)
    dialog._add_device(dialog.ela_list, "ELA")
    dialog._on_accept()

    dialog.apply_to_project()
    assert p.settings["ela_devices"] == ["ELA01"]

def test_removing_a_used_device_prompts_for_confirmation(qsettings, monkeypatch):
    """Mirrors the existing used-internal-signal-deletion confirmation —
    removing ELA01 while a DI block still addresses it must ask first,
    naming the block, not silently orphan the block's Address."""
    _app()
    from logic_studio.ui.dialogs import ProjectSettingsDialog
    from PySide6.QtWidgets import QMessageBox, QDialog

    p = Project()
    p.settings["ela_devices"] = ["ELA01", "ELA02"]
    di = BlockRegistry.create_block("input.di")
    di.properties["Address"] = "ELA02.DI.1"
    p.add_block(di)

    dialog = ProjectSettingsDialog(p)
    # Remove ELA02 (still used by `di`) from the list widget.
    for i in range(dialog.ela_list.count()):
        if dialog.ela_list.item(i).text() == "ELA02":
            dialog.ela_list.item(i).setSelected(True)
    dialog._remove_selected_devices(dialog.ela_list)

    asked = {"count": 0}
    def fake_question(*args, **kwargs):
        asked["count"] += 1
        return QMessageBox.No  # decline -> accept must abort
    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))

    before_ela_devices = p.settings["ela_devices"]
    dialog._on_accept()  # should return early, never call self.accept()

    assert asked["count"] == 1
    assert dialog.result() != QDialog.Accepted
    assert p.settings["ela_devices"] == before_ela_devices  # nothing applied yet either way


# ---- System-signal catalog, per device (ARCHITECTURE.md §9.2) ------------
# core/system_signals_catalog.json used to hardcode ELA01/ADA01's own
# ONLINE/FAULT/SAFE_PATH_OK entries — a project defining a second device got
# no corresponding diagnostic signals. Generated instead from the project's
# own ela_devices/ada_devices list (system_signals.py::_device_signals()).

def test_no_project_generates_no_device_signals():
    """Task "jedno źródło listy kart": project=None (or a project with
    no ELA/ADA devices) must generate NO per-device diagnostic signals -
    there is no device to generate one for, and no reason to keep
    pretending "ELA01"/"ADA01" exist."""
    from logic_studio.core import system_signals

    for sig_id in ("ELA01.ONLINE", "ELA01.FAULT", "ADA01.ONLINE", "ADA01.FAULT", "ADA01.SAFE_PATH_OK"):
        assert system_signals.get_signal(sig_id) is None, sig_id


def test_project_with_devices_generates_their_signals():
    """Companion to the above - a project that DOES define ELA01/ADA01
    (its own real configuration, not a silent default) still gets
    exactly the same diagnostic content the old static catalog had."""
    from logic_studio.core import system_signals

    p = Project()
    DeviceModel.set_ela_devices(p, ["ELA01"])
    DeviceModel.set_ada_devices(p, ["ADA01"])
    expected = {
        "ELA01.ONLINE": ("Moduł ELA01 komunikuje się poprawnie", "ELA OK", False),
        "ELA01.FAULT": ("Awaria modułu ELA01", "ELA AW", True),
        "ADA01.ONLINE": ("Moduł ADA01 komunikuje się poprawnie", "ADA OK", False),
        "ADA01.FAULT": ("Awaria modułu ADA01", "ADA AW", True),
        "ADA01.SAFE_PATH_OK": ("Sprzętowa droga wyłączenia sprawna", "DROGA OK", True),
    }
    for sig_id, (desc, label, safety) in expected.items():
        entry = system_signals.get_signal(sig_id, p)
        assert entry is not None, sig_id
        assert entry["description"] == desc
        assert entry["label"] == label
        assert entry["type"] == "BOOL"
        assert entry["safety_relevant"] is safety

def test_second_device_gets_its_own_diagnostic_signals():
    from logic_studio.core import system_signals

    p = Project()
    p.settings["ela_devices"] = ["ELA01", "ELA02"]
    p.settings["ada_devices"] = ["ADA01", "ADA02"]

    assert system_signals.get_signal("ELA02.ONLINE") is None  # not visible without the project
    entry = system_signals.get_signal("ELA02.ONLINE", p)
    assert entry is not None
    assert entry["description"] == "Moduł ELA02 komunikuje się poprawnie"
    assert entry["safety_relevant"] is False

    fault = system_signals.get_signal("ELA02.FAULT", p)
    assert fault["description"] == "Awaria modułu ELA02"
    assert fault["safety_relevant"] is True

    safe_path = system_signals.get_signal("ADA02.SAFE_PATH_OK", p)
    assert safe_path is not None
    assert safe_path["label"] == "DROGA OK"
    assert safe_path["safety_relevant"] is True

def test_get_categories_places_device_signals_under_komunikacja():
    from logic_studio.core import system_signals

    p = Project()
    p.settings["ela_devices"] = ["ELA01", "ELA02"]

    comms = next(c for c in system_signals.get_categories(p) if c["id"] == "SYS.COMMS")
    ids = [s["id"] for s in comms["signals"]]
    assert "SYS.COMMS_OK" in ids  # non-device-specific signal untouched
    assert "ELA02.ONLINE" in ids
    assert "ELA02.FAULT" in ids

    # The cached static catalog itself must never be mutated by this.
    default_comms = next(c for c in system_signals.get_categories() if c["id"] == "SYS.COMMS")
    assert "ELA02.ONLINE" not in [s["id"] for s in default_comms["signals"]]

def test_validator_recognizes_second_device_signal_instead_of_warning(qsettings=None):
    _app()
    p = Project()
    p.settings["ela_devices"] = ["ELA01", "ELA02"]
    sig_block = BlockRegistry.create_block("system.signal")
    sig_block.properties["Sygnał"] = "ELA02.ONLINE"
    p.add_block(sig_block)

    from logic_studio.compiler.validator import Validator
    errors, warnings = [], []
    Validator(p).run(errors, warnings)

    assert not any("Nierozpoznany sygnał systemowy" in w for w in warnings)

def test_signal_picker_lists_second_device_signal(qsettings):
    _app()
    from logic_studio.ui.signal_picker import SignalPickerDialog, SIGNAL_ID_ROLE

    p = Project()
    p.settings["ada_devices"] = ["ADA01", "ADA02"]

    dialog = SignalPickerDialog(p, value_type="BOOL", sections=("system",))
    ids = []
    def _walk(item):
        ids.append(item.data(0, SIGNAL_ID_ROLE))
        for i in range(item.childCount()):
            _walk(item.child(i))
    for i in range(dialog.tree.topLevelItemCount()):
        _walk(dialog.tree.topLevelItem(i))

    assert "ADA02.ONLINE" in ids
    assert "ADA02.SAFE_PATH_OK" in ids
