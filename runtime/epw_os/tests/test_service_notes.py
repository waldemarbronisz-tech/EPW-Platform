"""Tests for per-device service history (epw_os/core/service_notes.py) -
headless, no Qt needed at all."""

import inspect

import pytest

from epw_os.core.access_manager import AccessLevel
from epw_os.core.service_notes import (
    ServiceNoteManager, build_device_report_csv, format_timestamp,
)


class FakeProjectManager:
    """Minimal stand-in matching the ProjectManager methods this module
    actually calls - get_service_notes()/set_service_notes()/
    save_project() - same pattern as test_switching_counters.py's own
    FakeProjectManager."""
    def __init__(self, initial=None):
        self._data = initial or {}
        self.save_count = 0

    def get_service_notes(self):
        return self._data

    def set_service_notes(self, data):
        self._data = data

    def save_project(self):
        self.save_count += 1


@pytest.fixture
def pm():
    return FakeProjectManager()


@pytest.fixture
def mgr(pm):
    return ServiceNoteManager(pm)


# --- DOWÓD: an entry saves and survives a restart -----------------------

def test_add_note_returns_the_stored_entry(mgr):
    note = mgr.add_note("DI1", "Replaced contact set.", AccessLevel.ENGINEER)
    assert note["text"] == "Replaced contact set."
    assert note["author_level"] == "Engineer"
    assert isinstance(note["timestamp"], float)


def test_added_note_is_immediately_visible_via_get_notes(mgr):
    mgr.add_note("DI1", "First note.", AccessLevel.OPERATOR)
    notes = mgr.get_notes("DI1")
    assert len(notes) == 1
    assert notes[0]["text"] == "First note."


def test_notes_persist_and_a_fresh_manager_restores_them(pm):
    mgr1 = ServiceNoteManager(pm)
    mgr1.add_note("DI1", "Cleaned contacts.", AccessLevel.ENGINEER)
    mgr1.add_note("DI1", "Verified operation after cleaning.", AccessLevel.OPERATOR)
    assert pm.save_count == 2, "each add must save immediately (low-frequency, must-not-lose writes)"

    # A brand-new manager, same (fake) persisted store - as if the app
    # restarted with the same project.json still on disk.
    mgr2 = ServiceNoteManager(pm)
    notes = mgr2.get_notes("DI1")
    assert len(notes) == 2
    assert {n["text"] for n in notes} == {"Cleaned contacts.", "Verified operation after cleaning."}


def test_notes_for_different_tags_are_independent(mgr):
    mgr.add_note("DI1", "Note for DI1.", AccessLevel.OPERATOR)
    mgr.add_note("DO01", "Note for DO01.", AccessLevel.OPERATOR)
    assert len(mgr.get_notes("DI1")) == 1
    assert len(mgr.get_notes("DO01")) == 1
    assert mgr.get_notes("DI1")[0]["text"] == "Note for DI1."


def test_no_notes_for_an_untouched_tag_is_an_empty_list(mgr):
    assert mgr.get_notes("DI50") == []


def test_multiple_notes_accumulate_in_order_added(mgr):
    mgr.add_note("DI1", "First.", AccessLevel.OPERATOR)
    mgr.add_note("DI1", "Second.", AccessLevel.ENGINEER)
    mgr.add_note("DI1", "Third.", AccessLevel.OPERATOR)
    notes = mgr.get_notes("DI1")
    assert [n["text"] for n in notes] == ["First.", "Second.", "Third."]


def test_corrupt_persisted_notes_are_dropped_not_crashed_on():
    pm = FakeProjectManager(initial={
        "DI1": "not a list",
        "DI2": ["not a dict", {"text": ""}, {"text": "ok but no timestamp"},
                {"text": "ok", "timestamp": "not a number", "author_level": "Operator"},
                {"text": "valid", "timestamp": 123.0, "author_level": "Operator"}],
    })
    mgr = ServiceNoteManager(pm)  # must not raise
    assert mgr.get_notes("DI1") == []
    notes = mgr.get_notes("DI2")
    assert len(notes) == 1
    assert notes[0]["text"] == "valid"


# --- DOWÓD: no way to edit or delete an entry, at any level -------------

def test_manager_exposes_no_edit_or_delete_method_at_all():
    """The structural guarantee (Task: "NIEUSUWALNE i NIEEDYTOWALNE"):
    not "disabled for User", not "Engineer-only" - the capability simply
    does not exist anywhere in the public API, for any level."""
    public_methods = {name for name, _ in inspect.getmembers(ServiceNoteManager, predicate=inspect.isfunction)
                       if not name.startswith("_")}
    assert public_methods == {"add_note", "get_notes"}
    forbidden_substrings = ("edit", "update", "delete", "remove", "clear")
    for name in public_methods:
        assert not any(bad in name.lower() for bad in forbidden_substrings), name


