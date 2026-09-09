"""Single source of truth for the left navigation tree's structure -
which pages exist, which group each belongs to, and the order of both
(Task 5: "Kolejnosc grup i stron... ma wynikac z konfiguracji, nie z
rozsypanych po kodzie wywolan... stala, sensowna kolejnosc zdefiniowana
w JEDNYM miejscu"). Headless (no Qt import), same rule every other
core/ module follows - the tree-SHAPING logic (which groups/pages
survive a given feature configuration) is plain data transformation,
testable without a QApplication; only the actual widget lives in
epw_os/gui/widgets/nav_tree.py.

Each page entry's `feature` names an entry in feature_config.TOGGLABLE_
FEATURES, or is None for a page in feature_config.ALWAYS_ON_FEATURES
(feature_config.is_feature_enabled() treats both consistently - None
here is never passed to it directly, see build_nav_tree() below).

GROUP-WITH-ONE-PAGE DECISION (Task 3's own open question, see an
earlier SESSION_REPORT.md revision for the full original reasoning): a
group left with exactly one ENABLED page collapses to a single flat
leaf (using the GROUP's own label, not the page's narrower one)
instead of staying an expandable group with one child - avoids a
pointless extra click. Originally this is how "Nastawy zabezpieczen"
ended up a standalone item (it only ever had one page); after the
page-split task both SYSTEM ALARMOWY and ZABEZPIECZENIA normally show
as real 2-3-page groups, but each still collapses the same way if
enough of its own sub-toggles are off that only one page survives -
still no special case needed here, the mechanism is unchanged. ONE
exception: `always_expand=True` groups stay a real group even at one
child - used ONLY for Main View, which the Task itself frames as
deliberately prepared for multiple synoptic screens (multiple .epwsyn
files) in the near future; collapsing it now would just have to
un-collapse again very soon.

SUB-PAGE DEPENDENCY (page-split task): a group whose pages all read
the SAME underlying core module (SYSTEM ALARMOWY's three pages all
read the one live IntrusionManager; ZABEZPIECZENIA's Elektryczne page
owns the one ProtectionManager Engineer Mode also depends on) needs
its OWN, brand-new sub-toggle to also require the module's own parent
toggle - see intrusion_subpage_available()/protection_subpage_
available() below, the exact same dependency shape
engineer_mode_available() already established for engineer_mode
depending on protection_settings. PROCESOWE is deliberately NOT
included in that dependency - its ProcessProtectionManager is fully
independent of protection_settings/Elektryczne (a different manager,
a different data model, no shared instance), so it stays toggleable on
its own.
"""

