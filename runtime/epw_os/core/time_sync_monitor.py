"""Time synchronization monitor - headless, no PyQt import (same rule as
every other core/ module: the GUI bridges this via events, it never
imports Qt itself).

Deliberately checks the OS's own time-sync service status (`w32tm
/query /status` on Windows; `timedatectl`/`chronyc` on Linux) instead of
reaching out to an NTP server directly (e.g. via the ntplib package). EPW
OS commonly runs on an industrial control network with no outbound
internet access - in that environment, an ntplib query to a public pool
would just time out and report NOT_SYNCED even if the plant's own
internal NTP/AD time source has the machine perfectly synced. Asking the
OS what it already believes reuses whatever time source it has been
configured against (a local NTP server, a domain controller, or - if
actually configured that way - an internet pool) without a second,
possibly-blocked network call and without a new runtime dependency
(ntplib isn't in requirements.txt today, on either platform).

Two platform-specific checks, picked at runtime by platform.system():
  - Windows (dev machine today): w32tm /query /status - unchanged, see
    _check_windows_time_service().
  - Linux (Orange Pi, the production target): timedatectl show, falling
    back to chronyc tracking if timedatectl isn't installed - see
    _check_linux_time_service() and its docstring for exactly which
    fields are read and why.
Anything else (or every available tool failing) reports UNKNOWN with a
human-readable reason, the same contract both platforms already followed.

GPS hook: EPW OS has no physical GPS time receiver yet. `report_gps_status()`
below is where a future GPS driver would report in - see its docstring.
"""
import platform
import subprocess
import threading
from datetime import datetime

from epw_os.core.logging import log


class TimeSyncStatus:
    SYNCED = "SYNCED"
    NOT_SYNCED = "NOT_SYNCED"
    UNKNOWN = "UNKNOWN"


