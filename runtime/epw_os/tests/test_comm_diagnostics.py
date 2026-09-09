"""Bus Diagnostics (Task: "ekran diagnostyczny komunikacji szeregowej").

Covers the neutral interface itself (comm_diagnostics.py's counting
engine, and BaseDriver's get_comm_stats()/reset_comm_stats() default),
and that SimulatorDriver actually fills it in from a real running poll
loop - the two things the DOWOD explicitly asks for ("interfejs
statystyk dziala i jest wypelniany przez SimulatorDriver", "zerowanie
licznikow dziala").
"""
import time

import pytest

from epw_os.core.comm_diagnostics import (
    CommDiagnostics, DeviceCommStats, ERROR_TIMEOUT, ERROR_CRC, ERROR_INVALID_RESPONSE,
)
from epw_os.drivers.base_driver import BaseDriver
from epw_os.drivers.simulator_driver import SimulatorDriver
from epw_os.core.events import EventBus


# --- CommDiagnostics engine, in isolation -------------------------------

def test_new_device_has_no_data_until_first_record():
    diag = CommDiagnostics()
    assert diag.get_stats("Dev1") is None
    assert diag.get_all_stats() == {}


def test_record_frame_sent_increments_counter():
    diag = CommDiagnostics()
    diag.record_frame_sent("Dev1")
    diag.record_frame_sent("Dev1")
    stats = diag.get_stats("Dev1")
    assert stats.frames_sent == 2
    assert stats.frames_received == 0


def test_record_success_updates_response_times_and_timestamp():
    diag = CommDiagnostics()
    diag.record_frame_sent("Dev1")
    diag.record_success("Dev1", 10.0)
    diag.record_frame_sent("Dev1")
    diag.record_success("Dev1", 30.0)

    stats = diag.get_stats("Dev1")
    assert stats.frames_received == 2
    assert stats.last_response_ms == 30.0
    assert stats.avg_response_ms == 20.0
    assert stats.worst_response_ms == 30.0
    assert stats.last_success_time is not None
    since = stats.seconds_since_success()
    assert since is not None and since >= 0.0


def test_record_error_increments_the_right_counter_and_logs_it():
    diag = CommDiagnostics()
    diag.record_error("Dev1", ERROR_TIMEOUT, "no response")
    diag.record_error("Dev1", ERROR_CRC, "bad checksum")
    diag.record_error("Dev1", ERROR_INVALID_RESPONSE, "wrong length")

    stats = diag.get_stats("Dev1")
    assert stats.errors_timeout == 1
    assert stats.errors_crc == 1
    assert stats.errors_invalid_response == 1
    assert stats.total_errors == 3
    assert len(stats.recent_errors) == 3
    assert stats.recent_errors[0].description == "no response"


def test_success_rate_pct_none_before_any_attempt_then_reflects_errors():
    diag = CommDiagnostics()
    stats = DeviceCommStats(device_id="Dev1")
    assert stats.success_rate_pct is None  # nothing attempted yet

    for _ in range(8):
        diag.record_frame_sent("Dev1")
        diag.record_success("Dev1", 1.0)
    diag.record_frame_sent("Dev1")
    diag.record_error("Dev1", ERROR_TIMEOUT)
    diag.record_frame_sent("Dev1")
    diag.record_error("Dev1", ERROR_CRC)

    stats = diag.get_stats("Dev1")
    assert stats.frames_sent == 10
    assert stats.success_rate_pct == pytest.approx(80.0)


def test_recent_errors_ring_buffer_is_bounded():
    diag = CommDiagnostics()
    from epw_os.core.comm_diagnostics import MAX_RECENT_ERRORS
    for i in range(MAX_RECENT_ERRORS + 20):
        diag.record_error("Dev1", ERROR_TIMEOUT, f"error {i}")
    stats = diag.get_stats("Dev1")
    assert len(stats.recent_errors) == MAX_RECENT_ERRORS
    # Oldest entries evicted first - the ring buffer kept the newest ones.
    assert stats.recent_errors[-1].description == f"error {MAX_RECENT_ERRORS + 19}"


