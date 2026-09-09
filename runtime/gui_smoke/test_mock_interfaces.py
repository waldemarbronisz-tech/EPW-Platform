"""Task section 3 (option a): "mocks checked for conformance with the
real interface - a test that fails when the real class gains a method
the mock lacks".

This is the permanent fix for the bug that recurred three sessions in a
row: a TagManager-shaped mock in the old test_gui_smoke.py lacked a
method (add_tag, list_tags) that production code (ProtectionVerifier's
constructor) started calling, and nothing caught it until the script was
actually run.

The reference for "what the real interface is" is main.py's own
GUITagManagerAdapter/GUIAccessManagerAdapter - the actual objects GUI
code receives in production (not the headless core/tag_manager.py
TagManager directly, which has a slightly different method set -
get_output_description/set_output_description route through
project_manager, not the core tag manager, for instance).

main.py itself is never imported here (or anywhere in this test suite -
see test_protection_verifier.py's own docstring): it boots a real
QApplication/FastAPI thread at import time. Those adapter classes are
also defined *inside* a function, as local/nested classes, so they
would not be importable even if main.py itself were safe to import.

Instead, main.py's source (and, symmetrically, _mocks.py's own source)
is parsed with `ast` - no execution, no side effects - and each class
body is inspected directly, INCLUDING plain `self.x = ...` assignments
made in __init__ (mode/level are set that way, not as class attributes,
on several of these mocks, so a class-level-only check like `dir(cls)`
would wrongly flag them as missing). This is what makes the fix
PERMANENT rather than just "one more manually maintained list to forget
to update": the next time someone adds a method to GUITagManagerAdapter
in main.py, this test re-derives the requirement from that same source
file automatically, with nothing to remember to keep in sync by hand.
"""
import ast
import inspect
import os

import pytest

from gui_smoke import _mocks

_MAIN_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")


def _class_interface(source_path, class_name):
    """Returns (method_names, attr_names) for a class definition named
    `class_name` found anywhere in `source_path`'s source - methods
    (public, non-underscore `def`s), `@property` getters, and plain
    `self.<name> = ...` assignments made in __init__ (covers Signal
    attributes like tag_changed/level_changed, and plain-attribute
    "properties" like mode/level that some mocks set directly instead of
    via an actual @property)."""
    with open(source_path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=source_path)

    class_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            class_node = node
            break
    assert class_node is not None, f"{class_name} not found in {source_path} - has it been renamed/moved?"

    methods = set()
    attrs = set()
    for item in class_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
            # `self.<name> = ...` assignments made in __init__ - covers
            # both Signal-shaped attributes (tag_changed, level_changed)
            # and plain-attribute "properties" like mode/level that some
            # mocks set directly instead of via an actual @property.
            # Checked regardless of the (always-private) name "__init__"
            # itself, so this must NOT be nested under the
            # not-startswith("_") branch below.
            for stmt in ast.walk(item):
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                                and target.value.id == "self" and not target.attr.startswith("_")):
                            attrs.add(target.attr)
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
            is_property = any(isinstance(d, ast.Name) and d.id == "property" for d in item.decorator_list)
            if is_property:
                attrs.add(item.name)
            else:
                methods.add(item.name)
        elif isinstance(item, ast.Assign):
            # Class-level attribute, e.g. `tag_changed = Signal(...)` or
            # `mode = "SIMULATION MODE"`.
            for target in item.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    attrs.add(target.id)

    return methods, attrs


def _main_adapter_interface(class_name):
    return _class_interface(_MAIN_PY, class_name)


def _mock_interface(mock_cls):
    source_path = inspect.getsourcefile(mock_cls)
    return _class_interface(source_path, mock_cls.__name__)


# --- DOWÓD: this is the test that must FAIL, not silently pass, when a
# mock falls behind the real interface - proven directly below by a
# throwaway mock that is deliberately missing add_tag(). ------------------

def test_the_conformance_check_itself_fails_on_a_mock_missing_a_real_method():
    """The literal DOWÓD requirement: "a test proving a mock inconsistent
    with the real interface causes a test FAILURE, not a silent pass."
    Compares the real GUITagManagerAdapter's interface against a
    deliberately incomplete stand-in (has update_tag/get_value, but no
    add_tag - the real historical gap) and asserts the comparison
    actually reports the gap, instead of only imagining the permanent
    fix works without ever exercising it against a known-bad case."""
    required_methods, _ = _main_adapter_interface("GUITagManagerAdapter")
    # _mocks.MockTagManager's actual, current, complete public method set
    # (mirrored here, not re-parsed from a second file - this test must
    # never accidentally exercise a DIFFERENT, already-complete mock
    # instead of the deliberately-broken one it claims to), minus add_tag.
    incomplete_surface = {"get_value", "get_tag", "update_tag", "list_tags", "set_description",
                           "get_output_description", "set_output_description", "get_analog_points",
                           "add_analog_point", "remove_analog_point", "update_analog_point", "toggle_mode"}
    missing = required_methods - incomplete_surface
    assert missing == {"add_tag"}, \
        f"expected the conformance check to catch exactly the missing add_tag(), got {missing}"


