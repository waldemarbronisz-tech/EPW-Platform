"""Studio's one link to a controller (SPEC "Studio — sterownik — połączenie
na żywo"): the address and token (QSettings, per project file), one
stdlib HTTP request helper every panel shares, and the LIVE monitor -
a timer that reads the controller's tags and forces and hands them to
whoever shows them (the point registry, the cards, the Synoptic editor),
plus the force heartbeat while Studio holds forces.

Nothing here knows a widget: panels get plain dicts.
"""
import hashlib
import json
import os
import urllib.error
import urllib.request

from PySide6.QtCore import QObject, QTimer, Signal

from studio.shell.i18n import tr

LIVE_INTERVAL_MS = 2000
SETTINGS_HOST = "controller/host"
SETTINGS_TOKEN = "controller/token"


class ControllerLink:
    """Address + token for the active project, and request()."""

    def __init__(self, studio_window):
        self._win = studio_window
        self.last_error_detail = None

    def _scope(self) -> str:
        path = getattr(self._win, "_project_path", None)
        if not path:
            return ""
        return "controller/" + hashlib.sha1(os.path.abspath(path).encode("utf-8")).hexdigest()[:12] + "/"

    def host(self) -> str:
        settings = self._win.settings
        scope = self._scope()
        value = settings.value(scope + "host", None) if scope else None
        return (value if value is not None else settings.value(SETTINGS_HOST, "")) or ""

    def token(self) -> str:
        settings = self._win.settings
        scope = self._scope()
        value = settings.value(scope + "token", None) if scope else None
        return (value if value is not None else settings.value(SETTINGS_TOKEN, "")) or ""

    def set_connection(self, host: str, token: str):
        settings = self._win.settings
        scope = self._scope()
        for prefix in ((scope,) if scope else ()) + ("controller/",):
            settings.setValue(prefix + "host", host.strip())
            settings.setValue(prefix + "token", token)

    def request(self, path: str, timeout: float = 4.0, method: str = "GET", data=None, raw: bool = False,
                content_type: str = None):
        """(True, parsed json | bytes) or (False, message); never raises.
        An HTTP error's JSON `detail` is kept in last_error_detail."""
        self.last_error_detail = None
        host = self.host().strip().rstrip("/")
        if not host:
            return False, tr("controller.error_no_host")
        headers = {}
        token = self.token().strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(f"{host}{path}", headers=headers, data=data, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
            if raw:
                return True, body
            text = body.decode("utf-8")
            return True, json.loads(text) if text else {}
        except urllib.error.HTTPError as e:
            try:
                self.last_error_detail = json.loads(e.read().decode("utf-8")).get("detail")
            except Exception:  # noqa: BLE001 - a body that is not JSON is simply no detail
                self.last_error_detail = None
            return False, tr("controller.error_http", code=e.code, reason=e.reason)
        except urllib.error.URLError as e:
            return False, tr("controller.error_connection", reason=str(e.reason))
        except Exception as e:  # noqa: BLE001 - any failure here is "show it", not a Studio crash
            return False, str(e)

    def request_json(self, path: str, payload: dict, method: str = "POST", timeout: float = 6.0):
        return self.request(path, timeout=timeout, method=method, data=json.dumps(payload).encode("utf-8"),
                            content_type="application/json")


class LiveMonitor(QObject):
    """Reads /api/v1/tags and /api/v1/forces every LIVE_INTERVAL_MS while
    enabled and publishes them; sends the force heartbeat while any
    force is held. `updated` carries (tags, forces): tags {name: {value,
    quality, data_type}}, forces {tag: entry}. `failed` carries the
    reason of the last failed read (the timer keeps trying)."""

    updated = Signal(object, object)
    failed = Signal(str)

    def __init__(self, link: ControllerLink, parent=None):
        super().__init__(parent)
        self.link = link
        self.tags = {}
        self.forces = {}
        self.connected = False
        self.heartbeat_wanted = False
        self._timer = QTimer(self)
        self._timer.setInterval(LIVE_INTERVAL_MS)
        self._timer.timeout.connect(self.poll)

    def is_enabled(self) -> bool:
        return self._timer.isActive()

    def set_enabled(self, enabled: bool):
        if enabled:
            self.poll()
            self._timer.start()
        else:
            self._timer.stop()
            self.tags, self.forces, self.connected = {}, {}, False
            self.updated.emit({}, {})

    def poll(self):
        ok, tags = self.link.request("/api/v1/tags")
        if not ok or not isinstance(tags, list):
            self.connected = False
            self.tags, self.forces = {}, {}
            self.failed.emit(str(tags))
            self.updated.emit({}, {})
            return
        ok_f, forces = self.link.request("/api/v1/forces")
        force_entries = forces.get("forces", []) if ok_f and isinstance(forces, dict) else []
        self.tags = {t["name"]: t for t in tags if isinstance(t, dict) and "name" in t}
        self.forces = {f["tag"]: f for f in force_entries if isinstance(f, dict) and "tag" in f}
        self.connected = True
        if self.heartbeat_wanted and self.forces:
            self.link.request("/api/v1/forces/heartbeat", method="POST", timeout=3.0)
        self.updated.emit(self.tags, self.forces)

    def values(self) -> dict:
        """{tag: value} - what the Synoptic editor wants."""
        return {name: entry.get("value") for name, entry in self.tags.items()}
