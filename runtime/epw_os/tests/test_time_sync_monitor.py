"""Tests for TimeSyncMonitor's platform-specific checks
(epw_os/core/time_sync_monitor.py) - headless, no PyQt involved.

subprocess.run is always mocked here - these tests never actually spawn
timedatectl/chronyc/w32tm, so they run identically (and fast) on any CI
platform regardless of what's actually installed on it.
"""

import subprocess
from unittest.mock import patch

from epw_os.core.time_sync_monitor import TimeSyncMonitor, TimeSyncStatus


class StubEventBus:
    def __init__(self):
        self.events = []

    def emit(self, *args, **kwargs):
        self.events.append((args, kwargs))


def make_monitor():
    return TimeSyncMonitor(StubEventBus())


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")



# `timedatectl show` (unlike the human-readable `timedatectl` / `timedatectl
# status`) prints plain, unindented Key=Value pairs - no colons, no padding.
TIMEDATECTL_SYNCED = """\
Timezone=Europe/Warsaw
LocalRTC=no
CanNTP=yes
NTP=yes
NTPSynchronized=yes
TimeUSec=Wed 2026-08-27 10:00:00 UTC
RTCTimeUSec=Wed 2026-08-27 10:00:00 UTC
"""

TIMEDATECTL_NOT_SYNCED = """\
Timezone=Europe/Warsaw
LocalRTC=no
CanNTP=yes
NTP=yes
NTPSynchronized=no
"""

TIMEDATECTL_UNPARSEABLE = """\
Timezone=Europe/Warsaw
LocalRTC=no
"""

CHRONYC_SYNCED = """\
Reference ID    : C0A80101 (ntp.internal.lan)
Stratum         : 3
Ref time (UTC)  : Wed Aug 27 10:00:00 2026
System time     : 0.000012345 seconds fast of NTP time
Leap status     : Normal
"""

CHRONYC_NOT_SYNCED = """\
Reference ID    : 00000000 ()
Stratum         : 0
Leap status     : Not synchronised
"""


# --- timedatectl -----------------------------------------------------

@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_timedatectl_synchronized(mock_run):
    mock_run.return_value = completed(TIMEDATECTL_SYNCED)
    status, detail = make_monitor()._check_timedatectl()
    assert status == TimeSyncStatus.SYNCED
    assert "NTP client: enabled" in detail
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0] == ["timedatectl", "show"]


@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_timedatectl_not_synchronized(mock_run):
    mock_run.return_value = completed(TIMEDATECTL_NOT_SYNCED)
    status, detail = make_monitor()._check_timedatectl()
    assert status == TimeSyncStatus.NOT_SYNCED
    assert "Not synchronized" in detail


@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_timedatectl_missing_field_is_unknown(mock_run):
    mock_run.return_value = completed(TIMEDATECTL_UNPARSEABLE)
    status, detail = make_monitor()._check_timedatectl()
    assert status == TimeSyncStatus.UNKNOWN
    assert "parse" in detail.lower()


@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_timedatectl_nonzero_exit_is_unknown(mock_run):
    mock_run.return_value = completed("", returncode=1)
    status, detail = make_monitor()._check_timedatectl()
    assert status == TimeSyncStatus.UNKNOWN


@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_timedatectl_timeout_is_unknown(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="timedatectl", timeout=5)
    status, detail = make_monitor()._check_timedatectl()
    assert status == TimeSyncStatus.UNKNOWN
    assert "timed out" in detail.lower()


@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_timedatectl_not_installed_returns_none(mock_run):
    """None is the specific 'try the next tool' signal, not (UNKNOWN, ...) -
    _check_linux_time_service() relies on this to decide whether to fall
    back to chronyc."""
    mock_run.side_effect = FileNotFoundError()
    assert make_monitor()._check_timedatectl() is None


# --- chronyc -----------------------------------------------------------

@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_chronyc_synchronized(mock_run):
    mock_run.return_value = completed(CHRONYC_SYNCED)
    status, detail = make_monitor()._check_chronyc()
    assert status == TimeSyncStatus.SYNCED
    assert "ntp.internal.lan" in detail


@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_chronyc_not_synchronized(mock_run):
    mock_run.return_value = completed(CHRONYC_NOT_SYNCED)
    status, detail = make_monitor()._check_chronyc()
    assert status == TimeSyncStatus.NOT_SYNCED


