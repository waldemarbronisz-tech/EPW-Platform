"""What a screen object shows right now - pure Python, no Qt, so the
rules are testable on their own.

A screen object (SynopticObject in the editor) carries graphics and a
`deviceId`; everything about the apparatus lives in the project's own
register (SPEC_PROJEKT_EPW.md: "Obiekt ekranu niesie tylko grafikę i
deviceId"). The runtime's ApparatusRegistry holds that register
(Apparatus: behavior, feedback[0] = the CLOSED/ON contact, command...),
and TagManager holds the live values. This module joins the two:

  SWITCHED / SIGNAL  feedback[0] True  -> the symbol's "asserted" state
                     feedback[0] False -> its "released" state
                     tag missing / not GOOD -> FAULT when the symbol has
                     one, else the released state
  MEASURED           value + unit for a display symbol's text
  SELECTOR           position index -> LEFT/CENTER/RIGHT when the symbol
                     has those

Which state name means "asserted" depends on the symbol's own
vocabulary (a breaker CLOSES, a lamp goes ON, a fan RUNS, a valve
OPENS): pick_state() looks through the symbol's allowed states in a
fixed preference order, and treats water valves/dampers the other way
round (their energized contact opens them). An object bound to nothing
draws the symbol's default state.
"""
from epw_os.core.logging import log

ASSERTED_STATES = ("CLOSED", "ON", "RUNNING", "RUN", "ENERGIZED", "ACTIVE", "HEATING", "LIVE", "HIGH", "ALARM")
RELEASED_STATES = ("OPEN", "OFF", "STOP", "DEENERGIZED", "NORMAL", "DEAD", "LOW", "INACTIVE")
# Symbols whose energized contact means "flow": open, not closed.
FLOW_TYPE_MARKERS = ("valve", "damper", "drain", "gate")
GOOD_QUALITIES = ("GOOD", "UNCERTAIN")


def _is_flow_symbol(symbol_type: str) -> bool:
    lowered = (symbol_type or "").lower()
    return any(marker in lowered for marker in FLOW_TYPE_MARKERS)


def pick_state(symbol_type: str, allowed_states, asserted: bool, default_state: str = "NORMAL") -> str:
    """The state name a symbol of `symbol_type` shows for an asserted /
    released feedback, from its own allowed list."""
    allowed = list(allowed_states or [])
    if not allowed:
        return default_state or "NORMAL"
    if _is_flow_symbol(symbol_type):
        order = ("OPEN", "ON", "RUNNING", "ACTIVE", "LIVE") if asserted else ("CLOSED", "OFF", "NORMAL", "INACTIVE", "DEAD")
    else:
        order = ASSERTED_STATES if asserted else RELEASED_STATES
    for name in order:
        if name in allowed:
            return name
    return default_state if default_state in allowed else allowed[0]


def fault_state(allowed_states, fallback: str) -> str:
    return "FAULT" if "FAULT" in (allowed_states or []) else fallback


def selector_state(allowed_states, position_index, default_state):
    names = ("LEFT", "CENTER", "RIGHT")
    allowed = list(allowed_states or [])
    if position_index is None or not all(n in allowed for n in names):
        return default_state
    if position_index <= 0:
        return "LEFT"
    if position_index == 1:
        return "CENTER"
    return "RIGHT"


class TagReader:
    """Thin, tolerant view of TagManager (or any object with get_tag())."""

    def __init__(self, tag_manager):
        self._tags = tag_manager

    def read(self, tag_name):
        """(value, quality_name) - (None, None) when the tag does not exist."""
        if not tag_name or self._tags is None:
            return None, None
        getter = getattr(self._tags, "get_tag", None)
        tag = getter(tag_name) if callable(getter) else None
        if tag is None:
            return None, None
        quality = getattr(tag, "quality", None)
        quality_name = getattr(quality, "value", quality)
        return getattr(tag, "value", None), (str(quality_name) if quality_name is not None else None)


def format_value(value, decimals=1) -> str:
    if value is None:
        return "---"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return f"{value:.{decimals}f}" if isinstance(value, float) else str(value)
    return str(value)


class ObjectPresentation:
    """Everything the renderer needs for one object: the symbol state,
    the per-instance template fields, whether it is commandable and
    what its command target is."""

    __slots__ = ("state", "fields", "apparatus", "commandable", "bound", "live")

    def __init__(self, state, fields, apparatus=None, commandable=False, bound=False, live=False):
        self.state = state
        self.fields = fields
        self.apparatus = apparatus
        self.commandable = commandable
        self.bound = bound
        self.live = live