# (group_id, group_title_key, always_expand, [(page_id, page_title_key, feature), ...])
# `feature` is None for an ALWAYS_ON page (feature_config.ALWAYS_ON_FEATURES);
# otherwise one of feature_config.TOGGLABLE_FEATURES.
#
# Task (page-split): SYSTEM ALARMOWY and ZABEZPIECZENIA each used to be
# a single page (collapsing to a standalone item below - see the
# module docstring section above). Both are now real, always-expandable-
# in-spirit groups of 2-3 pages each: SYSTEM ALARMOWY separates live
# operational work (Podglad: arm/disarm, bypass, alarm memory, walk
# test - "ZADNYCH pol konfiguracyjnych") from installer-only setup
# (Konfiguracja: zones/lines/input modes/filters/power supervision/
# history retention) and its own reporting view (Historia zdarzen,
# promoted from a tab to its own page); ZABEZPIECZENIA separates
# ELEKTRYCZNE (voltage/current/frequency - unchanged from the old
# single page, minus the non-electrical categories deleted per this
# task's own analysis - see SESSION_REPORT.md) from PROCESOWE (a new,
# minimal, from-scratch threshold module bound to real analog points).
# Neither old page/feature id "intrusion"/"protection_settings" was
# renamed - see feature_config.py's own comment on why - so an old
# project.json needs no migration for either group.
NAV_STRUCTURE = [
    ("main_view_group", "nav.main_view", True, [
        ("main_view", "nav.main_diagram", None),
    ]),
    ("control_group", "nav.group_control", False, [
        ("digital_inputs", "nav.digital_inputs", None),
        ("analog_inputs", "nav.analog_inputs", "analog_inputs"),
        ("control_outputs", "nav.control_outputs", None),
    ]),
    ("intrusion_group", "nav.intrusion", False, [
        ("intrusion_overview", "nav.intrusion_overview", "intrusion"),
        ("intrusion_history", "nav.intrusion_history", "intrusion_history"),
        ("intrusion_config", "nav.intrusion_config", "intrusion_config"),
    ]),
    ("measurements_group", "nav.group_measurements", False, [
        ("power_quality", "nav.power_quality", "power_quality"),
        ("trends", "nav.trends", "trends"),
    ]),
    ("events_group", "nav.group_events", False, [
        ("events", "nav.event_recorder", None),
        ("alarms", "nav.alarms", None),
        ("audit_log", "nav.audit_log", None),
    ]),
    ("diagnostics_group", "nav.group_diagnostics", False, [
        ("system_topology", "nav.system_topology", "system_topology"),
        ("bus_diagnostics", "nav.bus_diagnostics", "bus_diagnostics"),
        ("engineer_mode", "nav.engineer_mode", "engineer_mode"),
    ]),
    ("protection_settings_group", "nav.group_protection", False, [
        ("protection_electrical", "nav.protection_electrical", "protection_settings"),
        ("protection_process", "nav.protection_process", "protection_process"),
    ]),
]


class NavNode:
    """One row the tree will render - either `kind="group"` (has
    `children`, a list of NavNode leaves) or `kind="leaf"` (has
    `page_id`, the stacked-widget page to switch to)."""
    __slots__ = ("kind", "id", "title_key", "page_id", "children")

    def __init__(self, kind, id, title_key, page_id=None, children=None):
        self.kind = kind
        self.id = id
        self.title_key = title_key
        self.page_id = page_id
        self.children = children or []

    def __repr__(self):
        if self.kind == "leaf":
            return f"NavNode(leaf, id={self.id!r}, page_id={self.page_id!r})"
        return f"NavNode(group, id={self.id!r}, children={[c.id for c in self.children]!r})"


def engineer_mode_available(enabled_features: dict) -> bool:
    """Task's own list has "Tryb inzyniera" and "Nastawy zabezpieczen"
    as two INDEPENDENTLY togglable features - but Engineer Mode's own
    verification page (page_engineer_mode.py) is wired to run its
    checks against the SAME ProtectionManager instance the Elektryczne
    page configures (main_window.py: `PageEngineerMode(...,
    self.page_protection_electrical.protection_manager, ...)` - the
    page-split task's own successor to
    `self.page_protection.protection_manager`, same instance/class,
    just constructed by a differently-named page now), unguarded. Two
    ways to resolve that dependency were considered: (a) give Engineer
    Mode its own, separate ProtectionManager when Protection Settings
    is off, or (b) treat Engineer Mode as implicitly requiring
    Protection Settings. (a) was rejected - Engineer Mode's whole
    purpose is verifying the ACTUAL configured protection settings; a
    silently-blank ProtectionManager would let it report a passing
    verification against nothing, which is worse than not offering the
    page at all. This function is (b): Engineer Mode is only ever
    considered available when Protection Settings is ALSO enabled,
    regardless of its own toggle - enforced here (not just in the
    dialog) so a direct call bypassing the UI can't produce it either.
    The feature-config dialog greys out/explains this, see
    feature_config_dialog.py."""
    from epw_os.core.feature_config import is_feature_enabled
    return is_feature_enabled(enabled_features, "protection_settings")


def intrusion_subpage_available(enabled_features: dict) -> bool:
    """Podglad/Historia zdarzen/Konfiguracja (SYSTEM ALARMOWY's three
    pages) all read the SAME live IntrusionManager instance - each one
    meaningless once the whole module itself ("intrusion") is off,
    regardless of its own sub-toggle. Same dependency shape
    engineer_mode_available() above already established; Podglad
    itself needs no separate check here since it reuses the "intrusion"
    feature id directly (see nav_model.py's own module docstring)."""
    from epw_os.core.feature_config import is_feature_enabled
    return is_feature_enabled(enabled_features, "intrusion")


