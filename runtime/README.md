# EPW-OS
Industrial SCADA and Automation Platform

EPW OS supervises and controls a plant from a touchscreen HMI: digital/
analog I/O, a one-line diagram (Main View), protection/alarm handling,
historical trending, and a REST API - all built on a headless core
(`epw_os/core/`, no Qt) driving a PySide6 GUI, with drivers today
simulated (`SimulatorDriver`) so the whole decision path (permissions →
logic → safety → driver layer) can be exercised and tested without any
physical hardware attached.

## Running it

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py            # normal window
python main.py --kiosk    # fullscreen, borderless, Engineer PIN required to exit
```

`python test_headless.py` runs the core (no Qt) as a smoke check that
everything installed correctly. See `ORANGE_PI_DEPLOYMENT.md` for a
full unattended-kiosk deployment on an Orange Pi/Armbian device.

## Help system (`epw_os/help/`)

The in-app Help window (Help menu / F1) reads its content from plain
Markdown files under `epw_os/help/<language>/` (currently `pl/` and
`en/`), one file per topic, with a `toc.json` per language defining the
chapter/topic tree and the index terms. English is the fallback
whenever a topic or a whole language is missing. Loading/search logic
lives in `epw_os/core/help_content.py` (headless, no Qt) — see
`epw_os/tests/test_help_content.py`.

This content is documentation, not UI chrome: it is **not** run through
`tr()`. Only the Help window's own chrome (toolbar buttons, tab labels,
window title) is, via `locales/en.json`/`pl.json`.

**House rule: help is kept current continuously, not caught up later.**
Whenever a session adds or changes a user-facing feature, the relevant
Help topic(s) must be added or updated in `epw_os/help/` in that same
session — never deferred to a later "documentation pass". A feature
without a matching, accurate Help topic is not considered done.
