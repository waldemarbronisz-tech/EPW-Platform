"""The OBJECT file - `obiekt.epwsite` (user, 2026-09-18: "możliwość
tworzenia wielu projektów w Studio - cały obiekt stworzony z wielu
sterowników", Etango-style: an object, and devices added to it).

An object is a named list of projects; every project stays its own,
self-contained `projekt.epw` (one controller, sent to that controller,
its own revision and settings hash), so nothing about a project changes
because it belongs to an object. The file is plain JSON next to the
projects, paths relative to it (POSIX separators), e.g.

    {"format": "EPW_SITE", "schema_version": 1, "name": "Dom",
     "projects": [{"path": "EntryGate/projekt.epw"}, {"path": "MainHouse/projekt.epw"}]}

Studio without an object file still works exactly as before: one
project is an implicit one-device object.
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import PurePosixPath

SITE_FORMAT = "EPW_SITE"
SITE_SCHEMA_VERSION = 1
SITE_SUFFIX = ".epwsite"


class SiteFormatError(Exception):
    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params

    def __str__(self):
        return {"not_object": "The object file is not a JSON object.",
                "wrong_format": "Not an EPW object file (format marker missing or wrong).",
                "unreadable": "The object file could not be read: {detail}",
                "bad_projects": "The object file's project list is malformed."}.get(self.key, self.key).format(
            **self.params)


@dataclass
class Site:
    name: str = ""
    projects: list = field(default_factory=list)   # relative project paths, POSIX separators, in tree order
    # Links between the object's controllers (2026-09-18): one controller's
    # tag read by another as a Link.* tag over MQTT - see apply_object_links().
    # [{"source": rel path, "tag": "ELA1.DI.1", "target": rel path,
    #   "link_tag": "Link.EntryGate.In1", "type": "BOOL", "stale_after_s": 30}]
    links: list = field(default_factory=list)
    is_dirty: bool = False


def new_site(name: str) -> Site:
    return Site(name=name, is_dirty=True)


def load_site(path) -> Site:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise SiteFormatError("unreadable", detail=str(exc)) from exc
    if not isinstance(data, dict):
        raise SiteFormatError("not_object")
    if data.get("format") != SITE_FORMAT:
        raise SiteFormatError("wrong_format")
    raw_projects = data.get("projects", [])
    if not isinstance(raw_projects, list):
        raise SiteFormatError("bad_projects")
    projects = []
    for entry in raw_projects:
        rel = entry.get("path") if isinstance(entry, dict) else entry
        if isinstance(rel, str) and rel.strip():
            projects.append(rel.strip())
    links = []
    for raw in data.get("links", []) if isinstance(data.get("links", []), list) else []:
        if isinstance(raw, dict) and all(isinstance(raw.get(k), str) and raw.get(k) for k in ("source", "tag", "target", "link_tag")):
            links.append({"source": raw["source"], "tag": raw["tag"], "target": raw["target"], "link_tag": raw["link_tag"],
                          "type": str(raw.get("type") or "BOOL"), "stale_after_s": int(raw.get("stale_after_s") or 30)})
    return Site(name=str(data.get("name") or ""), projects=projects, links=links, is_dirty=False)


def save_site(site: Site, path) -> None:
    data = {"format": SITE_FORMAT, "schema_version": SITE_SCHEMA_VERSION, "name": site.name,
            "projects": [{"path": rel} for rel in site.projects]}
    if site.links:
        data["links"] = [dict(link) for link in site.links]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    site.is_dirty = False


def resolve_project_path(site_path, relative: str) -> str:
    """Absolute path of a project listed in the object file."""
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(site_path)), *PurePosixPath(relative).parts))


def relative_project_path(site_path, project_path) -> str:
    """How the object file records a project: relative to itself, POSIX
    separators; a project on another drive stays absolute."""
    base = os.path.dirname(os.path.abspath(site_path))
    try:
        rel = os.path.relpath(os.path.abspath(project_path), base)
    except ValueError:                       # different drive on Windows
        return os.path.abspath(project_path).replace(os.sep, "/")
    return rel.replace(os.sep, "/")


# --- links between the object's controllers ------------------------------------------------------
#
# The mechanism is the MQTT integration both controllers already have:
# the SOURCE publishes every tag at "<prefix>/tag/<Tag/Path>/state"
# (runtime/epw_os/core/mqtt_manager.py) and the TARGET's `mqtt.link_in`
# turns such a topic into a local "Link.<Id>.In<n>" tag its logic and
# screens can use. An object link is that pair, written by Studio into
# the target project's link_in (marked "object_link" so a manual entry
# there is never touched) - runtime needs nothing new.

import re as _re

LINK_TAG_RE = _re.compile(r"^Link\.[^.]+\.In.+$")      # runtime's own rule for a Link.* tag
OBJECT_LINK_MARK = "object_link"


def sanitize_for_id(text: str) -> str:
    """The same rule runtime uses for its MQTT client id / default prefix."""
    return _re.sub(r"[^A-Za-z0-9_-]", "_", text or "") or "epw_os"


def default_topic_prefix(project) -> str:
    """What runtime uses when the project sets no topic_prefix."""
    return f"epw/{sanitize_for_id(project.mqtt.client_id or project.metadata.name)}"


def link_topic(prefix: str, tag: str) -> str:
    return f"{prefix.rstrip('/')}/tag/{tag.replace('.', '/')}/state"


def link_type_for(tag: str) -> str:
    kind = tag.split(".")[1] if tag.count(".") == 2 else ""
    return "REAL" if kind in ("AI", "AO") else "BOOL"


def suggest_link_tag(source_name: str, existing: list) -> str:
    """"Link.<SourceId>.In<n>" - the first n not already used."""
    base = f"Link.{sanitize_for_id(source_name)}.In"
    n = 1
    while f"{base}{n}" in existing:
        n += 1
    return f"{base}{n}"


def apply_object_links(site, projects: dict) -> dict:
    """Writes the object's links into the projects: every target project's
    link_in gets exactly the object links aimed at it (manual entries,
    those without the object mark, are kept as they are), and every
    source gets MQTT enabled with a topic prefix when it had none - a
    link cannot work otherwise. `projects` maps the site's relative
    paths to Project objects. Returns {rel path: [what changed]} for the
    projects that changed."""
    changed = {}

    def note(rel, what):
        changed.setdefault(rel, []).append(what)

    for link in site.links:
        source = projects.get(link["source"])
        if source is None:
            continue
        if not source.mqtt.topic_prefix:
            source.mqtt.topic_prefix = default_topic_prefix(source)
            note(link["source"], f"topic_prefix={source.mqtt.topic_prefix}")
        if not source.mqtt.enabled:
            source.mqtt.enabled = True
            note(link["source"], "mqtt enabled")
    for rel, project in projects.items():
        wanted = []
        for link in site.links:
            if link["target"] != rel:
                continue
            source = projects.get(link["source"])
            if source is None:
                continue
            wanted.append({"topic": link_topic(source.mqtt.topic_prefix, link["tag"]), "tag": link["link_tag"],
                           "type": link.get("type") or link_type_for(link["tag"]),
                           "stale_after_s": int(link.get("stale_after_s") or 30), OBJECT_LINK_MARK: True,
                           "source": link["source"], "source_tag": link["tag"]})
        manual = [entry for entry in project.mqtt.link_in if not entry.get(OBJECT_LINK_MARK)]
        current = [entry for entry in project.mqtt.link_in if entry.get(OBJECT_LINK_MARK)]
        if current != wanted:
            project.mqtt.link_in = manual + wanted
            if wanted and not project.mqtt.enabled:
                project.mqtt.enabled = True
                note(rel, "mqtt enabled")
            note(rel, f"{len(wanted)} object link(s)")
    for rel in changed:
        project = projects.get(rel)
        if project is not None:
            project.touch()
    return changed


def drop_links_of(site, rel: str) -> int:
    """A project leaving the object takes its links (both ways) with it."""
    before = len(site.links)
    site.links = [link for link in site.links if link["source"] != rel and link["target"] != rel]
    removed = before - len(site.links)
    if removed:
        site.is_dirty = True
    return removed
