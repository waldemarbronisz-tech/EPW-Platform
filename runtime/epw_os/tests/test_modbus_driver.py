"""Punkt 2 / luka 6: the Modbus I/O driver (epw_os/drivers/modbus_driver.py).

Framing is checked against published vectors; the driver itself runs
against a small Modbus TCP server on the loopback interface (a real
socket, real MBAP frames, real FC1/2/4/5/6 handling) - so what is proven
is the whole path a real gateway would take, not a mocked transport.
The RTU path shares every byte of the PDU code and adds only the CRC
frame, which is checked here too; the serial port itself needs pyserial
and is reported, not opened, on a controller without it.
"""
import json
import socket
import struct
import threading
import time

import pytest

from epw_os.core.comm_diagnostics import ERROR_CRC, ERROR_INVALID_RESPONSE, ERROR_TIMEOUT
from epw_os.core.events import EventBus
from epw_os.drivers import modbus_driver as mb
from epw_os.drivers.modbus_driver import (DRIVER_ID, ModbusClient, ModbusDriver, ModbusError, TcpTransport,
                                          TransportUnavailable, build_rtu_frame, crc16, make_transport,
                                          parse_rtu_frame, rtu_response_length, unpack_bits, unpack_registers)


# --- a Modbus TCP "module" on the loopback interface -------------------------------------

