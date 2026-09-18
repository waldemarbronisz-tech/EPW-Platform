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
    return Site(name=str(data.get("name") or ""), projects=projects, is_dirty=False)


def save_site(site: Site, path) -> None:
    data = {"format": SITE_FORMAT, "schema_version": SITE_SCHEMA_VERSION, "name": site.name,
            "projects": [{"path": rel} for rel in site.projects]}
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
