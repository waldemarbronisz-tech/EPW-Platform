"""Tests for EPWCore.set_feature_enabled() and the conditional
construction in EPWCore.startup() (Task: "okno konfiguracji funkcji") -
a real EPWCore, isolated to a temp project.json per test (same "never
touch the real project.json" isolation every other whole-core test in
this codebase already uses), backed by the real (test) SQLite database
via the `db` fixture in conftest.py (opt-in, not autouse - Task:
refactor/test-db-fixture) - `core` (below) and `_empty_audit_log`
(autouse in this file only) both request it.
"""
import os

import pytest

from epw_os.core.epw_core import EPWCore
from epw_os.core.access_manager import AccessLevel
from epw_os.core.feature_config import ALWAYS_ON_FEATURES, TOGGLABLE_FEATURES
from epw_os.core.tag_manager import TagType


@pytest.fixture(autouse=True)
def _empty_audit_log(db):
    """Requests `db` (this file's real reason to exist - see its own
    module docstring) so every test in this file gets the database,
    without having to add `db` to each one individually. The explicit
    delete below is now redundant with `db`'s own between-tests table
    cleanup (Task: refactor/test-db-fixture - `db` clears every table,
    audit_log included, before every test that requests it) - kept
    anyway as a harmless, explicit belt-and-suspenders for this table
    specifically, same pattern test_intrusion_history.py's own fixture
    already uses for a different table. Originally needed because
    several tests in this file (and EPWCore.startup() itself,
    indirectly, via other things it logs) write real AuditLog rows that
    would otherwise leak between tests and break exact-count
    assertions."""
    from epw_os.db.database import SessionLocal
    from epw_os.db.models import AuditLog
    db = SessionLocal()
    try:
        db.query(AuditLog).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture
def core(tmp_path, db):
    c = EPWCore()
    c.project_manager.project_file = str(tmp_path / "project.json")
    c.startup()
    yield c
    c.shutdown()


def test_every_togglable_feature_is_enabled_by_default(core):
    for feature in TOGGLABLE_FEATURES:
        assert core.enabled_features[feature] is True


def test_intrusion_disable_stops_thread_removes_tags_data_stops(core):
    """DOWOD: "wylaczenie funkcji zatrzymuje jej modul - tagi znikaja,
    watki sie koncza, dane przestaja powstawac"."""
    assert core.intrusion_manager is not None
    assert core.tag_manager.get_tag("Security.System.Alarm") is not None
    zone_id = core.intrusion_manager.add_zone("Z", 0.0, 0.0, level=AccessLevel.ENGINEER)
    assert core.tag_manager.get_tag(f"Security.Zone.{zone_id}.State") is not None

    result = core.set_feature_enabled("intrusion", False, actor="Engineer", level=AccessLevel.ENGINEER)
    assert result["success"] is True
    assert core.intrusion_manager is None
    assert core.tag_manager.get_tag("Security.System.Alarm") is None
    assert core.tag_manager.get_tag(f"Security.Zone.{zone_id}.State") is None
    # the zone CONFIGURATION itself is untouched (DOWOD: "nie kasuje danych")
    assert any(z["id"] == zone_id for z in core.project_manager.get_intrusion_zones())


def test_intrusion_disable_does_not_delete_persisted_zones_and_lines(core):
    zone_id = core.intrusion_manager.add_zone("Z", 0.0, 0.0, level=AccessLevel.ENGINEER)
    core.intrusion_manager.add_line("L", zone_id, "DI1", "NC", "INSTANT", level=AccessLevel.ENGINEER)
    core.set_feature_enabled("intrusion", False, actor="Engineer", level=AccessLevel.ENGINEER)
    assert len(core.project_manager.get_intrusion_zones()) == 1
    assert len(core.project_manager.get_intrusion_lines()) == 1


def test_intrusion_re_enable_starts_module_and_restores_tags(core):
    zone_id = core.intrusion_manager.add_zone("Z", 0.0, 0.0, level=AccessLevel.ENGINEER)
    core.set_feature_enabled("intrusion", False, actor="Engineer", level=AccessLevel.ENGINEER)
    assert core.intrusion_manager is None

    result = core.set_feature_enabled("intrusion", True, actor="Engineer", level=AccessLevel.ENGINEER)
    assert result["success"] is True
    assert core.intrusion_manager is not None
    assert core.tag_manager.get_tag("Security.System.Alarm") is not None
    # DOWOD: "po ponownym wlaczeniu maja byc na miejscu" - the zone from
    # before disabling reappears, loaded fresh from the untouched config.
    assert any(z["id"] == zone_id for z in core.intrusion_manager.get_zones())
    assert core.tag_manager.get_tag(f"Security.Zone.{zone_id}.State") is not None


