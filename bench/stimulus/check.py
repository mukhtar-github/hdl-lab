#!/usr/bin/env python3
"""Check a generated stimulus against what its generator says it contains.

    python3 check.py build/coverage-1

Reads stimulus.bin, rebuilds each connection's byte stream from the chunks, and walks intent.jsonl
over it. Every frame is parsed back and compared with the fields, fault and header values it was
declared to have. Every garbage run is checked against its alphabet. Then the rules that are
checkable from the output are checked: each connection's protocol in the stimulus's table, session
frames first, framing per connection, and the output hashes in manifest.json.

Independence, and its limit. This file imports none of the encoders. Frames are parsed in the order
Traccar reads them, and GT06 CRCs are computed by bench/rv32/crc_oracle.py, a different path from
gt06.py's table. But the same person read the same sources for both halves. So agreement shows the
encoder and this reader are consistent, not that either is right. What anchors them to the
sources is test_stimulus.py: the GT06 vendor examples, byte for byte.

Exit status 0 only if every check passes.
"""

import hashlib
import json
import os
import sys

import container

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rv32"))
from crc_oracle import ANCHORS, crc16_x25  # noqa: E402

SYNC = {"gt06": b"\x78\x79\x0d\x0a", "jt808": b"\x28\x29\x7e\xe7"}  # traffic.py rule R16
ITEM_LENGTHS = {0x01: 4, 0x02: 2, 0x25: 4, 0x2B: 4, 0x30: 1, 0x31: 1}  # Jt808ProtocolDecoder:791-831


class Mismatch(Exception):
    pass


def need(ok, what):
    if not ok:
        raise Mismatch(what)


def bcd_digits(b):
    s = b.hex()
    need(s.isdigit(), f"not BCD: {s}")
    return s


# --- GT06 -------------------------------------------------------------------------------------

def gt06_fields(protocol, c):
    """The content, read in Traccar's order (Gt06ProtocolDecoder.java)."""
    if protocol == 0x01:
        need(len(c) == 8, "login content is 8 bytes")
        return {"imei": bcd_digits(c)[1:]}  # :523, hexDump(8).substring(1)
    if protocol == 0x12:
        need(len(c) == 26, "location content is 26 bytes")
        need(c[6] >> 4 == 12, "GPS information length nibble is 12")
        flags = int.from_bytes(c[16:18], "big")
        need(flags >> 14 == 0, "course/status bits 15-14 are clear")
        return {"time": "".join(f"{v:02d}" for v in c[0:6]),  # decodeGps, :305-307
                "satellites": c[6] & 0x0F,  # :315
                "lat": int.from_bytes(c[7:11], "big"), "lon": int.from_bytes(c[11:15], "big"),
                "speed": c[15], "course": flags & 0x3FF, "differential": flags >> 13 & 1,
                "positioned": flags >> 12 & 1, "west": flags >> 11 & 1, "north": flags >> 10 & 1,
                "mcc": int.from_bytes(c[18:20], "big"), "mnc": c[20],  # decodeLbs, :374-379
                "lac": int.from_bytes(c[21:23], "big"), "cell": int.from_bytes(c[23:26], "big")}
    if protocol == 0x13:
        need(len(c) == 5, "status content is 5 bytes")
        return dict(zip(("info", "voltage", "gsm", "alarm", "language"), c))
    return {"content": c.hex()}


