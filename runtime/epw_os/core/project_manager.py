import json
import os
import shutil

from epw_os.core.logging import log

_RUNTIME_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# Task "runtime czyta projekt.epw": the project runtime works from is the
# one Studio writes - projekt.epw (shared/docs/SPEC_PROJEKT_EPW.md), read
# through shared/project_format.py. Absolute, anchored to runtime/ (same
# directory as main.py) - not relative to the process's CWD. A relative
# default here would silently create/read a *different* file depending on
# where the app is launched from (see AccessManager.DEFAULT_CONFIG_PATH for
# the confirmed real-world case of this exact bug class).
DEFAULT_PROJECT_FILE = os.path.join(_RUNTIME_ROOT, "projekt.epw")

# The old single-file project. Runtime no longer reads it at start;
# tools/migrate_project_json.py imports it once and leaves it in place as a
# copy (the task's own GRANICE: "NIE KASUJ pliku, zostaw jako kopię").
LEGACY_PROJECT_FILE = os.path.join(_RUNTIME_ROOT, "project.json")

# Kept next to the project file: the state (SPEC_PROJEKT_EPW.md, "Plik
# stanu") and the controller's own settings the project format does not
# carry (UI language, REST host/port, historian/audit retention, the
# database size warning, the .epwsyn/.epwlogic paths - see _save_epw()).
# MQTT and the service notes moved INTO the project on 2026-09-18 (they
# belong to the installation, not to one controller - ZADANIA p. 6).
STATE_FILE_NAME = "runtime_state.json"
SETTINGS_FILE_NAME = "controller.local.json"
PENDING_INSTALL_SUFFIX = ".pending"   # projekt.epw.pending - written by install_project_file(), read at start
SETTINGS_FORMAT = "EPW_CONTROLLER_SETTINGS"

PROJECT_FORMAT = "EPW_OS_PROJECT"
PROJECT_SCHEMA_VERSION = 1

DEFAULT_LANGUAGE = "en"


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


