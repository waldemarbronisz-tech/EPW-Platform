"""Task "Studio osadza ekrany i logikę w projekt.epw" - user report:
"tworząc synoptykę w projekcie i zapisując projekt na głównym pasku,
synoptyka nie zapisuje się, podejrzewam że to samo jest z logiką - dalej
to traktowane jest jako osobne programy".

Studio's own Save (the top toolbar) now pulls the Logic and Synoptic
documents into projekt.epw, Open/New hand them back to the editors, and
unsaved editor work counts as unsaved project work. The Logic editor is
the real embedded Logic Studio; the Synoptic page (a QWebEngineView) is
stood in for by a fake with the same three bridge methods, so this runs
offscreen without Chromium - synoptic_panel.py's own methods are one-line
JS calls whose JS half is covered by Synoptic's own
studio-bridge-project-document.test.ts.
"""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import load_project


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


SCREENS = {"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "S"},
           "canvas": {"width": 1920, "height": 1080, "background": "#00CFCF", "gridSize": 16},
           "objects": [{"id": "o1", "type": "water.ball_valve"}]}


class _FakeSynopticPanel:
    """query_project_data()/load_project_data()/mark_saved() exactly as
    SynopticPanel exposes them, plus is_page_ready()."""

    def __init__(self, document=SCREENS, ready=True):
        self.document = document
        self.ready = ready
        self.loaded = []
        self.saved_as = []

    def is_page_ready(self):
        return self.ready

    def is_page_pending(self):
        return False

    def query_project_data(self, callback):
        callback(self.document)

    def load_project_data(self, document, name):
        self.loaded.append((document, name))

    def mark_saved(self, name):
        self.saved_as.append(name)

    def query_state(self, callback):
        callback({"isDirty": False, "canUndo": False, "canRedo": False, "hasSelection": False})


def _with_logic_block(win):
    """One real block in the embedded Logic Studio, so the logic document
    has something to lose."""
    mw = win._logic_panel.main_window()
    from logic_studio.blocks.registry import BlockRegistry
    block = BlockRegistry.create_block("logic.and")
    mw.project.add_block(block)
    mw.set_dirty()
    return block


def test_save_on_the_top_toolbar_embeds_both_editors_documents(tmp_path, monkeypatch):
    _app()
    win = _window(tmp_path)
    win._ensure_logic_panel()
    win._synoptic_panel = _FakeSynopticPanel()
    _with_logic_block(win)
    path = tmp_path / "projekt.epw"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(path), "")))

    win.act_shared_save.trigger()

    saved = load_project(path)
    assert saved.screens == SCREENS
    assert [b["type_id"] for b in saved.logic["blocks"]] == ["logic.and"]
    assert saved.logic_runtime.get("format") == "EPW_RUNTIME_LOGIC"
    # both editors are clean now - the project file holds their work
    assert win._logic_panel.is_dirty() is False
    assert win._synoptic_panel.saved_as == [win._project.metadata.name]


def test_open_hands_the_documents_back_to_the_editors(tmp_path, monkeypatch):
    _app()
    win = _window(tmp_path)
    win._ensure_logic_panel()
    win._synoptic_panel = _FakeSynopticPanel()
    _with_logic_block(win)
    path = tmp_path / "projekt.epw"
    win._project_path = str(path)
    win._save_project()

    # a fresh window, a different fake page: Open must restore both
    win2 = _window(tmp_path)
    win2._ensure_logic_panel()
    fake = _FakeSynopticPanel(document=None)
    win2._synoptic_panel = fake
    assert win2._logic_panel.main_window().project.blocks == []
    win2._load_project_from_path(str(path))

    assert [b.type_id for b in win2._logic_panel.main_window().project.blocks] == ["logic.and"]
    assert fake.loaded[-1] == (SCREENS, win2._project.metadata.name)
    assert win2._logic_panel.is_dirty() is False


def test_new_project_clears_both_editors(tmp_path, monkeypatch):
    _app()
    win = _window(tmp_path)
    win._ensure_logic_panel()
    fake = _FakeSynopticPanel()
    win._synoptic_panel = fake
    _with_logic_block(win)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard))

    win.act_shared_new.trigger()

    assert win._logic_panel.main_window().project.blocks == []
    assert fake.loaded[-1][0] == {}  # an empty section = a fresh screen project


def test_unsaved_logic_counts_as_unsaved_project_work(tmp_path, monkeypatch):
    _app()
    win = _window(tmp_path)
    win._ensure_logic_panel()
    win._synoptic_panel = _FakeSynopticPanel()
    win._project.is_dirty = False  # new_project() itself starts dirty - not what this test is about
    assert win._confirm_discard_project() is True  # nothing to lose
    _with_logic_block(win)
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: asked.append(1) or QMessageBox.StandardButton.Cancel))
    assert win._confirm_discard_project() is False
    assert asked == [1]
    win._on_project_changed()
    assert win._status_project.text().endswith("*")


def test_a_page_that_is_not_up_keeps_the_previously_saved_screens(tmp_path):
    """Nothing was edited on a page that never loaded - saving must not
    wipe the screens the file already had."""
    _app()
    win = _window(tmp_path)
    win._project.screens = SCREENS
    win._synoptic_panel = _FakeSynopticPanel(document=None, ready=False)
    path = tmp_path / "projekt.epw"
    win._project_path = str(path)
    assert win._save_project() is True
    assert load_project(path).screens == SCREENS


def test_a_refused_synoptic_document_asks_before_saving_without_it(tmp_path, monkeypatch):
    _app()
    win = _window(tmp_path)
    win._project.screens = SCREENS
    win._synoptic_panel = _FakeSynopticPanel(document=None, ready=True)  # validation refused
    path = tmp_path / "projekt.epw"
    win._project_path = str(path)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel))
    assert win._save_project() is False
    assert not path.exists()
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    assert win._save_project() is True
    assert load_project(path).screens == SCREENS  # the previous screens, kept
