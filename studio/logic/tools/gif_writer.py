"""A minimal animated GIF (GIF89a) writer in plain Python - no Pillow, no
new dependency (GRANICE), just the LZW the format asks for.

Used by render_help_animations.py to turn frames rendered from the
editor's own canvas into the short animations the help shows next to a
block. Each frame is given as (width, height, palette, indices):
`palette` is a list of up to 256 (r, g, b) tuples shared by every frame
(a global colour table), `indices` a bytes object of width*height
palette indices, row-major.
"""
import struct


def _lzw_encode(indices: bytes, min_code_size: int) -> bytes:
    clear = 1 << min_code_size
    end = clear + 1
    code_size = min_code_size + 1
    next_code = end + 1
    table = {bytes([i]): i for i in range(clear)}
    out = bytearray()
    bit_buffer = 0
    bit_count = 0

    def emit(code):
        nonlocal bit_buffer, bit_count
        bit_buffer |= code << bit_count
        bit_count += code_size
        while bit_count >= 8:
            out.append(bit_buffer & 0xFF)
            bit_buffer >>= 8
            bit_count -= 8

    emit(clear)
    current = b""
    for byte in indices:
        candidate = current + bytes([byte])
        if candidate in table:
            current = candidate
            continue
        emit(table[current])
        if next_code < 4096:
            table[candidate] = next_code
            next_code += 1
            if next_code > (1 << code_size) and code_size < 12:
                code_size += 1
        else:
            emit(clear)
            table = {bytes([i]): i for i in range(clear)}
            next_code = end + 1
            code_size = min_code_size + 1
        current = bytes([byte])
    if current:
        emit(table[current])
    emit(end)
    if bit_count:
        out.append(bit_buffer & 0xFF)
    return bytes(out)


def _blocks(data: bytes) -> bytes:
    out = bytearray()
    for i in range(0, len(data), 255):
        chunk = data[i:i + 255]
        out.append(len(chunk))
        out.extend(chunk)
    out.append(0)
    return bytes(out)


def write_gif(path: str, width: int, height: int, palette, frames, delays_ms, loop: bool = True) -> None:
    """`frames`: a list of bytes (width*height indices into `palette`);
    `delays_ms`: one delay per frame."""
    if not frames:
        raise ValueError("no frames")
    if len(frames) != len(delays_ms):
        raise ValueError("one delay per frame")
    size = max(len(palette), 2)
    bits = max(1, (size - 1).bit_length())
    table_size = 1 << bits
    min_code_size = max(2, bits)
    out = bytearray(b"GIF89a")
    out.extend(struct.pack("<HHBBB", width, height, 0x80 | (bits - 1) << 4 | (bits - 1), 0, 0))
    for i in range(table_size):
        r, g, b = palette[i] if i < len(palette) else (0, 0, 0)
        out.extend(bytes((r, g, b)))
    if loop:
        out.extend(b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")
    for indices, delay in zip(frames, delays_ms):
        if len(indices) != width * height:
            raise ValueError("frame size mismatch")
        out.extend(struct.pack("<BBBBHBB", 0x21, 0xF9, 4, 0x00, max(1, int(delay) // 10), 0, 0))
        out.extend(struct.pack("<BHHHHB", 0x2C, 0, 0, width, height, 0))
        out.append(min_code_size)
        out.extend(_blocks(_lzw_encode(bytes(indices), min_code_size)))
    out.append(0x3B)
    with open(path, "wb") as f:
        f.write(out)
