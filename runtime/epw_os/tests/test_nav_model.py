"""Tests for epw_os/core/nav_model.py - the navigation tree's shape
(Task: "przebudowac lewe menu nawigacji na drzewo", extended by the
page-split task's SYSTEM ALARMOWY/ZABEZPIECZENIA 2-3-page split) -
headless, no Qt needed at all; the actual widget lives in
epw_os/gui/widgets/nav_tree.py and is exercised separately, in
gui_smoke/test_shell.py (formerly test_gui_smoke.py, split up in the
refactor/test-suite-split task - see gui_smoke/README.md)."""
from epw_os.core.nav_model import (
    NAV_STRUCTURE, build_nav_tree, first_page_id, all_page_ids, engineer_mode_available,
    intrusion_subpage_available,
)
from epw_os.core.feature_config import DEFAULT_ENABLED_FEATURES, TOGGLABLE_FEATURES


def _all_titles(nodes):
    titles = []
    for node in nodes:
        titles.append(node.id)
        titles.extend(c.id for c in node.children)
    return titles


def test_default_config_shows_every_page():
    """Task: "Domyslnie WSZYSTKIE funkcje wlaczone" - every one of the
    17 existing pages (14 pre-page-split + 3 new: intrusion_history,
    intrusion_config, protection_process) is reachable somewhere in
    the tree."""
    tree = build_nav_tree(DEFAULT_ENABLED_FEATURES)
    page_ids = set()
    for node in tree:
        if node.kind == "leaf":
            page_ids.add(node.page_id)
        else:
            page_ids.update(c.page_id for c in node.children)
    assert page_ids == set(all_page_ids())


def test_main_view_group_stays_a_group_even_with_one_page():
    """Task's own explicit exception (see nav_model.py's module
    docstring) - Main View is deliberately prepared for multiple
    synoptic screens, so it stays a real group with a [+]/[-] toggle
    even though it only has one page today."""
    tree = build_nav_tree(DEFAULT_ENABLED_FEATURES)
    main_view_node = next(n for n in tree if n.id == "main_view_group")
    assert main_view_node.kind == "group"
    assert len(main_view_node.children) == 1
    assert main_view_node.children[0].page_id == "main_view"


def test_intrusion_and_protection_groups_default_to_3_and_2_page_groups():
    """Page-split task: SYSTEM ALARMOWY (Podglad/Historia/Konfiguracja)
    and ZABEZPIECZENIA (Elektryczne/Procesowe) are now real, multi-page
    groups by default - neither collapses to a flat leaf any more with
    every sub-toggle on."""
    tree = build_nav_tree(DEFAULT_ENABLED_FEATURES)
    intrusion_node = next(n for n in tree if n.id == "intrusion_group")
    assert intrusion_node.kind == "group"
    assert [c.page_id for c in intrusion_node.children] == [
        "intrusion_overview", "intrusion_history", "intrusion_config"]

    protection_node = next(n for n in tree if n.id == "protection_settings_group")
    assert protection_node.kind == "group"
    assert [c.page_id for c in protection_node.children] == ["protection_electrical", "protection_process"]


def test_single_page_group_collapses_to_a_flat_leaf():
    """The general collapse rule (Task 3's own open question) still
    applies unchanged - it just takes disabling enough sub-toggles to
    get either page-split group down to one page now."""
    cfg = dict(DEFAULT_ENABLED_FEATURES)
    cfg["intrusion_history"] = False
    cfg["intrusion_config"] = False
    cfg["protection_process"] = False
    tree = build_nav_tree(cfg)

    protection_node = next(n for n in tree if n.id == "protection_settings_group")
    assert protection_node.kind == "leaf"
    assert protection_node.page_id == "protection_electrical"

    intrusion_node = next(n for n in tree if n.id == "intrusion_group")
    assert intrusion_node.kind == "leaf"
    assert intrusion_node.page_id == "intrusion_overview"


def test_intrusion_subpages_require_the_whole_module_on():
    """Page-split task's own new dependency (mirrors engineer_mode's
    existing one) - Historia zdarzen/Konfiguracja are unreachable
    whenever "intrusion" itself is off, regardless of their own toggle."""
    cfg = dict(DEFAULT_ENABLED_FEATURES)
    assert intrusion_subpage_available(cfg) is True
    cfg["intrusion"] = False
    assert intrusion_subpage_available(cfg) is False
    tree = build_nav_tree(cfg)
    assert not any(n.id == "intrusion_group" for n in tree)

    # Both sub-toggles staying True doesn't matter - still unavailable
    # while "intrusion" itself is off.
    cfg2 = dict(DEFAULT_ENABLED_FEATURES)
    cfg2["intrusion"] = False
    cfg2["intrusion_history"] = True
    cfg2["intrusion_config"] = True
    assert intrusion_subpage_available(cfg2) is False
    tree2 = build_nav_tree(cfg2)
    assert not any(n.id == "intrusion_group" for n in tree2)


