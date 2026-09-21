"""Which screens a project has, and one screen's own document (task
„runtime czyta projekt.epw", punkt 3: wiele ekranów, nie jeden).

The Synoptic Editor keeps every screen of a project in ONE document
(studio/synoptic/src/project/ScreenContent.ts): `screens` is the list of
identities in switching order, `activeScreenId` says which one was open
when it was saved, and the ACTIVE screen's content sits at the document's
top level (objects/connections/walls/...) while every other screen's
content waits in `screenContents[id]`. Registries shared by all screens -
devices, locations, cards - stay at the top level and belong to no single
screen.

Runtime read that document as one screen: whatever the editor happened to
have open. This module turns it into the screen list SPEC_PROJEKT_EPW.md
asks for ("screens: name, kolejność przełączania") and rebuilds one
screen's document on demand, so the panel can switch between them with
the same reader (epwsyn_loader) it already uses.

Headless (no Qt) and tolerant: a document from before multi-screen, a
`screens` list of the wrong shape, or an unknown screen id all resolve to
the document as it stands rather than raising - a damaged project must
not take the Synoptic page down with it.
"""

# Everything that belongs to ONE screen (ScreenContent.ts). Anything else
# in the document - format, schema_version, project, canvas, kind,
# devices, locations, cards, helpLanguage - is project-wide and is kept
# exactly as it is when a screen is swapped in.
SCREEN_CONTENT_KEYS = (
    "objects", "connections", "meters", "signalPanels", "frames", "walls", "rooms",
    "groupCommands", "setpointPanels", "floorMaterial", "viewport",
)

# The screen's own canvas settings. The editor keeps the ACTIVE screen's
# under `canvas` (canvasConfig) and every other screen's in its
# ScreenContent - the reader (epwsyn_loader) only ever looks at `canvas`,
# so screen_document() moves them there.
SCREEN_CANVAS_KEYS = ("floorMaterial", "viewport")

DEFAULT_SCREEN_ID = ""


def _screens_section(document) -> list:
    if not isinstance(document, dict):
        return []
    section = document.get("screens")
    if not isinstance(section, list):
        return []
    return [entry for entry in section if isinstance(entry, dict) and entry.get("id")]


def active_screen_id(document) -> str:
    """The screen whose content is at the document's top level."""
    if not isinstance(document, dict):
        return DEFAULT_SCREEN_ID
    active = document.get("activeScreenId")
    if isinstance(active, str) and active:
        return active
    screens = _screens_section(document)
    return screens[0]["id"] if screens else DEFAULT_SCREEN_ID


def screen_list(document) -> list:
    """[{"id", "name"}] in the editor's own switching order. A document
    with no `screens` section (one screen, or a file from before
    multi-screen) gives exactly one entry, named after the project."""
    screens = _screens_section(document)
    if screens:
        return [{"id": entry["id"], "name": str(entry.get("name") or entry["id"])} for entry in screens]
    if not isinstance(document, dict):
        return []
    name = ""
    project = document.get("project")
    if isinstance(project, dict):
        name = str(project.get("name") or "")
    return [{"id": active_screen_id(document), "name": name}]


def has_screen(document, screen_id: str) -> bool:
    return any(entry["id"] == screen_id for entry in screen_list(document))


def screen_document(document, screen_id: str) -> dict:
    """The document as it would look with `screen_id` open: the shared
    registries untouched, the content swapped for that screen's own. The
    active screen (and an unknown id) gives the document unchanged."""
    if not isinstance(document, dict):
        return {}
    if not screen_id or screen_id == active_screen_id(document):
        return document
    contents = document.get("screenContents")
    content = contents.get(screen_id) if isinstance(contents, dict) else None
    if not isinstance(content, dict):
        return document
    swapped = dict(document)
    for key in SCREEN_CONTENT_KEYS:
        if key in content:
            swapped[key] = content[key]
        else:
            swapped.pop(key, None)
    canvas = document.get("canvas")
    canvas = dict(canvas) if isinstance(canvas, dict) else {}
    for key in SCREEN_CANVAS_KEYS:
        if key in content:
            canvas[key] = content[key]
        else:
            canvas.pop(key, None)
    swapped["canvas"] = canvas
    swapped["activeScreenId"] = screen_id
    return swapped
