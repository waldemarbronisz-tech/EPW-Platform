"""Task „runtime czyta projekt.epw", punkt 3, on the panel: the Synoptic
page offers the project's screens, draws the chosen one, and comes back to
it after a restart (runtime_state.json, not the project file).
"""
from gui_smoke._mocks import MockTagManager


class _ProjectWithScreens:
    """Only what PageSynoptic reads from a project manager."""

    def __init__(self, document, remembered=None):
        self.document = document
        self.remembered = remembered
        self.written = []

    def get_embedded_screens(self):
        return self.document

    def get_analog_points(self):
        return []

    def get_last_synoptic_screen(self):
        return self.remembered

    def set_last_synoptic_screen(self, screen_id):
        self.remembered = screen_id
        self.written.append(screen_id)
        return True


def _document():
    def screen_content(objects, walls=()):
        return {"objects": list(objects), "connections": [], "meters": [], "signalPanels": [], "frames": [],
                "walls": list(walls), "rooms": [], "groupCommands": [], "setpointPanels": []}

    def obj(id_, type_, x, y):
        return {"id": id_, "type": type_, "category": "X", "x": x, "y": y, "rotation": 0, "scaleX": 1, "scaleY": 1,
                "visible": True, "locked": False, "layer": 1, "tag": "", "description": "", "color": "", "fill": "",
                "border": "", "text": "", "font": "Tahoma", "fontSize": 13, "tooltip": "", "width": 64, "height": 64,
                "customProperties": {}}

    return {
        "format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "Kotłownia"},
        "canvas": {"width": 800, "height": 600},
        "screens": [{"id": "s1", "name": "Rozdzielnia"}, {"id": "s2", "name": "Kotłownia - plan"}],
        "activeScreenId": "s1",
        "objects": [obj("q1", "electrical.circuit_breaker", 100, 100)],
        "connections": [], "walls": [], "devices": [],
        "screenContents": {"s2": screen_content([obj("p1", "water.pump", 200, 200)])},
    }


def _page(project_manager, qapp):
    from epw_os.gui.synoptic.page_synoptic import PageSynoptic
    return PageSynoptic(MockTagManager(), project_manager=project_manager)


def _drawn_object_ids(page):
    document = page.screen.document
    return [o.get("id") for o in document.project.objects] if document is not None else []


def test_the_page_lists_every_screen_and_opens_the_one_the_editor_left_active(qapp):
    page = _page(_ProjectWithScreens(_document()), qapp)

    assert page.screen_row.isVisibleTo(page)
    assert [page.screen_selector.itemText(i) for i in range(page.screen_selector.count())] == [
        "Rozdzielnia", "Kotłownia - plan"]
    assert page.screen_selector.currentData() == "s1"
    assert _drawn_object_ids(page) == ["q1"]
    page.deleteLater()


def test_switching_the_screen_redraws_it_and_writes_the_choice_to_the_state(qapp):
    project_manager = _ProjectWithScreens(_document())
    page = _page(project_manager, qapp)

    page.screen_selector.setCurrentIndex(1)

    assert _drawn_object_ids(page) == ["p1"]
    assert project_manager.written == ["s2"]  # written when switched, not on the initial draw
    page.deleteLater()


def test_the_screen_open_before_a_restart_comes_back(qapp):
    project_manager = _ProjectWithScreens(_document(), remembered="s2")
    page = _page(project_manager, qapp)

    assert page.screen_selector.currentData() == "s2"
    assert _drawn_object_ids(page) == ["p1"]
    assert project_manager.written == []  # restoring is not a new choice to store
    page.deleteLater()


def test_a_remembered_screen_the_project_no_longer_has_falls_back_to_the_active_one(qapp):
    project_manager = _ProjectWithScreens(_document(), remembered="skasowany")
    page = _page(project_manager, qapp)

    assert page.screen_selector.currentData() == "s1"
    assert _drawn_object_ids(page) == ["q1"]
    page.deleteLater()


def test_a_single_screen_project_hides_the_switcher(qapp):
    document = _document()
    document.pop("screens")
    document.pop("screenContents")
    page = _page(_ProjectWithScreens(document), qapp)

    assert not page.screen_row.isVisibleTo(page)
    assert _drawn_object_ids(page) == ["q1"]
    page.deleteLater()