def check_gt06(b, r):
    fault = r["fault"]
    if fault == "truncated":
        need(len(b) < r["frame_length"], "a truncated frame is shorter than its whole")
        need(b[:2] == b"\x78\x78"[:len(b)], "a truncated frame starts as a frame")
        if len(b) >= 3:
            need(b[2] + 5 == r["frame_length"], "its length field describes the whole frame")
        return
    need(b[:2] == b"\x78\x78" and b[-2:] == b"\r\n", "78 78 … 0D 0A")
    protocol = b[3]
    need(r["type"] == f"0x{protocol:02x}", "protocol number")
    need(int.from_bytes(b[-6:-4], "big") == r["serial"], "serial number")
    crc = int.from_bytes(b[-4:-2], "big") ^ crc16_x25(b[2:-4])
    need(crc == (r["check_error"] if fault == "bad_checksum" else 0), "CRC-ITU")
    if fault == "length_disagreement":
        need(b[2] == r["length_field"] != len(b) - 5, "the length field disagrees, as declared")
    else:
        need(b[2] == len(b) - 5, "the length field counts protocol .. CRC")
    need(gt06_fields(protocol, b[4:-6]) == r["fields"], "fields")


# --- JT808 ------------------------------------------------------------------------------------

def destuff(inner, delimiter):
    """Jt808FrameDecoder.java:65-88, the decoder's own loop."""
    out, i = bytearray(), 0
    while i < len(inner):
        b = inner[i]
        if delimiter == 0xE7 and b in (0xE6, 0x3E) or delimiter == 0x7E and b == 0x7D:
            pair = (b, inner[i + 1])
            need(pair in ((0xE6, 1), (0xE6, 2), (0x3E, 1), (0x3E, 2), (0x7D, 1), (0x7D, 2)),
                 f"escape pair {pair[0]:02x} {pair[1]:02x}")
            out.append({(0xE6, 1): 0xE6, (0xE6, 2): 0xE7, (0x3E, 1): 0x3E, (0x3E, 2): 0x3D,
                        (0x7D, 1): 0x7D, (0x7D, 2): 0x7E}[pair])
            i += 2
        else:
            out.append(b)
            i += 1
    return bytes(out)


def location(b):
    """decodeLocation, :748-786; its status bits from decodeCoordinates, :707-739."""
    need(len(b) >= 28, "a location body has 28 fixed bytes")
    status = int.from_bytes(b[4:8], "big")
    need(status & ~0xF == 0, "status bits above 3 are clear")
    f = {"alarm": int.from_bytes(b[0:4], "big"), "acc": status & 1, "positioned": status >> 1 & 1,
         "south": status >> 2 & 1, "west": status >> 3 & 1,
         "lat": int.from_bytes(b[8:12], "big"), "lon": int.from_bytes(b[12:16], "big"),
         "altitude": int.from_bytes(b[16:18], "big", signed=True),
         "speed": int.from_bytes(b[18:20], "big"), "course": int.from_bytes(b[20:22], "big"),
         "time": bcd_digits(b[22:28])}
    i = 28
    while i < len(b):
        item, n = b[i], b[i + 1]
        need(ITEM_LENGTHS.get(item) == n, f"item {item:02x} has its length")
        f[f"item_{item:02x}"] = int.from_bytes(b[i + 2:i + 2 + n], "big")
        i += 2 + n
    need(i == len(b), "items end with the body")
    return f


def location2(b):
    """Jt600ProtocolDecoder.decodeBinaryLocation, :95-116, then decodeLocation2, :1529-1548."""
    need(len(b) == 35, "a 0x5501 body is 35 bytes")
    date, lon = bcd_digits(b[0:3]), b[10:15].hex()
    need(lon[:9].isdigit(), "9 BCD longitude digits")
    return {"time": date[4:6] + date[2:4] + date[0:2] + bcd_digits(b[3:6]),
            "lat": int(bcd_digits(b[6:10])), "lon": int(lon[:9]),
            "valid": b[14] & 1, "north": b[14] >> 1 & 1, "east": b[14] >> 2 & 1,
            "speed": int(bcd_digits(b[15:16])), "course": b[16], "rssi": b[17],
            "satellites": b[18], "odometer": int.from_bytes(b[19:23], "big"), "battery": b[23],
            "cid": int.from_bytes(b[24:28], "big"), "lac": int.from_bytes(b[28:30], "big"),
            "product": b[30], "status": int.from_bytes(b[31:33], "big"),
            "alarm": int.from_bytes(b[33:35], "big")}


