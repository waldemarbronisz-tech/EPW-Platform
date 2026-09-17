"""Commissioning probe for the Modbus bus (task "sprawdzić Modbus na
sprzęcie"): talks to ONE card by unit id with the same framing/transport
code the runtime's ModbusDriver uses (epw_os/drivers/modbus_driver.py)
and prints what it answers - raw bits and registers - so the mapping the
driver assumes (channel n = address n-1, DI via FC2, DO via FC1/FC5, AI
via FC4, AO via FC6) can be checked against real ELA/ADA/EPM modules
before a project relies on it. Nothing here touches projekt.epw or the
running controller.

Examples:
  python tools/modbus_probe.py --tcp 192.168.1.60 --unit 1 --di 16
  python tools/modbus_probe.py --rtu COM3 --baud 19200 --parity E --unit 2 --ai 8
  python tools/modbus_probe.py --tcp 192.168.1.60 --unit 1 --write-coil 3 1 --do 8
  python tools/modbus_probe.py --tcp 192.168.1.60 --unit 1 --di 16 --loop 1.0

Exit code 0 when every requested exchange succeeded, 2 when any failed
(the reason is printed), 1 for bad arguments / a bus this machine cannot
open (an RTU bus needs pyserial).
"""
import argparse
import sys
import time
from pathlib import Path

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from epw_os.drivers.modbus_driver import (FC_READ_COILS, FC_READ_DISCRETE_INPUTS, FC_READ_HOLDING_REGISTERS,  # noqa: E402
                                          FC_READ_INPUT_REGISTERS, ModbusClient, ModbusError, TransportUnavailable,
                                          make_transport)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="\n".join(__doc__.split("\n\n")[1:]))
    bus = parser.add_mutually_exclusive_group(required=True)
    bus.add_argument("--tcp", metavar="HOST[:PORT]", help="Modbus TCP gateway or module (port 502 by default)")
    bus.add_argument("--rtu", metavar="PORT", help="serial port for Modbus RTU, e.g. COM3 or /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=9600, help="RTU baud rate (default 9600)")
    parser.add_argument("--parity", default="N", choices=("N", "E", "O"), help="RTU parity (default N)")
    parser.add_argument("--stop-bits", type=int, default=1, help="RTU stop bits (default 1)")
    parser.add_argument("--unit", type=int, required=True, help="Modbus unit id of the card")
    parser.add_argument("--timeout", type=float, default=1.0, help="response timeout in seconds (default 1.0)")
    parser.add_argument("--start", type=int, default=0, help="first address to read (default 0 = channel 1)")
    parser.add_argument("--di", type=int, metavar="N", help="read N discrete inputs (FC2)")
    parser.add_argument("--do", type=int, metavar="N", help="read N coils back (FC1)")
    parser.add_argument("--ai", type=int, metavar="N", help="read N input registers (FC4)")
    parser.add_argument("--holding", type=int, metavar="N", help="read N holding registers (FC3)")
    parser.add_argument("--signed", action="store_true", help="show registers as signed 16-bit")
    parser.add_argument("--write-coil", nargs=2, metavar=("ADDR", "0|1"), help="write one coil (FC5) before reading")
    parser.add_argument("--write-register", nargs=2, metavar=("ADDR", "VALUE"), help="write one holding register (FC6)")
    parser.add_argument("--loop", type=float, metavar="SECONDS", help="repeat the reads every SECONDS until Ctrl+C")
    return parser


def bus_config(args) -> dict:
    if args.tcp:
        host, _, port = args.tcp.partition(":")
        return {"transport": "TCP", "host": host, "tcp_port": int(port) if port else 502}
    return {"transport": "RTU", "port": args.rtu, "baud_rate": args.baud, "parity": args.parity,
            "data_bits": 8, "stop_bits": args.stop_bits}


def _bits_line(label, start, values):
    cells = " ".join(f"{start + i + 1}:{'1' if v else '0'}" for i, v in enumerate(values))
    return f"{label:<8} {cells}"


def _regs_line(label, start, values):
    cells = " ".join(f"{start + i + 1}:{v}" for i, v in enumerate(values))
    return f"{label:<8} {cells}"


def probe_once(client: ModbusClient, args, out=print) -> bool:
    """One round of the requested writes and reads. Prints one line per
    kind; returns False when any exchange failed."""
    unit, start, ok = args.unit, args.start, True
    if args.write_coil:
        address, value = int(args.write_coil[0]), args.write_coil[1] not in ("0", "false", "off")
        try:
            client.write_coil(unit, address, value)
            out(f"FC5      coil {address} (channel {address + 1}) <- {'1' if value else '0'}  ok")
        except ModbusError as e:
            out(f"FC5      coil {address} <- {'1' if value else '0'}  FAILED: {e.kind}: {e}")
            ok = False
    if args.write_register:
        address, value = int(args.write_register[0]), int(args.write_register[1])
        try:
            client.write_register(unit, address, value)
            out(f"FC6      register {address} (channel {address + 1}) <- {value}  ok")
        except ModbusError as e:
            out(f"FC6      register {address} <- {value}  FAILED: {e.kind}: {e}")
            ok = False
    reads = (("DI", args.di, FC_READ_DISCRETE_INPUTS, True), ("DO", args.do, FC_READ_COILS, True),
             ("AI", args.ai, FC_READ_INPUT_REGISTERS, False), ("HOLD", args.holding, FC_READ_HOLDING_REGISTERS, False))
    for label, count, function, bits in reads:
        if not count:
            continue
        t0 = time.perf_counter()
        try:
            if bits:
                values = client.read_bits(unit, function, start, count)
                line = _bits_line(f"{label} FC{function}", start, values)
            else:
                values = client.read_registers(unit, function, start, count, signed=args.signed)
                line = _regs_line(f"{label} FC{function}", start, values)
            out(f"{line}   ({(time.perf_counter() - t0) * 1000:.1f} ms)")
        except ModbusError as e:
            out(f"{label} FC{function}  FAILED: {e.kind}: {e}")
            ok = False
    return ok


def main(argv=None, out=print) -> int:
    args = build_parser().parse_args(argv)
    if not any((args.di, args.do, args.ai, args.holding, args.write_coil, args.write_register)):
        out("Nothing to do - give at least one of --di/--do/--ai/--holding/--write-coil/--write-register.")
        return 1
    bus = bus_config(args)
    try:
        client = ModbusClient(make_transport(bus, timeout=args.timeout), retries=0)
    except TransportUnavailable as e:
        out(f"Cannot open the bus: {e}")
        return 1
    out(f"Bus: {bus['transport']} {bus.get('host') or bus.get('port')}  unit {args.unit}  timeout {args.timeout}s")
    try:
        while True:
            ok = probe_once(client, args, out)
            if not args.loop:
                return 0 if ok else 2
            time.sleep(args.loop)
    except KeyboardInterrupt:
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
