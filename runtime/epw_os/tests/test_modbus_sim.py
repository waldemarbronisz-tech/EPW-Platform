"""tools/modbus_sim.py - the virtual Modbus TCP bus - exercised through the
driver's own client and through the ModbusDriver itself, plus the unit
list built from a project's cards."""
import importlib.util
import io
import sys
import time
from pathlib import Path

import pytest

from epw_os.core import project_format as pf
from epw_os.core.events import EventBus
from epw_os.drivers.modbus_driver import (FC_READ_COILS, FC_READ_DISCRETE_INPUTS, FC_READ_HOLDING_REGISTERS,
                                          FC_READ_INPUT_REGISTERS, ModbusClient, ModbusDriver, ModbusError,
                                          TcpTransport)

_SIM = Path(__file__).resolve().parents[2] / "tools" / "modbus_sim.py"
_spec = importlib.util.spec_from_file_location("modbus_sim", _SIM)
sim = importlib.util.module_from_spec(_spec)
sys.modules["modbus_sim"] = sim
_spec.loader.exec_module(sim)


@pytest.fixture
def bus():
    b = sim.VirtualBus({1: {"di": 8, "do": 8, "ai": 4, "ao": 2}, 2: {"do": 4}})
    yield b
    b.close()


def _client(bus, retries=0):
    return ModbusClient(TcpTransport("127.0.0.1", bus.port, timeout=1.0), retries=retries)


def test_reads_writes_and_exceptions_through_the_drivers_client(bus):
    bus.set_input(1, 3, True)
    bus.set_analog(1, 2, 4321)
    client = _client(bus)
    assert client.read_bits(1, FC_READ_DISCRETE_INPUTS, 0, 8) == [False, False, True] + [False] * 5
    assert client.read_registers(1, FC_READ_INPUT_REGISTERS, 0, 4) == [0, 4321, 0, 0]
    client.write_coil(1, 5, True)
    assert bus.coil(1, 6) is True and bus.writes[-1] == (1, "coil", 6, True)
    assert client.read_bits(1, FC_READ_COILS, 0, 8)[5] is True
    client.write_register(1, 1, 777)
    assert client.read_registers(1, FC_READ_HOLDING_REGISTERS, 0, 2) == [0, 777]
    client.write_coil(2, 0, True)
    assert bus.coil(2, 1) is True
    with pytest.raises(ModbusError):
        client.read_bits(1, FC_READ_DISCRETE_INPUTS, 0, 9)          # past the card's channels
    with pytest.raises(ModbusError):
        client.read_bits(9, FC_READ_DISCRETE_INPUTS, 0, 1)          # no such unit
    with pytest.raises(ModbusError):
        client.write_coil(2, 7, True)
    client.close()


def test_mirror_turns_a_written_coil_into_the_matching_input(bus):
    mirrored = sim.VirtualBus({1: {"di": 4, "do": 4}}, mirror_coils_to_inputs=True, mirror_delay_s=0.01)
    try:
        client = _client(mirrored)
        client.write_coil(1, 2, True)
        deadline = time.time() + 2
        while time.time() < deadline and not mirrored.units[1].inputs[2]:
            time.sleep(0.01)
        assert client.read_bits(1, FC_READ_DISCRETE_INPUTS, 0, 4) == [False, False, True, False]
        client.close()
    finally:
        mirrored.close()


def test_the_runtime_driver_polls_the_virtual_bus(bus):
    bus.set_input(1, 1, True)
    bus.set_analog(1, 1, 55)
    events = EventBus()
    seen = {}
    events.subscribe("driver_update", lambda tag, value, quality: seen.__setitem__(tag, value))
    driver = ModbusDriver(events)
    driver.configure({"transport": "TCP", "host": "127.0.0.1", "tcp_port": bus.port},
                     [{"id": "ELA1", "kind": "DI", "channels": 8, "modbus_unit_id": 1},
                      {"id": "ELA1", "kind": "AI", "channels": 4, "modbus_unit_id": 1},
                      {"id": "ADA2", "kind": "DO", "channels": 4, "modbus_unit_id": 2}],
                     {"poll_interval_ms": 30, "timeout_s": 0.5, "retries": 0})
    driver.start()
    try:
        deadline = time.time() + 3
        while time.time() < deadline and "ADA2.DO.1" not in seen:
            time.sleep(0.02)
        assert seen["ELA1.DI.1"] is True and seen["ELA1.AI.1"] == 55 and seen["ADA2.DO.1"] is False
        assert driver.write_tag("ADA2.DO.3", True) is True
        assert bus.coil(2, 3) is True
        assert driver.get_comm_stats()["ELA1"].total_errors == 0
    finally:
        driver.stop()


def test_units_come_from_a_projects_cards(tmp_path):
    project = pf.new_project("Bus", author="t")
    project.cards = [pf.Card("ELA1", "ELA01", channel_kinds={"DI": 16, "AI": 4}, modbus_unit_id=1),
                     pf.Card("ADA1", "ADA01", channel_kinds={"DO": 16, "AO": 2}, modbus_unit_id=2),
                     pf.Card("NOADDR", "ELA01", channel_kinds={"DI": 8})]
    path = tmp_path / "projekt.epw"
    pf.save_project(project, path)
    assert sim.units_from_project(path) == {1: {"di": 16, "ai": 4}, 2: {"do": 16, "ao": 2}}
    assert sim.parse_unit_arg("3:di=8,do=8") == (3, {"di": 8, "do": 8})


def test_the_prompt_changes_inputs_and_shows_a_unit(bus):
    out = []
    sim.run_prompt(bus, stdin=io.StringIO("di 1 2 on\nai 1 1 99\nshow 1\nbogus\ndi 7 1 on\nquit\n"), out=out.append)
    assert bus.units[1].inputs[1] is True and bus.units[1].input_registers[0] == 99
    assert any(line.startswith("di ['0', '1'") for line in out)
    assert any(line.startswith("? ") for line in out) and any(line.startswith("error:") for line in out)