class LoopbackModbusServer:
    """One unit id, 16 discrete inputs, 16 coils, 4 input registers."""

    def __init__(self, unit=1, misbehave=None):
        self.unit = unit
        self.inputs = [False] * 16
        self.coils = [False] * 16
        self.input_registers = [0, 0, 0, 0]
        self.misbehave = misbehave  # None | "exception" | "silent" | "wrong_unit"
        self.requests = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(4)
        self.port = self._sock.getsockname()[1]
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def close(self):
        self._running = False
        try:
            self._sock.close()
        except OSError:
            pass

    def _serve(self):
        while self._running:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._session, args=(conn,), daemon=True).start()

    @staticmethod
    def _recv_exact(conn, n):
        data = b""
        while len(data) < n:
            part = conn.recv(n - len(data))
            if not part:
                return None
            data += part
        return data

    def _session(self, conn):
        conn.settimeout(5.0)
        try:
            while self._running:
                header = self._recv_exact(conn, 7)
                if header is None:
                    return
                tid, _proto, length, unit = struct.unpack(">HHHB", header)
                pdu = self._recv_exact(conn, length - 1)
                if pdu is None:
                    return
                self.requests.append((unit, pdu))
                if self.misbehave == "silent":
                    continue
                reply = self._respond(unit, pdu)
                reply_unit = unit + 1 if self.misbehave == "wrong_unit" else unit
                conn.sendall(struct.pack(">HHHB", tid, 0, len(reply) + 1, reply_unit) + reply)
        except OSError:
            return
        finally:
            conn.close()

    @staticmethod
    def _pack_bits(bits):
        out = bytearray((len(bits) + 7) // 8)
        for i, bit in enumerate(bits):
            if bit:
                out[i // 8] |= 1 << (i % 8)
        return bytes(out)

    def _respond(self, unit, pdu):
        function = pdu[0]
        if self.misbehave == "exception" or unit != self.unit:
            return bytes([function | 0x80, 2])
        if function in (1, 2):
            start, count = struct.unpack(">HH", pdu[1:5])
            table = self.coils if function == 1 else self.inputs
            if start + count > len(table):
                return bytes([function | 0x80, 2])
            payload = self._pack_bits(table[start:start + count])
            return bytes([function, len(payload)]) + payload
        if function == 4:
            start, count = struct.unpack(">HH", pdu[1:5])
            if start + count > len(self.input_registers):
                return bytes([function | 0x80, 2])
            regs = self.input_registers[start:start + count]
            return bytes([function, 2 * count]) + struct.pack(">" + "H" * count, *[r & 0xFFFF for r in regs])
        if function == 5:
            address, value = struct.unpack(">HH", pdu[1:5])
            if address >= len(self.coils):
                return bytes([function | 0x80, 2])
            self.coils[address] = value == 0xFF00
            return pdu
        if function == 6:
            address, value = struct.unpack(">HH", pdu[1:5])
            self.input_registers[address % 4] = value  # a module that mirrors its AO into an AI
            return pdu
        return bytes([function | 0x80, 1])


@pytest.fixture
def server():
    srv = LoopbackModbusServer()
    yield srv
    srv.close()


def _bus(server):
    return {"transport": "TCP", "host": "127.0.0.1", "tcp_port": server.port}


def _cards(unit=1):
    return [
        {"id": "ELA1", "kind": "DI", "channels": 16, "modbus_unit_id": unit},
        {"id": "ELA1", "kind": "AI", "channels": 4, "modbus_unit_id": unit},
        {"id": "ADA1", "kind": "DO", "channels": 16, "modbus_unit_id": unit},
        {"id": "NOADDR", "kind": "DI", "channels": 8, "modbus_unit_id": None},
    ]


class _Events:
    def __init__(self, bus):
        self.updates = {}
        self.comm_ok = []
        bus.subscribe("driver_update", self._update)
        bus.subscribe("driver_comm_ok", self.comm_ok.append)

    def _update(self, tag, value, quality):
        self.updates[tag] = (value, quality)


# --- framing --------------------------------------------------------------------------

def test_crc16_matches_the_published_vectors():
    # Two textbook request frames: unit 0x11 reading 3 holding registers
    # from 0x6B carries CRC 76 87; unit 1 reading 10 from 0 carries C5 CD
    # (both CRC low byte first on the wire).
    assert build_rtu_frame(0x11, bytes.fromhex("03006B0003")) == bytes.fromhex("1103006B00037687")
    assert build_rtu_frame(0x01, bytes.fromhex("030000000A")) == bytes.fromhex("01030000000AC5CD")
    assert crc16(bytes.fromhex("1103006B0003")) == 0x8776


def test_rtu_frame_round_trip_and_crc_detection():
    frame = build_rtu_frame(17, bytes([2, 0, 0, 0, 8]))
    assert parse_rtu_frame(frame) == (17, bytes([2, 0, 0, 0, 8]))
    damaged = frame[:-1] + bytes([frame[-1] ^ 0xFF])
    with pytest.raises(ModbusError) as err:
        parse_rtu_frame(damaged)
    assert err.value.kind == ERROR_CRC


def test_rtu_response_length_is_known_from_the_first_three_bytes():
    assert rtu_response_length(bytes([1, 2, 2])) == 7        # read: 3 + byte count + CRC
    assert rtu_response_length(bytes([1, 4, 8])) == 13
    assert rtu_response_length(bytes([1, 5, 0])) == 8        # write echo
    assert rtu_response_length(bytes([1, 0x82, 2])) == 5     # exception
    with pytest.raises(ModbusError):
        rtu_response_length(bytes([1, 0x2B, 0]))


def test_bits_and_registers_unpack_lsb_first_and_big_endian():
    assert unpack_bits(bytes([2, 2, 0b00000101, 0b00000001]), 12) == [True, False, True] + [False] * 5 + [True] + [False] * 3
    assert unpack_registers(bytes([4, 4, 0x00, 0x10, 0xFF, 0xFE]), 2) == [16, 65534]
    assert unpack_registers(bytes([4, 4, 0x00, 0x10, 0xFF, 0xFE]), 2, signed=True) == [16, -2]
    with pytest.raises(ModbusError):
        unpack_bits(bytes([2, 1, 0]), 16)


def test_make_transport_reports_what_this_controller_cannot_open(monkeypatch):
    with pytest.raises(TransportUnavailable):
        make_transport({"transport": "TCP"})           # no host
    with pytest.raises(TransportUnavailable):
        make_transport({"transport": "RTU"})           # no port
    with pytest.raises(TransportUnavailable):
        make_transport({"transport": "PROFIBUS", "port": "COM1"})
    import builtins
    real_import = builtins.__import__

    def _no_serial(name, *args, **kwargs):
        if name == "serial":
            raise ImportError("No module named 'serial'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_serial)
    with pytest.raises(TransportUnavailable) as err:
        make_transport({"transport": "RTU", "port": "COM3", "baud_rate": 19200, "parity": "E"})
    assert "pyserial" in str(err.value)
    assert isinstance(make_transport(_bus(type("S", (), {"port": 1502})())), TcpTransport)


# --- client against the loopback module ------------------------------------------------------

def test_client_reads_and_writes_through_a_real_tcp_exchange(server):
    server.inputs[0] = server.inputs[3] = True
    server.input_registers[:] = [100, 2000, 65535, 7]
    client = ModbusClient(TcpTransport("127.0.0.1", server.port, timeout=1.0), retries=0)

    assert client.read_bits(1, mb.FC_READ_DISCRETE_INPUTS, 0, 16)[:4] == [True, False, False, True]
    assert client.read_registers(1, mb.FC_READ_INPUT_REGISTERS, 0, 4) == [100, 2000, 65535, 7]
    client.write_coil(1, 5, True)
    assert server.coils[5] is True
    assert client.read_bits(1, mb.FC_READ_COILS, 0, 8)[5] is True
    client.write_register(1, 2, 4242)
    assert server.input_registers[2] == 4242
    client.close()


def test_client_reports_exception_timeout_and_wrong_unit_as_comm_errors(server):
    client = ModbusClient(TcpTransport("127.0.0.1", server.port, timeout=0.3), retries=1)
    with pytest.raises(ModbusError) as err:
        client.read_bits(9, mb.FC_READ_DISCRETE_INPUTS, 0, 8)       # unit 9 does not exist -> exception reply
    assert err.value.kind == ERROR_INVALID_RESPONSE and "exception" in str(err.value)

    server.misbehave = "silent"
    with pytest.raises(ModbusError) as err:
        client.read_bits(1, mb.FC_READ_DISCRETE_INPUTS, 0, 8)
    assert err.value.kind == ERROR_TIMEOUT
    assert len([r for r in server.requests if r[0] == 1]) == 2   # one retry, as configured

    server.misbehave = "wrong_unit"
    with pytest.raises(ModbusError) as err:
        client.read_bits(1, mb.FC_READ_DISCRETE_INPUTS, 0, 8)
    assert err.value.kind == ERROR_INVALID_RESPONSE
    client.close()


def test_unreachable_host_is_a_timeout_not_a_crash():
    dead = socket.socket()
    dead.bind(("127.0.0.1", 0))
    port = dead.getsockname()[1]
    dead.close()  # nothing listens there now
    client = ModbusClient(TcpTransport("127.0.0.1", port, timeout=0.3), retries=0)
    with pytest.raises(ModbusError) as err:
        client.read_bits(1, mb.FC_READ_DISCRETE_INPUTS, 0, 8)
    assert err.value.kind == ERROR_TIMEOUT


# --- the driver ---------------------------------------------------------------------------

def _wait(predicate, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def test_driver_polls_every_kind_of_a_card_into_driver_update_events(server):
    server.inputs[1] = True
    server.coils[2] = True
    server.input_registers[:] = [12, 34, 56, 78]
    bus = EventBus()
    events = _Events(bus)
    driver = ModbusDriver(bus)

    polled = driver.configure(_bus(server), _cards(), {"poll_interval_ms": 50, "timeout_s": 0.5, "retries": 0})

    assert polled == ["ELA1", "ADA1"]
    assert driver.skipped_card_ids() == ["NOADDR"]
    assert driver.unavailable_reason is None
    driver.start()
    try:
        assert driver.is_alive()
        assert _wait(lambda: "ADA1.DO.3" in events.updates and "ELA1.AI.4" in events.updates)
        assert events.updates["ELA1.DI.2"] == (True, "GOOD")
        assert events.updates["ELA1.DI.1"] == (False, "GOOD")
        assert events.updates["ELA1.AI.1"] == (12, "GOOD")
        assert events.updates["ELA1.AI.4"] == (78, "GOOD")
        assert events.updates["ADA1.DO.3"] == (True, "GOOD")
        assert "NOADDR.DI.1" not in events.updates
        assert _wait(lambda: events.comm_ok.count("ELA1") >= 2 and "ADA1" in events.comm_ok)
        stats = driver.get_comm_stats()
        assert stats["ELA1"].frames_sent >= 2 and stats["ELA1"].total_errors == 0
        assert stats["ELA1"].avg_response_ms is not None and stats["ELA1"].avg_response_ms >= 0
    finally:
        driver.stop()
    assert driver.is_alive() is False


def test_driver_write_tag_drives_a_coil_and_a_register_and_refuses_inputs(server):
    bus = EventBus()
    events = _Events(bus)
    driver = ModbusDriver(bus)
    driver.configure(_bus(server), _cards() + [{"id": "ADA1", "kind": "AO", "channels": 2, "modbus_unit_id": 1}],
                     {"poll_interval_ms": 50, "timeout_s": 0.5})
    # No poll thread needed for a write - CommandManager calls write_tag() directly.
    assert driver.write_tag("ADA1.DO.4", True) is True
    assert server.coils[3] is True
    assert events.updates["ADA1.DO.4"] == (True, "GOOD")
    assert driver.write_tag("ADA1.DO.4", False) is True
    assert server.coils[3] is False

    assert driver.write_tag("ADA1.AO.2", 300.4) is True
    assert server.input_registers[1] == 300
    assert events.updates["ADA1.AO.2"] == (300, "GOOD")

    assert driver.write_tag("ELA1.DI.1", True) is False       # an input
    assert driver.write_tag("NOADDR.DI.1", True) is False     # not on the bus
    assert driver.write_tag("Security.Zone1.Armed", True) is False
    assert driver.write_tag("ADA1.DO.99", True) is False      # module answers with an exception
    assert driver.get_comm_stats()["ADA1"].total_errors == 1


def test_driver_counts_errors_and_withholds_the_heartbeat_when_the_module_stops_answering(server):
    bus = EventBus()
    events = _Events(bus)
    driver = ModbusDriver(bus)
    driver.configure(_bus(server), _cards()[:1], {"poll_interval_ms": 30, "timeout_s": 0.2, "retries": 0})
    driver.start()
    try:
        assert _wait(lambda: events.comm_ok.count("ELA1") >= 1)
        server.misbehave = "silent"
        assert _wait(lambda: driver.get_comm_stats()["ELA1"].total_errors >= 1, timeout=4.0)
        heartbeats = events.comm_ok.count("ELA1")
        time.sleep(0.5)
        assert events.comm_ok.count("ELA1") <= heartbeats + 1   # at most the one already in flight
        assert driver.is_alive()                                  # the loop keeps retrying
        server.misbehave = None
        assert _wait(lambda: events.comm_ok.count("ELA1") > heartbeats + 1, timeout=4.0)
    finally:
        driver.stop()


def test_driver_without_an_openable_bus_still_starts_and_says_why(monkeypatch):
    import builtins
    real_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__",
                        lambda name, *a, **k: (_ for _ in ()).throw(ImportError(name)) if name == "serial"
                        else real_import(name, *a, **k))
    driver = ModbusDriver(EventBus())
    assert driver.configure({"transport": "RTU", "port": "/dev/ttyUSB0"}, _cards(), {}) == ["ELA1", "ADA1"]
    assert "pyserial" in driver.unavailable_reason
    driver.start()
    try:
        assert driver.is_running and driver.is_alive()
        assert driver.write_tag("ADA1.DO.1", True) is False
    finally:
        driver.stop()


# --- through EPWCore: projekt.epw + controller.local.json ------------------------------------------

@pytest.fixture
def start_core(db):
    cores = []

    def _start(project_path):
        from epw_os.core.epw_core import EPWCore
        core = EPWCore()
        core.project_manager.project_file = str(project_path)
        core.startup()
        cores.append(core)
        return core

    yield _start
    for core in cores:
        if core.is_running:
            core.shutdown()


def _project(tmp_path, server, with_unit_ids=True):
    from epw_os.core import project_format as pf
    project = pf.new_project("Modbus site", author="Test")
    project.modules = ["analog_inputs"]
    project.locations = [pf.Location("KOT", "Kotlownia")]
    unit = 1 if with_unit_ids else None
    project.cards = [pf.Card("ELA1", "ELA01", channel_kinds={"DI": 8, "AI": 2}, modbus_unit_id=unit, location="KOT"),
                     pf.Card("ADA1", "ADA01", channel_kinds={"DO": 4}, modbus_unit_id=unit, location="KOT"),
                     pf.Card("SIMDI", "ELA01", channel_kinds={"DI": 2}, location="KOT")]
    project.points = ([pf.Point(address=f"ELA1.DI.{n}") for n in range(1, 9)]
                      + [pf.Point(address=f"ELA1.AI.{n}") for n in (1, 2)]
                      + [pf.Point(address=f"ADA1.DO.{n}") for n in range(1, 5)]
                      + [pf.Point(address=f"SIMDI.DI.{n}") for n in (1, 2)])
    project.devices = [pf.Device(id="KOT_KM1", behavior="SWITCHED", feedback=["ELA1.DI.1"], command=["ADA1.DO.1"])]
    project.modbus_bus = pf.ModbusBusConfig(transport="TCP", host="127.0.0.1", tcp_port=server.port)
    path = tmp_path / "projekt.epw"
    pf.save_project(project, path)
    return path


def _local_settings(tmp_path, **io):
    (tmp_path / "controller.local.json").write_text(json.dumps({
        "format": "EPW_CONTROLLER_SETTINGS", "schema_version": 1,
        "io_driver": {"driver": "MODBUS", "poll_interval_ms": 50, "timeout_s": 0.5, "retries": 0, **io},
    }), encoding="utf-8")


def test_core_runs_the_project_against_the_modbus_bus_when_the_controller_says_so(tmp_path, server, start_core):
    server.inputs[0] = True
    server.input_registers[0] = 1234
    path = _project(tmp_path, server)
    _local_settings(tmp_path)

    core = start_core(path)

    assert core.modbus_driver is not None and core.modbus_driver.is_alive()
    assert core.driver_manager.get_driver(DRIVER_ID) is core.modbus_driver
    assert core.device_manager.devices["ELA1"]["driver_id"] == DRIVER_ID
    assert core.device_manager.devices["SIMDI"]["driver_id"] == "SIM_DRIVER"
    assert sorted(core.sim_driver.device_ids)[:1] == ["ADA01"] and "ELA1" not in core.sim_driver.device_ids
    assert core.sim_driver._analog_tags == []       # ELA1.AI.* belong to the bus, not the simulator

    assert _wait(lambda: core.tag_manager.get_tag("ELA1.DI.1").value is True)
    assert _wait(lambda: core.tag_manager.get_tag("ELA1.AI.1").value == 1234.0)
    assert core.tag_manager.get_tag("ELA1.DI.1").quality.value == "GOOD"

    # A command for the apparatus goes to the bus: KOT_KM1.CLOSE -> ADA1.DO.1 -> coil 0.
    definition = core.command_manager._definitions["KOT_KM1.CLOSE"]
    assert definition.driver_id == DRIVER_ID
    assert core.driver_manager.route_command(DRIVER_ID, "ADA1.DO.1", True) is True
    assert server.coils[0] is True
    assert _wait(lambda: core.tag_manager.get_tag("ADA1.DO.1").value is True)
    assert [i["id"] for i in core.startup_issues] == ["MODBUS_NO_UNIT_ID.SIMDI"]  # the simulator card, by design


def test_core_reports_cards_without_a_unit_id_and_keeps_the_simulator_for_them(tmp_path, server, start_core):
    path = _project(tmp_path, server, with_unit_ids=False)
    _local_settings(tmp_path)

    core = start_core(path)

    ids = [issue["id"] for issue in core.startup_issues]
    assert "MODBUS_NO_UNIT_ID.ELA1" in ids and "MODBUS_NO_UNIT_ID.ADA1" in ids
    assert core.modbus_driver.polled_card_ids() == []
    assert core.device_manager.devices["ELA1"]["driver_id"] == "SIM_DRIVER"
    assert core.tag_manager.get_tag("ELA1.AI.1") is not None
    assert "ELA1.AI.1" in core.sim_driver._analog_tags


def test_core_without_the_setting_is_the_simulator_exactly_as_before(tmp_path, server, start_core):
    path = _project(tmp_path, server)

    core = start_core(path)

    assert core.modbus_driver is None
    assert core.driver_manager.get_driver(DRIVER_ID) is None
    assert core.device_manager.devices["ELA1"]["driver_id"] == "SIM_DRIVER"
    assert "ELA1.AI.1" in core.sim_driver._analog_tags
    assert server.requests == []
