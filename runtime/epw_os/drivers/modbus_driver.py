"""Modbus I/O driver (punkt 2 / luka 6: "Modbus driver in runtime").

The controller (Orange Pi) reaches every ELA/ADA/EPM module over ONE bus
(projekt.epw's `modbus_bus`: RTU on a serial port or TCP to a gateway),
each card answering under its own `modbus_unit_id`. This driver polls
those cards and turns what they answer into the same "driver_update"
events SimulatorDriver emits, so nothing above the driver layer
(TagManager, CommandManager, the pages) knows which of the two is
running - BaseDriver's neutral interface is the whole contract.

Address mapping (the standard one for discrete I/O modules; channel n
of a card is address n-1 on the unit):

    DI  <card>.DI.n   read  FC2 (discrete inputs)
    DO  <card>.DO.n   write FC5 (single coil), read back FC1 (coils)
    AI  <card>.AI.n   read  FC4 (input registers)   - the RAW register
                      value; analog_scaling.py turns it into engineering
                      units exactly as it does for the simulator's raw
                      values
    AO  <card>.AO.n   write FC6 (single holding register)

A card with no `modbus_unit_id` is not polled at all (logged once at
configure time) - "not configured" is reported, never guessed.

Framing and the PDUs are implemented here with the standard library
only - no new dependency. A TCP bus needs nothing else; an RTU bus needs
the serial port, which Python cannot open without pyserial: that import
is optional, and a controller without it gets a clear startup issue
("install pyserial") instead of a crash. Errors on the bus are counted
per card in CommDiagnostics (the Bus Diagnostics page) and never stop
the poll loop - a cable unplugged at boot is retried every cycle, the
same as one unplugged later.
"""
import socket
import struct
import threading
import time

from epw_os.core.comm_diagnostics import (CommDiagnostics, ERROR_CRC, ERROR_INVALID_RESPONSE,
                                          ERROR_TIMEOUT)
from epw_os.core.logging import log
from epw_os.drivers.base_driver import BaseDriver

DRIVER_ID = "MODBUS_DRIVER"

FC_READ_COILS = 1
FC_READ_DISCRETE_INPUTS = 2
FC_READ_HOLDING_REGISTERS = 3
FC_READ_INPUT_REGISTERS = 4
FC_WRITE_SINGLE_COIL = 5
FC_WRITE_SINGLE_REGISTER = 6

MODBUS_EXCEPTIONS = {
    1: "ILLEGAL_FUNCTION", 2: "ILLEGAL_DATA_ADDRESS", 3: "ILLEGAL_DATA_VALUE", 4: "SLAVE_DEVICE_FAILURE",
    5: "ACKNOWLEDGE", 6: "SLAVE_DEVICE_BUSY", 8: "MEMORY_PARITY_ERROR", 10: "GATEWAY_PATH_UNAVAILABLE",
    11: "GATEWAY_TARGET_FAILED_TO_RESPOND",
}


class ModbusError(Exception):
    """One failed exchange. `kind` is a comm_diagnostics error type
    (TIMEOUT / CRC / INVALID_RESPONSE) so the Bus Diagnostics page can
    count it without knowing anything Modbus-specific."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


class TransportUnavailable(Exception):
    """The bus cannot be opened on this controller at all (an RTU bus
    without pyserial installed, an unknown transport name) - a
    configuration fact worth a startup issue, unlike a cable that is
    merely unplugged right now."""


# --- framing (pure functions, no I/O) -------------------------------------------------

def crc16(data: bytes) -> int:
    """Modbus RTU CRC-16 (polynomial 0xA001 reflected, init 0xFFFF)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def build_rtu_frame(unit: int, pdu: bytes) -> bytes:
    body = bytes([unit]) + pdu
    return body + struct.pack("<H", crc16(body))  # CRC low byte first, per the spec


def parse_rtu_frame(frame: bytes) -> tuple:
    """(unit, pdu) - raises ModbusError(CRC) on a bad checksum."""
    if len(frame) < 4:
        raise ModbusError(ERROR_INVALID_RESPONSE, f"RTU frame too short ({len(frame)} bytes)")
    body, (crc,) = frame[:-2], struct.unpack("<H", frame[-2:])
    if crc16(body) != crc:
        raise ModbusError(ERROR_CRC, "RTU CRC mismatch")
    return body[0], body[1:]