def test_protection_process_is_independent_of_protection_settings():
    """Page-split task's own deliberate NON-dependency (see
    nav_model.py's module docstring SUB-PAGE DEPENDENCY section) -
    Procesowe has no shared instance with Elektryczne's ProtectionManager,
    so it stays available even with protection_settings off."""
    cfg = dict(DEFAULT_ENABLED_FEATURES)
    cfg["protection_settings"] = False
    tree = build_nav_tree(cfg)
    node = next(n for n in tree if n.id == "protection_settings_group")
    assert node.kind == "leaf"
    assert node.page_id == "protection_process"


def test_disabling_every_page_in_a_group_removes_the_whole_group():
    """Task 3: "grupa, w ktorej wszystkie strony sa wylaczone, ZNIKA
    calkowicie - nie zostaje jako pusty folder"."""
    cfg = dict(DEFAULT_ENABLED_FEATURES)
    cfg["power_quality"] = False
    cfg["trends"] = False
    tree = build_nav_tree(cfg)
    assert not any(n.id == "measurements_group" for n in tree)
    # every OTHER group is still there, untouched
    assert any(n.id == "control_group" for n in tree)


def test_disabling_one_of_two_pages_keeps_the_group_with_one_child():
    cfg = dict(DEFAULT_ENABLED_FEATURES)
    cfg["power_quality"] = False
    tree = build_nav_tree(cfg)
    node = next(n for n in tree if n.id == "measurements_group")
    assert node.kind == "leaf"  # down to one page - collapses, per the general rule
    assert node.page_id == "trends"


def test_disabling_analog_inputs_leaves_control_group_with_two_children():
    cfg = dict(DEFAULT_ENABLED_FEATURES)
    cfg["analog_inputs"] = False
    tree = build_nav_tree(cfg)
    node = next(n for n in tree if n.id == "control_group")
    assert node.kind == "group"
    assert [c.page_id for c in node.children] == ["digital_inputs", "control_outputs"]


def test_always_on_pages_are_never_dropped_by_any_config():
    cfg = {f: False for f in TOGGLABLE_FEATURES}
    tree = build_nav_tree(cfg)
    page_ids = set()
    for node in tree:
        if node.kind == "leaf":
            page_ids.add(node.page_id)
        else:
            page_ids.update(c.page_id for c in node.children)
    assert page_ids == {"main_view", "digital_inputs", "control_outputs", "events", "alarms", "audit_log"}


def test_engineer_mode_requires_protection_settings():
    """See nav_model.engineer_mode_available()'s own docstring - a
    dependency this task's own survey found, not something the Task
    text asked for directly, flagged and resolved in an earlier
    SESSION_REPORT.md revision. Unaffected by the page-split task -
    "protection_settings" (now specifically Elektryczne) still means
    exactly what it always did."""
    cfg = dict(DEFAULT_ENABLED_FEATURES)
    assert engineer_mode_available(cfg) is True
    cfg["protection_settings"] = False
    assert engineer_mode_available(cfg) is False
    tree = build_nav_tree(cfg)
    diagnostics = next(n for n in tree if n.id == "diagnostics_group")
    assert "engineer_mode" not in [c.page_id for c in diagnostics.children]

    # engineer_mode's OWN toggle staying True doesn't matter - it's
    # still unavailable while protection_settings is off.
    cfg2 = dict(DEFAULT_ENABLED_FEATURES)
    cfg2["protection_settings"] = False
    cfg2["engineer_mode"] = True
    assert engineer_mode_available(cfg2) is False


def test_first_page_id_of_a_group_is_its_first_child():
    tree = build_nav_tree(DEFAULT_ENABLED_FEATURES)
    control_node = next(n for n in tree if n.id == "control_group")
    assert first_page_id(control_node) == "digital_inputs"

    intrusion_node = next(n for n in tree if n.id == "intrusion_group")
    assert first_page_id(intrusion_node) == "intrusion_overview"


def test_first_page_id_of_a_leaf_is_itself():
    cfg = dict(DEFAULT_ENABLED_FEATURES)
    cfg["protection_process"] = False
    tree = build_nav_tree(cfg)
    protection_node = next(n for n in tree if n.id == "protection_settings_group")
    assert first_page_id(protection_node) == "protection_electrical"


def test_nav_structure_matches_the_task_s_own_17_pages():
    """Task: "Sprawdz te liste wzgledem rzeczywistego stanu kodu" -
    the DOWOD-required confirmation that nothing else was added/removed
    besides the page-split task's own 3 new pages (intrusion_history,
    intrusion_config, protection_process)."""
    assert len(all_page_ids()) == 17
    assert set(all_page_ids()) == {
        "main_view", "digital_inputs", "analog_inputs", "control_outputs",
        "intrusion_overview", "intrusion_history", "intrusion_config",
        "power_quality", "trends", "events", "alarms", "audit_log",
        "system_topology", "bus_diagnostics", "engineer_mode",
        "protection_electrical", "protection_process",
    }


def test_group_order_matches_task_specification():
    assert [gid for gid, _t, _e, _p in NAV_STRUCTURE] == [
        "main_view_group", "control_group", "intrusion_group", "measurements_group",
        "events_group", "diagnostics_group", "protection_settings_group",
    ]
