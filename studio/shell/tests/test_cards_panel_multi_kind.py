"""User report: "karta ELA1 ma DI oraz AI, a karta ADA ma DO i AO" - a
real I/O module routinely carries more than one channel kind (an ELA
card with both digital and analog inputs; an ADA card with both digital
and analog outputs). Card.channel_kinds (shared/project_format.py) maps
every kind a card has to its OWN channel count - one Card row, one id,
one Modbus address, one location, however many kinds it has.

(An earlier version of this fix represented a mixed module as TWO Card
rows sharing an id, one per kind - abandoned once "adres modbus nie
wchodzi" surfaced: modbus_unit_id/location would have to be entered
twice and kept in sync by hand, for no reason the address grammar,
<id>.<KIND>.<channel> with KIND already its own segment, ever required.
See Card's own docstring for the full account.)

These tests exercise the real QWidget (same harness test_aspect_
container_reuse.py already established) - CardsPanel's own
_ChannelKindsEditor and its event handlers, not just the underlying
pure functions test_project_panels.py covers.

QMessageBox.warning() is monkeypatched everywhere below: unpatched, a
real modal dialog blocks forever under pytest-qt/offscreen with nothing
to click it away.
"""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from studio.shell.main_window import StudioMainWindow


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


def _no_dialogs(monkeypatch):
    calls = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: calls.append(a) or QMessageBox.StandardButton.Ok)
    return calls


def _set_cell(panel, row, col, text):
    panel.cards_table.item(row, col).setText(text)


def _check_kind(panel, row, kind, channels=None):
    """Drives the _ChannelKindsEditor exactly as a user click would -
    check the box, then (if given) set its own channel-count spinbox."""
    editor = panel.cards_table.cellWidget(row, 2)
    editor._checks[kind].setChecked(True)
    if channels is not None:
        editor._spins[kind].setValue(channels)


def _uncheck_kind(panel, row, kind):
    editor = panel.cards_table.cellWidget(row, 2)
    editor._checks[kind].setChecked(False)


def test_a_fresh_card_starts_with_no_kind_checked(tmp_path):
    """"We consequently assign, never suggest" - same stance the no-
    default-address fix for a freshly-placed DI/DO block already takes;
    add_card() must not guess a kind for a card the user hasn't
    configured yet."""
    _app()
    win = _window(tmp_path)
    win._open_io_cards()
    panel = win._cards_panel
    panel.add_card()
    assert win._project.cards[0].channel_kinds == {}


def test_checking_two_kinds_gives_one_card_both(tmp_path, monkeypatch):
    """The exact scenario from the report: ELA1 with both DI and AI, one
    row, one id."""
    calls = _no_dialogs(monkeypatch)
    _app()
    win = _window(tmp_path)
    win._open_io_cards()
    panel = win._cards_panel

    panel.add_card()
    _set_cell(panel, 0, 0, "ELA1")
    _check_kind(panel, 0, "DI", 8)
    _check_kind(panel, 0, "AI", 4)

    assert calls == []
    assert win._project.cards[0].id == "ELA1"
    assert win._project.cards[0].channel_kinds == {"DI": 8, "AI": 4}
    addresses = {p.address for p in win._project.points}
    assert addresses == {f"ELA1.DI.{n}" for n in range(1, 9)} | {f"ELA1.AI.{n}" for n in range(1, 5)}


def test_an_ada_card_may_have_both_do_and_ao(tmp_path, monkeypatch):
    calls = _no_dialogs(monkeypatch)
    _app()
    win = _window(tmp_path)
    win._open_io_cards()
    panel = win._cards_panel

    panel.add_card()
    _set_cell(panel, 0, 0, "ADA1")
    _check_kind(panel, 0, "DO", 16)
    _check_kind(panel, 0, "AO", 2)

    assert calls == []
    assert win._project.cards[0].channel_kinds == {"DO": 16, "AO": 2}


