"""Virtual Modbus TCP bus - the cards of a project, in software, so the
runtime's Modbus driver (io_driver "MODBUS" in controller.local.json,
modbus_bus transport TCP, host 127.0.0.1) can be exercised end to end
before any ELA/ADA/EPM module is on the bench.

    python tools/modbus_sim.py --project ../projekt.epw           # units and channel counts from the cards
    python tools/modbus_sim.py --unit 1:di=16,ai=4 --unit 2:do=16 # or by hand
    python tools/modbus_sim.py --project projekt.epw --port 1502 --mirror

Then, on the prompt:
    di 1 3 on        discrete input 3 of unit 1 closes
    ai 1 2 1234      input register 2 of unit 1 (raw value)
    show 1           everything unit 1 holds
    quit

Every coil/register write the runtime sends is printed as it arrives.
With --mirror a written coil n also closes discrete input n of the SAME
unit after a short delay - a stand-in for the field feedback a real
apparatus would give, so PULSE/PULSE_TOGGLE styles confirm like on a
real installation. The server speaks FC1/2/3/4/5/6/15/16 and answers a
Modbus exception for anything else or out of range; standard library
only, the same as the driver.
"""
import argparse
import socketserver
import struct
import sys
import threading
import time
from pathlib import Path

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

KINDS = ("di", "do", "ai", "ao")


class VirtualUnit:
    def __init__(self, di=0, do=0, ai=0, ao=0):
        self.inputs = [False] * di
        self.coils = [False] * do
        self.input_registers = [0] * ai
        self.holding = [0] * ao

    def describe(self):
        return {"di": self.inputs, "do": self.coils, "ai": self.input_registers, "ao": self.holding}


