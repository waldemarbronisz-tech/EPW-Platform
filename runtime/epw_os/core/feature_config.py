"""Which optional controller functions are enabled for THIS project
(Task: "okno konfiguracji, w ktorym wlacza i wylacza sie poszczegolne
funkcje sterownika"). Headless (no Qt import), same rule every other
core/ module follows - this is pure data plus the yes/no logic, so it's
testable without a QApplication.

GRANICE: "Domyslnie WSZYSTKIE funkcje wlaczone. Istniejace projekty
musza dzialac identycznie jak dzis, bez migracji" - a project.json that
predates this feature entirely has no "enabled_features" key at all,
and DEFAULT_ENABLED (every togglable feature True) is exactly what an
old project already behaved as, unmigrated.

TWO KINDS of feature, deliberately not the same collection:
- ALWAYS_ON: cannot be disabled by this dialog, or by any direct call
  bypassing it (enforced in feature_config.py itself, not just the
  GUI - see is_feature_enabled()/normalize_enabled_features() below).
  Task's own list: the core controller (Main View, Digital Inputs,
  Control Outputs) and baseline diagnostics/audit (Alarms, Event
  Recorder, Audit Log) - disabling audit specifically would turn "turn
  off the audit trail" into a way to hide one's own actions, which
  defeats the entire point of having one.
- TOGGLABLE: everything else - starts a real core-layer module (or
  just tag registration) that can be started/stopped at runtime, and
  removed entirely from the navigation tree while off.
"""

# Task's own explicit list, word for word - order here is NOT the
# nav/dialog display order (see nav_model.py for that); this is just
# the source-of-truth identity list.
ALWAYS_ON_FEATURES = (
    "main_view",
    "digital_inputs",
    "control_outputs",
    "alarms",
    "events",
    "audit_log",
)

TOGGLABLE_FEATURES = (
    "intrusion",
    "trends",
    "power_quality",
    "protection_settings",
    "bus_diagnostics",
    "system_topology",
    "engineer_mode",
    "analog_inputs",
    "switching_counters",
    "service_notes",
    # Task (page-split): "intrusion"/"protection_settings" above KEEP
    # their old meaning unchanged (whole-module on/off - "intrusion"
    # now specifically also gates the Podglad page, "protection_settings"
    # now specifically also gates the Elektryczne page - see
    # nav_model.py) so an old project.json needs no migration. These
    # three are genuinely NEW toggles, one per genuinely NEW page (Task:
    # "kazda nowa strona ma dostac wlasny przelacznik") - each also
    # requires its own parent feature above to be on regardless of its
    # own checkbox (see nav_model.py's intrusion_subpage_available()/
    # protection_subpage_available(), the same dependency pattern
    # engineer_mode_available() already established for protection_
    # settings/engineer_mode).
    "intrusion_history",
    "intrusion_config",
    "protection_process",
)

ALL_FEATURES = ALWAYS_ON_FEATURES + TOGGLABLE_FEATURES

# Task: "Domyslnie WSZYSTKIE funkcje wlaczone."
DEFAULT_ENABLED_FEATURES = {f: True for f in TOGGLABLE_FEATURES}


def normalize_enabled_features(raw) -> dict:
    """Backfills every togglable feature missing from `raw` (an old
    project.json section, a corrupt one, or None/{} entirely) with its
    default (True) - the single place that shape is decided, so
    project_manager's own load, the feature-config dialog, and
    EPWCore.startup() can never disagree about what an unconfigured
    project actually means. ALWAYS_ON features are deliberately never
    read from `raw` at all - is_feature_enabled() below hardcodes True
    for them regardless of what a hand-edited project.json might say,
    so a tampered file can't disable audit logging by editing JSON
    either."""
    result = dict(DEFAULT_ENABLED_FEATURES)
    if isinstance(raw, dict):
        for feature in TOGGLABLE_FEATURES:
            if feature in raw:
                result[feature] = bool(raw[feature])
    return result


def is_feature_enabled(enabled_features: dict, feature: str) -> bool:
    """The one place this question is ever answered - callers never
    inline `feature in ALWAYS_ON_FEATURES or enabled_features.get(...)`
    themselves. An unrecognized feature id reads as enabled (fails
    open to "show it") rather than silently disappearing over a typo -
    the same reasoning _level_rank() in intrusion_manager.py documents
    for the opposite (security-relevant) direction; this is a
    visibility toggle, not an access gate, so failing open is the safe
    default here."""
    if feature in ALWAYS_ON_FEATURES:
        return True
    if feature not in TOGGLABLE_FEATURES:
        return True
    return bool(enabled_features.get(feature, True))
