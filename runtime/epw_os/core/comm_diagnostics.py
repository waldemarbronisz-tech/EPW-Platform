"""Per-device serial/bus communication diagnostics - a small, thread-safe
counter engine any driver can own and update from its own polling loop.

Task: "Dane maja pochodzic z warstwy sterownikow przez neutralny
interfejs - tak, zeby ModbusDriver mogl je dostarczac bez zmiany tej
strony." The actual neutral interface the GUI page (page_bus_diagnostics.py)
depends on is BaseDriver.get_comm_stats()/reset_comm_stats() (see
base_driver.py) - two methods any driver implements, returning/consuming
plain DeviceCommStats snapshots, nothing simulator-specific. This module
is a reusable IMPLEMENTATION of the counting logic behind that contract,
so a future ModbusDriver doesn't have to reinvent it: it can compose one
of these exactly like SimulatorDriver does below, and call
record_*()/reset() from wherever its real request/response cycle
actually happens (see SESSION_REPORT.md for the full interface writeup
aimed at that future implementation).

Deliberately cheap: every record_*() call is a handful of dict/deque
operations under one lock, no I/O, no DB writes - safe to call from a
tight polling loop without slowing it down (GRANICE: "zbieranie
statystyk nie moze spowalniac petli komunikacyjnej"). Headless (no Qt
import), same rule as every other core/ module - the driver layer that
calls into this must never depend on Qt either.
"""
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Per-device ring buffer size for recent_errors - bounded so a device
# stuck erroring forever can't grow this without limit; old errors age
# out as new ones arrive, same "most recent matters most" reasoning as
# Historian's own row cap.
MAX_RECENT_ERRORS = 50

ERROR_TIMEOUT = "TIMEOUT"
ERROR_CRC = "CRC"
ERROR_INVALID_RESPONSE = "INVALID_RESPONSE"


@dataclass(frozen=True)
class CommError:
    timestamp: float  # epoch seconds
    error_type: str
    description: str = ""


@dataclass
class DeviceCommStats:
    """A read-only snapshot - returned by CommDiagnostics.get_stats()/
    get_all_stats() (and, through those, by any driver's
    get_comm_stats()). Safe to read from the GUI thread without holding
    the same lock the live counters do - it's a plain copy, not a live
    view."""
    device_id: str
    frames_sent: int = 0
    frames_received: int = 0
    errors_timeout: int = 0
    errors_crc: int = 0
    errors_invalid_response: int = 0
    last_response_ms: Optional[float] = None
    avg_response_ms: Optional[float] = None
    worst_response_ms: Optional[float] = None
    last_success_time: Optional[float] = None  # epoch seconds, None = never
    recent_errors: List[CommError] = field(default_factory=list)

    @property
    def total_errors(self) -> int:
        return self.errors_timeout + self.errors_crc + self.errors_invalid_response

    @property
    def success_rate_pct(self) -> Optional[float]:
        """None before anything has been attempted yet - distinct from
        0%, same "no data yet" convention used elsewhere in this app
        (e.g. the status bar's Latency field before the first command)."""
        if self.frames_sent <= 0:
            return None
        successful = self.frames_sent - self.total_errors
        return max(0.0, min(100.0, 100.0 * successful / self.frames_sent))

    def seconds_since_success(self, now: float = None) -> Optional[float]:
        if self.last_success_time is None:
            return None
        now = now if now is not None else time.time()
        return max(0.0, now - self.last_success_time)