def build_tcp_frame(transaction_id: int, unit: int, pdu: bytes) -> bytes:
    return struct.pack(">HHHB", transaction_id & 0xFFFF, 0, len(pdu) + 1, unit) + pdu


def rtu_response_length(head: bytes) -> int:
    """Total RTU frame length once its first three bytes (unit, function,
    third byte) are known - how many bytes to wait for on the wire."""
    function, third = head[1], head[2]
    if function & 0x80:
        return 5
    if function in (FC_READ_COILS, FC_READ_DISCRETE_INPUTS, FC_READ_HOLDING_REGISTERS, FC_READ_INPUT_REGISTERS):
        return 3 + third + 2
    if function in (FC_WRITE_SINGLE_COIL, FC_WRITE_SINGLE_REGISTER, 15, 16):
        return 8
    raise ModbusError(ERROR_INVALID_RESPONSE, f"Unexpected function code {function} in response")


def pdu_read(function: int, start: int, count: int) -> bytes:
    return struct.pack(">BHH", function, start, count)


def pdu_write_coil(address: int, value: bool) -> bytes:
    return struct.pack(">BHH", FC_WRITE_SINGLE_COIL, address, 0xFF00 if value else 0x0000)


def pdu_write_register(address: int, value: int) -> bytes:
    return struct.pack(">BHH", FC_WRITE_SINGLE_REGISTER, address, value & 0xFFFF)


def check_response(request_pdu: bytes, response_pdu: bytes) -> bytes:
    """The response PDU for `request_pdu`, or ModbusError for an
    exception reply / a reply to a different function."""
    if not response_pdu:
        raise ModbusError(ERROR_INVALID_RESPONSE, "Empty response PDU")
    function = request_pdu[0]
    if response_pdu[0] == (function | 0x80):
        code = response_pdu[1] if len(response_pdu) > 1 else 0
        raise ModbusError(ERROR_INVALID_RESPONSE,
                          f"Modbus exception {code} ({MODBUS_EXCEPTIONS.get(code, 'UNKNOWN')}) to function {function}")
    if response_pdu[0] != function:
        raise ModbusError(ERROR_INVALID_RESPONSE, f"Response function {response_pdu[0]} does not match request {function}")
    return response_pdu