class VirtualBus:
    """Importable (tests, bench scripts) and runnable as the CLI below."""

    def __init__(self, units: dict, host="127.0.0.1", port=0, mirror_coils_to_inputs=False, mirror_delay_s=0.05,
                 on_write=None):
        self.units = {int(unit): VirtualUnit(**{k: int(v) for k, v in kinds.items() if k in KINDS})
                      for unit, kinds in units.items()}
        self.mirror = mirror_coils_to_inputs
        self.mirror_delay_s = mirror_delay_s
        self.on_write = on_write
        self.writes = []
        self._silent = set()      # units that do not answer at all (a dead card, a cut wire)
        self._lock = threading.RLock()
        bus = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                while True:
                    header = bus._recv_exact(self.request, 7)
                    if header is None:
                        return
                    tid, _proto, length, unit = struct.unpack(">HHHB", header)
                    pdu = bus._recv_exact(self.request, length - 1)
                    if pdu is None:
                        return
                    if unit in bus._silent:
                        continue          # no reply: the master times out, exactly like a dead card
                    reply = bus.respond(unit, pdu)
                    self.request.sendall(struct.pack(">HHHB", tid, 0, len(reply) + 1, unit) + reply)

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self.server = Server((host, port), Handler)
        self.host, self.port = self.server.server_address[0], self.server.server_address[1]
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="ModbusSim")
        self._thread.start()

    @staticmethod
    def _recv_exact(sock, n):
        data = b""
        while len(data) < n:
            try:
                part = sock.recv(n - len(data))
            except OSError:
                return None
            if not part:
                return None
            data += part
        return data

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    # -- state ---------------------------------------------------------------------------

    def silence(self, unit: int, silent: bool = True):
        """A unit that stops answering (the card lost power, the wire is
        cut): every request to it times out until silence(unit, False)."""
        with self._lock:
            if silent:
                self._silent.add(int(unit))
            else:
                self._silent.discard(int(unit))

    def is_silent(self, unit: int) -> bool:
        return int(unit) in self._silent

    def set_input(self, unit: int, channel: int, value: bool):
        with self._lock:
            self.units[unit].inputs[channel - 1] = bool(value)

    def set_analog(self, unit: int, channel: int, value: int):
        with self._lock:
            self.units[unit].input_registers[channel - 1] = int(value) & 0xFFFF

    def coil(self, unit: int, channel: int) -> bool:
        return self.units[unit].coils[channel - 1]

    def _coil_written(self, unit: int, address: int, value: bool):
        self.writes.append((unit, "coil", address + 1, value))
        if self.on_write:
            self.on_write(unit, "coil", address + 1, value)
        if self.mirror and address < len(self.units[unit].inputs):
            def mirror():
                with self._lock:
                    self.units[unit].inputs[address] = value
            timer = threading.Timer(self.mirror_delay_s, mirror)
            timer.daemon = True
            timer.start()

    # -- protocol --------------------------------------------------------------------------

    @staticmethod
    def _exception(function, code):
        return bytes([function | 0x80, code])

    @staticmethod
    def _pack_bits(bits):
        out = bytearray((len(bits) + 7) // 8)
        for i, bit in enumerate(bits):
            if bit:
                out[i // 8] |= 1 << (i % 8)
        return bytes(out)

    def respond(self, unit: int, pdu: bytes) -> bytes:
        function = pdu[0]
        target = self.units.get(unit)
        if target is None:
            return self._exception(function, 11)   # gateway: no such unit
        with self._lock:
            try:
                if function in (1, 2):
                    start, count = struct.unpack(">HH", pdu[1:5])
                    table = target.coils if function == 1 else target.inputs
                    if count < 1 or start + count > len(table):
                        return self._exception(function, 2)
                    payload = self._pack_bits(table[start:start + count])
                    return bytes([function, len(payload)]) + payload
                if function in (3, 4):
                    start, count = struct.unpack(">HH", pdu[1:5])
                    table = target.holding if function == 3 else target.input_registers
                    if count < 1 or start + count > len(table):
                        return self._exception(function, 2)
                    return bytes([function, 2 * count]) + struct.pack(">" + "H" * count,
                                                                     *[v & 0xFFFF for v in table[start:start + count]])
                if function == 5:
                    address, value = struct.unpack(">HH", pdu[1:5])
                    if address >= len(target.coils):
                        return self._exception(function, 2)
                    if value not in (0x0000, 0xFF00):
                        return self._exception(function, 3)
                    target.coils[address] = value == 0xFF00
                    self._coil_written(unit, address, value == 0xFF00)
                    return pdu
                if function == 6:
                    address, value = struct.unpack(">HH", pdu[1:5])
                    if address >= len(target.holding):
                        return self._exception(function, 2)
                    target.holding[address] = value
                    self.writes.append((unit, "register", address + 1, value))
                    if self.on_write:
                        self.on_write(unit, "register", address + 1, value)
                    return pdu
                if function == 15:
                    start, count, byte_count = struct.unpack(">HHB", pdu[1:6])
                    if count < 1 or start + count > len(target.coils):
                        return self._exception(function, 2)
                    data = pdu[6:6 + byte_count]
                    for i in range(count):
                        value = bool((data[i // 8] >> (i % 8)) & 1)
                        target.coils[start + i] = value
                        self._coil_written(unit, start + i, value)
                    return pdu[:5]
                if function == 16:
                    start, count, byte_count = struct.unpack(">HHB", pdu[1:6])
                    if count < 1 or start + count > len(target.holding):
                        return self._exception(function, 2)
                    values = struct.unpack(">" + "H" * count, pdu[6:6 + 2 * count])
                    for i, value in enumerate(values):
                        target.holding[start + i] = value
                        self.writes.append((unit, "register", start + i + 1, value))
                    return pdu[:5]
            except (struct.error, IndexError):
                return self._exception(function, 3)
        return self._exception(function, 1)


def units_from_project(path) -> dict:
    """{unit id: {"di": n, "do": n, "ai": n, "ao": n}} from a projekt.epw's cards."""
    from epw_os.core import project_format as pf
    result = pf.read_project(str(path))
    if not result.ok:
        raise SystemExit(f"Cannot read {path}: {result.error}")
    units = {}
    for card in result.project.cards:
        if card.modbus_unit_id is None:
            print(f"card {card.id}: no Modbus unit id - skipped")
            continue
        kinds = units.setdefault(int(card.modbus_unit_id), {})
        for kind, count in card.channel_kinds.items():
            kinds[kind.lower()] = kinds.get(kind.lower(), 0) + int(count)
    return units


def parse_unit_arg(text: str):
    """"1:di=16,ai=4" -> (1, {"di": 16, "ai": 4})"""
    unit, _, spec = text.partition(":")
    kinds = {}
    for part in spec.split(","):
        if not part:
            continue
        kind, _, count = part.partition("=")
        if kind not in KINDS:
            raise argparse.ArgumentTypeError(f"unknown kind {kind!r} in {text!r} (di/do/ai/ao)")
        kinds[kind] = int(count or 0)
    return int(unit), kinds


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="\n".join(__doc__.split("\n\n")[1:]))
    parser.add_argument("--project", help="projekt.epw whose cards define the units")
    parser.add_argument("--unit", action="append", default=[], type=parse_unit_arg, metavar="ID:di=N,do=N,ai=N,ao=N")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=502, help="TCP port (default 502; use 1502 without root)")
    parser.add_argument("--mirror", action="store_true", help="a written coil n closes DI n of the same unit")
    return parser


def run_prompt(bus: VirtualBus, stdin=sys.stdin, out=print):
    out(f"Virtual Modbus bus on {bus.host}:{bus.port} - units: " +
        ", ".join(f"{u} (di {len(v.inputs)}, do {len(v.coils)}, ai {len(v.input_registers)}, ao {len(v.holding)})"
                  for u, v in sorted(bus.units.items())))
    out("Commands: di <unit> <ch> on|off | ai <unit> <ch> <value> | show <unit> | quit")
    for line in stdin:
        parts = line.split()
        if not parts:
            continue
        try:
            if parts[0] == "quit":
                return
            if parts[0] == "di":
                bus.set_input(int(parts[1]), int(parts[2]), parts[3].lower() in ("1", "on", "true"))
                out("ok")
            elif parts[0] == "ai":
                bus.set_analog(int(parts[1]), int(parts[2]), int(parts[3]))
                out("ok")
            elif parts[0] == "show":
                unit = bus.units[int(parts[1])]
                out(f"di {['1' if v else '0' for v in unit.inputs]}")
                out(f"do {['1' if v else '0' for v in unit.coils]}")
                out(f"ai {unit.input_registers}")
                out(f"ao {unit.holding}")
            else:
                out("? di/ai/show/quit")
        except (KeyError, IndexError, ValueError) as e:
            out(f"error: {e}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    units = units_from_project(args.project) if args.project else {}
    for unit, kinds in args.unit:
        units.setdefault(unit, {}).update(kinds)
    if not units:
        print("No units - give --project or --unit.")
        return 1
    bus = VirtualBus(units, host=args.host, port=args.port, mirror_coils_to_inputs=args.mirror,
                     on_write=lambda unit, what, channel, value: print(f"<- unit {unit} {what} {channel} = {value}"))
    try:
        run_prompt(bus)
    except KeyboardInterrupt:
        pass
    finally:
        bus.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
