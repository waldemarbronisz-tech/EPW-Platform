import json
import os
from epw_os.core.logging import log

# Absolute, anchored to the repo root (same directory as main.py) - not
# relative to the process's CWD. A relative default here would silently
# create/read a *different* project.json depending on where the app is
# launched from (see AccessManager.DEFAULT_CONFIG_PATH for the confirmed
# real-world case of this exact bug class with access.local.json).
DEFAULT_PROJECT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "project.json")

PROJECT_FORMAT = "EPW_OS_PROJECT"
PROJECT_SCHEMA_VERSION = 1

DEFAULT_LANGUAGE = "en"


class ProjectManager:
    def __init__(self, project_file: str = None):
        self.project_file = project_file or DEFAULT_PROJECT_FILE
        self.config = {}
        # JSON snapshot of the last state that is known to match disk. Used
        # by is_dirty() to drive the "unsaved changes" prompt in the File
        # menu. None until the first load/save.
        self._saved_snapshot = None

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
        return json.dumps(self.config, sort_keys=True, ensure_ascii=False)

    def _mark_clean(self):
        self._saved_snapshot = self._snapshot()

    def is_dirty(self) -> bool:
        """True when self.config has changed since the last load/save - i.e.
        there is unsaved work. A freshly created (never-saved) project also
        counts as dirty."""
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
        self._write(self.project_file)
        self._mark_clean()

    def save_project_as(self, path: str):
        """Make `path` the active project file and write to it."""
        self.project_file = path
        self.save_project()

    def new_project(self):
        """Reset to a blank in-memory project. Not written to disk until the
        operator saves - so it shows up as unsaved (is_dirty() -> True)."""
        self.config = self._default_config()
        # deliberately do NOT _mark_clean(): a brand-new project is unsaved

    def load_from(self, path: str) -> bool:
        """Open an external project file and make it the active project."""
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
        data = self._read(path)
        if data is None or not self._is_valid(data):
            log.error(f"Invalid project format in {path}.")
            return False
        self.config = data
        self.save_project()
        return True

    def export_to(self, path: str):
        """Write a standalone backup copy of the current project. The active
        project file is unchanged and dirty state is untouched."""
        self._write(path)

    # --- typed accessors ------------------------------------------

    def get_synoptic_file(self):
        return self.config.get("synoptic_project")

    def get_logic_file(self):
        return self.config.get("logic_project")

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
        self.config.setdefault("tag_descriptions", {})[name] = description

    def get_tag_descriptions(self) -> dict:
        return self.config.get("tag_descriptions", {})

    def set_output_description(self, name: str, description: str):
        """Persisted custom label for a Control Outputs row, keyed by its
        visible Tag column text (e.g. "DO02") - see SwitchingDeviceRow in
        page_control_outputs.py. Separate namespace from
        set_tag_description() since DO0N tags aren't real TagManager tags
        for the first 4 rows: DO01-DO04 resolve their live state from
        DI1-DI4 instead of their own DO tag (see epw_core.py's default
        command definitions), even though their command-routing
        designation is the DO0N tag itself, same as every other channel."""
        self.config.setdefault("output_descriptions", {})[name] = description

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
        self.config["enabled_features"] = dict(data)

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