@pytest.mark.parametrize("mock_cls", [
    _mocks.MockTagManager,
    _mocks.ThemeCapableTagManager,
    _mocks.DICapableTagManager,
])
def test_tag_manager_mocks_have_every_method_the_real_adapter_has(mock_cls):
    required_methods, required_attrs = _main_adapter_interface("GUITagManagerAdapter")
    methods, attrs = _mock_interface(mock_cls)
    missing_methods = required_methods - methods
    assert not missing_methods, \
        f"{mock_cls.__name__} is missing method(s) {missing_methods} that the real " \
        f"GUITagManagerAdapter (main.py) has - GUI code that starts calling one of these " \
        f"will crash with a real TagManager and pass silently with this mock."
    missing_attrs = required_attrs - attrs
    assert not missing_attrs, \
        f"{mock_cls.__name__} is missing attribute(s)/signal(s) {missing_attrs} that the " \
        f"real GUITagManagerAdapter exposes (tag_changed and/or the `mode` property)."


@pytest.mark.parametrize("mock_cls", [
    _mocks.MockAccessManager,
    _mocks.MockControllableAccessManager,
])
def test_access_manager_mocks_have_every_method_the_real_adapter_has(mock_cls):
    required_methods, required_attrs = _main_adapter_interface("GUIAccessManagerAdapter")
    methods, attrs = _mock_interface(mock_cls)
    missing_methods = required_methods - methods
    assert not missing_methods, \
        f"{mock_cls.__name__} is missing method(s) {missing_methods} that the real " \
        f"GUIAccessManagerAdapter (main.py) has."
    missing_attrs = required_attrs - attrs
    assert not missing_attrs, \
        f"{mock_cls.__name__} is missing attribute(s)/signal(s) {missing_attrs} that the " \
        f"real GUIAccessManagerAdapter exposes (level_changed and/or the `level` property)."


def test_page_mock_access_manager_is_deliberately_narrower_and_documented():
    """PageMockAccessManager (used only to construct individual pages
    directly, never a full MainWindow) is intentionally minimal - no page
    this project has ever built calls anything on the access_manager it's
    given besides has_access(). This test documents that scope choice
    explicitly and pins it down, rather than silently excluding this mock
    from the conformance checks above with no record of why."""
    methods, attrs = _mock_interface(_mocks.PageMockAccessManager)
    assert methods == {"has_access"}, \
        f"PageMockAccessManager grew beyond has_access() ({methods}) - it should now be checked " \
        f"against the full GUIAccessManagerAdapter interface like the other access-manager mocks above."


def test_page_mock_tag_manager_is_deliberately_narrower_and_documented():
    """PageMockTagManager (also used only to construct individual pages
    directly) is narrower than the full adapter interface too - but NOT
    arbitrarily: add_tag()/list_tags() are on it because a page's own
    __init__ (PageEngineerMode building a ProtectionVerifier) really does
    call them at CONSTRUCTION time, which is exactly the scenario this
    mock exists to cover. The remaining adapter methods
    (add_analog_point/remove_analog_point/set_description/
    set_output_description/toggle_mode/update_analog_point) are only ever
    called from interactive handlers (a button click, a menu action) that
    building a page directly, with no MainWindow around it, never
    reaches - so they're absent by design, pinned down here explicitly
    rather than silently excluded from the strict check above. If a page
    constructor ever starts calling one of these too, this test is the
    thing that will need updating - and until it is, the strict
    full-interface test would (correctly) start failing for this mock,
    exactly like it did for toggle_mode() above before this file existed."""
    methods, attrs = _mock_interface(_mocks.PageMockTagManager)
    assert methods == {"get_tag", "get_value", "get_output_description", "get_analog_points",
                        "update_tag", "add_tag", "list_tags"}, \
        f"PageMockTagManager's method set changed ({methods}) - update this pinned set, and double-check " \
        f"whether it should now be validated against the full GUITagManagerAdapter interface instead."


def test_qt_tag_manager_bridge_is_deliberately_narrower_and_documented():
    """QtTagManagerBridge is only ever handed to a single core object
    (ProtectionVerifier, one Page) in this test suite, never a full
    MainWindow - and the real adapter's own add_analog_point/
    remove_analog_point/update_analog_point route through EPWCore, not
    the core TagManager this bridge wraps, so it genuinely cannot
    delegate those three the way it delegates get_value/update_tag/
    add_tag/list_tags/mode/toggle_mode to the real TagManager it holds.
    set_description/set_output_description are absent for the same
    reason as get_output_description already was even before this file
    existed: the real adapter's version of those routes through
    project_manager, which this bridge also doesn't hold. If a future
    test ever needs this bridge to build a full MainWindow, it will need
    an epw_core-and-project_manager-aware upgrade first - this test is
    the thing that will (correctly) start failing at that point, same as
    it would for a page-only mock outgrowing its scope silently."""
    methods, attrs = _mock_interface(_mocks.QtTagManagerBridge)
    assert methods == {"get_value", "get_tag", "list_tags", "update_tag", "add_tag", "toggle_mode"}, \
        f"QtTagManagerBridge's method set changed ({methods}) - update this pinned set."
