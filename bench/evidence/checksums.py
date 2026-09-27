#!/usr/bin/env python3
"""Who checks the checksums? Evidence for bench/PROTOCOL-EVIDENCE.md, Findings 4 to 6.

    python3 bench/evidence/checksums.py
    scripts/capture.sh protocol-checksums python3 bench/evidence/checksums.py

Three questions, each answered from a pinned source:

  1. Do the GT06 vendor document's own example frames pass the document's own check?
     The frames are transcribed below from the pinned PDF, with page numbers.
  2. Does Traccar verify the checksum of a frame it receives? Read from its source.
  3. Do the frames in Traccar's own test suite pass their checksum and length checks?

The inputs are gitignored. Refetch them with reference/README.md. Each file's SHA-256 is printed,
so a capture records exactly what was read. Traccar's test frames come from real devices and forum
posts, so none of their bytes are printed or committed here (bench/README rule 2a), only counts.
They are test inputs, not a sample of traffic. **Nothing here measures how often anything happens.**

The CRC is crc_oracle.py's CRC-16/X-25, which reproduces published values before it is used.
"""

import hashlib
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REF = os.path.join(ROOT, "reference")
sys.path.insert(0, os.path.join(ROOT, "bench", "rv32"))

from crc_oracle import ANCHORS, crc16_x25  # noqa: E402

PDF = "GT06_GPS_Tracker_Communication_Protocol_v1.8.1.pdf"
PDF_SHA256 = "adbb99f64b3b84c2296b274d59c96f85cd316a1cfd1434ab0a2870ab72b633e8"  # reference/README.md

# ---------------------------------------------------------------------------
# 1. The vendor document's examples, transcribed from GT06 v1.8.1 (Concox).
#    "p." is the PDF page; the printed page number is one lower.
# ---------------------------------------------------------------------------

VENDOR = [
    # (name, where, hex as printed, device-sent?)
    ("login", "§5.1.3, p.12", "78780D01012345678901234500018CDD0D0A", True),
    ("login response", "§5.1.3, p.12", "787805010001D9DC0D0A", False),
    ("location 0x12", "§5.2.2, p.16",
     "78781F120B081D112E10CC027AC7EB0C46584900148F01CC00287D001FB8000380810D0A", True),
    ("heartbeat 0x13", "§5.4.3, p.26", "787808134B040300010011061F0D0A", True),
    ("heartbeat response", "§5.4.3, p.26", "787805130011F9700D0A", False),
]

# What the document's own field tables say, where they differ from its example strings.
TABLE_LOCATION_GPS_BYTE = 0xCF  # §5.2.1, p.13: "Quantity of GPS information satellites … 0xCF"
HEARTBEAT_ALARM_LANGUAGE = bytes([0x00, 0x01])  # §5.4.1.7, p.25; the example labels it "Reserved bit (Language)"


def gt06_parts(frame):
    """Split a 0x7878 frame into (length field, bytes the length should count, crc span, crc field)."""
    assert frame[:2] == b"\x78\x78" and frame[-2:] == b"\r\n", "not a 0x7878 … 0x0D0A frame"
    counted = frame[3:-2]  # protocol number .. error check: §4.2, p.9, "(5+N) Bytes"
    span = frame[2:-4]  # packet length .. serial number: §4.6, p.10
    return frame[2], len(counted), span, int.from_bytes(frame[-4:-2], "big")


def single_byte_repairs(frame):
    """Every one-byte change inside the CRC span that makes the printed CRC verify."""
    _, _, span, want = gt06_parts(frame)
    work, hits = bytearray(span), []
    for i, orig in enumerate(span):
        for v in range(256):
            if v != orig:
                work[i] = v
                if crc16_x25(bytes(work)) == want:
                    hits.append((i + 2, orig, v))  # +2: offset in the frame, not the span
        work[i] = orig
    return hits


