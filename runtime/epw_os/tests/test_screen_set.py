"""Task „runtime czyta projekt.epw", punkt 3: a project carries several
screens, not one.

The editor keeps them in one document - `screens` (identity and switching
order), `activeScreenId`, and `screenContents` for every screen except the
active one, whose content sits at the top level. These tests pin what
runtime makes of that: the list it offers, and the document it hands the
reader for one chosen screen - with the shared registries (devices,
locations, cards) untouched, because those belong to the project, not to
a screen.
"""
from epw_os.core.screen_set import active_screen_id, has_screen, screen_document, screen_list


def _document():
    return {
        "format": "EPW_SYNOPTIC", "schema_version": 2,
        "project": {"name": "Kotłownia"},
        "canvas": {"width": 800, "height": 600},
        "screens": [{"id": "s1", "name": "Parter"}, {"id": "s2", "name": "Piętro"}, {"id": "s3", "name": ""}],
        "activeScreenId": "s1",
        "objects": [{"id": "q1", "type": "electrical.circuit_breaker"}],
        "walls": [{"id": "w1", "from": {"x": 0, "y": 0}, "to": {"x": 10, "y": 0}}],
        "connections": [{"id": "c1", "points": []}],
        "devices": [{"id": "KOT_Q1", "behavior": "SWITCHED"}],
        "locations": [{"code": "KOT"}],
        "screenContents": {
            "s2": {"objects": [{"id": "p1", "type": "water.pump"}], "connections": [], "meters": [],
                   "signalPanels": [], "frames": [], "walls": [], "rooms": [], "groupCommands": [],
                   "setpointPanels": []},
            "s3": {"objects": [], "connections": [], "meters": [], "signalPanels": [], "frames": [],
                   "walls": [{"id": "w9", "from": {"x": 0, "y": 0}, "to": {"x": 99, "y": 0}}], "rooms": [],
                   "groupCommands": [], "setpointPanels": []},
        },
    }


def test_the_screen_list_keeps_the_editors_order_and_falls_back_to_the_id_for_an_unnamed_screen():
    assert screen_list(_document()) == [
        {"id": "s1", "name": "Parter"}, {"id": "s2", "name": "Piętro"}, {"id": "s3", "name": "s3"}]
    assert active_screen_id(_document()) == "s1"
    assert has_screen(_document(), "s2") and not has_screen(_document(), "s9")


def test_a_document_from_before_multi_screen_is_one_screen_named_after_the_project():
    document = {"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "Hala"},
                "objects": [{"id": "a"}]}
    assert screen_list(document) == [{"id": "", "name": "Hala"}]
    assert screen_document(document, "") is document


def test_switching_to_another_screen_swaps_the_content_and_keeps_the_project_registries():
    document = _document()
    second = screen_document(document, "s2")

    assert [o["id"] for o in second["objects"]] == ["p1"]
    assert second["walls"] == []                      # that screen has no walls of its own
    assert second["devices"] == document["devices"]   # registries are project-wide
    assert second["locations"] == document["locations"]
    assert second["canvas"] == document["canvas"]
    assert second["activeScreenId"] == "s2"
    # the document the caller passed in is not mutated
    assert [o["id"] for o in document["objects"]] == ["q1"]


def test_the_active_screen_and_an_unknown_id_give_the_document_as_it_stands():
    document = _document()
    assert screen_document(document, "s1") is document
    assert screen_document(document, "nie-ma-takiego") is document
    assert screen_document(document, "") is document


def test_a_screen_whose_content_is_missing_or_damaged_does_not_raise():
    document = _document()
    document["screenContents"] = {"s2": "to nie jest ekran"}
    assert screen_document(document, "s2") is document

    document["screens"] = "też nie"
    # the list is gone, but activeScreenId still names the screen on the table
    assert screen_list(document) == [{"id": "s1", "name": "Kotłownia"}]
    assert screen_list(None) == []
    assert screen_document(None, "s1") == {}
    assert active_screen_id("nonsens") == ""


def test_a_screen_that_only_declares_walls_replaces_the_objects_it_does_not_have():
    third = screen_document(_document(), "s3")
    assert third["objects"] == []
    assert [w["id"] for w in third["walls"]] == ["w9"]