def jt808_fields(msg_type, body):
    if msg_type == 0x0102:
        return {"code": body.decode("ascii")}
    if msg_type == 0x0200:
        return location(body)
    if msg_type == 0x0704:  # decodeLocationBatch, :1634-1655
        records, i = [], 3
        while i < len(body):
            n = int.from_bytes(body[i:i + 2], "big")
            records.append(location(body[i + 2:i + 2 + n]))
            i += 2 + n
        need(i == len(body) and int.from_bytes(body[0:2], "big") == len(records), "batch count")
        return {"archive": body[2], "records": records}
    if msg_type == 0x5501:
        return location2(body)
    return {"body": body.hex()}


def check_jt808(b, r, conn):
    fault = r["fault"]
    delimiter = int(conn["delimiter"], 16)
    need(r["framing"] == conn["delimiter"], "the connection's delimiter")
    need(b[0] == delimiter and delimiter not in b[1:-1], "one delimiter at each end, none inside")
    if fault == "truncated":  # it may be cut down to its opening delimiter alone
        need(len(b) < r["frame_length"] and delimiter not in b[1:], "a truncated frame lacks its end")
        return
    need(b[-1] == delimiter, "closing delimiter")
    # The second byte of an escape pair is 01 or 02, never an introducer, so introducers and
    # pairs correspond one to one.
    introducers = (0xE6, 0x3E) if delimiter == 0xE7 else (0x7D,)
    need(sum(v in introducers for v in b[1:-1]) == r["escapes"], "escape count")
    d = destuff(b[1:-1], delimiter)
    x = 0
    for v in d[:-1]:
        x ^= v
    need(x ^ d[-1] == (r["check_error"] if fault == "bad_checksum" else 0), "XOR check")
    msg_type, attribute = int.from_bytes(d[0:2], "big"), int.from_bytes(d[2:4], "big")
    need(r["type"] == f"0x{msg_type:04x}", "message type")
    v2019 = conn["version"] == 2019
    # Jt808ProtocolDecoder.java:359-373. A lying flag says 2019 over a 2013 header.
    need(bool(attribute & 0x4000) == (v2019 or fault == "flag_lying"), "attribute bit 14")
    need(attribute & 0xBC00 == 0, "attribute bits 10-13 and 15 are clear")
    i = 4
    if v2019:
        need(d[4] == 1, "version byte 1 (rule R8)")
        i += 1
    n = 10 if v2019 else (7 if delimiter == 0xE7 else 6)
    need(bcd_digits(d[i:i + n]) == conn["device"].rjust(2 * n, "0"), "terminal ID")
    i += n
    width = 1 if msg_type in (0x5501, 0x5502) else 2
    need(int.from_bytes(d[i:i + width], "big") == r["index"], "message index")
    body = d[i + width:-1]
    if fault == "length_disagreement":
        need(attribute & 0x3FF == r["length_field"] != len(body), "body length disagrees, as declared")
    else:
        need(attribute & 0x3FF == len(body), "body length")
    need(jt808_fields(msg_type, body) == r["fields"], "fields")


def check_sentence(b, r):
    text = ("(" + r["fields"]["text"] + ")").encode("ascii")
    if r["fault"] == "truncated":
        need(len(b) < len(text) == r["frame_length"] and text.startswith(b), "a truncated sentence")
        need(b")" not in b, "no closing parenthesis")
    else:
        need(b == text and b")" not in b[:-1], "( text )")


# --- The whole run ----------------------------------------------------------------------------

def check_device(r):
    """No identifier in a stimulus may be a real one (bench/README rule 2a). A GT06 IMEI must fail
    its Luhn check digit, computed as Traccar's helper/Checksum.java:214-232 does. A JT808
    terminal number must be 12 digits beginning 00000."""
    device = r["device"]
    if r["protocol"] == "gt06":
        need(len(device) == 15 and device.isdigit(), "a 15-digit IMEI")
        total = 0
        for i, ch in enumerate(reversed(device[:14])):
            d = int(ch) * (1 if i % 2 else 2)
            total += d - 9 if d > 9 else d
        need((10 - total % 10) % 10 != int(device[14]), "the IMEI fails its Luhn check, so is not real")
    else:
        need(len(device) == 12 and device.startswith("00000") and device.isdigit(),
             "a terminal number of 12 digits beginning 00000")