class _DeviceCounters:
    """Internal, mutable, lock-protected state for one device - never
    handed out directly; snapshot() is the only way out, producing the
    immutable DeviceCommStats above."""
    __slots__ = ("device_id", "frames_sent", "frames_received", "errors_timeout",
                 "errors_crc", "errors_invalid_response", "last_response_ms",
                 "worst_response_ms", "_response_sum_ms", "_response_count",
                 "last_success_time", "recent_errors")

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.frames_sent = 0
        self.frames_received = 0
        self.errors_timeout = 0
        self.errors_crc = 0
        self.errors_invalid_response = 0
        self.last_response_ms = None
        self.worst_response_ms = None
        self._response_sum_ms = 0.0
        self._response_count = 0
        self.last_success_time = None
        self.recent_errors = deque(maxlen=MAX_RECENT_ERRORS)

    def snapshot(self) -> DeviceCommStats:
        avg = (self._response_sum_ms / self._response_count) if self._response_count else None
        return DeviceCommStats(
            device_id=self.device_id,
            frames_sent=self.frames_sent,
            frames_received=self.frames_received,
            errors_timeout=self.errors_timeout,
            errors_crc=self.errors_crc,
            errors_invalid_response=self.errors_invalid_response,
            last_response_ms=self.last_response_ms,
            avg_response_ms=avg,
            worst_response_ms=self.worst_response_ms,
            last_success_time=self.last_success_time,
            recent_errors=list(self.recent_errors),
        )


class CommDiagnostics:
    """Owns per-device counters for however many device_ids a driver has
    reported activity for - devices are created lazily on first use
    (record_frame_sent()/record_success()/record_error()), never
    pre-registered, so the driver never has to tell this class its
    device list up front; it just calls record_*() with whatever
    device_id it's talking to right now."""

    def __init__(self):
        self._lock = threading.RLock()
        self._devices: Dict[str, _DeviceCounters] = {}

    def _get_or_create(self, device_id: str) -> _DeviceCounters:
        counters = self._devices.get(device_id)
        if counters is None:
            counters = _DeviceCounters(device_id)
            self._devices[device_id] = counters
        return counters

    def record_frame_sent(self, device_id: str):
        """Call once per outbound request - independent of whether it
        ever gets a response (see record_success()/record_error()
        below), mirroring how frames_sent on a real bus counts requests
        transmitted, not requests answered."""
        with self._lock:
            self._get_or_create(device_id).frames_sent += 1

    def record_success(self, device_id: str, response_time_ms: float):
        """One full request/response cycle that succeeded - increments
        frames_received, updates last/avg/worst response time, and
        stamps last_success_time to now. Does NOT touch frames_sent -
        call record_frame_sent() separately when the request actually
        goes out, same as a real transaction has a send half and a
        (possibly failed) receive half."""
        with self._lock:
            c = self._get_or_create(device_id)
            c.frames_received += 1
            c.last_response_ms = response_time_ms
            c.worst_response_ms = (
                response_time_ms if c.worst_response_ms is None else max(c.worst_response_ms, response_time_ms)
            )
            c._response_sum_ms += response_time_ms
            c._response_count += 1
            c.last_success_time = time.time()

    def record_error(self, device_id: str, error_type: str, description: str = ""):
        """error_type: ERROR_TIMEOUT / ERROR_CRC / ERROR_INVALID_RESPONSE
        for the three named counters DOWOD asks for - any other string
        is still recorded in recent_errors (so a driver reporting a
        failure mode this module doesn't have a dedicated counter for
        yet doesn't raise), it just won't increment one of the three."""
        with self._lock:
            c = self._get_or_create(device_id)
            if error_type == ERROR_TIMEOUT:
                c.errors_timeout += 1
            elif error_type == ERROR_CRC:
                c.errors_crc += 1
            elif error_type == ERROR_INVALID_RESPONSE:
                c.errors_invalid_response += 1
            c.recent_errors.append(CommError(time.time(), error_type, description))

    def get_stats(self, device_id: str) -> Optional[DeviceCommStats]:
        with self._lock:
            c = self._devices.get(device_id)
            return c.snapshot() if c else None

    def get_all_stats(self) -> Dict[str, DeviceCommStats]:
        with self._lock:
            return {device_id: c.snapshot() for device_id, c in self._devices.items()}

    def reset(self, device_id: str = None):
        """Resets counters for one device, or every device if device_id
        is None (Task: "przycisk zerowania licznikow"). recent_errors
        clears too - a fresh start means forgetting old errors, not
        just zeroing the numeric counters."""
        with self._lock:
            if device_id is None:
                self._devices.clear()
            else:
                self._devices.pop(device_id, None)
