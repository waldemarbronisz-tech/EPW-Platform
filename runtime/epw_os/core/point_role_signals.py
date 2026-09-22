"""PWR / UPS / PROT bits carried by a contact on a digital input
(etap 4 of the signal register; the roles themselves:
shared/logic/point_roles.py).

Studio's point registry gives a DI point a role and a contact type;
this source reads the input's tag and exposes the register bit under
the very name an EPM or an ADA01 would have given it. It is asked
BEFORE core/device_signals.py, so a role assigned in the project wins
over the device block for that one bit - and says so once in the log,
because two sources of one bit is something the engineer should have
seen in Studio's "Sprawdź projekt" already (4.4).

Rule Z4: an input whose quality is not GOOD (card silent, never read,
forced bad) gives the catalogue's safe value; COMM.<card>.ONLINE is
where the reason lives. Every UPS.* bit is served here whether or not
a point carries it - a UPS nobody wired reads its safe value, exactly
as PWR.* reads without an EPM.
"""
from epw_os.core.device_manager import DeviceStatus
from epw_os.core.logging import log
from epw_os.core.tag_manager import TagQuality
from shared.logic import point_roles
from shared.logic.system_signals import raw_signals

# GOOD, or a value a simulator deliberately produced; anything else
# (never read, stale, comm failure, bad) is "no data" - rule Z4.
_TRUSTED = {TagQuality.GOOD.value, TagQuality.SIMULATED.value}


def _ups_ids() -> tuple:
    return tuple(s["id"] for s in raw_signals() if s.get("id", "").startswith("UPS.") and "<" not in s["id"])


class PointRoleSignals:
    def __init__(self, core):
        self.core = core
        self._ups = _ups_ids()
        self._roles = set(point_roles.role_ids())
        self._cache_key = None
        self._cache = {}
        self._warn_double_sources()

    # --- the project's assignments -----------------------------------------------------------

    def _registry(self) -> list:
        """The project's point registry as the config holds it (no copy:
        this runs inside the logic scan)."""
        pm = getattr(self.core, "project_manager", None) if self.core is not None else None
        config = getattr(pm, "config", None)
        registry = config.get("point_registry") if isinstance(config, dict) else None
        return registry if isinstance(registry, list) else []

    def assignments(self) -> dict:
        """{role signal id: [(address, contact)]} for the DI points that
        carry a role. Rebuilt when the project's registry is replaced
        (a load or a reconfigure), read from a cache otherwise."""
        registry = self._registry()
        key = (id(registry), len(registry))
        if key == self._cache_key:
            return self._cache
        out = {}
        for point in registry:
            if not isinstance(point, dict):
                continue
            role = point.get("role")
            if not role or role not in self._roles or point.get("kind") != "DI":
                continue
            contact = point.get("contact") or point_roles.CONTACT_NO
            out.setdefault(role, []).append((point["address"], contact))
        self._cache_key, self._cache = key, out
        return out

    def _card_models(self) -> list:
        pm = getattr(self.core, "project_manager", None) if self.core is not None else None
        config = getattr(pm, "config", None)
        if not isinstance(config, dict):
            return []
        return [str(dev.get("model") or "") for dev in config.get("devices", []) if dev.get("id")]

    def _warn_double_sources(self):
        """What Studio's "Sprawdź projekt" would have said (4.4), said
        here too, once, and kept in `notices` for whoever asks."""
        self.notices = []
        models = self._card_models()
        for role, points in self.assignments().items():
            prefix = point_roles.device_source_for(role)
            if prefix and any(m.upper().startswith(prefix) for m in models):
                self.notices.append(f"{role} comes from the contact on {', '.join(a for a, _c in points)} AND from a "
                                    f"{prefix} card's register block - the point's role wins; check the project in Studio.")
            if len(points) > 1:
                self.notices.append(f"{role} is carried by more than one point ({', '.join(a for a, _c in points)}) - "
                                    f"{'all' if role in point_roles.HEALTHY_TRUE else 'any'} of them decide the bit.")
        for notice in self.notices:
            log.warning(notice)

    # --- reading -----------------------------------------------------------------------------

    def _card_online(self, address: str) -> bool:
        """The card the input sits on, as DeviceManager sees it - the same
        verdict COMM.<card>.ONLINE gives. A card DeviceManager does not
        know is left to the tag's own quality."""
        manager = getattr(self.core, "device_manager", None) if self.core is not None else None
        devices = getattr(manager, "devices", None)
        card_id = address.split(".", 1)[0]
        if not isinstance(devices, dict) or card_id not in devices:
            return True
        return devices[card_id].get("status") == DeviceStatus.ONLINE

    def _input(self, address: str):
        """(value, trusted) of a DI tag; (None, False) when unknown, when
        its quality is not GOOD, or when its card is not answering - the
        card's watchdog and the tag's own staleness timer run apart, and
        rule Z4 wants the safe value the moment COMM says offline."""
        tags = getattr(self.core, "tag_manager", None) if self.core is not None else None
        getter = getattr(tags, "get_tag", None)
        tag = getter(address) if callable(getter) else None
        if tag is None:
            return None, False
        quality = getattr(tag, "quality", None)
        quality = getattr(quality, "value", quality)
        return tag.value, quality in _TRUSTED and self._card_online(address)

    def _role_value(self, role: str, points: list):
        """(the bit, every input trusted) for the contacts carrying `role`."""
        values = []
        for address, contact in points:
            value, trusted = self._input(address)
            if not trusted:
                return None, False
            values.append(point_roles.bit_from_contact(contact, value))
        return point_roles.combine(role, values), True

    def serves(self, signal_id: str) -> bool:
        if signal_id in self._ups:
            return True
        assigned = self.assignments()
        if signal_id in assigned:
            return True
        return point_roles.DERIVED.get(signal_id) in assigned

    def read(self, signal_id: str):
        assigned = self.assignments()
        positive = point_roles.DERIVED.get(signal_id)
        if positive is not None:
            if positive not in assigned:
                return point_roles.safe_value(signal_id)
            value, trusted = self._role_value(positive, assigned[positive])
            return (not value) if trusted else point_roles.safe_value(signal_id)
        if signal_id in assigned:
            value, trusted = self._role_value(signal_id, assigned[signal_id])
            return value if trusted else point_roles.safe_value(signal_id)
        if signal_id in self._ups:
            return point_roles.safe_value(signal_id)
        return None