@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_chronyc_not_installed_returns_none(mock_run):
    mock_run.side_effect = FileNotFoundError()
    assert make_monitor()._check_chronyc() is None


# --- Linux dispatch: timedatectl -> chronyc fallback chain -------------

@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_linux_check_prefers_timedatectl_when_available(mock_run):
    mock_run.return_value = completed(TIMEDATECTL_SYNCED)
    status, detail = make_monitor()._check_linux_time_service()
    assert status == TimeSyncStatus.SYNCED
    assert "timedatectl" in detail
    mock_run.assert_called_once()  # chronyc never even attempted


@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_linux_check_falls_back_to_chronyc_when_timedatectl_missing(mock_run):
    mock_run.side_effect = [FileNotFoundError(), completed(CHRONYC_SYNCED)]
    status, detail = make_monitor()._check_linux_time_service()
    assert status == TimeSyncStatus.SYNCED
    assert "ntp.internal.lan" in detail
    assert mock_run.call_count == 2


@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_linux_check_does_not_fall_back_on_parse_failure(mock_run):
    """A tool that IS installed but returns garbage is a real failure, not
    an absent-tool signal - must not be masked by trying chronyc next."""
    mock_run.return_value = completed(TIMEDATECTL_UNPARSEABLE)
    status, detail = make_monitor()._check_linux_time_service()
    assert status == TimeSyncStatus.UNKNOWN
    assert "timedatectl" in detail.lower()
    mock_run.assert_called_once()


@patch("epw_os.core.time_sync_monitor.subprocess.run")
def test_linux_check_unknown_with_readable_reason_when_neither_tool_exists(mock_run):
    mock_run.side_effect = FileNotFoundError()
    status, detail = make_monitor()._check_linux_time_service()
    assert status == TimeSyncStatus.UNKNOWN
    assert "timedatectl" in detail and "chronyc" in detail


# --- top-level platform dispatch ---------------------------------------

@patch("epw_os.core.time_sync_monitor.subprocess.run")
@patch("epw_os.core.time_sync_monitor.platform.system", return_value="Linux")
def test_dispatch_routes_linux_to_timedatectl(mock_system, mock_run):
    mock_run.return_value = completed(TIMEDATECTL_SYNCED)
    status, detail = make_monitor()._check_time_sync()
    assert status == TimeSyncStatus.SYNCED
    assert "timedatectl" in detail


@patch("epw_os.core.time_sync_monitor.subprocess.run")
@patch("epw_os.core.time_sync_monitor.platform.system", return_value="Windows")
def test_dispatch_routes_windows_to_w32tm_unchanged(mock_system, mock_run):
    mock_run.return_value = completed(
        "Leap Indicator: 0(no warning)\nSource: time.windows.com\n"
    )
    status, detail = make_monitor()._check_time_sync()
    assert status == TimeSyncStatus.SYNCED
    assert "time.windows.com" in detail
    assert mock_run.call_args[0][0] == ["w32tm", "/query", "/status"]


@patch("epw_os.core.time_sync_monitor.platform.system", return_value="Darwin")
def test_dispatch_unsupported_platform_is_unknown(mock_system):
    status, detail = make_monitor()._check_time_sync()
    assert status == TimeSyncStatus.UNKNOWN
    assert "Darwin" in detail


# --- check_once() end to end (publishes + returns) ----------------------

@patch("epw_os.core.time_sync_monitor.subprocess.run")
@patch("epw_os.core.time_sync_monitor.platform.system", return_value="Linux")
def test_check_once_publishes_and_returns_linux_result(mock_system, mock_run):
    mock_run.return_value = completed(TIMEDATECTL_NOT_SYNCED)
    monitor = make_monitor()
    status, detail = monitor.check_once()
    assert status == TimeSyncStatus.NOT_SYNCED
    assert monitor.status == TimeSyncStatus.NOT_SYNCED
    assert monitor.event_bus.events, "status change must be published on the event bus"
    emitted_args = monitor.event_bus.events[0][0]
    assert emitted_args[0] == "time_sync_status_changed"
    assert emitted_args[1] == TimeSyncStatus.NOT_SYNCED