def test_get_notes_returns_copies_not_the_stored_list(mgr):
    mgr.add_note("DI1", "Original.", AccessLevel.OPERATOR)
    notes = mgr.get_notes("DI1")
    notes[0]["text"] = "TAMPERED"
    notes.append({"text": "INJECTED", "timestamp": 0.0, "author_level": "Engineer"})
    # The mutation above must not have reached the stored data.
    fresh = mgr.get_notes("DI1")
    assert len(fresh) == 1
    assert fresh[0]["text"] == "Original."


def test_mutating_the_dict_a_note_add_returned_does_not_affect_storage(mgr):
    returned = mgr.add_note("DI1", "Original.", AccessLevel.OPERATOR)
    returned["text"] = "TAMPERED"
    assert mgr.get_notes("DI1")[0]["text"] == "Original."


# --- DOWÓD: User level cannot add an entry ------------------------------

def test_user_level_cannot_add_a_note(mgr):
    result = mgr.add_note("DI1", "Sneaky user note.", AccessLevel.USER)
    assert result is None
    assert mgr.get_notes("DI1") == []


def test_unrecognized_author_level_cannot_add_a_note(mgr):
    result = mgr.add_note("DI1", "Note.", "SomeMadeUpLevel")
    assert result is None
    assert mgr.get_notes("DI1") == []


def test_operator_and_engineer_can_add_a_note(mgr):
    assert mgr.add_note("DI1", "From Operator.", AccessLevel.OPERATOR) is not None
    assert mgr.add_note("DI1", "From Engineer.", AccessLevel.ENGINEER) is not None
    assert len(mgr.get_notes("DI1")) == 2


def test_empty_or_whitespace_only_note_is_refused(mgr):
    assert mgr.add_note("DI1", "", AccessLevel.ENGINEER) is None
    assert mgr.add_note("DI1", "   ", AccessLevel.ENGINEER) is None
    assert mgr.add_note("DI1", None, AccessLevel.ENGINEER) is None
    assert mgr.get_notes("DI1") == []


def test_note_text_is_stripped_of_surrounding_whitespace(mgr):
    note = mgr.add_note("DI1", "  Padded note.  ", AccessLevel.OPERATOR)
    assert note["text"] == "Padded note."


def test_refused_add_does_not_write_to_disk(pm):
    mgr = ServiceNoteManager(pm)
    mgr.add_note("DI1", "Nope.", AccessLevel.USER)
    mgr.add_note("DI1", "", AccessLevel.ENGINEER)
    assert pm.save_count == 0


# --- GRANICE: content is never translated - trivially true since it's
# stored/returned completely verbatim, in whatever language/script it
# was typed in ----------------------------------------------------------

def test_note_text_is_stored_and_returned_completely_verbatim(mgr):
    text = "Wymieniono styki - widoczne przypalenia. Replaced contacts — visible pitting. 検査済み"
    mgr.add_note("DI1", text, AccessLevel.ENGINEER)
    assert mgr.get_notes("DI1")[0]["text"] == text


# --- CSV export ("razem z reszta danych aparatu") -----------------------

def test_csv_export_contains_properties_and_notes():
    properties = {"Tag": "DI1", "Description": "Main breaker feedback", "Closes": "42"}
    notes = [
        {"text": "Second note.", "timestamp": 200.0, "author_level": "Engineer"},
        {"text": "First note.", "timestamp": 100.0, "author_level": "Operator"},
    ]
    csv_text = build_device_report_csv(properties, notes)
    assert "Tag,DI1" in csv_text
    assert "Description,Main breaker feedback" in csv_text
    assert "Closes,42" in csv_text
    assert "Timestamp,Access Level,Note" in csv_text
    assert "First note." in csv_text
    assert "Second note." in csv_text
    # Oldest first in the export (a report reads start to finish).
    assert csv_text.index("First note.") < csv_text.index("Second note.")


def test_csv_export_with_no_notes_still_has_the_notes_header():
    csv_text = build_device_report_csv({"Tag": "DI1"}, [])
    assert "Timestamp,Access Level,Note" in csv_text


def test_csv_export_does_not_alter_note_text_content():
    # GRANICE: note content is user data, never translated/rewritten -
    # the CSV builder must pass it through byte-for-byte.
    text = "Coś się stało — sprawdzić ponownie."
    csv_text = build_device_report_csv({}, [{"text": text, "timestamp": 1.0, "author_level": "Operator"}])
    assert text in csv_text


# --- format_timestamp() -------------------------------------------------

def test_format_timestamp_none_is_na():
    assert format_timestamp(None) == "N/A"


def test_format_timestamp_renders_a_real_date():
    assert format_timestamp(0) != "N/A"
    assert "1970" in format_timestamp(0) or ":" in format_timestamp(0)