def unpack_bits(response_pdu: bytes, count: int) -> list:
    """FC1/FC2 reply -> [bool] * count (LSB of the first byte = first channel)."""
    if len(response_pdu) < 2 or len(response_pdu) < 2 + response_pdu[1]:
        raise ModbusError(ERROR_INVALID_RESPONSE, "Truncated bit response")
    byte_count = response_pdu[1]
    if byte_count < (count + 7) // 8:
        raise ModbusError(ERROR_INVALID_RESPONSE, f"Bit response carries {byte_count} bytes, {count} bits needed")
    payload = response_pdu[2:2 + byte_count]
    return [bool((payload[i // 8] >> (i % 8)) & 1) for i in range(count)]


def unpack_registers(response_pdu: bytes, count: int, signed: bool = False) -> list:
    """FC3/FC4 reply -> [int] * count (big-endian 16-bit)."""
    if len(response_pdu) < 2 or len(response_pdu) < 2 + response_pdu[1]:
        raise ModbusError(ERROR_INVALID_RESPONSE, "Truncated register response")
    byte_count = response_pdu[1]
    if byte_count < 2 * count:
        raise ModbusError(ERROR_INVALID_RESPONSE, f"Register response carries {byte_count} bytes, {count} registers needed")
    fmt = ">" + ("h" if signed else "H") * count
    return list(struct.unpack(fmt, response_pdu[2:2 + 2 * count]))


# --- transports ------------------------------------------------------------------------

class TcpTransport:
    """Modbus TCP over a plain socket (a gateway, or a module with its
    own Ethernet port). Opens lazily, drops the socket on any error so
    the next exchange reconnects."""

    def __init__(self, host: str, port: int = 502, timeout: float = 1.0):
        self.host, self.port, self.timeout = host, int(port), float(timeout)
        self._sock = None
        self._transaction = 0

    @property
    def is_open(self) -> bool:
        return self._sock is not None

    def open(self):
        if self._sock is None:
            self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            self._sock.settimeout(self.timeout)

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def _recv_exact(self, n: int) -> bytes:
        chunks = b""
        while len(chunks) < n:
            part = self._sock.recv(n - len(chunks))
            if not part:
                raise ModbusError(ERROR_INVALID_RESPONSE, "Connection closed by the remote side")
            chunks += part
        return chunks

    def exchange(self, unit: int, pdu: bytes) -> bytes:
        try:
            self.open()
            self._transaction = (self._transaction + 1) & 0xFFFF
            self._sock.sendall(build_tcp_frame(self._transaction, unit, pdu))
            header = self._recv_exact(7)
            transaction, protocol, length, reply_unit = struct.unpack(">HHHB", header)
            if protocol != 0 or length < 2:
                raise ModbusError(ERROR_INVALID_RESPONSE, "Malformed MBAP header")
            reply = self._recv_exact(length - 1)
            if transaction != self._transaction:
                raise ModbusError(ERROR_INVALID_RESPONSE, "Transaction id mismatch")
            if reply_unit != unit:
                raise ModbusError(ERROR_INVALID_RESPONSE, f"Reply from unit {reply_unit}, expected {unit}")
            return reply
        except socket.timeout as e:
            self.close()
            raise ModbusError(ERROR_TIMEOUT, f"Timeout talking to unit {unit}") from e
        except (OSError, ConnectionError) as e:
            self.close()
            raise ModbusError(ERROR_TIMEOUT, f"{self.host}:{self.port} unreachable: {e}") from e
        except ModbusError:
            self.close()
            raise


class SerialTransport:
    """Modbus RTU on a serial port through pyserial - imported only here,
    only when an RTU bus is configured, so a controller without it still
    starts (TransportUnavailable says what to install)."""

    def __init__(self, port: str, baud_rate: int = 9600, parity: str = "N", data_bits: int = 8, stop_bits: int = 1,
                 timeout: float = 1.0):
        try:
            import serial  # noqa: F401 - optional dependency, checked here on purpose
        except ImportError as e:
            raise TransportUnavailable("Modbus RTU needs the pyserial package (pip install pyserial).") from e
        self._serial_module = serial
        self.port, self.baud_rate, self.parity = port, int(baud_rate), (parity or "N")[0].upper()
        self.data_bits, self.stop_bits, self.timeout = int(data_bits), int(stop_bits), float(timeout)
        self._port = None

    @property
    def is_open(self) -> bool:
        return self._port is not None

    def open(self):
        if self._port is None:
            serial = self._serial_module
            parity = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}.get(
                self.parity, serial.PARITY_NONE)
            self._port = serial.Serial(port=self.port, baudrate=self.baud_rate, bytesize=self.data_bits,
                                       parity=parity, stopbits=self.stop_bits, timeout=self.timeout)

    def close(self):
        if self._port is not None:
            try:
                self._port.close()
            finally:
                self._port = None

    def _read_exact(self, n: int) -> bytes:
        data = self._port.read(n)
        if len(data) < n:
            raise ModbusError(ERROR_TIMEOUT, f"Timeout: {len(data)} of {n} bytes received")
        return data

    def exchange(self, unit: int, pdu: bytes) -> bytes:
        try:
            self.open()
            self._port.reset_input_buffer()
            self._port.write(build_rtu_frame(unit, pdu))
            head = self._read_exact(3)
            frame = head + self._read_exact(rtu_response_length(head) - 3)
            reply_unit, reply_pdu = parse_rtu_frame(frame)
            if reply_unit != unit:
                raise ModbusError(ERROR_INVALID_RESPONSE, f"Reply from unit {reply_unit}, expected {unit}")
            return reply_pdu
        except ModbusError:
            raise
        except Exception as e:  # pyserial's own SerialException family
            self.close()
            raise ModbusError(ERROR_TIMEOUT, f"Serial port {self.port}: {e}") from e


def make_transport(bus: dict, timeout: float = 1.0):
    """projekt.epw's `modbus_bus` section -> a transport, or
    TransportUnavailable when this controller cannot open that kind of bus."""
    transport = str(bus.get("transport") or "RTU").upper()
    if transport == "TCP":
        if not bus.get("host"):
            raise TransportUnavailable("Modbus TCP bus has no host configured.")
        return TcpTransport(bus["host"], bus.get("tcp_port") or 502, timeout=timeout)
    if transport == "RTU":
        if not bus.get("port"):
            raise TransportUnavailable("Modbus RTU bus has no serial port configured.")
        return SerialTransport(bus["port"], bus.get("baud_rate") or 9600, bus.get("parity") or "N",
                               bus.get("data_bits") or 8, bus.get("stop_bits") or 1, timeout=timeout)
    raise TransportUnavailable(f"Unknown Modbus transport {transport!r} (RTU or TCP).")


# --- client ------------------------------------------------------------------------------

class ModbusClient:
    """One request/response at a time on one bus (a serial line is
    physically half-duplex; a TCP gateway to RS-485 behaves the same)."""

    def __init__(self, transport, retries: int = 1):
        self.transport = transport
        self.retries = max(0, int(retries))
        self._lock = threading.RLock()

    def _request(self, unit: int, pdu: bytes) -> bytes:
        with self._lock:
            last = None
            for _attempt in range(self.retries + 1):
                try:
                    return check_response(pdu, self.transport.exchange(unit, pdu))
                except ModbusError as e:
                    last = e
                    if e.kind == ERROR_INVALID_RESPONSE and "exception" in str(e):
                        raise  # the device answered; asking again changes nothing
            raise last

    def read_bits(self, unit: int, function: int, start: int, count: int) -> list:
        return unpack_bits(self._request(unit, pdu_read(function, start, count)), count)

    def read_registers(self, unit: int, function: int, start: int, count: int, signed: bool = False) -> list:
        return unpack_registers(self._request(unit, pdu_read(function, start, count)), count, signed)

    def write_coil(self, unit: int, address: int, value: bool):
        self._request(unit, pdu_write_coil(address, value))

    def write_register(self, unit: int, address: int, value: int):
        self._request(unit, pdu_write_register(address, value))

    def close(self):
        with self._lock:
            self.transport.close()


# --- the driver ---------------------------------------------------------------------------

UNSUPPORTED_BLOCK_RETRY_S = 30.0


class ModbusDriver(BaseDriver):
    """Polls the project's cards over the project's bus - see the module
    docstring for the mapping. `configure()` takes projekt.epw's own
    data (ProjectManager.get_modbus_bus() / the flat `devices` view) and
    the controller-local polling settings; `start()` never fails on an
    unplugged bus, only on a bus this controller cannot open at all."""

    def __init__(self, event_bus):
        super().__init__("ModbusDriver", event_bus)
        self._thread = None
        self._lock = threading.RLock()
        self._client = None
        self._bus = {}
        self._cards = []       # [{"id", "unit", "kinds": {"DI": n, ...}}]
        self._skipped = []     # card ids without a unit id
        self._poll_interval = 0.25
        self._timeout = 1.0
        self._retries = 1
        self._ai_signed = False
        self._read_back_outputs = True
        self._comm_diagnostics = CommDiagnostics()
        self.unavailable_reason = None
        # (card_id, block) -> monotonic time until which the block is not
        # asked for again: a firmware without it answers "illegal address",
        # which is not a communication error.
        self._unsupported_blocks = {}

    # -- configuration -----------------------------------------------------------------

    def configure(self, bus: dict, cards: list, settings: dict = None):
        """`cards`: the flat project view entries ({id, kind, channels,
        modbus_unit_id}) - one physical card may appear once per kind.
        Returns the ids of cards that will be polled."""
        settings = settings or {}
        with self._lock:
            self._bus = dict(bus or {})
            self._poll_interval = max(0.02, float(settings.get("poll_interval_ms", 250)) / 1000.0)
            self._timeout = max(0.05, float(settings.get("timeout_s", 1.0)))
            self._retries = int(settings.get("retries", 1))
            self._ai_signed = bool(settings.get("ai_signed", False))
            self._read_back_outputs = bool(settings.get("read_back_outputs", True))
            by_id, order, skipped = {}, [], []
            for entry in cards:
                card_id = entry.get("id")
                kind = entry.get("kind")
                # A card with no channel kind (an EPM meter) is still on
                # the bus for its register blocks (device_blocks.py).
                if not card_id or (kind is not None and kind not in ("DI", "DO", "AI", "AO")):
                    continue
                unit = entry.get("modbus_unit_id")
                if unit is None:
                    if card_id not in skipped:
                        skipped.append(card_id)
                    continue
                if card_id not in by_id:
                    by_id[card_id] = {"id": card_id, "unit": int(unit), "kinds": {}, "model": entry.get("model") or ""}
                    order.append(card_id)
                if kind is not None:
                    by_id[card_id]["kinds"][kind] = int(entry.get("channels") or 0)
            self._cards = [by_id[i] for i in order]
            self._skipped = skipped
            self._client = None
            self.unavailable_reason = None
            try:
                self._client = ModbusClient(make_transport(self._bus, timeout=self._timeout), retries=self._retries)
            except TransportUnavailable as e:
                self.unavailable_reason = str(e)
                log.error(f"ModbusDriver: bus cannot be opened on this controller - {e}")
        for card_id in skipped:
            log.warning(f"ModbusDriver: card {card_id} has no Modbus unit id - not polled.")
        return [c["id"] for c in self._cards]

    def polled_card_ids(self) -> list:
        with self._lock:
            return [c["id"] for c in self._cards]

    def skipped_card_ids(self) -> list:
        with self._lock:
            return list(self._skipped)

    # -- lifecycle --------------------------------------------------------------------

    def start(self):
        super().start()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ModbusDriver")
        self._thread.start()
        log.info(f"ModbusDriver started ({self._bus.get('transport', 'RTU')} bus, "
                 f"{len(self._cards)} card(s) polled).")

    def stop(self):
        super().stop()
        if self._thread:
            self._thread.join(timeout=max(2.0, self._timeout * 3))
        with self._lock:
            if self._client is not None:
                self._client.close()
        log.info("ModbusDriver stopped.")

    def is_alive(self) -> bool:
        return self.is_running and self._thread is not None and self._thread.is_alive()

    # -- polling -----------------------------------------------------------------------

    def _run_loop(self):
        while self.is_running:
            cycle_start = time.time()
            with self._lock:
                cards = [dict(c, kinds=dict(c["kinds"])) for c in self._cards]
                client = self._client
            if client is not None:
                for card in cards:
                    if not self.is_running:
                        break
                    self.poll_card(card, client)
            elapsed_ms = (time.time() - cycle_start) * 1000.0
            self.event_bus.emit("driver_scan_cycle", self.name, elapsed_ms)
            remaining = self._poll_interval - (time.time() - cycle_start)
            if remaining > 0:
                time.sleep(remaining)

    def poll_card(self, card: dict, client=None) -> bool:
        """One poll of one card - every kind it has, in one go. Emits
        the tag updates and the comm heartbeat; on any failure counts the
        error and withholds the heartbeat. Returns success."""
        client = client or self._client
        card_id, unit = card["id"], card["unit"]
        from epw_os.core.addressing import format_address
        updates = []
        self._comm_diagnostics.record_frame_sent(card_id)
        t0 = time.perf_counter()
        try:
            for kind, count in card["kinds"].items():
                if count <= 0:
                    continue
                if kind == "DI":
                    values = client.read_bits(unit, FC_READ_DISCRETE_INPUTS, 0, count)
                elif kind == "DO":
                    if not self._read_back_outputs:
                        continue
                    values = client.read_bits(unit, FC_READ_COILS, 0, count)
                elif kind == "AI":
                    values = client.read_registers(unit, FC_READ_INPUT_REGISTERS, 0, count, self._ai_signed)
                else:
                    continue  # AO: write-only
                updates.extend((format_address(card_id, kind, n + 1), value) for n, value in enumerate(values))
            blocks = self._read_blocks(card, client)
        except ModbusError as e:
            # No heartbeat this cycle: DeviceManager's watchdog flips the
            # card to COMM_FAILURE by itself (the same path a stalled
            # simulator takes); the tags keep their last value.
            self._comm_diagnostics.record_error(card_id, e.kind, str(e))
            log.debug(f"ModbusDriver: card {card_id} (unit {unit}) - {e}")
            return False
        self._comm_diagnostics.record_success(card_id, (time.perf_counter() - t0) * 1000.0)
        for tag_name, value in updates:
            self.event_bus.emit("driver_update", tag_name, value, "GOOD")
        for block, values in blocks:
            self.event_bus.emit("device_block_read", card_id, block, values)
        self.event_bus.emit("driver_comm_ok", card_id)
        return True

    def _read_blocks(self, card: dict, client) -> list:
        """The register blocks the card's model carries (device_blocks.py):
        PROT on an ADA, POWER on an EPM, DIAG on every card. A Modbus
        exception (illegal address - a firmware without the block) marks
        the block unsupported for a while and is not a comm error; a
        timeout or CRC error is, and propagates like a channel read's."""
        from epw_os.drivers import device_blocks as B
        out = []
        now = time.monotonic()
        for block in B.blocks_for_model(card.get("model", "")):
            until = self._unsupported_blocks.get((card["id"], block), 0.0)
            if until > now:
                continue
            start, count = B.BLOCK_RANGES[block]
            try:
                values = client.read_registers(card["unit"], B.FC_READ_INPUT_REGISTERS, start, count)
            except ModbusError as e:
                if e.kind == ERROR_INVALID_RESPONSE and "exception" in str(e):
                    self._unsupported_blocks[(card["id"], block)] = now + UNSUPPORTED_BLOCK_RETRY_S
                    log.info(f"ModbusDriver: card {card['id']} has no {block} block ({e}) - not asked again for "
                             f"{UNSUPPORTED_BLOCK_RETRY_S:.0f} s.")
                    continue
                raise
            out.append((block, values))
        return out

    def write_device_register(self, card_id: str, address: int, value: int) -> bool:
        """One holding register of a card - the command registers of the
        maps (PROT_CMD, DIAG_CMD, ...). False, logged, when the card is
        not on this bus or the write fails."""
        card = self._card_for(card_id)
        with self._lock:
            client = self._client
        if card is None or client is None:
            log.error(f"ModbusDriver: {card_id} is not on the bus - register {address} not written.")
            return False
        try:
            client.write_register(card["unit"], int(address), int(value) & 0xFFFF)
        except (ModbusError, TypeError, ValueError) as e:
            self._comm_diagnostics.record_error(card_id, getattr(e, "kind", ERROR_INVALID_RESPONSE), str(e))
            log.error(f"ModbusDriver: write {card_id} register {address} = {value} failed - {e}")
            return False
        return True

    def reconnect(self) -> bool:
        """Closes and reopens the transport (REQ.DEV.<id>.RECONNECT)."""
        with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:  # noqa: BLE001 - a transport that will not close is replaced anyway
                    pass
            try:
                self._client = ModbusClient(make_transport(self._bus, timeout=self._timeout), retries=self._retries)
                self.unavailable_reason = None
            except TransportUnavailable as e:
                self._client = None
                self.unavailable_reason = str(e)
                log.error(f"ModbusDriver: reconnect failed - {e}")
                return False
        return True

    # -- commands ------------------------------------------------------------------------

    def _card_for(self, card_id: str):
        with self._lock:
            for card in self._cards:
                if card["id"] == card_id:
                    return card
        return None

    def write_tag(self, tag_name: str, value) -> bool:
        from epw_os.core.addressing import try_parse_address
        parsed = try_parse_address(tag_name)
        if parsed is None:
            log.error(f"ModbusDriver: {tag_name!r} is not a channel address - nothing written.")
            return False
        card_id, kind, channel = parsed
        card = self._card_for(card_id)
        with self._lock:
            client = self._client
        if card is None or client is None:
            log.error(f"ModbusDriver: {tag_name} - card {card_id} is not on the bus - nothing written.")
            return False
        try:
            if kind == "DO":
                client.write_coil(card["unit"], channel - 1, bool(value))
                written = bool(value)
            elif kind == "AO":
                written = int(round(float(value)))
                client.write_register(card["unit"], channel - 1, written)
            else:
                log.error(f"ModbusDriver: {tag_name} is an input - it cannot be written.")
                return False
        except (ModbusError, TypeError, ValueError) as e:
            kind_name = getattr(e, "kind", ERROR_INVALID_RESPONSE)
            self._comm_diagnostics.record_error(card_id, kind_name, str(e))
            log.error(f"ModbusDriver: write {tag_name} = {value!r} failed - {e}")
            return False
        # The output tag reflects the command at once (SimulatorDriver
        # does the same); the next poll's FC1 read-back confirms it.
        self.event_bus.emit("driver_update", tag_name, written, "GOOD")
        return True

    # -- neutral diagnostics interface --------------------------------------------------

    def get_comm_stats(self):
        return self._comm_diagnostics.get_all_stats()

    def reset_comm_stats(self, device_id: str = None):
        self._comm_diagnostics.reset(device_id)