def vendor_examples():
    print("## 1. The GT06 vendor document's example frames\n")
    print(f"{'example':20} {'where':14} {'length field':>13} {'bytes counted':>14} "
          f"{'CRC printed':>12} {'CRC computed':>13}  verdict")
    for name, where, hexstr, _ in VENDOR:
        length, counted, span, want = gt06_parts(bytes.fromhex(hexstr))
        got = crc16_x25(span)
        verdict = "verifies" if (got == want and length == counted) else "FAILS: " + ", ".join(
            [x for x, bad in (("CRC", got != want), ("length", length != counted)) if bad])
        print(f"{name:20} {where:14} {length:>13} {counted:>14} {f'0x{want:04x}':>12} {f'0x{got:04x}':>13}"
              f"  {verdict}")
    sent = [v for v in VENDOR if v[3]]
    ok = sum(1 for _, _, h, _ in sent if (lambda p: crc16_x25(p[2]) == p[3] and p[0] == p[1])(
        gt06_parts(bytes.fromhex(h))))
    print(f"\nDevice-sent examples that verify as printed: {ok} of {len(sent)}.")

    loc = bytes.fromhex(VENDOR[2][2])
    print("\nlocation 0x12: every single-byte repair that makes its printed CRC verify:")
    for off, orig, new in single_byte_repairs(loc):
        print(f"  frame offset {off}: {orig:#04x} -> {new:#04x}")
    fixed = bytearray(loc)
    fixed[10] = TABLE_LOCATION_GPS_BYTE
    _, _, span, want = gt06_parts(bytes(fixed))
    print(f"  the field table on p.13 gives offset 10 as {TABLE_LOCATION_GPS_BYTE:#04x}. "
          f"With it, the CRC is {crc16_x25(span):#06x} (printed {want:#06x}).")

    hb = bytes.fromhex(VENDOR[3][2])
    repairs = single_byte_repairs(hb)
    print(f"\nheartbeat 0x13: single-byte repairs that make its printed CRC verify: {len(repairs)}")
    i = hb.index(HEARTBEAT_ALARM_LANGUAGE, 7)  # after terminal info, voltage, GSM signal
    without = hb[:i] + hb[i + 2:]
    length, counted, span, want = gt06_parts(without)
    print(f"  without its two Alarm/Language bytes ({without.hex(' ')}):")
    print(f"  length field {length}, bytes counted {counted}; CRC printed {want:#06x}, "
          f"computed {crc16_x25(span):#06x}")


# ---------------------------------------------------------------------------
# 2. Where Traccar's decoders compute a checksum at all.
# ---------------------------------------------------------------------------

# A method declaration in these files: indented exactly four spaces, a name followed by "(", and no
# "=" before it (a field initialiser is not a method). Package-private methods have no modifier.
METHOD = re.compile(r"^    (?=\S)(?!return\b)[\w<>\[\],.? ]*?\b(\w+)\s*\([^=]*$")


def checksum_sites(path):
    """Each use of Traccar's Checksum helper, with the method it sits in."""
    method, sites = "?", []
    with open(path) as f:
        for n, line in enumerate(f, 1):
            m = METHOD.match(line)
            if m and "=" not in line.split("(")[0]:
                method = m.group(1)
            if "Checksum." in line and "import" not in line:
                sites.append((n, method, line.strip()))
    return sites


def traccar_sources():
    print("\n## 2. Where Traccar's decoders compute a checksum\n")
    for name in ("Gt06ProtocolDecoder.java", "Jt808ProtocolDecoder.java", "Gt06FrameDecoder.java",
                 "Jt808FrameDecoder.java"):
        sites = checksum_sites(os.path.join(REF, name))
        print(f"{name}: {len(sites)} use(s) of Checksum")
        for n, method, text in sites:
            print(f"  :{n:<5} in {method}()   {text}")


# ---------------------------------------------------------------------------
# 3. Traccar's own test frames, counted. No bytes are printed.
# ---------------------------------------------------------------------------

FRAME = re.compile(r'binary\(\s*"([0-9a-fA-F]+)"')


def test_frames(name):
    with open(os.path.join(REF, name)) as f:
        return [bytes.fromhex(h) for h in FRAME.findall(f.read())]


def gt06_corpus():
    frames = test_frames("Gt06ProtocolDecoderTest.java")
    c, bad_types, per_type = Counter(), Counter(), Counter()
    for b in frames:
        if len(b) < 10 or b[-2:] != b"\r\n" or b[:2] not in (b"\x78\x78", b"\x79\x79"):
            c["not a 0x7878/0x7979 … 0x0D0A frame"] += 1
            continue
        long_form = b[:2] == b"\x79\x79"  # Gt06FrameDecoder.java:40-44
        length = int.from_bytes(b[2:4], "big") if long_form else b[2]
        typ = b[4] if long_form else b[3]
        c["frames"] += 1
        c["length field disagrees with the bytes present"] += (len(b) != (4 if long_form else 3) + length + 2)
        crc_ok = crc16_x25(b[2:-4]) == int.from_bytes(b[-4:-2], "big")
        c["CRC-ITU verifies" if crc_ok else "CRC-ITU fails"] += 1
        per_type[(typ, crc_ok)] += 1
        if not crc_ok:
            bad_types[typ] += 1
    print("\n## 3. Traccar's own test frames (inputs to its unit tests, not traffic)\n")
    print(f"Gt06ProtocolDecoderTest.java: {len(frames)} binary test inputs")
    for k in ("frames", "CRC-ITU verifies", "CRC-ITU fails", "length field disagrees with the bytes present",
              "not a 0x7878/0x7979 … 0x0D0A frame"):
        print(f"  {k:48} {c[k]}")
    print("  CRC-ITU fails, by protocol number: " + ", ".join(
        f"{t:#04x}×{n}" for t, n in sorted(bad_types.items())))
    print("  SPEC §2 types (verifies / fails): " + ", ".join(
        f"{t:#04x} {per_type[(t, True)]}/{per_type[(t, False)]}" for t in (0x01, 0x12, 0x13)))