def test_protection_process_disable_stops_evaluation_removes_tags(core):
    """Page-split task, mirroring the intrusion tests above: "wylaczenie
    funkcji zatrzymuje jej modul - tagi znikaja, nie ewaluuje juz
    watkiem/timerem"."""
    assert core.process_protection_manager is not None
    core.add_analog_point({"tag": "AI_TEST_PP", "description": "test"})
    pid = core.process_protection_manager.add_protection(
        "PP Test", "AI_TEST_PP", 80.0, 10.0, level=AccessLevel.ENGINEER)
    assert pid is not None
    assert core.tag_manager.get_tag(f"Process.{pid}.Exceeded") is not None

    result = core.set_feature_enabled("protection_process", False, actor="Engineer", level=AccessLevel.ENGINEER)
    assert result["success"] is True
    assert core.process_protection_manager is None
    assert core.tag_manager.get_tag(f"Process.{pid}.Exceeded") is None
    # the protection CONFIGURATION itself is untouched (DOWOD: "nie kasuje danych")
    assert any(p["id"] == pid for p in core.project_manager.get_process_protections())


def test_protection_process_re_enable_starts_module_and_restores_tags(core):
    core.add_analog_point({"tag": "AI_TEST_PP2", "description": "test"})
    pid = core.process_protection_manager.add_protection(
        "PP Test", "AI_TEST_PP2", 80.0, 10.0, level=AccessLevel.ENGINEER)
    core.set_feature_enabled("protection_process", False, actor="Engineer", level=AccessLevel.ENGINEER)
    assert core.process_protection_manager is None

    result = core.set_feature_enabled("protection_process", True, actor="Engineer", level=AccessLevel.ENGINEER)
    assert result["success"] is True
    assert core.process_protection_manager is not None
    assert core.tag_manager.get_tag(f"Process.{pid}.Exceeded") is not None
    assert any(p["id"] == pid for p in core.process_protection_manager.get_protections())


def test_switching_counters_disable_stops_thread_and_detaches(core):
    assert core.switching_counters is not None
    result = core.set_feature_enabled("switching_counters", False, actor="Engineer", level=AccessLevel.ENGINEER)
    assert result["success"] is True
    assert core.switching_counters is None
    assert core.presentation_mode.switching_counter_manager is None


def test_switching_counters_disable_preserves_recorded_counts(core):
    core.tag_manager.update_tag("DI1", False)
    core.tag_manager.update_tag("DI1", True)
    # flush_to_project() normally only runs periodically (every 60s) or
    # on stop() - force one now so "before" reflects what was just
    # counted, same as stop()'s own final flush (called inside
    # set_feature_enabled() below) would do anyway a little later.
    core.switching_counters.flush_to_project()
    before = core.project_manager.get_switching_counters()
    assert before  # something was actually counted
    core.set_feature_enabled("switching_counters", False, actor="Engineer", level=AccessLevel.ENGINEER)
    after = core.project_manager.get_switching_counters()
    assert after == before  # DOWOD: never deleted


def test_switching_counters_re_enable_starts_fresh_manager(core):
    core.set_feature_enabled("switching_counters", False, actor="Engineer", level=AccessLevel.ENGINEER)
    result = core.set_feature_enabled("switching_counters", True, actor="Engineer", level=AccessLevel.ENGINEER)
    assert result["success"] is True
    assert core.switching_counters is not None
    assert core.presentation_mode.switching_counter_manager is core.switching_counters


def test_service_notes_disable_and_re_enable(core):
    assert core.service_notes is not None
    core.service_notes.add_note("DI1", "a note", AccessLevel.ENGINEER)
    core.set_feature_enabled("service_notes", False, actor="Engineer", level=AccessLevel.ENGINEER)
    assert core.service_notes is None
    # persisted note survives being disabled
    assert core.project_manager.get_service_notes().get("DI1")

    core.set_feature_enabled("service_notes", True, actor="Engineer", level=AccessLevel.ENGINEER)
    assert core.service_notes is not None
    assert core.service_notes.get_notes("DI1")


def test_analog_inputs_disable_removes_tags_but_keeps_persisted_points(core):
    core.add_analog_point({"tag": "AI99", "description": "test"})
    assert core.tag_manager.get_tag("AI99") is not None

    core.set_feature_enabled("analog_inputs", False, actor="Engineer", level=AccessLevel.ENGINEER)
    assert core.tag_manager.get_tag("AI99") is None
    assert any(p["tag"] == "AI99" for p in core.project_manager.get_analog_points())

    core.set_feature_enabled("analog_inputs", True, actor="Engineer", level=AccessLevel.ENGINEER)
    assert core.tag_manager.get_tag("AI99") is not None


def test_always_on_features_cannot_be_disabled_even_bypassing_the_ui(core):
    """DOWOD: "funkcji z listy zabronionej NIE da sie wylaczyc, takze
    przez bezposrednie wywolanie z pominieciem interfejsu" - called
    directly on EPWCore, the same as every other call in this file,
    with no GUI/dialog involved at all."""
    for feature in ALWAYS_ON_FEATURES:
        result = core.set_feature_enabled(feature, False, actor="Engineer", level=AccessLevel.ENGINEER)
        assert result["success"] is False
        assert feature not in TOGGLABLE_FEATURES