class ProjectManager:
    """Runtime's one door to project data. Every module reads and writes
    flat sections of `self.config` (get_intrusion_zones(), set_switching_
    counters(), ...) and calls save_project(); where a section physically
    lives depends on the project file:

    - projekt.epw (the default - task "runtime czyta projekt.epw"): three
      files, split by SPEC_PROJEKT_EPW.md's own layers.
        projekt.epw            structure + settings (nastawy); a panel
                               write reaches it only for settings, bumps
                               `revision`, sets modified_by="panel", and
                               is audited - structure is refused
                               (project_epw.diff_settings()).
        runtime_state.json     counters, arming, bypass, alarm memory,
                               last screen (runtime_state.py) - never the
                               project file.
        controller.local.json  settings of this controller the project
                               format does not carry.
      save_project() writes only the files whose part actually changed, so
      a counter flush never touches projekt.epw.

    - any other path (a *.json file): the old single-file project.json
      behaviour, byte for byte. Nothing in the running program selects it
      any more; it remains the storage the unit tests' scratch projects use
      and what tools/migrate_project_json.py reads from.
    """

    def __init__(self, project_file: str = None, state_file: str = None, settings_file: str = None):
        # EPW_PROJECT_FILE lets one installation run a project file kept
        # somewhere else (a test bench, a second site on the same machine)
        # without editing code; unset, runtime/projekt.epw is used.
        self.project_file = project_file or os.environ.get("EPW_PROJECT_FILE") or DEFAULT_PROJECT_FILE
        self._state_file = state_file
        self._settings_file = settings_file
        self.config = {}
        self.rolled_back = None   # set by _rollback_pending_install() at a start that refused an install
        # JSON snapshot of the last state that is known to match disk. Used
        # by is_dirty() to drive the "unsaved changes" prompt in the File
        # menu. None until the first load/save.
        self._saved_snapshot = None

        # projekt.epw mode only:
        self.project = None           # the shared Project dataclass as read, or None when unusable
        self.load_error = None        # {"key", "params", "text"} when projekt.epw could not be used
        self.load_warnings = []       # shared FormatIssue list the reader reported
        self.state_load_problem = None  # RuntimeStateStore.load_problem
        self._saved_parts = {}
        self._audit_logger = None
        self._actor_provider = None

    # --- which storage ----------------------------------------------------

    def is_epw_project(self) -> bool:
        return str(self.project_file).lower().endswith(".epw")

    def structure_editable(self) -> bool:
        """False for projekt.epw: zones, lines, points, protections,
        composition - everything that says WHAT exists - are designed in
        Studio only (SPEC_PROJEKT_EPW.md, "Trzy warstwy dostępu"). Modules
        ask this before any add/remove/rename; settings stay editable."""
        return not self.is_epw_project()

    @property
    def state_file(self) -> str:
        return self._state_file or os.path.join(os.path.dirname(os.path.abspath(self.project_file)), STATE_FILE_NAME)

    @property
    def settings_file(self) -> str:
        return self._settings_file or os.path.join(os.path.dirname(os.path.abspath(self.project_file)),
                                                   SETTINGS_FILE_NAME)

    # --- helpers ------------------------------------------------------

    @staticmethod
    def _default_config() -> dict:
        return {
            "format": PROJECT_FORMAT,
            "schema_version": PROJECT_SCHEMA_VERSION,
            "project_id": "DEFAULT_PROJECT",
            "synoptic_project": None,
            "logic_project": None,
        }

    @staticmethod
    def _is_valid(data) -> bool:
        return (
            isinstance(data, dict)
            and data.get("format") == PROJECT_FORMAT
            and data.get("schema_version") == PROJECT_SCHEMA_VERSION
        )

    def _snapshot(self) -> str:
        return json.dumps(self.config, sort_keys=True, ensure_ascii=False, default=str)

    def _mark_clean(self):
        self._saved_snapshot = self._snapshot()
        if self.is_epw_project():
            self._saved_parts = {name: _canonical(self._part(name)) for name in ("project", "state", "settings")}

    def is_dirty(self) -> bool:
        """True when self.config has changed since the last load/save - i.e.
        there is unsaved work. A freshly created (never-saved) project also
        counts as dirty. With projekt.epw every part is written the moment
        it changes (settings, state, controller settings - see _save_epw()
        and save_runtime_state()), so this compares each part with what was
        last written instead of one snapshot of everything: an immediate
        state write must not leave the panel asking to "save changes" on
        exit."""
        if self.is_epw_project():
            return any(_canonical(self._part(name)) != self._saved_parts.get(name)
                       for name in ("project", "state", "settings"))
        return self._snapshot() != self._saved_snapshot

    def _write(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def _read(self, path: str):
        """Returns the parsed dict, or None (logging why) if the file
        exists but isn't readable as JSON at all - a truncated/corrupted
        file (e.g. a power loss mid-write on an embedded deployment, or
        a full SD card) must be reported and handled like any other bad
        project file, not crash the whole program at startup with an
        unhandled JSONDecodeError. Distinct from _is_valid()'s check,
        which handles a file that DOES parse as JSON but isn't this
        program's project format - every caller below already treats
        that case as "invalid, don't crash" and now treats an unparseable
        file exactly the same way."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            log.error(f"Could not read project file {path}: {e}")
            return None

    # --- lifecycle --------------------------------------------------

    def load_project(self):
        if self.is_epw_project():
            return self._load_epw(self.project_file)
        if os.path.exists(self.project_file):
            data = self._read(self.project_file)

            if data is None or not self._is_valid(data):
                log.error(f"Invalid project format in {self.project_file}. Maintaining existing configuration.")
                return False

            self.config = data
            log.info(f"Successfully activated project: {self.config.get('project_id')}")
        else:
            log.info("No project file found. Using default empty configuration.")
            self.config = self._default_config()

        self._mark_clean()
        return True

    def save_project(self):
        if self.is_epw_project():
            return self._save_epw()
        self._write(self.project_file)
        self._mark_clean()
        return True

    def save_project_as(self, path: str):
        """Make `path` the active project file and write to it. Not for
        projekt.epw - the panel does not author projects (see
        structure_editable())."""
        if self.is_epw_project():
            log.warning("Refused Save As: projekt.epw is authored in Studio, the panel only writes settings back.")
            return False
        self.project_file = path
        return self.save_project()

    def new_project(self):
        """Reset to a blank in-memory project. Not written to disk until the
        operator saves - so it shows up as unsaved (is_dirty() -> True)."""
        if self.is_epw_project():
            log.warning("Refused New Project: projects are created in Studio.")
            return False
        self.config = self._default_config()
        # deliberately do NOT _mark_clean(): a brand-new project is unsaved
        return True

    def load_from(self, path: str) -> bool:
        """Open an external project file and make it the active project.
        A projekt.epw is validated with the shared reader first - a file
        that would be refused never replaces the working project."""
        if str(path).lower().endswith(".epw"):
            from epw_os.core import project_format as pf
            result = pf.read_project(path)
            if not result.ok:
                log.error(f"Refused project {path}: {result.error}")
                return False
            self.project_file = path
            return self._load_epw(path)
        data = self._read(path)
        if data is None or not self._is_valid(data):
            log.error(f"Invalid project format in {path}.")
            return False
        self.config = data
        self.project_file = path
        self._mark_clean()
        return True

    def import_from(self, path: str) -> bool:
        """Pull an external project file's contents into the current project
        and persist to the active project file. Unlike load_from(), the
        active project path does not move to the imported file."""
        if self.is_epw_project():
            log.warning("Refused Import: projekt.epw is authored in Studio.")
            return False
        data = self._read(path)
        if data is None or not self._is_valid(data):
            log.error(f"Invalid project format in {path}.")
            return False
        self.config = data
        self.save_project()
        return True

    def export_to(self, path: str):
        """Write a standalone backup copy of the current project. The active
        project file is unchanged and dirty state is untouched. For
        projekt.epw that is the file itself, exactly as the controller
        runs it (settings changed on the panel included) - what an engineer
        downloads to compare with Studio."""
        if self.is_epw_project():
            if self.project is None or not os.path.exists(self.project_file):
                log.error("Nothing to export: no valid projekt.epw is loaded.")
                return False
            shutil.copyfile(self.project_file, path)
            return True
        self._write(path)
        return True

    # --- typed accessors ------------------------------------------

    def get_synoptic_file(self):
        return self.config.get("synoptic_project")

    def get_logic_file(self):
        return self.config.get("logic_project")

    # Task "Studio osadza ekrany i logikę w projekt.epw" - the project's
    # own embedded documents (shared/project_format.py's Project.screens /
    # logic_runtime), {} when the project predates that task or has none.
    def get_embedded_screens(self) -> dict:
        return dict(getattr(self.project, "screens", None) or {}) if self.project is not None else {}

    def get_embedded_logic_runtime(self) -> dict:
        return dict(getattr(self.project, "logic_runtime", None) or {}) if self.project is not None else {}

    def get_language(self) -> str:
        return self.config.get("language", DEFAULT_LANGUAGE)

    def set_language(self, code: str):
        self.config["language"] = code

    def get_api_host(self) -> str:
        """Task: REST API security - one typed accessor instead of the
        bare .config.get("api_host", ...) literal previously duplicated
        in main.py, so the default (127.0.0.1) and the key name live in
        exactly one place."""
        return self.config.get("api_host", "127.0.0.1")

    def get_api_port(self) -> int:
        return int(self.config.get("api_port", 8000))

    def set_tag_description(self, name: str, description: str):
        """In projekt.epw a point's description is structure - it lives in
        Studio's point registry and reaches tags from there."""
        if self.is_epw_project():
            log.warning(f"Refused to change the description of {name!r}: descriptions come from the "
                        f"project's point registry (Studio).")
            return False
        self.config.setdefault("tag_descriptions", {})[name] = description
        return True

    def get_tag_descriptions(self) -> dict:
        return self.config.get("tag_descriptions", {})

    def set_output_description(self, name: str, description: str):
        """Persisted custom label for a Control Outputs row, keyed by its
        visible Tag column text. Same projekt.epw rule as
        set_tag_description()."""
        if self.is_epw_project():
            log.warning(f"Refused to change the description of {name!r}: descriptions come from the "
                        f"project's point registry (Studio).")
            return False
        self.config.setdefault("output_descriptions", {})[name] = description
        return True

    def get_output_descriptions(self) -> dict:
        return self.config.get("output_descriptions", {})

    def get_switching_counters(self) -> dict:
        """Persisted mechanical-wear counters (Task: liczba przelaczen i
        czas w stanie zamknietym per aparat), keyed by tag name - same
        "new top-level section, key = tag name" pattern as
        tag_descriptions/output_descriptions above (GRANICE: "nie
        zmieniaj struktury istniejacych danych... tylko dolóz nowa
        sekcje"). Read/written wholesale by
        epw_os.core.switching_counters.SwitchingCounterManager, not
        per-field - see that module for the record shape."""
        return self.config.get("switching_counters", {})

    def set_switching_counters(self, data: dict):
        self.config["switching_counters"] = dict(data)

    def get_counter_warning_thresholds(self) -> dict:
        """{DI tag: warning_threshold or None} from the project - the
        setting the counter records are seeded with (ZADANIA p. 6)."""
        return {r.get("tag"): r.get("warning_threshold")
                for r in self.config.get("switching_counter_settings", []) if isinstance(r, dict) and r.get("tag")}

    def set_counter_warning_threshold(self, tag_name: str, threshold) -> bool:
        """A panel change of the threshold - into the project view, so the
        next save writes it back to projekt.epw as a setting (revision +1,
        "panel"). False when the tag is not a DI point of the project (the
        counter still keeps it in runtime state, as before)."""
        for record in self.config.get("switching_counter_settings", []):
            if isinstance(record, dict) and record.get("tag") == tag_name:
                record["warning_threshold"] = int(threshold) if threshold is not None else None
                return True
        return False

    def get_service_notes(self) -> dict:
        """Persisted per-device service history (Task: historia
        serwisowa przypisana do aparatu), keyed by tag name - same
        "new top-level section, key = tag name" pattern as
        tag_descriptions/output_descriptions/switching_counters above.
        Read/written wholesale by
        epw_os.core.service_notes.ServiceNoteManager, not per-field -
        see that module for the entry shape and the immutability
        guarantee (no setter here ever removes or edits an existing
        entry, only replaces the whole section with one that has more)."""
        return self.config.get("service_notes", {})

    def set_service_notes(self, data: dict):
        self.config["service_notes"] = dict(data)

    def set_analog_config(self, name: str, config: dict):
        """Persisted per-channel Analog Inputs config (signal type, raw/
        engineering ranges, unit, decimals) - same pattern as
        set_tag_description(), keyed by tag name (e.g. "AI1") in its own
        namespace since it's a dict of settings, not a single string.

        Superseded by analog_points below (each point's config now lives
        alongside its tag/description/note in one record) - kept only as
        a read-only migration SOURCE for get_analog_points(). Nothing
        writes through this method any more; do not add new callers."""
        self.config.setdefault("analog_config", {})[name] = dict(config)

    def get_analog_configs(self) -> dict:
        return self.config.get("analog_config", {})

    # --- Analog Inputs: dynamic points collection ----------------------
    #
    # Unlike DI/DO (a fixed number of physical terminals on ELA/ADA), an
    # analog point is a name on a shared I2C/1-Wire bus - the operator adds
    # and removes them freely, so the persisted representation is a LIST of
    # point records (identity + config together), not a fixed slot count or
    # a dict keyed by an assumed-to-already-exist tag name.

    DEFAULT_LEGACY_POINT_COUNT = 16

    def get_analog_points(self) -> list:
        """The full list of configured analog points, each a dict with
        keys: tag, description, signal_type, raw_min, raw_max, eng_min,
        eng_max, unit, decimals, technical_note.

        Migrates in place (and persists immediately) the first time this
        is called against a project.json from before this feature existed
        (no "analog_points" key yet) - synthesizes AI1..AI16 point records
        from whatever was already in analog_config/tag_descriptions for
        those tags (or defaults, for ones nobody had customized), so nothing
        configured before is lost. Idempotent - a second call is a no-op
        read.
        """
        if "analog_points" not in self.config:
            self.config["analog_points"] = self._migrate_legacy_analog_points()
            self.save_project()
        return self.config["analog_points"]

    def _migrate_legacy_analog_points(self) -> list:
        from epw_os.core.analog_scaling import default_channel_config
        legacy_config = self.config.get("analog_config", {})
        legacy_descriptions = self.config.get("tag_descriptions", {})
        points = []
        for i in range(1, self.DEFAULT_LEGACY_POINT_COUNT + 1):
            tag = f"AI{i}"
            cfg = default_channel_config()
            cfg.update(legacy_config.get(tag, {}))
            points.append({
                "tag": tag,
                "description": legacy_descriptions.get(tag, f"Analog Input Channel {i}"),
                "technical_note": "",
                **cfg,
            })
        if points:
            log.info(f"Migrated {len(points)} legacy Analog Input channel(s) to the dynamic points format.")
        return points

    def set_analog_points(self, points: list):
        self.config["analog_points"] = list(points)

    # --- Project metadata (Task: Project menu > Properties) -------------
    #
    # A new, OPTIONAL section (config["metadata"]) - same "not in
    # _default_config(), synthesized lazily via .get()/.setdefault()"
    # pattern as tag_descriptions/output_descriptions/analog_points
    # above, deliberately NOT added to _default_config() itself: a
    # project.json from before this feature existed simply has no
    # "metadata" key at all, and every accessor below already handles
    # that (GRANICE: no migration, no error, existing projects keep
    # working). Nothing here touches load_project()/save_project()/
    # new_project()'s own bodies - those stay exactly as they were.

    def get_metadata(self) -> dict:
        """name/description/location/author are operator-entered (never
        translate their content - GRANICE); created/modified are ISO
        timestamps this class stamps itself (see set_metadata()/
        touch_metadata_modified()), or None if never set yet (a project
        never saved under this feature)."""
        meta = self.config.get("metadata", {})
        return {
            "name": meta.get("name", ""),
            "description": meta.get("description", ""),
            "location": meta.get("location", ""),
            "author": meta.get("author", ""),
            "created": meta.get("created"),
            "modified": meta.get("modified"),
        }

    def set_metadata(self, name: str = "", description: str = "", location: str = "", author: str = ""):
        """Operator-edited fields only - does not touch created/modified.
        "created" is stamped here exactly once, the first time metadata
        is ever actually set (task: "ustawiana raz") - untouched on every
        later call. Caller (the Properties dialog) still needs to call
        save_project() itself afterwards, same as every other
        project_manager setter in this codebase (e.g. set_language())."""
        from datetime import datetime, timezone
        if self.is_epw_project():
            log.warning("Refused to edit project properties: name, description and author are part of "
                        "projekt.epw and are edited in Studio.")
            return False
        meta = self.config.setdefault("metadata", {})
        meta["name"] = name
        meta["description"] = description
        meta["location"] = location
        meta["author"] = author
        if meta.get("created") is None:
            meta["created"] = datetime.now(timezone.utc).isoformat()

    def touch_metadata_modified(self):
        """Stamps 'now' as the last-modified time - called right before
        ANY project save (task: "aktualizowana przy zapisie" - every
        save, not just a Properties-dialog edit), from main_window.py,
        never from inside save_project() itself (that method's own logic
        is unchanged, per GRANICE). Also backfills "created" if this is
        the first save this project has ever gone through under this
        feature - same "set once" contract as set_metadata()."""
        from datetime import datetime, timezone
        if self.is_epw_project():
            return  # projekt.epw stamps its own modified_at whenever it is written
        meta = self.config.setdefault("metadata", {})
        now = datetime.now(timezone.utc).isoformat()
        if meta.get("created") is None:
            meta["created"] = now
        meta["modified"] = now

    # --- Historian write deadband (Task: ograniczenie zapisow do bazy na
    # ograniczonej trwalosci karcie SD) -----------------------------------
    #
    # A new, OPTIONAL section (config["historian_deadband"]) - same lazy
    # "not in _default_config(), synthesized via .get() with sensible
    # defaults" pattern as metadata/analog_points above: a project.json
    # saved before this feature existed simply has no
    # "historian_deadband" key, and get_deadband_config() already returns
    # workable defaults for that case (GRANICE: no migration required).

    def get_deadband_config(self) -> dict:
        """{"default_threshold", "forced_write_seconds", "per_tag"} - see
        historian.py's DEFAULT_DEADBAND_THRESHOLD/DEFAULT_FORCED_WRITE_SECONDS
        for what an absent section falls back to (this method itself has
        no opinion on those numbers, it just passes through whatever the
        project has, or nothing)."""
        db = self.config.get("historian_deadband", {})
        return {
            "default_threshold": db.get("default_threshold"),
            "forced_write_seconds": db.get("forced_write_seconds"),
            "per_tag": dict(db.get("per_tag", {})),
        }

    def set_deadband_config(self, default_threshold: float = None, forced_write_seconds: float = None,
                             per_tag: dict = None):
        """Any argument left None keeps that part of the section
        unchanged. Caller still needs to call save_project() afterwards,
        same as every other project_manager setter in this codebase."""
        db = self.config.setdefault("historian_deadband", {})
        if default_threshold is not None:
            db["default_threshold"] = float(default_threshold)
        if forced_write_seconds is not None:
            db["forced_write_seconds"] = float(forced_write_seconds)
        if per_tag is not None:
            db["per_tag"] = dict(per_tag)

    def set_tag_deadband(self, tag_name: str, threshold: float):
        """Convenience for setting a single tag's override without having
        to read-modify-write the whole per_tag dict."""
        db = self.config.setdefault("historian_deadband", {})
        per_tag = db.setdefault("per_tag", {})
        per_tag[tag_name] = float(threshold)

    # --- Historian retention (Task: feature/retention-and-test-fix, B1) -
    #
    # A new, OPTIONAL section (config["historian_retention"]) - same lazy
    # ".get(key, {})" pattern as historian_deadband above: a project.json
    # saved before this feature existed simply has no
    # "historian_retention" key, and get_historian_retention_config()
    # already returns the "off" defaults for that case (GRANICE: no
    # migration required, existing installations behave identically to
    # today).

    def get_historian_retention_config(self) -> dict:
        """{"max_days", "max_rows"} - 0 means unlimited/off for that axis.
        See historian.py's DEFAULT_RETENTION_MAX_DAYS/DEFAULT_RETENTION_MAX_ROWS
        for what an absent section falls back to."""
        r = self.config.get("historian_retention", {})
        return {"max_days": int(r.get("max_days", 0) or 0), "max_rows": int(r.get("max_rows", 0) or 0)}

    def set_historian_retention_config(self, max_days: int = None, max_rows: int = None):
        """Any argument left None keeps that part of the section
        unchanged. Caller still needs to call save_project() afterwards,
        same as every other project_manager setter in this codebase."""
        r = self.config.setdefault("historian_retention", {})
        if max_days is not None:
            r["max_days"] = max(0, int(max_days))
        if max_rows is not None:
            r["max_rows"] = max(0, int(max_rows))

    # --- Audit log retention + archival (Task: feature/retention-and-
    # test-fix, B2) - same lazy-optional-section shape as above, but with
    # a third field (archive_dir) since, unlike Historian, the audit log
    # may NEVER be purged without a successful archive write first (see
    # audit_logger.py's own configure_retention()/_enforce_retention()).

    def get_audit_retention_config(self) -> dict:
        """{"max_days", "max_rows", "archive_dir"} - 0 means unlimited/
        off for the two numeric axes; archive_dir "" means "use
        AuditLogger's own built-in default location"."""
        r = self.config.get("audit_retention", {})
        return {
            "max_days": int(r.get("max_days", 0) or 0),
            "max_rows": int(r.get("max_rows", 0) or 0),
            "archive_dir": r.get("archive_dir", "") or "",
        }

    def set_audit_retention_config(self, max_days: int = None, max_rows: int = None, archive_dir: str = None):
        r = self.config.setdefault("audit_retention", {})
        if max_days is not None:
            r["max_days"] = max(0, int(max_days))
        if max_rows is not None:
            r["max_rows"] = max(0, int(max_rows))
        if archive_dir is not None:
            r["archive_dir"] = str(archive_dir)

    # --- Database size warning (Task: feature/retention-and-test-fix,
    # B3) - a single overall threshold, deliberately separate from BOTH
    # retention sections above ("rozmiar bazy", the whole file, not a
    # per-table limit).

    def get_db_size_warning_config(self) -> dict:
        """{"enabled", "threshold_mb"} - off by default (GRANICE)."""
        w = self.config.get("db_size_warning", {})
        return {"enabled": bool(w.get("enabled", False)), "threshold_mb": int(w.get("threshold_mb", 500) or 500)}

    def set_db_size_warning_config(self, enabled: bool = None, threshold_mb: int = None):
        w = self.config.setdefault("db_size_warning", {})
        if enabled is not None:
            w["enabled"] = bool(enabled)
        if threshold_mb is not None:
            w["threshold_mb"] = max(1, int(threshold_mb))

    # --- Intrusion alarm system: zones + supervision lines --------------
    #
    # Two new, OPTIONAL top-level sections (config["intrusion_zones"]/
    # config["intrusion_lines"]) - same lazy ".get(key, [])" pattern as
    # analog_points, keyed by each record's own "id" field rather than a
    # dict keyed by name (a zone/line's user-facing name is freely
    # editable; "id" - "Z1", "L1", ... - is the stable identity every
    # tag path and cross-reference actually uses - see
    # epw_os.core.intrusion_manager._next_id()). A project.json saved
    # before this feature existed simply has neither key, and both
    # accessors below already default to an empty list for that case
    # (GRANICE: no migration required, existing projects keep working).
    # Read/written wholesale by IntrusionManager, not per-field - see
    # that module for the record shapes and why bypass state is
    # deliberately NOT part of what's persisted here.

    def get_intrusion_zones(self) -> list:
        return self.config.get("intrusion_zones", [])

    def set_intrusion_zones(self, zones: list):
        self.config["intrusion_zones"] = list(zones)

    def get_intrusion_lines(self) -> list:
        return self.config.get("intrusion_lines", [])

    def set_intrusion_lines(self, lines: list):
        self.config["intrusion_lines"] = list(lines)

    # Task (line supervision - "nadzor zycia czujek"): a new, OPTIONAL
    # top-level section, keyed by line id (same identity intrusion_lines
    # itself uses) - a project.json saved before this feature existed
    # simply has no key, and the getter already defaults to {} for that
    # case (GRANICE: no migration required). Read/written wholesale by
    # IntrusionManager, periodically flushed (not on every violation) -
    # see intrusion_manager.py's own docstring on why this reuses
    # switching_counters.py's record shape/helpers rather than that
    # module's SwitchingCounterManager class itself.
    def get_intrusion_line_supervision(self) -> dict:
        return self.config.get("intrusion_line_supervision", {})

    def set_intrusion_line_supervision(self, data: dict):
        self.config["intrusion_line_supervision"] = dict(data)

    # Task (nadzor zasilania): a single, OPTIONAL config dict, not a
    # per-id list - there is only ever one mains input and one battery
    # input for the whole system. Missing key = "not configured, no
    # supervision" (GRANICE: "brak konfiguracji oznacza brak nadzoru,
    # bez bledow") - see IntrusionManager.configure_power_supervision().
    def get_intrusion_power_supervision(self) -> dict:
        return self.config.get("intrusion_power_supervision", {})

    def set_intrusion_power_supervision(self, data: dict):
        self.config["intrusion_power_supervision"] = dict(data)

    # Task (pamiec alarmu - "zatrzask", ta sama zasada co safety_kernel):
    # a new, OPTIONAL section keyed by zone id (same identity
    # intrusion_zones itself uses) - a project.json saved before this
    # feature existed simply has no key, and the getter already defaults
    # to {} (GRANICE: no migration required). Written on every alarm
    # cause/clear (not buffered/periodic like line supervision) - an
    # alarm memory record is exactly the kind of low-frequency,
    # safety-relevant write immediate persistence exists for (Task: "MA
    # PRZEZYC restart programu" - must survive even a crash right after
    # the write, not just a clean shutdown). See IntrusionManager's own
    # _record_alarm_cause()/clear_alarm_memory().
    def get_intrusion_alarm_memory(self) -> dict:
        return self.config.get("intrusion_alarm_memory", {})

    def set_intrusion_alarm_memory(self, data: dict):
        self.config["intrusion_alarm_memory"] = dict(data)

    # Task (historia zdarzen alarmowych - retencja): a single, OPTIONAL
    # config dict (system-wide, not per-zone) - IntrusionAlarmHistoryLogger
    # reads this to decide how many rows / how many days of history to
    # keep. Missing key = the logger's own built-in defaults (GRANICE: no
    # migration required) - see intrusion_history.py.
    def get_intrusion_history_retention(self) -> dict:
        return self.config.get("intrusion_history_retention", {})

    def set_intrusion_history_retention(self, data: dict):
        self.config["intrusion_history_retention"] = dict(data)

    # --- Process protections (Zabezpieczenia procesowe - a from-scratch,
    # minimal module built for the page-split task; see
    # process_protection_manager.py) - a list keyed by each protection's
    # own id, same list-of-dicts shape as intrusion_lines above. Missing
    # key = an old project.json, or one where this feature is simply
    # unused - the getter's [] default means "no process protections
    # configured", not an error.
    def get_process_protections(self) -> list:
        return self.config.get("process_protections", [])

    def set_process_protections(self, protections: list):
        self.config["process_protections"] = list(protections)

    # Task ("okno konfiguracji, w ktorym wlacza i wylacza sie
    # poszczegolne funkcje sterownika"): a single, OPTIONAL dict, keyed
    # by feature id (epw_os.core.feature_config.TOGGLABLE_FEATURES),
    # each value a bool. Missing key = old project.json, predating this
    # feature entirely - feature_config.normalize_enabled_features()
    # backfills every togglable feature to True (GRANICE: "Domyslnie
    # WSZYSTKIE funkcje wlaczone... bez migracji"), so this getter
    # deliberately returns the raw, possibly-incomplete dict as-is
    # (same "let the caller normalize" stance intrusion_manager.py's
    # own _normalize_line_filters() callers already follow) rather than
    # duplicating that defaulting logic here too. Configuration belongs
    # to the PROJECT, not the program (Task: "przeniesienie projektu
    # przenosi zestaw funkcji").
    def get_enabled_features(self) -> dict:
        return self.config.get("enabled_features", {})

    def set_enabled_features(self, data: dict):
        if self.is_epw_project():
            log.warning("Refused to change the device composition: modules are defined in projekt.epw (Studio).")
            return False
        self.config["enabled_features"] = dict(data)
        return True

    # --- MQTT integration (Task: "integracja MQTT") ---------------------
    #
    # A single, OPTIONAL section (config["mqtt"]) - same lazy ".get(key,
    # {})" pattern as historian_deadband/enabled_features above, so a
    # project.json saved before this feature existed simply has no "mqtt"
    # key at all (GRANICE: "Integracja MQTT domyslnie WYLACZONA -
    # istniejace instalacje maja dzialac identycznie jak dzis" - no key
    # means get_mqtt_config()'s own "enabled": False default applies, no
    # migration needed). The broker PASSWORD is deliberately NEVER part
    # of this section - see epw_os.core.mqtt_manager's own module
    # docstring for where it actually lives (a separate, gitignored local
    # file, the same "never in project.json or the repo" rule
    # access.local.json/api_tokens.local.json already follow).
    #
    # "link_in" (A5 - incoming Link.* mappings: remote MQTT topic -> local
    # tag name) lives INSIDE this same dict rather than its own top-level
    # section - it's config for the one MqttManager instance, exactly
    # like the broker connection settings themselves, not a separate
    # subsystem with its own lifecycle.

    def get_mqtt_config(self) -> dict:
        """{"enabled", "host", "port", "username", "tls", "client_id",
        "topic_prefix", "publish_interval_s", "default_deadband",
        "deadband_per_tag", "queue_max", "link_in"} - every key has a
        sensible built-in default here (mqtt_manager.py has no opinion of
        its own on defaults; it just receives whatever this returns), so
        an absent section reads exactly like "integration off, nothing
        configured yet" rather than needing separate None-handling at
        every call site."""
        m = self.config.get("mqtt", {})
        return {
            "enabled": bool(m.get("enabled", False)),
            "host": m.get("host", ""),
            "port": int(m.get("port", 1883)),
            "username": m.get("username", ""),
            "tls": bool(m.get("tls", False)),
            "client_id": m.get("client_id", ""),
            "topic_prefix": m.get("topic_prefix", ""),
            "publish_interval_s": float(m.get("publish_interval_s", 2.0)),
            "default_deadband": float(m.get("default_deadband", 0.0)),
            "deadband_per_tag": dict(m.get("deadband_per_tag", {})),
            "queue_max": int(m.get("queue_max", 1000)),
            "link_in": [dict(entry) for entry in m.get("link_in", [])],
        }

    def set_mqtt_config(self, data: dict):
        """Replaces the whole section wholesale (same "read the typed
        dict, mutate, set it back" contract as set_deadband_config()'s
        siblings) - caller still needs to call save_project() afterwards.
        Never accepts a "password" key even if one is passed - a defensive
        pop(), not just a documented convention, so a future caller
        mistake can't leak a credential into project.json."""
        clean = dict(data)
        clean.pop("password", None)
        self.config["mqtt"] = clean

    def get_mqtt_link_mappings(self) -> list:
        return self.get_mqtt_config()["link_in"]

    def set_mqtt_link_mappings(self, mappings: list):
        m = self.config.setdefault("mqtt", {})
        m["link_in"] = [dict(entry) for entry in mappings]

    # --- projekt.epw: what the rest of runtime reads from the project ----

    def get_modules(self) -> list:
        """The device composition (SPEC_PROJEKT_EPW.md, "Skład urządzenia")."""
        return list(self.config.get("modules", []))

    def get_point_registry(self) -> list:
        """[{address, kind, description, location, technical_note}] - the
        location already resolved (a point without its own inherits its
        card's)."""
        return [dict(p) for p in self.config.get("point_registry", [])]

    def get_modbus_bus(self) -> dict:
        """projekt.epw's `modbus_bus` section (transport, port, baud_rate,
        parity, data_bits, stop_bits, host, tcp_port) - project data,
        authored in Studio."""
        bus = self.config.get("modbus_bus")
        return dict(bus) if isinstance(bus, dict) else {}

    def get_io_driver_config(self) -> dict:
        """controller.local.json's "io_driver" section - WHICH I/O driver
        this controller runs (a controller-local choice, like the REST
        port: the same projekt.epw runs on the bench against the
        simulator and on site against the real bus):
            {"driver": "SIM" | "MODBUS", "poll_interval_ms": 250,
             "timeout_s": 1.0, "retries": 1, "ai_signed": false,
             "read_back_outputs": true}
        An absent section is the simulator, exactly as before this
        setting existed."""
        io = self.config.get("io_driver")
        io = io if isinstance(io, dict) else {}
        driver = str(io.get("driver", "SIM") or "SIM").upper()

        def _num(key, default, cast):
            try:
                return cast(io.get(key, default))
            except (TypeError, ValueError):
                return default

        return {
            "driver": driver if driver in ("SIM", "MODBUS") else "SIM",
            "poll_interval_ms": _num("poll_interval_ms", 250, int),
            "timeout_s": _num("timeout_s", 1.0, float),
            "retries": _num("retries", 1, int),
            "ai_signed": bool(io.get("ai_signed", False)),
            "read_back_outputs": bool(io.get("read_back_outputs", True)),
        }

    def get_apparatuses(self) -> list:
        """[{id, behavior, kind, feedback, command}] from the project's
        apparatus register ("devices" in projekt.epw)."""
        return [dict(a) for a in self.config.get("apparatuses", [])]

    def get_electrical_protection_stages(self) -> list:
        return [dict(s) for s in self.config.get("electrical_protection_stages", [])]

    def set_electrical_protection_stages(self, stages: list):
        self.config["electrical_protection_stages"] = [dict(s) for s in stages]

    # --- state that must be written at once ------------------------------

    def get_intrusion_armed_zones(self) -> list:
        return list(self.config.get("intrusion_armed_zones", []))

    def get_intrusion_bypassed_lines(self) -> list:
        return list(self.config.get("intrusion_bypassed_lines", []))

    def set_intrusion_operation_state(self, armed_zones, bypassed_lines, arm_modes=None) -> bool:
        """Which zones are armed, HOW they are armed, and which lines are
        bypassed - written to disk before this returns
        (SPEC_PROJEKT_EPW.md: arming state "musi być natychmiastowy przy
        każdej zmianie"). Returns False when the write failed; the caller
        logs it as an error.

        `arm_modes` is {zone_id: "FULL"|"NIGHT"} for the armed zones;
        None leaves whatever is stored (an older caller that does not
        know about night arming)."""
        self.config["intrusion_armed_zones"] = sorted(armed_zones)
        self.config["intrusion_bypassed_lines"] = sorted(bypassed_lines)
        if arm_modes is not None:
            self.config["intrusion_arm_modes"] = dict(arm_modes)
        return self.save_runtime_state()

    def get_intrusion_arm_modes(self) -> dict:
        """How each armed zone was armed, as last stored. A zone missing
        from it reads as a full arm - what every zone was before night
        arming existed."""
        stored = self.config.get("intrusion_arm_modes")
        return dict(stored) if isinstance(stored, dict) else {}

    def get_intrusion_users(self) -> list:
        """The people allowed to operate the alarm system, from the
        project (shared/project_format.py's IntrusionUser). Their codes
        are NOT here - those live in this controller's own access file,
        keyed by user id (access_manager.py)."""
        return [dict(u) for u in self.config.get("intrusion_users", [])]

    def get_last_screen(self):
        return self.config.get("last_screen")

    def set_last_screen(self, screen_id: str) -> bool:
        if self.config.get("last_screen") == screen_id:
            return True
        self.config["last_screen"] = screen_id
        if not self.is_epw_project():
            return True  # an old project.json is not rewritten on every page change
        return self.save_runtime_state()

    def get_analog_output_points(self) -> list:
        """[{tag, description, technical_note, signal_type, raw_min,
        raw_max, eng_min, eng_max, unit, decimals}] for every AO point of
        the project - the scaling an analog output is written through
        (analog_scaling.compute_raw_value())."""
        return [dict(point) for point in self.config.get("analog_outputs", [])]

    def get_last_synoptic_screen(self):
        """Which screen of the project's `screens` the panel had open."""
        return self.config.get("last_synoptic_screen")

    def set_last_synoptic_screen(self, screen_id) -> bool:
        if self.config.get("last_synoptic_screen") == screen_id:
            return True
        self.config["last_synoptic_screen"] = screen_id
        if not self.is_epw_project():
            return True  # an old project.json is not rewritten on every screen change
        return self.save_runtime_state()

    def set_electrical_stage(self, function_id: str, stage_name: str, level: str = None, **fields) -> bool:
        """One electrical protection stage's settings (enabled/setting/
        hysteresis/delay_ms/action), written back to the project.

        Engineer level, like every other setting change. Lives here, next
        to the stage list itself, so the panel page and a remote command
        change a protection stage through the SAME gated call instead of
        each assembling the record on its own - the shape of bug the REST
        API once had (api_auth.py) was exactly a second path to a change
        that skipped the first path's checks."""
        from epw_os.core.access_manager import AccessLevel
        if level is not None and level != AccessLevel.ENGINEER:
            log.warning(f"Refused to change protection stage {function_id}/{stage_name}: "
                        f"level {level!r} is below Engineer.")
            return False
        allowed = {"enabled", "setting", "hysteresis", "delay_ms", "action"}
        unknown = set(fields) - allowed
        if unknown:
            log.warning(f"Refused to change protection stage {function_id}/{stage_name}: "
                        f"unknown field(s) {', '.join(sorted(unknown))}.")
            return False
        if not fields:
            return False
        stages = self.get_electrical_protection_stages()
        for index, existing in enumerate(stages):
            if existing.get("function_id") == function_id and existing.get("stage_name") == stage_name:
                stages[index] = {**existing, **fields}
                break
        else:
            log.warning(f"Refused to change protection stage {function_id}/{stage_name}: no such stage.")
            return False
        self.set_electrical_protection_stages(stages)
        return self.save_project() is not False

    def get_retentive_signals(self) -> dict:
        """The logic program's retentive internal signals as last stored -
        {"MR.NAME": value}. Empty for a controller that never ran a
        program with any."""
        stored = self.config.get("logic_retentive")
        return dict(stored) if isinstance(stored, dict) else {}

    def set_retentive_signals(self, values: dict) -> bool:
        """Stores them, writing the state file only when something
        actually changed - this is called on a timer while the scan runs,
        and an unchanged M-bit must not cost an SD-card write."""
        values = dict(values or {})
        if self.config.get("logic_retentive") == values:
            return True
        self.config["logic_retentive"] = values
        if not self.is_epw_project():
            return True  # an old project.json is not rewritten for this
        return self.save_runtime_state()

    def save_runtime_state(self) -> bool:
        """Writes only the state part - runtime_state.json for projekt.epw,
        the whole file for an old project.json."""
        if not self.is_epw_project():
            self.save_project()
            return True
        from epw_os.core.runtime_state import RuntimeStateStore
        state = self._part("state")
        if not RuntimeStateStore(self.state_file).save(state):
            return False
        self._saved_parts["state"] = _canonical(state)
        self._saved_snapshot = self._snapshot()
        return True

    def install_project_file(self, source_path, actor=None):
        """Puts a projekt.epw prepared in Studio in place of this
        controller's project file - only after the shared reader accepted
        it, keeping the replaced file as projekt.epw.bak. Takes effect on the
        next start: tags, modules and pages are built from the project once,
        at startup, and swapping them under a running controller is not
        something this method pretends to do. Returns (True, None) or
        (False, {"key", "params", "text"}) with the reader's refusal.

        Task "wysyłanie projektu na sterownik przez REST": the install also
        leaves a `projekt.epw.pending` marker next to the file. The next
        start (_load_epw) removes it once the new file loaded; if the new
        file is refused at that start, the marker says the previous one is
        in `.bak` and it is put back (see _rollback_pending_install) -
        "powrót do .bak przy nieudanym starcie". `actor` (an API level,
        say) names who installed in the audit entry; None = whoever is
        logged in on the panel."""
        from epw_os.core import project_format as pf
        result = pf.read_project(source_path)
        if not result.ok:
            return False, {"key": "project_format." + result.error.key, "params": dict(result.error.params),
                           "text": str(result.error)}
        target = self.project_file if self.is_epw_project() else DEFAULT_PROJECT_FILE
        try:
            if os.path.exists(target) and os.path.samefile(source_path, target):
                return True, None
            payload = open(source_path, "rb").read()
            if os.path.exists(target):
                shutil.copy2(target, target + ".bak")
            temporary = target + ".installing"
            with open(temporary, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, target)
            with open(target + PENDING_INSTALL_SUFFIX, "w", encoding="utf-8") as f:
                json.dump({"revision": result.project.revision, "modified_by": result.project.modified_by,
                           "source": str(source_path)}, f)
        except OSError as e:
            return False, {"key": "project_format.unreadable", "params": {"detail": str(e)}, "text": str(e)}
        self._audit("PROJECT_FILE_INSTALLED",
                    f"{source_path} installed as {target} (revision {result.project.revision}, "
                    f"last saved by {result.project.modified_by}) - active after restart",
                    actor=actor)
        return True, None

    def project_file_bytes(self):
        """The project file exactly as it is on disk (GET
        /api/v1/project/file - "Zgraj z urządzenia"), or None."""
        if not self.is_epw_project() or not os.path.exists(self.project_file):
            return None
        with open(self.project_file, "rb") as f:
            return f.read()

    def _rollback_pending_install(self, path, refusal):
        """Called by _load_epw when `path` was refused: if a pending-install
        marker and a .bak exist, the previous project comes back and the
        refused file is kept as `.rejected` for inspection. Returns True
        when a rollback happened (the caller then reads `path` again)."""
        marker = str(path) + PENDING_INSTALL_SUFFIX
        backup = str(path) + ".bak"
        if not os.path.exists(marker) or not os.path.exists(backup):
            return False
        try:
            os.replace(str(path), str(path) + ".rejected")
            shutil.copy2(backup, str(path))
            os.remove(marker)
        except OSError as e:
            log.error(f"Rollback of {path} to {backup} failed: {e}")
            return False
        self.rolled_back = {"path": str(path), "backup": backup, "rejected": str(path) + ".rejected",
                            "reason": refusal}
        log.error(f"Installed project {path} was refused ({refusal}) - the previous file was put back from "
                  f"{backup}; the refused one is kept as {self.rolled_back['rejected']}.")
        return True

    # --- projekt.epw: header, audit ---------------------------------------

    def set_audit_sink(self, audit_logger, actor_provider=None):
        """Settings written back to projekt.epw are audited here, the one
        place every writer passes through. `actor_provider()` returns who
        is logged in (EPWCore passes the access manager's level)."""
        self._audit_logger = audit_logger
        self._actor_provider = actor_provider

    def _audit(self, event_type: str, detail: str, success: bool = True, actor=None):
        if self._audit_logger is None:
            return
        if actor:
            self._audit_logger.record(event_type, actor, detail, success=success)
            return
        actor = "SYSTEM"
        if self._actor_provider is not None:
            try:
                actor = self._actor_provider() or "SYSTEM"
            except Exception:
                actor = "SYSTEM"
        self._audit_logger.record(event_type, actor, detail, success=success)

    def local_settings(self) -> dict:
        """controller.local.json as it is in memory - what stays on THIS
        controller (language, REST host/port, retentions, the database
        size warning, the I/O driver, file paths). Read-only for Studio
        through GET /api/v1/controller/settings, so nothing on the
        controller is invisible from Studio; a plain project.json
        installation has no such part and reports {}."""
        if not self.is_epw_project():
            return {}
        return json.loads(_canonical(self._part("settings")))

    def get_project_header(self) -> dict:
        """What GET /api/v1/project reports - which project the controller
        runs and which revision of it (task etap 5.2)."""
        if not self.is_epw_project():
            return {"source": "project.json", "path": os.path.abspath(self.project_file), "loaded": True,
                    "name": self.get_metadata().get("name") or self.config.get("project_id", ""),
                    "revision": None, "modified_by": None, "modified_at": None, "load_error": None}
        from epw_os.core import project_format as pf
        project = self.project
        header = {
            "source": "projekt.epw",
            "path": os.path.abspath(self.project_file),
            "format": pf.FORMAT_MARKER,
            "schema_version": pf.SCHEMA_VERSION,
            "loaded": project is not None,
            "load_error": self.load_error["text"] if self.load_error else None,
            "warnings": [str(w) for w in self.load_warnings],
        }
        if project is not None:
            header.update({
                "name": project.metadata.name,
                "description": project.metadata.description,
                "author": project.metadata.author,
                "created_at": project.metadata.created_at,
                "modified_at": project.metadata.modified_at,
                "revision": project.revision,
                "modified_by": project.modified_by,
                # SPEC "Wersjonowanie" - what Studio compares before sending.
                "settings_hash": pf.settings_hash(project),
                "modules": list(project.modules),
                "counts": {
                    "cards": len(project.cards), "points": len(project.points), "devices": len(project.devices),
                    "zones": len(project.zones), "lines": len(project.lines),
                    "process_protections": len(project.process_protections),
                    "electrical_protection_stages": len(project.electrical_protection_stages),
                },
            })
        return header

    # --- projekt.epw: reading and writing ---------------------------------

    def _part(self, name: str) -> dict:
        from epw_os.core.project_epw import PROJECT_KEYS
        from epw_os.core.runtime_state import STATE_KEYS, default_state
        if name == "project":
            return {key: self.config.get(key) for key in PROJECT_KEYS}
        if name == "state":
            defaults = default_state()
            return {key: self.config.get(key, defaults[key]) for key in STATE_KEYS}
        return {key: value for key, value in self.config.items()
                if key not in PROJECT_KEYS and key not in STATE_KEYS}

    def _empty_project(self):
        from epw_os.core import project_format as pf
        return pf.Project(metadata=pf.ProjectMetadata(name=""))

    def _load_epw(self, path) -> bool:
        """Never raises. A missing or refused projekt.epw leaves runtime
        with an EMPTY project (no cards, no modules) and `load_error` set -
        the controller still comes up and says why, instead of dying at
        startup (task point 1.2). A refused file is never overwritten:
        _write_project_settings() refuses while `self.project` is None."""
        from epw_os.core import project_format as pf
        from epw_os.core.local_json import read_json_object
        from epw_os.core.project_epw import PROJECT_KEYS, build_project_view
        from epw_os.core.runtime_state import STATE_KEYS, RuntimeStateStore

        store = RuntimeStateStore(self.state_file)
        state = store.load()
        self.state_load_problem = store.load_problem

        settings, settings_problem = read_json_object(self.settings_file)
        if settings_problem == "corrupt":
            log.error(f"Controller settings {self.settings_file} are unreadable - defaults used.")
        settings = {key: value for key, value in (settings or {}).items()
                    if key not in ("format", "schema_version") and key not in PROJECT_KEYS and key not in STATE_KEYS}

        self.load_warnings = []
        self.rolled_back = None
        if not os.path.exists(path):
            self.project = None
            self.load_error = {"key": "startup.project_missing", "params": {"path": str(path)},
                               "text": f"No project file at {path}."}
        else:
            result = pf.read_project(path)
            if not result.ok and self._rollback_pending_install(path, str(result.error)):
                result = pf.read_project(path)
            if result.ok:
                self.project = result.project
                self.load_error = None
                self.load_warnings = list(result.warnings)
                marker = str(path) + PENDING_INSTALL_SUFFIX
                if os.path.exists(marker):
                    try:
                        os.remove(marker)   # the installed project started - nothing to roll back any more
                    except OSError:
                        pass
            else:
                self.project = None
                self.load_error = {"key": "project_format." + result.error.key, "params": dict(result.error.params),
                                   "text": str(result.error)}

        view = build_project_view(self.project if self.project is not None else self._empty_project())
        self.config = {**settings, **view, **state}

        for warning in self.load_warnings:
            log.warning(f"{path}: {warning}")
        if self.load_error:
            log.error(f"Project {path} was not loaded: {self.load_error['text']} "
                      f"Runtime starts with an empty project.")
        else:
            log.info(f"Loaded project {path}: '{self.project.metadata.name}', revision {self.project.revision} "
                     f"(last saved by {self.project.modified_by}).")
        self._mark_clean()
        return self.project is not None

    def _save_epw(self) -> bool:
        from epw_os.core.local_json import atomic_write_json
        ok = True
        if _canonical(self._part("state")) != self._saved_parts.get("state"):
            ok = self.save_runtime_state() and ok
        settings = self._part("settings")
        if _canonical(settings) != self._saved_parts.get("settings"):
            try:
                atomic_write_json(self.settings_file, {"format": SETTINGS_FORMAT, "schema_version": 1, **settings})
                self._saved_parts["settings"] = _canonical(settings)
            except OSError as e:
                log.error(f"Could not write controller settings {self.settings_file}: {e}")
                ok = False
        if _canonical(self._part("project")) != self._saved_parts.get("project"):
            ok = self._write_project_settings() and ok
        self._saved_snapshot = self._snapshot()
        return ok

    def _restore_project_view(self):
        from epw_os.core.project_epw import PROJECT_KEYS, build_project_view
        view = build_project_view(self.project if self.project is not None else self._empty_project())
        for key in PROJECT_KEYS:
            self.config[key] = view[key]
        self._saved_parts["project"] = _canonical(self._part("project"))

    def _write_project_settings(self) -> bool:
        """Etap 4: a setting changed on the panel goes back into
        projekt.epw - revision + 1, modified_by "panel", one audit entry per
        changed value. Anything structural in the difference refuses the
        whole write (and is audited as refused); the in-memory sections
        are put back to what the project says."""
        from epw_os.core import project_format as pf
        from epw_os.core.project_epw import apply_changes, diff_settings

        if self.project is None:
            log.error("Refused to write settings: no valid projekt.epw is loaded, and a file that could not "
                      "be read is never overwritten.")
            self._restore_project_view()
            return False

        diff = diff_settings(self.project, self.config)
        if diff.structural:
            detail = "Structural change(s) refused - edit the project in Studio: " + ", ".join(diff.structural)
            log.error(detail)
            self._audit("PROJECT_STRUCTURE_CHANGE_REFUSED", detail, success=False)
            self._restore_project_view()
            return False

        if diff.changes:
            apply_changes(self.project, diff.changes)
            try:
                pf.save_project(self.project, self.project_file, modified_by="panel")
            except OSError as e:
                log.error(f"Could not write settings to {self.project_file}: {e}")
                self._audit("PROJECT_SETTING_WRITE_FAILED", str(e), success=False)
                return False
            for change in diff.changes:
                self._audit("PROJECT_SETTING_CHANGED",
                            f"{change.describe()} (projekt.epw revision {self.project.revision})")
            log.info(f"Wrote {len(diff.changes)} setting change(s) to {self.project_file}, "
                     f"revision {self.project.revision}.")
        self._restore_project_view()
        return True