def test_reset_single_device_leaves_others_untouched():
    diag = CommDiagnostics()
    diag.record_frame_sent("Dev1")
    diag.record_frame_sent("Dev2")
    diag.reset("Dev1")
    assert diag.get_stats("Dev1") is None
    assert diag.get_stats("Dev2").frames_sent == 1


def test_reset_all_clears_every_device():
    diag = CommDiagnostics()
    diag.record_frame_sent("Dev1")
    diag.record_frame_sent("Dev2")
    diag.reset()
    assert diag.get_all_stats() == {}


# --- BaseDriver: the neutral interface's default (base) behavior --------

def test_base_driver_comm_stats_default_is_empty_and_reset_is_a_noop():
    bus = EventBus()
    drv = BaseDriver("TestDriver", bus)
    assert drv.get_comm_stats() == {}
    drv.reset_comm_stats()          # must not raise
    drv.reset_comm_stats("Dev1")    # must not raise


# --- SimulatorDriver: the interface actually implemented and filled in --

def test_simulator_driver_fills_in_comm_stats_from_a_real_running_loop():
    bus = EventBus()
    drv = SimulatorDriver(bus)
    drv.set_devices(["DevA", "DevB"])
    drv.start()
    try:
        deadline = time.time() + 5.0
        while time.time() < deadline:
            stats = drv.get_comm_stats()
            if stats.get("DevA") and stats.get("DevA").frames_sent >= 2:
                break
            time.sleep(0.05)
        stats = drv.get_comm_stats()
    finally:
        drv.stop()

    assert "DevA" in stats and "DevB" in stats
    a = stats["DevA"]
    assert a.frames_sent >= 2
    assert a.frames_received == a.frames_sent  # the simulator never fails an exchange
    assert a.total_errors == 0                  # Task: "symulator moze raportowac zerowe bledy"
    assert a.last_response_ms is not None and a.last_response_ms >= 0.0
    assert a.avg_response_ms is not None
    assert a.success_rate_pct == pytest.approx(100.0)
    assert a.seconds_since_success() is not None


def test_simulator_driver_reset_comm_stats_clears_counters():
    bus = EventBus()
    drv = SimulatorDriver(bus)
    drv.set_devices(["DevA"])
    drv.start()
    try:
        deadline = time.time() + 5.0
        while time.time() < deadline and not drv.get_comm_stats().get("DevA"):
            time.sleep(0.05)
        assert drv.get_comm_stats().get("DevA") is not None

        drv.reset_comm_stats("DevA")
        assert drv.get_comm_stats().get("DevA") is None

        # Full reset (no device_id) after more activity accumulates.
        deadline = time.time() + 5.0
        while time.time() < deadline and not drv.get_comm_stats().get("DevA"):
            time.sleep(0.05)
        drv.reset_comm_stats()
        assert drv.get_comm_stats() == {}
    finally:
        drv.stop()


def test_simulator_driver_comm_diagnostics_survive_multiple_devices_independently():
    bus = EventBus()
    drv = SimulatorDriver(bus)
    drv.set_devices(["DevA", "DevB", "DevC"])
    drv.start()
    try:
        deadline = time.time() + 5.0
        while time.time() < deadline:
            stats = drv.get_comm_stats()
            if all(stats.get(d) for d in ("DevA", "DevB", "DevC")):
                break
            time.sleep(0.05)
        stats = drv.get_comm_stats()
    finally:
        drv.stop()

    assert set(stats.keys()) == {"DevA", "DevB", "DevC"}
    # Every device got its own counters advancing roughly together (same loop).
    counts = {d: s.frames_sent for d, s in stats.items()}
    assert max(counts.values()) - min(counts.values()) <= 2
