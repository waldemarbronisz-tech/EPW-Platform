"""Tests for epw_os/core/feature_config.py - which functions are
ALWAYS_ON vs. TOGGLABLE, and the defaulting/normalization logic. Pure
data, headless."""
from epw_os.core.feature_config import (
    ALWAYS_ON_FEATURES, TOGGLABLE_FEATURES, ALL_FEATURES, DEFAULT_ENABLED_FEATURES,
    normalize_enabled_features, is_feature_enabled,
)


def test_always_on_and_togglable_are_disjoint():
    assert set(ALWAYS_ON_FEATURES).isdisjoint(TOGGLABLE_FEATURES)
    assert set(ALL_FEATURES) == set(ALWAYS_ON_FEATURES) | set(TOGGLABLE_FEATURES)


def test_task_s_own_always_on_list():
    assert set(ALWAYS_ON_FEATURES) == {
        "main_view", "digital_inputs", "control_outputs", "alarms", "events", "audit_log",
    }


def test_task_s_own_togglable_list():
    """Extended by the page-split task with 3 new, genuinely new-page
    toggles (intrusion_history, intrusion_config, protection_process) -
    "intrusion"/"protection_settings" keep their old meaning unchanged
    (see feature_config.py's own comment)."""
    assert set(TOGGLABLE_FEATURES) == {
        "intrusion", "trends", "power_quality", "protection_settings", "bus_diagnostics",
        "system_topology", "engineer_mode", "analog_inputs", "switching_counters", "service_notes",
        "intrusion_history", "intrusion_config", "protection_process",
    }


def test_default_is_every_togglable_feature_enabled():
    assert set(DEFAULT_ENABLED_FEATURES.keys()) == set(TOGGLABLE_FEATURES)
    assert all(DEFAULT_ENABLED_FEATURES.values())


def test_normalize_backfills_missing_section():
    """Task: "Domyslnie WSZYSTKIE funkcje wlaczone... bez migracji" - an
    old project.json (no "enabled_features" key at all) reads back as
    every feature on, same as project_manager.get_enabled_features()
    would return {} for it."""
    assert normalize_enabled_features({}) == DEFAULT_ENABLED_FEATURES
    assert normalize_enabled_features(None) == DEFAULT_ENABLED_FEATURES
    assert normalize_enabled_features("not a dict") == DEFAULT_ENABLED_FEATURES


def test_normalize_backfills_partial_section():
    """A project that predates only SOME features (e.g. saved between
    this task and a later one that adds an 11th togglable feature)
    still gets sensible True defaults for whatever's missing."""
    result = normalize_enabled_features({"intrusion": False})
    assert result["intrusion"] is False
    assert result["trends"] is True
    assert set(result.keys()) == set(TOGGLABLE_FEATURES)


def test_normalize_ignores_unknown_keys():
    result = normalize_enabled_features({"some_future_feature": False, "intrusion": False})
    assert "some_future_feature" not in result
    assert result["intrusion"] is False


def test_is_feature_enabled_always_true_for_always_on():
    """Task's own DOWOD requirement: an always-on feature can't be
    disabled even by tampering with the raw config directly - fed a
    (nonsensical, hand-edited) config that claims it's off, this still
    reads True."""
    tampered = {"digital_inputs": False, "audit_log": False}
    for feature in ALWAYS_ON_FEATURES:
        assert is_feature_enabled(tampered, feature) is True


def test_is_feature_enabled_reads_togglable_from_config():
    cfg = normalize_enabled_features({"intrusion": False})
    assert is_feature_enabled(cfg, "intrusion") is False
    assert is_feature_enabled(cfg, "trends") is True


def test_is_feature_enabled_fails_open_for_unknown_feature():
    assert is_feature_enabled({}, "some_typo_feature") is True