class TimeSyncMonitor:
    """Polls the OS's time-sync service status (Windows Time / w32tm, or
    timedatectl/chronyc on Linux - see _check_time_sync()) on its own
    background thread (same pattern as SimulatorDriver's polling thread)
    and emits 'time_sync_status_changed' on the shared EventBus whenever
    the status or detail text changes - not on every poll, so a healthy
    steady-state doesn't spam the event bus / audit trail."""

    DEFAULT_POLL_INTERVAL_SECONDS = 60

    def __init__(self, event_bus, poll_interval: float = None):
        self.event_bus = event_bus
        self.poll_interval = poll_interval or self.DEFAULT_POLL_INTERVAL_SECONDS
        self.status = TimeSyncStatus.UNKNOWN
        self.detail = "Not yet checked"
        self.last_checked = None
        self._thread = None
        self._stop_event = threading.Event()

        # GPS_SOURCE_HOOK: no physical GPS receiver exists yet. When one is
        # added, its driver should call report_gps_status(...) - a direct
        # hardware time reference should take priority over (or at least
        # be shown alongside) the OS-level NTP status this class polls.
        # Unused for now; present so the GUI/EventBus contract for it
        # already exists and doesn't need a breaking change later.
        self.gps_status = None
        self.gps_detail = None

    def start(self):
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="TimeSyncMonitor"
        )
        self._thread.start()
        log.info("TimeSyncMonitor started.")

    def stop(self):
        self._stop_event.set()

    def check_once(self):
        """Synchronous one-shot check, run right after start() so the
        indicator has a real reading immediately instead of sitting on
        UNKNOWN for up to poll_interval seconds."""
        status, detail = self._check_time_sync()
        self._publish(status, detail)
        return status, detail

    def report_gps_status(self, status: str, detail: str = ""):
        """Hook for a future GPS time source driver - not called by
        anything today. See GPS_SOURCE_HOOK note in __init__."""
        self.gps_status = status
        self.gps_detail = detail
        self._publish(status, detail)

    def _run_loop(self):
        # First reading immediately, not after a full poll_interval wait.
        status, detail = self._check_time_sync()
        self._publish(status, detail)
        while not self._stop_event.wait(self.poll_interval):
            status, detail = self._check_time_sync()
            self._publish(status, detail)

    def _publish(self, status, detail):
        changed = status != self.status or detail != self.detail
        self.status = status
        self.detail = detail
        self.last_checked = datetime.now()
        if changed:
            self.event_bus.emit("time_sync_status_changed", status, detail)

    def _check_time_sync(self):
        """Platform dispatch - the one thing check_once()/_run_loop() call.
        Each per-platform check below is self-contained and returns the
        same (status, detail) contract."""
        system = platform.system()
        if system == "Windows":
            return self._check_windows_time_service()
        if system == "Linux":
            return self._check_linux_time_service()
        return TimeSyncStatus.UNKNOWN, f"Time sync check not supported on {system or 'this platform'}"

    def _check_linux_time_service(self):
        """Orange Pi / Armbian / any systemd-based Debian target.

        Tries `timedatectl show` first (systemd-timesyncd or any NTP
        client registers its status with systemd-timedated, which this
        queries - present on stock Armbian/Debian images). Falls back to
        `chronyc tracking` only if timedatectl itself isn't installed
        (chrony is a common swap-in NTP client on smaller distros/images).
        A tool that IS installed but fails/times out/returns something
        unparseable reports UNKNOWN directly for that tool - it does not
        fall through to the other one, so a real failure is never masked
        as "tool not found"."""
        result = self._check_timedatectl()
        if result is not None:
            return result
        result = self._check_chronyc()
        if result is not None:
            return result
        return TimeSyncStatus.UNKNOWN, "No NTP status tool available (timedatectl/chronyc not found)"

    def _check_timedatectl(self):
        """Returns (status, detail), or None if `timedatectl` itself is
        not installed (the caller then tries chronyc)."""
        try:
            result = subprocess.run(
                ["timedatectl", "show"],
                capture_output=True, text=True, timeout=5,
            )
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired:
            return TimeSyncStatus.UNKNOWN, "timedatectl query timed out"
        except Exception as e:
            return TimeSyncStatus.UNKNOWN, f"timedatectl query failed: {e}"

        if result.returncode != 0:
            # e.g. systemd-timedated not reachable over D-Bus.
            return TimeSyncStatus.UNKNOWN, "timedatectl unavailable"

        return self._parse_timedatectl_output(result.stdout)

    @staticmethod
    def _parse_timedatectl_output(output: str):
        """`timedatectl show` prints one `Key=Value` pair per line (no
        query flags needed). Two fields matter here:

          - NTPSynchronized=yes|no - the definitive signal, directly
            analogous to w32tm's Leap Indicator: whether the system clock
            is *currently* synchronized. This is systemd-timedated's own
            verdict, regardless of which NTP client produced it.
          - NTP=yes|no - whether an NTP client is enabled/configured at
            all. Not used to decide SYNCED/NOT_SYNCED (a clock can still
            be correctly synced a moment after the client was disabled),
            only folded into the detail text so the tooltip says whether
            a time source is even supposed to be active.

        Every other field `timedatectl show` prints (Timezone, RTC*,
        LinuxHwClock, ...) is irrelevant to sync status and ignored."""
        fields = {}
        for line in output.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                fields[key.strip()] = value.strip()

        synced = fields.get("NTPSynchronized")
        if synced is None:
            return TimeSyncStatus.UNKNOWN, "Could not parse timedatectl output"

        ntp_state = {"yes": "enabled", "no": "disabled"}.get(fields.get("NTP"), "unknown")

        if synced.lower() == "yes":
            return TimeSyncStatus.SYNCED, f"Synchronized (source: timedatectl, NTP client: {ntp_state})"
        return TimeSyncStatus.NOT_SYNCED, f"Not synchronized (source: timedatectl, NTP client: {ntp_state})"

    def _check_chronyc(self):
        """Returns (status, detail), or None if `chronyc` itself is not
        installed."""
        try:
            result = subprocess.run(
                ["chronyc", "tracking"],
                capture_output=True, text=True, timeout=5,
            )
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired:
            return TimeSyncStatus.UNKNOWN, "chronyc query timed out"
        except Exception as e:
            return TimeSyncStatus.UNKNOWN, f"chronyc query failed: {e}"

        if result.returncode != 0:
            # e.g. chronyd isn't running at all.
            return TimeSyncStatus.UNKNOWN, "chrony (chronyd) unavailable"

        return self._parse_chronyc_output(result.stdout)

    @staticmethod
    def _parse_chronyc_output(output: str):
        """`chronyc tracking` is a fixed set of "Label  : value" lines.
        Two matter here:

          - "Leap status" - chrony's own verdict on whether the clock is
            synchronized, in its own words ("Normal" / "Insert second" /
            "Delete second" / "Not synchronised"). Exactly the same shape
            as w32tm's Leap Indicator: only the explicit "not
            synchronised" value means unsynced, everything else
            (including a pending leap second) counts as synced.
          - "Reference ID" - printed as "<hex id> (<hostname or IP>)";
            the parenthesized part is the closest thing chrony has to
            w32tm's "Source:" line, so it's reused for the detail text.

        Every other line (Stratum, System time, offsets, Frequency,
        Skew, Root delay/dispersion, Update interval, ...) describes
        sync *quality*, not sync *status*, and isn't needed for the
        SYNCED/NOT_SYNCED/UNKNOWN verdict this monitor reports."""
        lines = output.splitlines()
        leap_line = next((l for l in lines if l.strip().startswith("Leap status")), "")
        ref_line = next((l for l in lines if l.strip().startswith("Reference ID")), "")

        if not leap_line:
            return TimeSyncStatus.UNKNOWN, "Could not parse chronyc output"

        source = "unknown source"
        if "(" in ref_line and ")" in ref_line:
            inner = ref_line.split("(", 1)[1].split(")", 1)[0].strip()
            if inner:
                source = inner

        leap_value = leap_line.split(":", 1)[1].strip() if ":" in leap_line else ""
        if "not synchronised" in leap_value.lower():
            return TimeSyncStatus.NOT_SYNCED, f"Not synchronized (source: {source})"
        return TimeSyncStatus.SYNCED, f"Synchronized (source: {source})"

    def _check_windows_time_service(self):
        if platform.system() != "Windows":
            return TimeSyncStatus.UNKNOWN, "w32tm is Windows-only"

        try:
            result = subprocess.run(
                ["w32tm", "/query", "/status"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError:
            return TimeSyncStatus.UNKNOWN, "w32tm not found"
        except subprocess.TimeoutExpired:
            return TimeSyncStatus.UNKNOWN, "w32tm query timed out"
        except Exception as e:
            return TimeSyncStatus.UNKNOWN, f"w32tm query failed: {e}"

        if result.returncode != 0:
            # e.g. "The service has not been started." when W32Time is
            # stopped entirely.
            return TimeSyncStatus.UNKNOWN, "Windows Time service unavailable"

        return self._parse_w32tm_output(result.stdout)

    @staticmethod
    def _parse_w32tm_output(output: str):
        lines = output.splitlines()
        leap_line = next((l for l in lines if l.strip().startswith("Leap Indicator")), "")
        source_line = next((l for l in lines if l.strip().startswith("Source")), "")
        source = source_line.split(":", 1)[1].strip() if ":" in source_line else "unknown source"

        if not leap_line:
            return TimeSyncStatus.UNKNOWN, "Could not parse w32tm output"

        # "Leap Indicator: 3(not synchronized)" is the definitive signal -
        # 0/1/2 all mean the clock is synchronized (1/2 just flag a
        # pending leap second), only 3 means "not synchronized".
        if "3(" in leap_line or "not synchronized" in leap_line.lower():
            return TimeSyncStatus.NOT_SYNCED, f"Not synchronized (source: {source})"
        return TimeSyncStatus.SYNCED, f"Synchronized (source: {source})"
