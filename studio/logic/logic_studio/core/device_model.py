from logic_studio.core.addressing import format_address


class DeviceModel:
    """Centralized definition of EPW Controller IO topology.

    Task "jedno źródło listy kart": cards are now defined ONCE, in the
    Studio project (studio/shell/project_format.py's Card list) - every
    other program only READS them. When Logic Studio is embedded in
    Studio (LogicPanel), `project.external_cards` (set by LogicPanel,
    never serialized - see Project.__init__'s own comment) is a live
    mirror of Studio's real Card list: [{"id", "kind", "channels"}, ...],
    `kind` one of "DI"/"DO" (Studio's AI/AO cards have no Logic Studio
    module-list equivalent - analog points remain their own, separate,
    address-based mechanism, project.settings["analog_points"], untouched
    by this task). Every getter below checks `_external_family()` FIRST -
    when present, it is the ONLY source, entirely superseding
    project.settings["ela_devices"/"ela_channels"/...] for that project
    instance; the old settings are left in place on disk (never migrated
    away, GRANICE) but simply unused while a host is bridged in.

    project.settings["ela_devices"]/["ada_devices"] remain the source for
    a project with NO bridge (Logic Studio run standalone via
    studio/logic/main.py, still editable through Project Settings ->
    Urządzenia) - a real, user-typed device list, not a hidden default.
    A genuinely UNCONFIGURED project (nothing in `ela_devices` at all)
    now returns an EMPTY list rather than silently inventing "ELA01" -
    exactly the disease this task's own report described ("adresy,
    których w jego projekcie NIE MA"). Project.__init__ seeds both lists
    empty for this reason; Project.deserialize()'s own migration default
    for pre-multi-device FILES (which really did always mean exactly one
    implicit ELA01/ADA01 before this feature existed) is unaffected -
    see that method's own comment.

    ONE channel count per kind (ELA_CHANNELS/ADA_CHANNELS) remains the
    rule for the project.settings-based (non-bridged) path - every ELA
    module in a standalone project still shares one channel count, same
    as before. A bridged project has NO such limit: each external card
    carries its own `channels`, exactly matching Studio's own per-card
    Card.channels (get_ela_device_channels()/get_ada_device_channels()
    below are what both get_ela_addresses() and device_explorer.py's own
    tree build from, so the two can never disagree)."""

    ELA_CHANNELS = 32
    ADA_CHANNELS = 32
    MAX_CHANNELS = 256  # a sanity ceiling for set_ela_channels/set_ada_channels, not a platform limit

    @classmethod
    def _external_family(cls, project, kind: str):
        """None if `project` has no bridged Studio card list at all (the
        project.settings-based mechanism applies) - otherwise the
        {"id", "channels"} dicts for exactly this kind ("DI" or "DO"),
        in Studio's own card order. See this class's own docstring."""
        cards = getattr(project, "external_cards", None) if project is not None else None
        if cards is None:
            return None
        return [{"id": c["id"], "channels": c["channels"]} for c in cards if c.get("kind") == kind]

    @classmethod
    def get_ela_devices(cls, project=None) -> list:
        ext = cls._external_family(project, "DI")
        if ext is not None:
            return [c["id"] for c in ext]
        if project is None:
            return []
        return list(project.settings.get("ela_devices", []))

    @classmethod
    def get_ada_devices(cls, project=None) -> list:
        ext = cls._external_family(project, "DO")
        if ext is not None:
            return [c["id"] for c in ext]
        if project is None:
            return []
        return list(project.settings.get("ada_devices", []))

    @classmethod
    def get_ela_channels(cls, project=None) -> int:
        """The ONE shared channel count for the project.settings-based
        (non-bridged) path only - a bridged project has no single count
        at all, see get_ela_device_channels()."""
        if project is None:
            return cls.ELA_CHANNELS
        return project.settings.get("ela_channels", cls.ELA_CHANNELS)

    @classmethod
    def get_ada_channels(cls, project=None) -> int:
        if project is None:
            return cls.ADA_CHANNELS
        return project.settings.get("ada_channels", cls.ADA_CHANNELS)

    @classmethod
    def get_ela_device_channels(cls, project=None) -> list:
        """[(device_id, channel_count), ...] for every ELA device, in
        order - device_explorer.py's own tree build uses this directly
        (instead of get_ela_channels()+get_ela_devices() separately) so
        a bridged project's per-card channel counts are never flattened
        back into one shared number."""
        ext = cls._external_family(project, "DI")
        if ext is not None:
            return [(c["id"], c["channels"]) for c in ext]
        channels = cls.get_ela_channels(project)
        return [(dev, channels) for dev in cls.get_ela_devices(project)]

    @classmethod
    def get_ada_device_channels(cls, project=None) -> list:
        ext = cls._external_family(project, "DO")
        if ext is not None:
            return [(c["id"], c["channels"]) for c in ext]
        channels = cls.get_ada_channels(project)
        return [(dev, channels) for dev in cls.get_ada_devices(project)]

    @classmethod
    def set_ela_channels(cls, project, count: int) -> int:
        """Validates and stores the project's ELA channel count. Returns
        the value actually stored (falls back to ELA_CHANNELS for
        anything not a positive int within MAX_CHANNELS, same "never
        store garbage, never raise on a bad UI value" stance
        _set_devices() already has for device names)."""
        return cls._set_channels(project, "ela_channels", count, cls.ELA_CHANNELS)

    @classmethod
    def set_ada_channels(cls, project, count: int) -> int:
        return cls._set_channels(project, "ada_channels", count, cls.ADA_CHANNELS)

    @classmethod
    def _set_channels(cls, project, settings_key: str, count, default: int) -> int:
        if not isinstance(count, int) or isinstance(count, bool) or not (1 <= count <= cls.MAX_CHANNELS):
            count = default
        project.settings[settings_key] = count
        return count

    @classmethod
    def format_ela_address(cls, dev: str, channel: int) -> str:
        return format_address(dev, "DI", channel)

    @classmethod
    def format_ada_address(cls, dev: str, channel: int) -> str:
        return format_address(dev, "DO", channel)

    @classmethod
    def get_ela_addresses(cls, project=None):
        """Returns device-qualified ELA inputs (platform grammar -
        addressing.format_address()), across EVERY ELA device the
        project defines, each using ITS OWN channel count (see
        get_ela_device_channels())."""
        return [
            cls.format_ela_address(dev, i)
            for dev, channels in cls.get_ela_device_channels(project)
            for i in range(1, channels + 1)
        ]

    @classmethod
    def get_ada_addresses(cls, project=None):
        """Returns device-qualified ADA outputs (platform grammar), across
        EVERY ADA device the project defines, each using ITS OWN channel
        count (see get_ada_device_channels())."""
        return [
            cls.format_ada_address(dev, i)
            for dev, channels in cls.get_ada_device_channels(project)
            for i in range(1, channels + 1)
        ]

    _DEVICE_NAME_RE_CACHE = {}

    @classmethod
    def _device_name_pattern(cls, prefix: str):
        """"ELA" -> ^ELA\\d{2}$, "ADA" -> ^ADA\\d{2}$ — the naming
        convention every existing device name (and every reference to one
        elsewhere in the app: system_signals_catalog.json's "ELA01.ONLINE"
        etc., every doc/tooltip example) already assumes. Enforced on ADD
        (set_ela_devices/set_ada_devices below), not just documented, so a
        typo can't silently produce addresses like "ELA1.DI01" that would
        never match anything a block's Address combobox offers."""
        import re
        pattern = cls._DEVICE_NAME_RE_CACHE.get(prefix)
        if pattern is None:
            pattern = re.compile(rf"^{prefix}\d{{2}}$")
            cls._DEVICE_NAME_RE_CACHE[prefix] = pattern
        return pattern

    @classmethod
    def is_valid_device_name(cls, prefix: str, name: str) -> bool:
        return bool(cls._device_name_pattern(prefix).match(name or ""))

    @classmethod
    def set_ela_devices(cls, project, devices: list) -> list:
        """Validates (§ is_valid_device_name), de-duplicates (order-
        preserving) and stores `devices` as the project's ELA module list.
        Returns the list actually stored (empty/invalid entries dropped) —
        callers building an editor UI should re-read this back rather than
        assume every entry they passed survived."""
        return cls._set_devices(project, "ela_devices", "ELA", devices)

    @classmethod
    def set_ada_devices(cls, project, devices: list) -> list:
        return cls._set_devices(project, "ada_devices", "ADA", devices)

    @classmethod
    def _set_devices(cls, project, settings_key: str, prefix: str, devices: list) -> list:
        """Task "jedno źródło listy kart": no more falling back to a
        hardcoded "ELA01"/"ADA01" when every entry the caller passed was
        invalid - an empty result is the honest answer (nothing valid
        was provided), not an invented device the user never asked for."""
        seen = set()
        clean = []
        for name in devices or []:
            name = (name or "").strip().upper()
            if name and cls.is_valid_device_name(prefix, name) and name not in seen:
                seen.add(name)
                clean.append(name)
        project.settings[settings_key] = clean
        return clean

    @classmethod
    def next_device_name(cls, prefix: str, existing: list) -> str:
        """The next unused "<prefix><NN>" name — "ELA03" after
        ["ELA01","ELA02"] — for an "Add device" button to prefill rather
        than making the user invent a name by hand."""
        used_numbers = set()
        pattern = cls._device_name_pattern(prefix)
        for name in existing:
            if pattern.match(name or ""):
                used_numbers.add(int(name[len(prefix):]))
        n = 1
        while n in used_numbers:
            n += 1
        return f"{prefix}{n:02d}"

    # ---- Analog points -------------------------------------------------------
    # Unlike DI/DO, analog points have no fixed hardware channel count — they
    # are entirely defined by the project (project.settings["analog_points"]),
    # so these operate on a `project`, not on class-level constants.

    @classmethod
    def get_analog_points(cls, project) -> list:
        return list(project.settings.get("analog_points", []))

    @classmethod
    def get_analog_input_addresses(cls, project) -> list:
        return [p["address"] for p in cls.get_analog_points(project) if p.get("direction") == "input"]

    @classmethod
    def get_analog_output_addresses(cls, project) -> list:
        return [p["address"] for p in cls.get_analog_points(project) if p.get("direction") == "output"]

    @classmethod
    def get_analog_point(cls, project, address):
        for p in cls.get_analog_points(project):
            if p.get("address") == address:
                return p
        return None

    # ---- I/O labels (feat/io-labels-and-ids §1) -------------------------------
    # Descriptive labels for physical (ELA/ADA) and analog addresses —
    # project.settings["io_labels"], address -> label. Reference: e²TANGO's
    # "Etykiety i LED" configuration category (DTR §2.7.7) — labels
    # assigned to addresses are used as fragments of event texts, as
    # descriptions in logic, and on state-overview screens, "available
    # throughout the program interchangeably with physical addresses".
    # Every reader goes through get_io_label()/get_labelled_addresses()
    # here, never project.settings["io_labels"] directly, so the storage
    # shape (currently a flat dict) can change without every call site
    # needing to know.

    MAX_IO_LABEL_LENGTH = 64

    @classmethod
    def get_io_label(cls, project, address: str) -> str:
        """The label assigned to `address`, or "" if none (project.settings
        never stores an empty-string entry — see set_io_label)."""
        return project.settings.get("io_labels", {}).get(address, "")

    @classmethod
    def set_io_label(cls, project, address: str, label: str):
        """§1.2: any text is accepted (Polish diacritics/spaces included —
        unlike an internal-signal name, a label is never used as an
        identifier), truncated to MAX_IO_LABEL_LENGTH rather than rejected.
        An empty (post-strip) label REMOVES the entry instead of storing
        "" — io_labels is meant to answer "does this address have a
        label"; a stored empty string would make every reader re-implement
        that emptiness check itself."""
        io_labels = project.settings.setdefault("io_labels", {})
        label = (label or "").strip()[:cls.MAX_IO_LABEL_LENGTH]
        if label:
            io_labels[address] = label
        else:
            io_labels.pop(address, None)

    @classmethod
    def get_labelled_addresses(cls, project) -> dict:
        """A copy of the full address -> label mapping (never the live
        dict — callers must go through set_io_label() to write)."""
        return dict(project.settings.get("io_labels", {}))

    @classmethod
    def all_addresses(cls, project) -> list:
        """Every address a label (or the §2 editor table) could apply to:
        every ELA/ADA channel across every device the project defines,
        plus every analog point the project currently defines."""
        return (
            cls.get_ela_addresses(project) + cls.get_ada_addresses(project)
            + cls.get_analog_input_addresses(project) + cls.get_analog_output_addresses(project)
        )

    # ---- Internal signal registry (feat/internal-bits §1.4) ------------------
    # Also entirely project-defined (project.settings["internal_bits"]) —
    # see core/internal_bits.py for the entry shape and internal_bit_id().

    @classmethod
    def get_internal_bits(cls, project, type_filter: str = None) -> list:
        entries = list(project.settings.get("internal_bits", []))
        if type_filter is not None:
            entries = [e for e in entries if e.get("type") == type_filter]
        return entries

    @classmethod
    def get_internal_bit(cls, project, name: str):
        for e in cls.get_internal_bits(project):
            if e.get("name", "").lower() == (name or "").lower():
                return e
        return None
