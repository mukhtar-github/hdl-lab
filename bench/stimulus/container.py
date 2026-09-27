"""stimulus.bin: the chunks, in delivery order, in a form the decoder can read straight from memory.

Integers are little-endian, RV32's byte order, and every header starts on a 4-byte boundary, so
the decoder reads one with a single `lw`. The harness then costs one load per chunk, which keeps
it out of what the benchmark measures as far as it can be kept out.

    header   "TFDS" | u16 format version | u16 header bytes (20)
             | u32 chunks | u32 connections | u32 payload bytes (chunk data, no padding)
    chunk    u16 length | u16 connection | `length` bytes | zeros to a multiple of 4
"""

import struct

MAGIC, VERSION = b"TFDS", 1
HEADER = struct.Struct("<4sHHIII")
CHUNK = struct.Struct("<HH")


def pack(chunks, connections):
    """chunks: [(connection, bytes)] in delivery order."""
    payload = sum(len(d) for _, d in chunks)
    out = bytearray(HEADER.pack(MAGIC, VERSION, HEADER.size, len(chunks), connections, payload))
    for conn, data in chunks:
        if not 1 <= len(data) <= 0xFFFF or not 0 <= conn < connections:
            raise ValueError(f"chunk of {len(data)} bytes for connection {conn} does not fit")
        out += CHUNK.pack(len(data), conn) + data + bytes(-len(data) % 4)
    return bytes(out)


def unpack(blob):
    """(connections, [(connection, bytes)]), refusing anything pack() would not have written."""
    magic, version, size, count, connections, payload = HEADER.unpack_from(blob, 0)
    if (magic, version, size) != (MAGIC, VERSION, HEADER.size):
        raise ValueError(f"not a version-{VERSION} stimulus: {magic!r}, {version}, {size}")
    chunks, i = [], size
    for _ in range(count):
        length, conn = CHUNK.unpack_from(blob, i)
        i += CHUNK.size
        if not 1 <= length or i + length > len(blob) or conn >= connections:
            raise ValueError(f"bad chunk header at byte {i - CHUNK.size}")
        chunks.append((conn, blob[i:i + length]))
        pad = -length % 4
        if blob[i + length:i + length + pad] != bytes(pad):
            raise ValueError(f"non-zero padding after the chunk at byte {i}")
        i += length + pad
    if i != len(blob) or sum(len(d) for _, d in chunks) != payload:
        raise ValueError("the header's sizes do not match the chunks")
    return connections, chunks
