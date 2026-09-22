"""feat/signal-register §3.4 — the status report is generated, and the
generator is code like any other.

A hand-written status page is wrong within a week and nobody can tell
which half is stale. A GENERATED one is only worth that if it can be
re-run against a grown catalogue and still say something true, so what
these tests check is the classification - the part that would quietly
start lying - rather than the Markdown around it.

The one that matters most is the regression it was born from: the first
version compared the register against get_all_signals() with no project,
where a PATTERN expands to nothing. It therefore reported every per-zone
signal as missing on the very commit that added them - a status page
confidently understating the work it exists to report.
"""
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared.docs import generate_signal_register_status as gen
from shared.logic import system_signals


@pytest.fixture(scope="module")
def register():
    return gen.read_register()


@pytest.fixture(scope="module")
def catalog_by_id():
    return {gen._normalise(s["id"]): s for s in system_signals.raw_signals()}


# --- reading the workbook without openpyxl -----------------------------------

def test_the_workbook_is_read_at_all(register):
    """zipfile + ElementTree, because openpyxl is not a dependency here."""
    assert len(register) == 200


def test_every_row_has_the_columns_the_report_uses(register):
    for row in register:
        assert row["ID / Wzorzec"]
        assert "Grupa" in row and "Kierunek" in row


def test_the_workbook_is_only_ever_read(tmp_path):
    """The owner's register is not this repository's to edit."""
    before = Path(gen.WORKBOOK).read_bytes()
    gen.build()
    assert Path(gen.WORKBOOK).read_bytes() == before


# --- the classification -------------------------------------------------------

def test_a_placeholder_written_two_ways_is_one_signal():
    assert gen._normalise("SEC.ZONE.<zone_id>.ARMED") == gen._normalise("SEC.ZONE.<id>.ARMED")


def test_a_signal_the_controller_serves_is_reported_as_served(catalog_by_id):
    row = {"ID / Wzorzec": "SYS.READY", "Grupa": "SYS"}

    assert gen.classify(row, catalog_by_id, {})[0] == "w katalogu i obsłużony"


def test_a_pattern_in_the_catalogue_counts_as_covered(catalog_by_id):
    """THE REGRESSION. With the catalogue read as expansions rather than
    as written, this row reported "do zrobienia" although the platform
    had just gained one such signal per zone."""
    row = {"ID / Wzorzec": "SEC.ZONE.<zone_id>.ARMED", "Grupa": "SECURITY"}

    assert gen.classify(row, catalog_by_id, {})[0] == "w katalogu i obsłużony"


def test_the_per_zone_patterns_really_are_counted(register, catalog_by_id):
    covered = [r["ID / Wzorzec"] for r in register
               if gen.classify(r, catalog_by_id, {})[0] == "w katalogu i obsłużony"]

    assert "SEC.ZONE.<zone_id>.ARMED" in covered
    assert "SEC.LINE.<line_id>.VIOLATED" in covered
    assert "REQ.SEC.ZONE.<zone_id>.ARM" in covered


def test_power_and_ups_rows_are_served_not_waiting_on_hardware(catalog_by_id):
    # PWR.* since etap 3 (EPM's register block), UPS.* since etap 4 (a DI
    # point with a role) - and a POWER/UPS row the catalogue lacks is
    # honestly "do zrobienia", no longer excused as waiting on hardware.
    for signal_id, group in (("PWR.MAINS_OK", "POWER"), ("UPS.ONLINE", "UPS"), ("UPS.FAULT", "UPS"),
                             ("DEV.<id>.WATCHDOG_OK", "DEVICE HEALTH")):
        assert gen.classify({"ID / Wzorzec": signal_id, "Grupa": group}, catalog_by_id, {})[0] == "w katalogu i obsłużony"
    assert gen.classify({"ID / Wzorzec": "UPS.NOT_A_REAL_BIT", "Grupa": "UPS"}, catalog_by_id, {})[0] == "do zrobienia"