def check(out):
    for data, want, name in ANCHORS:
        need(crc16_x25(data) == want, f"CRC oracle anchor {name}")
    with open(os.path.join(out, "stimulus.bin"), "rb") as f:
        blob = f.read()
    with open(os.path.join(out, "intent.jsonl"), "rb") as f:
        intent = f.read()
    with open(os.path.join(out, "manifest.json")) as f:
        manifest = json.load(f)
    for name, data in (("stimulus.bin", blob), ("intent.jsonl", intent)):
        need(hashlib.sha256(data).hexdigest() == manifest["outputs"][name]["sha256"],
             f"{name} matches the manifest's hash")

    protocols, chunks = container.unpack(blob)
    connections = len(protocols)
    streams = [bytearray() for _ in range(connections)]
    sizes = [[] for _ in range(connections)]
    for conn, data in chunks:
        streams[conn] += data
        sizes[conn].append(len(data))
    lo, hi = manifest["params"]["chunk_size"]
    for s in sizes:  # a connection's last chunk is the remainder, and may be short
        need(all(lo <= n <= hi for n in s[:-1]) and (not s or 1 <= s[-1] <= hi), "chunk sizes")

    lines = [json.loads(line) for line in intent.decode().splitlines()]
    frames, seen, conn, offset, first = 0, set(), None, 0, False
    for n, r in enumerate(lines, 1):
        try:
            if r["kind"] == "connection":
                need(conn is None or offset == len(streams[conn["conn"]]),
                     "the previous connection's segments cover its stream")
                conn, offset, first = r, 0, True
                need(r["conn"] not in seen, "each connection once")
                seen.add(r["conn"])
                need(protocols[r["conn"]] == r["protocol"], "the protocol in the stimulus's table")
                check_device(r)
                continue
            need(r["conn"] == conn["conn"] and r["offset"] == offset, "segments are contiguous")
            b = bytes(streams[conn["conn"]][offset:offset + r["length"]])
            need(len(b) == r["length"], "the segment is inside the stream")
            offset += r["length"]
            if r["kind"] == "garbage":
                need(not first, "no garbage before a connection's first frame (rule R16)")
                if r["alphabet"] == "no_sync":
                    need(not set(b) & set(SYNC[conn["protocol"]]), "no_sync garbage")
                continue
            frames += 1
            if first:
                need(r["fault"] is None and r["type"] in ("0x01", "0x0102"), "session frame first (R2)")
                need(r["type"] != "0x01" or r["fields"]["imei"] == conn["device"], "the login's IMEI")
                first = False
            if conn["protocol"] == "gt06":
                check_gt06(b, r)
            elif r["framing"] == "paren":
                check_sentence(b, r)
            else:
                check_jt808(b, r, conn)
        except (Mismatch, IndexError, KeyError, UnicodeDecodeError, ValueError) as e:
            print(f"intent.jsonl line {n}: {type(e).__name__}: {e}\n  {json.dumps(r)[:300]}")
            return 1
    need(conn is None or offset == len(streams[conn["conn"]]), "the last connection is covered")
    need(seen == set(range(connections)), "every connection in the stimulus is described")
    need(frames == manifest["realized"]["frames"], "frame count")
    print(f"check: PASS. {frames} frames and {len(chunks)} chunks on {connections} connections "
          f"agree with intent.jsonl; the hashes match manifest.json.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.split("\n\n")[1])
        sys.exit(2)
    try:
        sys.exit(check(sys.argv[1]))
    except Mismatch as e:
        print(f"check: FAIL. {e}")
        sys.exit(1)