def jt808_destuff(inner, alternative):
    """Jt808FrameDecoder.java:65-88: unescape the bytes between the delimiters."""
    out, i = bytearray(), 0
    while i < len(inner):
        b = inner[i]
        if (alternative and b in (0xE6, 0x3E)) or (not alternative and b == 0x7D):
            ext = inner[i + 1] if i + 1 < len(inner) else None
            table = {(0xE6, 1): 0xE6, (0xE6, 2): 0xE7, (0x3E, 1): 0x3E, (0x3E, 2): 0x3D,
                     (0x7D, 1): 0x7D, (0x7D, 2): 0x7E}
            if (b, ext) in table:
                out.append(table[(b, ext)])  # any other pair is dropped, as the decoder does
            i += 2
        else:
            out.append(b)
            i += 1
    return bytes(out)


def jt808_corpus():
    frames = test_frames("Jt808ProtocolDecoderTest.java")
    c, bad_types, types = Counter(), Counter(), Counter()
    for b in frames:
        if len(b) < 2 or b[0] not in (0x7E, 0xE7) or b[-1] != b[0]:
            c["not delimiter-framed (7e/e7)"] += 1
            continue
        c["frames"] += 1
        c[f"delimiter {b[0]:#04x}"] += 1
        c["an unescaped delimiter between the delimiters"] += (b[0] in b[1:-1])
        d = jt808_destuff(b[1:-1], b[0] == 0xE7)
        typ, attr = int.from_bytes(d[0:2], "big"), int.from_bytes(d[2:4], "big")
        types[typ] += 1
        v2019 = bool(attr & 0x4000)
        c["attribute bit 14 set"] += v2019
        # Header length, Jt808ProtocolDecoder.java:359-373 (bench/PROTOCOL-EVIDENCE.md Finding 2)
        header = 2 + 2 + v2019 + (10 if v2019 else (7 if b[0] == 0xE7 else 6)) + (
            1 if typ in (0x5501, 0x5502) else 2)
        c["body-length field disagrees with the bytes present"] += (len(d) - header - 1 != attr & 0x3FF)
        x = 0
        for v in d[:-1]:
            x ^= v
        # The check code: XOR of every byte after the start delimiter up to it (formatMessage, :146)
        c["XOR check verifies" if x == d[-1] else "XOR check fails"] += 1
        if x != d[-1]:
            bad_types[typ] += 1
    print(f"\nJt808ProtocolDecoderTest.java: {len(frames)} binary test inputs")
    for k in ("frames", "delimiter 0x7e", "delimiter 0xe7", "attribute bit 14 set", "XOR check verifies",
              "XOR check fails", "body-length field disagrees with the bytes present",
              "an unescaped delimiter between the delimiters", "not delimiter-framed (7e/e7)"):
        print(f"  {k:52} {c[k]}")
    print("  XOR check fails, by message type: " + ", ".join(
        f"{t:#06x}×{n}" for t, n in sorted(bad_types.items())))
    print("  SPEC §2 types present: " + ", ".join(
        f"{t:#06x}×{types[t]}" for t in (0x0102, 0x0200, 0x0704, 0x5501)))


def main():
    for data, want, name in ANCHORS:
        if crc16_x25(data) != want:
            print(f"CRC anchor FAILED: {name}")
            return 2
    print("CRC-16/X-25 from bench/rv32/crc_oracle.py; its anchors reproduced: "
          + ", ".join(name for _, _, name in ANCHORS) + "\n")

    inputs = [PDF, "Gt06FrameDecoder.java", "Gt06ProtocolDecoder.java", "Jt808FrameDecoder.java",
              "Jt808ProtocolDecoder.java", "Gt06ProtocolDecoderTest.java", "Jt808ProtocolDecoderTest.java"]
    print("Inputs (reference/, gitignored; Traccar at 847edd2c8c4dcc47426fb76b7800b342dea3cde6):")
    for name in inputs:
        path = os.path.join(REF, name)
        if not os.path.exists(path):
            print(f"  MISSING {name}: see reference/README.md to refetch")
            return 2
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        print(f"  {digest}  {name}")
        if name == PDF and digest != PDF_SHA256:
            print("  the PDF is not the pinned copy; the transcribed examples may not match it")
            return 2
    print("  (The vendor examples in section 1 are transcribed in this file, not read from the PDF.)\n")

    vendor_examples()
    traccar_sources()
    gt06_corpus()
    jt808_corpus()
    return 0


if __name__ == "__main__":
    sys.exit(main())
