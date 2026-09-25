#!/usr/bin/env python3
"""An independent oracle for crc_itu_ref.c's reference lines.

Six builds agreeing is consistency, not correctness: six compilations of a
wrong CRC agree perfectly. This computes CRC-16/X-25 through a different code
path from anything in crc_itu_ref.c — CPython's C crc_hqx (MSB-first CCITT,
poly 0x1021), reflected by hand — and refuses to judge a run until that path
has reproduced published values. See docs/experiments/0001, step 4.

    python3 crc_oracle.py             print the expected reference lines
    python3 crc_oracle.py run.out     check a run's output against them
    make -C bench/rv32 check          build, run, then this

Exit status is 0 only if every reference line is present and matches.
"""

import binascii
import re
import sys


def reflect(value, width):
    return int(f"{value:0{width}b}"[::-1], 2)


def crc16_x25(data):
    """CRC-16/X-25: poly 0x1021, init 0xFFFF, reflected in and out, xorout 0xFFFF."""
    crc = binascii.crc_hqx(bytes(reflect(b, 8) for b in data), 0xFFFF)
    return reflect(crc, 16) ^ 0xFFFF


# The oracle is checked before it checks anything.
ANCHORS = [
    # [V] RevEng CRC catalogue, CRC-16/IBM-SDLC (alias X-25): check=0x906e.
    #     https://reveng.sourceforge.io/crc-catalogue/16.htm
    (b"123456789", 0x906E, "RevEng catalogue check value"),
    # [V] GT06 GPS Tracker Communication Protocol v1.8.1 (Concox), §5.1.3, PDF
    #     page 12 (printed 11); SHA-256 adbb99f6…33e8, see reference/README.md.
    #     The login example, CRC over length byte .. serial number:
    #       78 78 0D 01 01 23 45 67 89 01 23 45 00 01 8C DD 0D 0A
    #     (The document's hex string has a typo, "78 780 0D"; the byte-by-byte
    #     row beneath it gives 78 78 0D.) This also checks the claim that GT06
    #     uses CRC-16/X-25 over exactly that span.
    (bytes.fromhex("0D0101234567890123450001"), 0x8CDD, "GT06 login example"),
    # [V] Same page: the server's response, 78 78 05 01 00 01 D9 DC 0D 0A.
    (bytes.fromhex("05010001"), 0xD9DC, "GT06 login response"),
]

# The workload. This must match crc_itu_ref.c; if it drifts, acc and iters
# stop matching, and the check fails loudly rather than agreeing with a
# different benchmark.
FRAME = bytes([0x0D, 0x01, 0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF, 0x00, 0x01])
ITERS = 1000


def expected():
    ref = crc16_x25(FRAME)
    acc, frame = 0, bytearray(FRAME)
    for i in range(ITERS):
        frame[10], frame[11] = (i >> 8) & 0xFF, i & 0xFF
        acc = ((acc << 1) | (acc >> 31)) & 0xFFFFFFFF
        acc ^= crc16_x25(frame)
    return {"crc_ref": ref, "acc": acc, "iters": ITERS}


LINE = re.compile(r"^(crc_ref|acc|iters)\s*=\s*(?:0x)?([0-9a-fA-F]+)\s*$")


def main(argv):
    for data, want, name in ANCHORS:
        got = crc16_x25(data)
        if got != want:
            print(f"oracle: anchor FAILED — {name}: got 0x{got:04X}, want 0x{want:04X}")
            return 2
    print("oracle: anchors reproduced — " + ", ".join(
        f"{name} 0x{want:04X}" for _, want, name in ANCHORS))

    want = expected()
    if len(argv) < 2:
        for key, value in want.items():
            print(f"{key:<8} = 0x{value:x}")
        return 0

    with open(argv[1]) as f:
        got = {m[1]: int(m[2], 16) for m in map(LINE.match, f) if m}

    ok = True
    for key, value in want.items():
        if key not in got:
            print(f"{key:<8} MISSING      expected 0x{value:x}")
            ok = False
        elif got[key] != value:
            print(f"{key:<8} 0x{got[key]:<10x} expected 0x{value:x}   MISMATCH")
            ok = False
        else:
            print(f"{key:<8} 0x{got[key]:<10x} ok")
    print("oracle: PASS" if ok else "oracle: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
