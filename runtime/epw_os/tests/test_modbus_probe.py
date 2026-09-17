"""tools/modbus_probe.py - the commissioning probe - against the same
loopback Modbus TCP module test_modbus_driver.py uses: it reads and
writes through the driver's own client and reports failures as data."""
import importlib.util
import sys
from pathlib import Path

import pytest

from epw_os.tests.test_modbus_driver import LoopbackModbusServer

_PROBE = Path(__file__).resolve().parents[2] / "tools" / "modbus_probe.py"
_spec = importlib.util.spec_from_file_location("modbus_probe", _PROBE)
probe = importlib.util.module_from_spec(_spec)
sys.modules["modbus_probe"] = probe
_spec.loader.exec_module(probe)


@pytest.fixture
def server():
    srv = LoopbackModbusServer()
    yield srv
    srv.close()


def _run(argv):
    lines = []
    code = probe.main(argv, out=lines.append)
    return code, "\n".join(lines)


def test_reads_inputs_coils_and_registers_by_channel_number(server):
    server.inputs[0] = server.inputs[3] = True
    server.input_registers[:] = [100, 65535, 7, 0]
    code, text = _run(["--tcp", f"127.0.0.1:{server.port}", "--unit", "1", "--di", "4", "--do", "2", "--ai", "2"])
    assert code == 0, text
    assert "DI FC2   1:1 2:0 3:0 4:1" in text
    assert "DO FC1   1:0 2:0" in text
    assert "AI FC4   1:100 2:65535" in text
    assert "unit 1" in text


def test_signed_registers_and_a_start_offset(server):
    server.input_registers[:] = [65534, 5, 6, 7]
    code, text = _run(["--tcp", f"127.0.0.1:{server.port}", "--unit", "1", "--ai", "2", "--signed"])
    assert code == 0 and "AI FC4   1:-2 2:5" in text
    code, text = _run(["--tcp", f"127.0.0.1:{server.port}", "--unit", "1", "--ai", "2", "--start", "2"])
    assert code == 0 and "AI FC4   3:6 4:7" in text


def test_writes_a_coil_and_a_register_then_reads_back(server):
    code, text = _run(["--tcp", f"127.0.0.1:{server.port}", "--unit", "1", "--write-coil", "3", "1", "--do", "4",
                       "--write-register", "1", "4242", "--ai", "2"])
    assert code == 0, text
    assert server.coils[3] is True and server.input_registers[1] == 4242
    assert "FC5      coil 3 (channel 4) <- 1  ok" in text
    assert "DO FC1   1:0 2:0 3:0 4:1" in text
    assert "AI FC4   1:0 2:4242" in text


def test_failures_are_reported_and_change_the_exit_code(server):
    code, text = _run(["--tcp", f"127.0.0.1:{server.port}", "--unit", "9", "--di", "4"])   # no such unit -> exception reply
    assert code == 2 and "DI FC2  FAILED: INVALID_RESPONSE" in text
    server.misbehave = "silent"
    code, text = _run(["--tcp", f"127.0.0.1:{server.port}", "--unit", "1", "--di", "4", "--timeout", "0.2"])
    assert code == 2 and "FAILED: TIMEOUT" in text


def test_argument_problems_exit_with_one(monkeypatch):
    code, text = _run(["--tcp", "127.0.0.1:1", "--unit", "1"])
    assert code == 1 and "Nothing to do" in text
    import builtins
    real_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__",
                        lambda name, *a, **k: (_ for _ in ()).throw(ImportError(name)) if name == "serial"
                        else real_import(name, *a, **k))
    code, text = _run(["--rtu", "COM77", "--unit", "1", "--di", "1"])
    assert code == 1 and "pyserial" in text
