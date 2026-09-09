# gui_smoke/ - the GUI construction/behavior test suite

This package replaces the old, monolithic `test_gui_smoke.py` (a single
~2676-line, non-pytest script run via `python test_gui_smoke.py`, one
shared `QApplication`, one Python process, top to bottom). See
`SESSION_REPORT.md` (branch `refactor/test-suite-split`) for the full
rationale, the found progressive-slowdown cause, and the mock-drift fix.

Every file here is a normal pytest file - real `def test_*` functions,
independently discoverable and runnable, no dependency on file order or
on what another file did first (verified with `pytest-randomly`, already
installed in this environment, which runs the whole suite in a random
order every invocation).

## How to run

**Everything in this package** (still the whole GUI slice, no database):

```
pytest gui_smoke/
```

**One area alone** - exactly the point of the split:

```
pytest gui_smoke/test_kiosk.py
pytest gui_smoke/test_keyboard.py -k pin_dialog
```

**The fast slice** (no interface/database construction at all - the
`slow`/`gui` markers registered in the repo's `pytest.ini`): every test
in this package IS marked `slow`+`gui` (see `conftest.py`'s
`pytest_collection_modifyitems`) because every one of them constructs at
least a `QApplication`-backed mock, usually a full `MainWindow` - there
is no "fast" subset *within* gui_smoke/ itself. The actual fast, no-GUI,
no-DB slice of the whole project's suite is the plain logic tests under
`epw_os/tests/` that don't themselves construct Qt objects or touch the
database:

```
pytest epw_os/tests/ -m "not slow" gui_smoke/test_mock_interfaces.py
```

(`test_mock_interfaces.py` is the one file in this package that is
genuinely fast - it never constructs a `QApplication` object beyond what
`conftest.py`'s session fixture already sets up once, only parses source
files with `ast` - but it is still marked `slow`/`gui` for consistency
with the rest of the package, since it lives here and depends on this
package's mocks.)

**Before pushing** - the full suite, matching what CI runs:

```
pytest epw_os/tests/
pytest gui_smoke/
python test_headless.py
```

(Combining the first two into one `pytest epw_os/tests/ gui_smoke/`
call also works now - see "The combined-suite crash" below - CI just
hasn't been changed to do that, and there's no need to.)

## The split

One file per axis, each runnable alone:

| File | Covers |
|---|---|
| `test_mock_interfaces.py` | The permanent fix for mock/interface drift (see below) - not GUI behavior itself |
| `test_shell.py` | Menu bar, Help system + About, "Settings is a menu", nav tree, Analog Inputs page, window resizability, synoptic label wrap |
| `test_themes.py` | Visual themes: switching, persistence, tag-driven control, Automatyczny/Staly work mode |
| `test_project.py` | Export Signal List, Project Properties dialog, Recently Opened |
| `test_i18n.py` | Polish translation: menu/nav/statusbar after rebuild, and the full page/dialog sweep |
| `test_event_recorder.py` | Event Recorder's row cap (oldest-evicted-first) |
| `test_kiosk.py` | Kiosk Mode (frameless/fullscreen/PIN-gated exit) and Fullscreen Mode |
| `test_keyboard.py` | The on-screen keyboard, embedded PIN/Change-PIN keypads, Bug 1's real root cause |
| `test_permissions_core.py` | Per-level permission gates on existing pages/features with no extra state of their own |
| `test_permissions_features.py` | Permission-gated features that carry their own persistent state (switching counters, Training Mode, service notes, Analog Inputs add/edit) |

`_mocks.py` and `conftest.py` are shared support, not test files.

### Why this split, not a different one

The original suggested axes (pages / work modes / permissions /
keyboard+modals / alarms / translations) mostly held up against the
actual content, with two adjustments:

- **"alarms" is not big enough to be its own file.** The only
  alarm-specific behavior test_gui_smoke.py had beyond what
  `epw_os/tests/test_*.py` already covers headless is the one
  acknowledge-permission matrix - folded into `test_permissions_core.py`
  rather than left as a one-test file.
- **"permissions" split into two files**, not one ~680-line block: the
  original was one giant section covering both simple per-level gates
  (a description field, a Force menu, a nav target) AND several
  permission-gated features that each carry meaningful persistent state
  of their own (a mechanical-wear counter, Training Mode's indicator,
  service-history notes, Analog Inputs' point list). Splitting these two
  kept either file from re-growing into the same "too big to run the
  interesting piece alone" problem this whole task exists to fix.
- **"themes" got its own file**, separate from "translations" - the
  original script's largest section after the on-screen keyboard (~180
  lines), and color palettes are a different concern from language.
- Several otherwise-unrelated checks (menu bar, Help, Settings-is-a-menu,
  nav tree, Analog Inputs page, window resizability, a synoptic label
  wrap fix) all happened to reuse the SAME single default `MainWindow`
  the original script built once at the very top - grouped into
  `test_shell.py` for that reason (the program's basic chrome/shell),
  not because they're one feature.

### Checks preserved, none removed

Every `assert` and every `print(...)`-as-checkpoint from the original
script survives in one of these files, in the same logical grouping (a
`def test_...` per original comment-delimited sub-check, mostly - a few
adjacent one-or-two-line checks that only ever made sense run together
were kept in the same test function). Nothing was found here that
checked type instead of content, or otherwise turned out to be a no-op -
see SESSION_REPORT.md's "checks found to be useless" section for the
full accounting (there were none new; a previously-known instance of
this pattern elsewhere in the project is referenced there, not
reintroduced here).

## The mock-drift fix (task section 3)

Three sessions in a row, the same bug: a `TagManager`-shaped mock in the
old script was missing a method (`add_tag`, `list_tags`) that production
code started calling - only ever caught by actually *running* the
script, never by writing or compiling it.

`_mocks.py` consolidates every mock that used to be a separately
hand-rolled copy (`MockTagManager`, `_ThemeCapableTagManager`,
`_DICapableTagManager`, `_PageMockTM`, and the `_QtTagManagerBridge`
pattern independently reinvented at least three times across this
project) into one module - option (c) from the task.

`test_mock_interfaces.py` is the permanent, automatic version of option
(a): it parses `main.py`'s real `GUITagManagerAdapter`/
`GUIAccessManagerAdapter` - the actual objects GUI code receives in
production - straight out of its source with `ast` (never importing
`main.py`, which boots a real QApplication/FastAPI thread at import
time), and fails any mock in `_mocks.py` that is missing a method the
real adapter has. Nothing here is a manually-maintained list to forget
to update: the next method added to either adapter in `main.py` is
picked up automatically the next time this test runs. Running it while
writing this task already caught one previously-undetected real gap
(`toggle_mode()` - see SESSION_REPORT.md) that had been silently missing
from every mock the whole time, precisely the bug class this file exists
to catch.

`QtTagManagerBridge` (`_mocks.py`) is option (b): wraps a REAL, headless
`epw_os.core.tag_manager.TagManager` in the same Qt-signal shape the
production adapter uses, for tests that need real tag storage/quality/
event behavior rather than just a window that constructs without error -
a real object cannot drift from itself the way a hand-written mock can.
It is deliberately not used everywhere a `TagManager` mock is needed
(see its own docstring): several of the narrower mocks exist
specifically to give a test cheap, deterministic state a real
`TagManager` + `EventBus` + (for some production adapter methods)
`EPWCore`/`project_manager` wiring doesn't need to build.

## The combined-suite crash (fixed in feature/retention-and-test-fix)

`pytest epw_os/tests/ gui_smoke/` in one process used to crash, at full
scale, with a native fault (a Windows heap corruption or access
violation, at a different point each run). Found and fixed in the
feature/retention-and-test-fix task - see that branch's SESSION_REPORT.md
for the full diagnosis. Two independent, compounding causes, both now
gone:

1. **`pytest-qt`** is installed in this environment but nothing here
   uses its `qtbot` fixture - yet its own `pytest_runtest_teardown` hook
   unconditionally calls `QApplication.processEvents()` after EVERY test
   in the WHOLE session (not just gui_smoke/'s own), the moment any
   `QApplication` exists. Disabled globally (`pytest.ini`'s
   `addopts = -p no:pytest-qt`) - it provided no value here and every
   captured crash trace ran through its own `_process_events()`.
2. This package's own `_pump_qt_events_after_test` fixture used to ALSO
   force a `gc.collect()` after every test - a full Python heap walk,
   not a Qt-specific operation, whose cost scales with the size of the
   WHOLE process's live-object graph. Combined with `epw_os/tests/`'s
   own 500+ tests in the same process, this was both a second crash site
   and, even before the fix removed it, a large chunk of the combined
   run's own inflated timing (12m24s -> 5m19s just from removing this
   one call, before the `pytest-qt` fix). `processEvents()` alone
   (kept) is what actually reclaims a `.deleteLater()`'d Qt object -
   Qt's own deferred-deletion queue, unrelated to Python's cyclic
   garbage collector - and was always the operative half of that
   fixture.

**The two suites can now be run together** (`pytest epw_os/tests/
gui_smoke/`) - verified clean across multiple full runs, no crash, no
progressive-slowdown-return, ~144s. Running them as two separate
invocations (as shown above, and as CI still does) remains fine too -
neither is "more correct" now, just two working options.