def test_disabling_requires_engineer_level(core):
    result = core.set_feature_enabled("trends", False, actor="Operator", level=AccessLevel.OPERATOR)
    assert result["success"] is False
    assert core.enabled_features["trends"] is True


def test_disabling_without_a_level_argument_is_not_gated(core):
    """level=None means "caller already checked" (same convention every
    other Engineer-gated core method in this codebase already has, e.g.
    IntrusionManager.add_zone()) - used here by tests/internal callers
    that don't go through the GUI's own access_manager."""
    result = core.set_feature_enabled("trends", False, actor="SYSTEM", level=None)
    assert result["success"] is True


def test_feature_change_reaches_the_audit_log(core):
    """DOWOD: "zmiana konfiguracji trafia do dziennika audytowego"."""
    from epw_os.db.database import SessionLocal
    from epw_os.db.models import AuditLog
    core.set_feature_enabled("trends", False, actor="Engineer", level=AccessLevel.ENGINEER)
    db = SessionLocal()
    try:
        entries = db.query(AuditLog).filter(AuditLog.event_type == "FEATURE_DISABLED").all()
        assert any("trends" in e.detail for e in entries)
    finally:
        db.close()


def test_toggling_to_the_same_state_is_idempotent_no_duplicate_audit(core):
    from epw_os.db.database import SessionLocal
    from epw_os.db.models import AuditLog
    result = core.set_feature_enabled("trends", True, actor="Engineer", level=AccessLevel.ENGINEER)  # already True
    assert result == {"success": True, "reason": "unchanged"}
    db = SessionLocal()
    try:
        count = db.query(AuditLog).filter(AuditLog.event_type.in_(["FEATURE_ENABLED", "FEATURE_DISABLED"])).count()
        assert count == 0
    finally:
        db.close()


def test_old_project_with_no_enabled_features_section_has_everything_on(tmp_path, db):
    """DOWOD: "projekt bez sekcji konfiguracji (stary format) ma
    wszystkie funkcje wlaczone"."""
    import json
    project_file = tmp_path / "project.json"
    project_file.write_text(json.dumps({"project_name": "Old Project"}), encoding="utf-8")

    c = EPWCore()
    c.project_manager.project_file = str(project_file)
    c.startup()
    try:
        for feature in TOGGLABLE_FEATURES:
            assert c.enabled_features[feature] is True
        assert c.intrusion_manager is not None
        assert c.switching_counters is not None
        assert c.service_notes is not None
    finally:
        c.shutdown()


def test_feature_disabled_in_project_stays_disabled_across_a_restart(tmp_path, db):
    c1 = EPWCore()
    c1.project_manager.project_file = str(tmp_path / "project.json")
    c1.startup()
    c1.set_feature_enabled("intrusion", False, actor="Engineer", level=AccessLevel.ENGINEER)
    c1.shutdown()

    c2 = EPWCore()
    c2.project_manager.project_file = str(tmp_path / "project.json")
    c2.startup()
    try:
        assert c2.enabled_features["intrusion"] is False
        assert c2.intrusion_manager is None
    finally:
        c2.shutdown()


def test_get_feature_tag_names_for_intrusion(core):
    zone_id = core.intrusion_manager.add_zone("Z", 0.0, 0.0, level=AccessLevel.ENGINEER)
    names = core.get_feature_tag_names("intrusion")
    assert f"Security.Zone.{zone_id}.State" in names
    assert "Security.System.Alarm" in names


def test_get_feature_tag_names_for_protection_process(core):
    core.add_analog_point({"tag": "AI_TEST_PP3", "description": "test"})
    pid = core.process_protection_manager.add_protection(
        "PP Test", "AI_TEST_PP3", 80.0, 10.0, level=AccessLevel.ENGINEER)
    names = core.get_feature_tag_names("protection_process")
    assert f"Process.{pid}.Exceeded" in names


def test_feature_referenced_by_logic_true_when_tag_present(core, tmp_path):
    import json
    zone_id = core.intrusion_manager.add_zone("Z", 0.0, 0.0, level=AccessLevel.ENGINEER)
    logic_file = tmp_path / "logic.json"
    logic_file.write_text(json.dumps({
        "format": "EPW_RUNTIME_LOGIC",
        "rules": [{"tag": f"Security.Zone.{zone_id}.State"}],
    }), encoding="utf-8")
    core.logic_engine.load_program(str(logic_file))
    assert core.feature_referenced_by_logic("intrusion") is True
    assert core.feature_referenced_by_logic("trends") is False  # trends owns no tags at all


def test_feature_referenced_by_logic_false_with_no_logic_loaded(core):
    assert core.feature_referenced_by_logic("intrusion") is False