def protection_subpage_available(enabled_features: dict) -> bool:
    """Placeholder for symmetry with intrusion_subpage_available() -
    currently unused: neither ZABEZPIECZENIA page needs it. Elektryczne
    reuses the "protection_settings" feature id directly (see module
    docstring); Procesowe is deliberately independent (see module
    docstring's SUB-PAGE DEPENDENCY section) since ProcessProtectionManager
    shares no instance with the electrical side. Kept as a named,
    documented no-op rather than silently having no equivalent at all,
    in case a later Zabezpieczenia sub-page DOES need this dependency."""
    from epw_os.core.feature_config import is_feature_enabled
    return is_feature_enabled(enabled_features, "protection_settings")


def build_nav_tree(enabled_features: dict) -> list:
    """The one function that turns NAV_STRUCTURE + a feature
    configuration into what the tree should actually show right now:
    - a page whose feature is disabled is dropped entirely
    - a group left with zero pages is dropped entirely (Task 3: "grupa,
      w ktorej wszystkie strony sa wylaczone, ZNIKA calkowicie")
    - a group left with exactly one page collapses to a flat leaf,
      UNLESS it's marked always_expand (see module docstring)
    - Engineer Mode is ALSO dropped whenever Protection Settings is
      off, regardless of its own toggle - see engineer_mode_available().
    - Historia zdarzen/Konfiguracja (SYSTEM ALARMOWY) are ALSO dropped
      whenever "intrusion" itself is off, regardless of their own
      toggle - see intrusion_subpage_available().
    Returns a list of NavNode (groups and/or bare leaves, in
    NAV_STRUCTURE's own order - see that list's own docstring section
    for why the order itself isn't yet independently configurable)."""
    from epw_os.core.feature_config import is_feature_enabled

    engineer_mode_ok = engineer_mode_available(enabled_features)
    intrusion_subpage_ok = intrusion_subpage_available(enabled_features)
    result = []
    for group_id, group_title_key, always_expand, pages in NAV_STRUCTURE:
        visible_pages = [
            (page_id, title_key) for page_id, title_key, feature in pages
            if (feature is None or is_feature_enabled(enabled_features, feature))
            and (feature != "engineer_mode" or engineer_mode_ok)
            and (feature not in ("intrusion_history", "intrusion_config") or intrusion_subpage_ok)
        ]
        if not visible_pages:
            continue
        if len(visible_pages) == 1 and not always_expand:
            page_id, _page_title_key = visible_pages[0]
            # Collapsed: the GROUP's own label is what's shown (see
            # module docstring) - the page's own narrower title_key is
            # discarded here, not the group's.
            result.append(NavNode("leaf", group_id, group_title_key, page_id=page_id))
        else:
            children = [
                NavNode("leaf", page_id, title_key, page_id=page_id)
                for page_id, title_key in visible_pages
            ]
            result.append(NavNode("group", group_id, group_title_key, children=children))
    return result


def first_page_id(node: "NavNode") -> "str | None":
    """The page a click on a GROUP's own name/row should open (Task 3:
    "kliknieciem w NAZWE GRUPY otwiera pierwsza dostepna strone... a nie
    tylko rozwija"). For a leaf, that's simply its own page."""
    if node.kind == "leaf":
        return node.page_id
    return node.children[0].page_id if node.children else None


def all_page_ids() -> list:
    """Every page id NAV_STRUCTURE knows about, regardless of feature
    state - used to build the always-present QStackedWidget index map
    is NOT this (pages are only constructed when enabled - see
    main_window.py), but tests and the feature-config dialog both need
    the full universe of page ids at least once."""
    return [page_id for _gid, _title, _exp, pages in NAV_STRUCTURE for page_id, _t, _f in pages]