def test_one_modbus_unit_id_covers_every_kind_on_the_card(tmp_path, monkeypatch):
    """The problem the redesign exists to fix ("adres modbus nie
    wchodzi") - one field, entered once, not one per kind."""
    calls = _no_dialogs(monkeypatch)
    _app()
    win = _window(tmp_path)
    win._open_io_cards()
    panel = win._cards_panel

    panel.add_card()
    _set_cell(panel, 0, 0, "ELA1")
    _check_kind(panel, 0, "DI", 8)
    _check_kind(panel, 0, "AI", 4)
    _set_cell(panel, 0, 3, "5")  # column 3 = modbus_unit_id

    assert calls == []
    assert win._project.cards[0].modbus_unit_id == 5
    assert win._project.cards[0].channel_kinds == {"DI": 8, "AI": 4}


def test_unchecking_a_kind_removes_only_its_own_points(tmp_path, monkeypatch):
    calls = _no_dialogs(monkeypatch)
    _app()
    win = _window(tmp_path)
    win._open_io_cards()
    panel = win._cards_panel

    panel.add_card()
    _set_cell(panel, 0, 0, "ELA1")
    _check_kind(panel, 0, "DI", 2)
    _check_kind(panel, 0, "AI", 2)
    assert calls == []

    _uncheck_kind(panel, 0, "AI")

    assert win._project.cards[0].channel_kinds == {"DI": 2}
    addresses = {p.address for p in win._project.points}
    assert addresses == {"ELA1.DI.1", "ELA1.DI.2"}  # the AI.* points are gone, not orphaned


def test_duplicate_id_is_still_rejected_plain_and_simple(tmp_path, monkeypatch):
    """id is unique again - a card can now have several kinds ITSELF,
    so there is no longer a "same id, different kind is fine" carve-out
    to make room for (see Card's own docstring for why the earlier two-
    rows-sharing-an-id design was abandoned)."""
    calls = _no_dialogs(monkeypatch)
    _app()
    win = _window(tmp_path)
    win._open_io_cards()
    panel = win._cards_panel

    panel.add_card()
    _set_cell(panel, 0, 0, "ELA1")

    panel.add_card()
    second_auto_id = win._project.cards[1].id
    _set_cell(panel, 1, 0, "ELA1")

    assert len(calls) == 1
    assert win._project.cards[1].id == second_auto_id  # rejected: kept its own id
    assert win._project.cards[0].id == "ELA1"


class _FakeSynopticPanel:
    """Stands in for the real SynopticPanel (a QWebEngineView-backed
    widget, deliberately not constructed here - see synoptic_panel.py's
    own module docstring for why that's heavy) so _sync_device_registry_
    with_synoptic() can be exercised without a live page. Mirrors only
    the two methods that closure actually calls."""

    def __init__(self, registry):
        self._registry = registry
        self.pushed = None

    def query_device_registry(self, callback):
        callback(self._registry)

    def push_device_registry(self, cards, locations):
        self.pushed = (cards, locations)


def test_pulling_the_synoptic_registry_adds_a_missing_kind_to_an_existing_card(tmp_path):
    """main_window.py's own _sync_device_registry_with_synoptic():
    Synoptic's OWN registry stays flat, one CardEntry per kind (it never
    reads Modbus/location, so it has no reason to merge them into one
    row). Pulling in Synoptic's AI entry for a module Studio already has
    a DI row for must ADD the AI kind to that row, not skip it as
    "id already exists" and not create a second row for the same id."""
    _app()
    win = _window(tmp_path)
    win._open_io_cards()
    panel = win._cards_panel
    panel.add_card()
    _set_cell(panel, 0, 0, "ELA1")
    _check_kind(panel, 0, "DI", 8)

    registry = {
        "cards": [
            {"id": "ELA1", "model": "ELA01", "channelKind": "DI", "channelCount": 8},   # already have this
            {"id": "ELA1", "model": "ELA01", "channelKind": "AI", "channelCount": 4},   # the missing kind
        ],
        "locations": [],
    }
    win._synoptic_panel = _FakeSynopticPanel(registry)
    win._sync_device_registry_with_synoptic()

    assert len(win._project.cards) == 1  # still one row, not two
    assert win._project.cards[0].id == "ELA1"
    assert win._project.cards[0].channel_kinds == {"DI": 8, "AI": 4}
