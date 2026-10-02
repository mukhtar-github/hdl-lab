"""stimulus.bin: the chunks, in delivery order, in a form the decoder can read straight from memory.

Integers are little-endian, RV32's byte order, and every header starts on a 4-byte boundary, so
the decoder reads one with a single `lw`. The harness then costs one load per chunk, which keeps
it out of what the benchmark measures as far as it can be kept out.

    header   "TFDS" | u16 format version (2) | u16 header bytes (20)
             | u32 chunks | u32 connections | u32 payload bytes (chunk data, no padding)
    table    u8 protocol per connection: 1 GT06, 2 JT808 | zeros to a multiple of 4
    chunk    u16 length | u16 connection | `length` bytes | zeros to a multiple of 4

The table stands in for the port that each connection arrived on, so the decoder knows a
connection's protocol before its first byte (decisions/0011, decisions/0014). Version 1 had no
table, and is refused.
"""

import struct

MAGIC, VERSION = b"TFDS", 2
HEADER = struct.Struct("<4sHHIII")
CHUNK = struct.Struct("<HH")
PROTOCOLS = {"gt06": 1, "jt808": 2}  # 0 is not a protocol, so a table of zeros fails
NAMES = {code: name for name, code in PROTOCOLS.items()}


def pack(chunks, protocols):
    """chunks: [(connection, bytes)] in delivery order. protocols: each connection's, in order."""
    for conn, p in enumerate(protocols):
        if p not in PROTOCOLS:
            raise ValueError(f"connection {conn} has no protocol code: {p!r}")
    payload = sum(len(d) for _, d in chunks)
    out = bytearray(HEADER.pack(MAGIC, VERSION, HEADER.size, len(chunks), len(protocols), payload))
    out += bytes(PROTOCOLS[p] for p in protocols) + bytes(-len(protocols) % 4)
    for conn, data in chunks:
        if not 1 <= len(data) <= 0xFFFF or not 0 <= conn < len(protocols):
            raise ValueError(f"chunk of {len(data)} bytes for connection {conn} does not fit")
        out += CHUNK.pack(len(data), conn) + data + bytes(-len(data) % 4)
    return bytes(out)


def unpack(blob):
    """([protocol], [(connection, bytes)]), refusing anything pack() would not have written."""
    magic, version, size, count, connections, payload = HEADER.unpack_from(blob, 0)
    if (magic, version, size) != (MAGIC, VERSION, HEADER.size):
        raise ValueError(f"not a version-{VERSION} stimulus: {magic!r}, {version}, {size}")
    end = size + connections + -connections % 4
    if end > len(blob):
        raise ValueError("the protocol table runs past the end of the file")
    protocols = []
    for code in blob[size:size + connections]:
        if code not in NAMES:
            raise ValueError(f"protocol code {code} for connection {len(protocols)}")
        protocols.append(NAMES[code])
    if blob[size + connections:end] != bytes(end - size - connections):
        raise ValueError("non-zero padding after the protocol table")
    chunks, i = [], end
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
    return protocols, chunks