def test_a_position_without_a_source_says_so_with_its_reason(catalog_by_id):
    status, note = gen.classify({"ID / Wzorzec": "PROT.POWER_REVERSE", "Grupa": "PROTECTION"}, catalog_by_id, {})
    assert status == "bez źródła" and "funkcji 32" in note
    status, note = gen.classify({"ID / Wzorzec": "MODE.LOCAL", "Grupa": "MODES"}, catalog_by_id, {})
    assert status == "bez źródła" and "LOCAL" in note
    assert gen.classify({"ID / Wzorzec": "MODE.NORMAL", "Grupa": "MODES"}, catalog_by_id, {})[0] == "w katalogu i obsłużony"


def test_nothing_is_left_as_merely_to_do(register, catalog_by_id):
    """Etap 6's goal: every register position is served, or carries a
    named reason (future, outside the catalogue, no source)."""
    from shared.logic.signal_renames import RENAMES
    renames = {gen._normalise(old): new for old, new in RENAMES.items()}
    undone = [row["ID / Wzorzec"] for row in register
              if gen.classify(row, catalog_by_id, renames)[0] == "do zrobienia"]
    assert undone == []


def test_a_diagnostic_row_the_catalog_lacks_is_still_named_as_firmware_work(catalog_by_id):
    row = {"ID / Wzorzec": "DEV.<id>.NOT_A_REAL_BIT", "Grupa": "DEVICE HEALTH"}
    assert gen.classify(row, catalog_by_id, {})[0] == "czeka na firmware"


def test_a_user_marker_is_not_reported_as_missing_from_the_catalogue(catalog_by_id):
    """M.* belongs to the project, not to the platform contract. Calling
    it "do zrobienia" would put it on a list it can never leave."""
    row = {"ID / Wzorzec": "M.USER.LIGHT_REQUIRED", "Grupa": "USER INTERNAL"}

    assert gen.classify(row, catalog_by_id, {})[0] == "poza katalogiem"


def test_something_in_scope_and_absent_is_honestly_called_unfinished(catalog_by_id):
    # A row in a group the catalogue covers, absent from the catalogue
    # and with no named reason: the honest word is "do zrobienia", never
    # a facade (rule Z1). (MODE.LOCAL, once the example here, now carries
    # its reason - see test_a_position_without_a_source_says_so_with_its_reason.)
    row = {"ID / Wzorzec": "MODE.NOT_YET_INVENTED", "Grupa": "MODES"}

    assert gen.classify(row, catalog_by_id, {})[0] == "do zrobienia"


# --- the report itself --------------------------------------------------------

def test_the_report_names_its_own_source_and_the_catalogue_version():
    text = gen.build()

    assert "EPW_Rejestr_Bitow_Wewnetrznych_V2.xlsx" in text
    assert system_signals.get_catalog_version() in text


def test_the_report_says_it_is_generated():
    """So nobody edits it and loses the edit on the next run."""
    assert "Plik generowany" in gen.build()


def test_the_report_lists_every_register_position(register):
    text = gen.build()

    for row in register:
        assert "`%s`" % row["ID / Wzorzec"] in text, row["ID / Wzorzec"]


def test_the_report_separates_names_taken_from_the_register_from_names_invented():
    """The eleven with no row in the register were a decision, accepted
    by the owner. They stay listed apart from the twelve that came from
    the register, so a later revision knows which names were settled
    here - but they are no longer presented as pending."""
    text = gen.build()

    assert "Nazwy wzięte z rejestru (12)" in text
    assert "Nazwy ustalone tutaj, przyjęte (11)" in text
    assert "właściciel przyjął je 2026-09-21" in text
    assert "Do potwierdzenia" not in text, "a settled decision is still shown as open"


def test_the_report_also_lists_what_the_platform_has_and_the_register_does_not():
    """The other direction, which is how the register itself grows."""
    text = gen.build()

    assert "W katalogu, poza rejestrem" in text


def test_running_it_twice_produces_the_same_text():
    """Nothing in it depends on the clock or on dict ordering - a report
    that churns on every run makes its own diff useless."""
    assert gen.build() == gen.build()


def test_the_checked_in_file_is_what_the_generator_produces():
    """Otherwise somebody edited it by hand, or forgot to re-run it after
    changing the catalogue."""
    on_disk = Path(gen.OUTPUT).read_text(encoding="utf-8")

    assert on_disk == gen.build(), (
        "SIGNAL_REGISTER_STATUS.md is out of date - run "
        "python shared/docs/generate_signal_register_status.py")