def present_object(obj: dict, geometry, apparatus_registry, tag_reader: TagReader,
                   analog_units=None) -> ObjectPresentation:
    """`obj`: a raw screen object dict; `geometry`: SymbolGeometry (or
    None); `apparatus_registry`: ApparatusRegistry (or None);
    `analog_units`: {tag: unit} for MEASURED displays."""
    symbol_type = obj.get("type") or ""
    allowed = geometry.allowed_states(symbol_type) if geometry is not None else []
    default_state = geometry.default_state(symbol_type) if geometry is not None else "NORMAL"
    fields = {
        "text": obj.get("text") or "",
        "fill": obj.get("fill") or "",
        "border": obj.get("border") or "",
        "color": obj.get("color") or "",
        "font": obj.get("font") or "",
        "fontSize": obj.get("fontSize") or 0,
        "designation": obj.get("designation") or "",
        "name": obj.get("name") or "",
        "description": obj.get("description") or "",
        "tag": obj.get("tag") or "",
        "textColor": obj.get("textColor") or "",
        "circuit": obj.get("circuit") or "",
        "value": "",
        "unit": (obj.get("editor") or {}).get("unit") or "",
    }
    device_id = obj.get("deviceId")
    apparatus = apparatus_registry.get(device_id) if (apparatus_registry is not None and device_id) else None
    if apparatus is None:
        preview = (obj.get("editor") or {}).get("preview_state")
        state = preview if preview in allowed else default_state
        return ObjectPresentation(state, fields, bound=bool(device_id))

    behavior = (apparatus.behavior or "").upper()
    feedback = list(apparatus.feedback or [])
    if behavior in ("SWITCHED", "SIGNAL"):
        value, quality = tag_reader.read(feedback[0] if feedback else None)
        if value is None or quality not in GOOD_QUALITIES:
            released = pick_state(symbol_type, allowed, False, default_state)
            state = fault_state(allowed, released) if feedback else default_state
            live = False
        else:
            state = pick_state(symbol_type, allowed, bool(value), default_state)
            live = True
        commandable = behavior == "SWITCHED" and bool(apparatus.command)
        return ObjectPresentation(state, fields, apparatus, commandable=commandable, bound=True, live=live)

    if behavior == "MEASURED":
        tag_name = feedback[0] if feedback else None
        value, quality = tag_reader.read(tag_name)
        fields["value"] = format_value(value) if quality in GOOD_QUALITIES else "---"
        if not fields["unit"] and analog_units:
            fields["unit"] = analog_units.get(tag_name, "") or ""
        if not fields["tag"] and tag_name:
            fields["tag"] = tag_name
        state = fault_state(allowed, default_state) if (value is None or quality not in GOOD_QUALITIES) else default_state
        return ObjectPresentation(state, fields, apparatus, bound=True, live=value is not None)

    if behavior == "SELECTOR":
        index = None
        for n, tag_name in enumerate(feedback):
            value, quality = tag_reader.read(tag_name)
            if value and quality in GOOD_QUALITIES:
                index = n
                break
        return ObjectPresentation(selector_state(allowed, index, default_state), fields, apparatus, bound=True,
                                  live=index is not None)

    if behavior == "MODULATED":
        tag_name = feedback[0] if feedback else None
        value, quality = tag_reader.read(tag_name)
        fields["value"] = format_value(value) if quality in GOOD_QUALITIES else "---"
        return ObjectPresentation(default_state, fields, apparatus, bound=True, live=value is not None)

    log.debug(f"Screen object {obj.get('id')}: apparatus {device_id} has behavior {behavior!r} - default state drawn.")
    return ObjectPresentation(default_state, fields, apparatus, bound=True)


def command_for_toggle(apparatus, tag_reader: TagReader):
    """The command action ("CLOSE"/"OPEN") that would change a SWITCHED
    apparatus's state, judged from its CLOSED contact; None when it
    cannot be judged (no feedback / not GOOD)."""
    if apparatus is None or not apparatus.command:
        return None
    feedback = list(apparatus.feedback or [])
    if not feedback:
        return "CLOSE"
    value, quality = tag_reader.read(feedback[0])
    if value is None or quality not in GOOD_QUALITIES:
        return None
    return "OPEN" if value else "CLOSE"
