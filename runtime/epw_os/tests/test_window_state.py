"""Tests for window size/maximized persistence (epw_os/gui/window_state)."""

import importlib
import json

import pytest

from epw_os.gui import window_state


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    path = tmp_path / "window_state.local.json"
    monkeypatch.setattr(window_state, "_STATE_PATH", str(path))
    return path


def test_load_returns_defaults_when_no_file(isolated_state):
    st = window_state.load()
    assert st == {
        "width": window_state.DEFAULT_WIDTH,
        "height": window_state.DEFAULT_HEIGHT,
        "maximized": False,
    }


def test_save_then_load_roundtrip(isolated_state):
    window_state.save(1600, 900, True)
    st = window_state.load()
    assert st == {"width": 1600, "height": 900, "maximized": True}
    on_disk = json.loads(isolated_state.read_text(encoding="utf-8"))
    assert on_disk == {"width": 1600, "height": 900, "maximized": True}


def test_corrupt_file_falls_back_to_defaults(isolated_state):
    isolated_state.write_text("{ not json", encoding="utf-8")
    st = window_state.load()
    assert st["width"] == window_state.DEFAULT_WIDTH
    assert st["maximized"] is False


def test_tiny_persisted_size_is_clamped_to_minimum(isolated_state):
    window_state.save(50, 40, False)
    st = window_state.load()
    assert st["width"] >= window_state.MIN_WIDTH
    assert st["height"] >= window_state.MIN_HEIGHT


def test_partial_file_uses_defaults_for_missing_keys(isolated_state):
    isolated_state.write_text(json.dumps({"width": 1280}), encoding="utf-8")
    st = window_state.load()
    assert st["width"] == 1280
    assert st["height"] == window_state.DEFAULT_HEIGHT
    assert st["maximized"] is False


# --- Recent projects (Task: Project menu > "Recently opened") --------------

def test_recent_projects_empty_by_default(isolated_state):
    assert window_state.load_recent_projects() == []


def test_add_recent_project_survives_reload(isolated_state):
    # DOWÓD: "lista przezywa restart programu" - there is no in-memory
    # cache anywhere in this module, only the file itself, so a fresh
    # load_recent_projects() call already IS "as if the app restarted".
    window_state.add_recent_project("/path/to/a.json")
    assert window_state.load_recent_projects() == ["/path/to/a.json"]
    on_disk = json.loads(isolated_state.read_text(encoding="utf-8"))
    assert on_disk["recent_projects"] == ["/path/to/a.json"]


def test_add_recent_project_newest_first(isolated_state):
    window_state.add_recent_project("/a.json")
    window_state.add_recent_project("/b.json")
    window_state.add_recent_project("/c.json")
    assert window_state.load_recent_projects() == ["/c.json", "/b.json", "/a.json"]


def test_add_recent_project_moves_existing_entry_to_front(isolated_state):
    window_state.add_recent_project("/a.json")
    window_state.add_recent_project("/b.json")
    window_state.add_recent_project("/a.json")
    assert window_state.load_recent_projects() == ["/a.json", "/b.json"], \
        "re-opening an already-listed project must move it to the front, not duplicate it"


def test_recent_projects_list_is_capped_at_ten(isolated_state):
    assert window_state.MAX_RECENT_PROJECTS == 10
    for i in range(window_state.MAX_RECENT_PROJECTS + 5):
        window_state.add_recent_project(f"/p{i}.json")
    paths = window_state.load_recent_projects()
    assert len(paths) == window_state.MAX_RECENT_PROJECTS
    assert paths[0] == f"/p{window_state.MAX_RECENT_PROJECTS + 4}.json"


def test_clear_recent_projects(isolated_state):
    window_state.add_recent_project("/a.json")
    window_state.clear_recent_projects()
    assert window_state.load_recent_projects() == []


def test_recent_projects_corrupt_value_falls_back_to_empty(isolated_state):
    isolated_state.write_text(json.dumps({"recent_projects": "not-a-list"}), encoding="utf-8")
    assert window_state.load_recent_projects() == []


# --- Visual theme (Task: przelaczane motywy wizualne) -----------------

def test_theme_index_defaults_to_industrial_when_no_file(isolated_state):
    from epw_os.core.themes import DEFAULT_THEME_INDEX
    assert window_state.load_theme_index() == DEFAULT_THEME_INDEX == 0


def test_theme_index_save_then_load_roundtrip(isolated_state):
    # DOWÓD: "wybrany motyw przezywa restart programu" - like recent
    # projects above, there is no in-memory cache here, only the file
    # itself, so a fresh load_theme_index() call already IS "as if the
    # app restarted".
    window_state.save_theme_index(3)
    assert window_state.load_theme_index() == 3
    on_disk = json.loads(isolated_state.read_text(encoding="utf-8"))
    assert on_disk["theme_index"] == 3


def test_theme_index_corrupt_value_falls_back_to_default(isolated_state):
    isolated_state.write_text(json.dumps({"theme_index": "not-a-number"}), encoding="utf-8")
    assert window_state.load_theme_index() == 0


def test_theme_index_out_of_range_falls_back_to_default(isolated_state):
    isolated_state.write_text(json.dumps({"theme_index": 99}), encoding="utf-8")
    assert window_state.load_theme_index() == 0


def test_theme_index_shares_the_file_with_window_geometry(isolated_state):
    window_state.save(1600, 900, True)
    window_state.save_theme_index(2)
    assert window_state.load() == {"width": 1600, "height": 900, "maximized": True}
    assert window_state.load_theme_index() == 2


def test_recent_projects_share_the_file_with_window_geometry(isolated_state):
    """Same merge-onto-whatever-else-is-there contract as
    load()/save_screen_sleep_minutes()/etc above - adding a recent
    project must not clobber unrelated settings already in the file."""
    window_state.save(1600, 900, True)
    window_state.add_recent_project("/a.json")
    assert window_state.load() == {"width": 1600, "height": 900, "maximized": True}
    assert window_state.load_recent_projects() == ["/a.json"]


# --- navigation tree expand/collapse state (Task: "stan rozwiniecia
# zapamietywany miedzy uruchomieniami (wzorzec window_state.py)") -------

def test_nav_tree_expanded_returns_empty_dict_when_no_file(isolated_state):
    """An empty dict, not defaults per group - nav_tree.py itself
    decides what an unmentioned group id defaults to (expanded), not
    this module (see its own docstring)."""
    assert window_state.load_nav_tree_expanded() == {}


def test_nav_tree_expanded_save_then_load_roundtrip(isolated_state):
    window_state.save_nav_tree_expanded({"control_group": False, "measurements_group": True})
    assert window_state.load_nav_tree_expanded() == {"control_group": False, "measurements_group": True}
    on_disk = json.loads(isolated_state.read_text(encoding="utf-8"))
    assert on_disk["nav_tree_expanded"] == {"control_group": False, "measurements_group": True}


def test_nav_tree_expanded_corrupt_value_falls_back_to_empty(isolated_state):
    isolated_state.write_text(json.dumps({"nav_tree_expanded": "not-a-dict"}), encoding="utf-8")
    assert window_state.load_nav_tree_expanded() == {}


def test_nav_tree_expanded_shares_the_file_with_window_geometry(isolated_state):
    window_state.save(1600, 900, True)
    window_state.save_nav_tree_expanded({"diagnostics_group": False})
    assert window_state.load() == {"width": 1600, "height": 900, "maximized": True}
    assert window_state.load_nav_tree_expanded() == {"diagnostics_group": False}
