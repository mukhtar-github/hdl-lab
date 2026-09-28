#!/usr/bin/env python3
"""After a broken frame, where does Traccar look for the next one? Evidence for
bench/PROTOCOL-EVIDENCE.md, Finding 8.

    python3 bench/evidence/framing.py
    scripts/capture.sh traccar-framing python3 bench/evidence/framing.py

Traccar's two frame decoders are ported below, framing only, line for line from the pinned source.
Three sections:

  1. The port reproduces every vector in Traccar's own framer tests, and three deliberately broken
     ports each fail at least one. So the vectors can tell a wrong port from a right one.
  2. Constructed streams: a broken frame, then whole frames. Which whole frames come out?
  3. The coverage stimulus from bench/stimulus, run through the same port.

The ported decoders see a connection's whole byte stream as one buffer. Netty semantics used:
getByte() and getUnsigned*() do not move the reader index; indexOf(from, to, value) returns an
absolute index, or -1; readRetainedSlice(n) takes a length; a decode() that returns null waits for
more bytes. Netty itself is not pinned here, so these are its documented semantics, not read code.

The inputs are gitignored. Refetch them with reference/README.md, and each file's SHA-256 is
printed. Traccar's test vectors are real-device and forum hex, so none of their bytes is printed
or committed (bench/README rule 2a), only counts. Every frame in sections 2 and 3 is made by
bench/stimulus's encoders from a seed. **Nothing here measures how often anything happens.**
"""

import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REF = os.path.join(ROOT, "reference")
STIMULUS = os.path.join(ROOT, "bench", "stimulus")
sys.path.insert(0, STIMULUS)

import common  # noqa: E402
import gt06  # noqa: E402
import jt808  # noqa: E402
import traffic  # noqa: E402
from prng import SplitMix64  # noqa: E402

SOURCES = ("Gt06FrameDecoder.java", "Jt808FrameDecoder.java", "Gt06FrameDecoderTest.java",
           "Jt808FrameDecoderTest.java")


# ---------------------------------------------------------------------------
# The port. `broken` names a deliberate fault, for section 1 only.
# ---------------------------------------------------------------------------

class Buf:
    """The part of a Netty ByteBuf the two decoders use. `r` is the reader index."""

    def __init__(self, data):
        self.d, self.r = bytes(data), 0

    def readable(self):
        return len(self.d) - self.r

    def index_of(self, start, value):
        return self.d.find(bytes([value]), start)

    def read_slice(self, n):
        if n > self.readable():
            raise IndexError(f"readRetainedSlice({n}) with {self.readable()} bytes readable")
        s = self.d[self.r:self.r + n]
        self.r += n
        return s


def gt06_decode(buf, broken=None):
    """Gt06FrameDecoder.java:31-59."""
    if buf.readable() < 5:                                                    # :34
        return None
    length = 2 + 2                                                            # :38
    if buf.d[buf.r] == 0x78:                                                  # :40
        length += 1 + buf.d[buf.r + 2]
    else:
        length += 2 + int.from_bytes(buf.d[buf.r + 2:buf.r + 4], "big")       # :43
    if buf.readable() >= length and buf.d[buf.r + length - 2:buf.r + length] == b"\r\n":
        return buf.read_slice(length)                                         # :46-47
    if broken == "gt06: no search for 0D 0A":
        return None
    end = buf.r - 1                                                           # :50
    while True:
        end = buf.index_of(end + 1, 0x0D)                                     # :52
        if end > 0 and len(buf.d) > end + 1 and buf.d[end + 1] == 0x0A:       # :53
            return buf.read_slice(end + 2 - buf.r)                            # :54
        if not end > 0:                                                       # :56
            return None


UNESCAPE = {0x7E: {(0x7D, 0x01): 0x7D, (0x7D, 0x02): 0x7E},
            0xE7: {(0xE6, 0x01): 0xE6, (0xE6, 0x02): 0xE7, (0x3E, 0x01): 0x3E, (0x3E, 0x02): 0x3D}}


def jt808_decode(buf, broken=None, sentence_length_fixed=False):
    """Jt808FrameDecoder.java:31-96. `sentence_length_fixed` corrects :53's length; see Finding 8."""
    while buf.readable() and broken != "jt808: no skipping to a frame start":   # :35-41
        if buf.d[buf.r] in (0x28, 0x7E, 0xE7):
            break
        buf.r += 1
    if buf.readable() < 2:                                                    # :43
        return None
    first = buf.d[buf.r]
    if first == 0x28:                                                         # :49
        index = buf.index_of(buf.r + 1, 0x29)                                 # :51
        if index >= 0:
            return buf.read_slice(index + 1 - (buf.r if sentence_length_fixed else 0))  # :53
        return None
    delimiter = first                                                         # :58
    introducers = {0xE6, 0x3E} if delimiter == 0xE7 else {0x7D}               # :59, :67, :78
    index = buf.index_of(buf.r + 1, delimiter)                                # :61
    if index < 0:
        return None
    out = bytearray()
    while buf.r <= index:                                                     # :65
        b = buf.d[buf.r]
        buf.r += 1
        if b in introducers and broken != "jt808: no unescaping":
            ext = buf.d[buf.r]
            buf.r += 1
            if (b, ext) in UNESCAPE[delimiter]:                               # :69-84
                out.append(UNESCAPE[delimiter][b, ext])
        else:
            out.append(b)                                                     # :86
    return bytes(out)


def frames_of(decode, stream, **kw):
    """Every frame decode() returns from one buffer, in order, then the bytes left unread."""
    buf, out = Buf(stream), []
    while True:
        try:
            f = decode(buf, **kw)
        except IndexError as e:
            out.append(e)
            return out, buf.readable()
        if f is None:
            return out, buf.readable()
        out.append(f)


# ---------------------------------------------------------------------------
# 1. Traccar's framer tests, as anchors.
# ---------------------------------------------------------------------------

VECTOR = re.compile(r'verifyFrame\(\s*binary\("([0-9a-fA-F]+)"\),\s*'
                    r'decoder\.decode\(null,\s*null,\s*binary\("([0-9a-fA-F]+)"\)\)\)', re.S)


def vectors(name):
    with open(os.path.join(REF, name)) as f:
        return [(bytes.fromhex(want), bytes.fromhex(given)) for want, given in VECTOR.findall(f.read())]


def failures(decode, vecs, **kw):
    """Traccar's decode() is called once per vector, on a fresh buffer; so is the port's."""
    bad = 0
    for want, given in vecs:
        try:
            got = decode(Buf(given), **kw)
        except IndexError:
            got = None
        bad += got != want
    return bad


def anchors():
    print("## 1. The port against Traccar's own framer tests\n")
    g, j = vectors("Gt06FrameDecoderTest.java"), vectors("Jt808FrameDecoderTest.java")
    ok = True
    for name, decode, vecs in (("Gt06FrameDecoderTest", gt06_decode, g),
                               ("Jt808FrameDecoderTest", jt808_decode, j)):
        bad = failures(decode, vecs)
        ok &= bad == 0 and len(vecs) > 0
        print(f"{name}: the port reproduces {len(vecs) - bad} of {len(vecs)} vectors")
    print("\nEach deliberately broken port must fail at least one vector:")
    for decode, vecs, broken in ((gt06_decode, g, "gt06: no search for 0D 0A"),
                                 (jt808_decode, j, "jt808: no skipping to a frame start"),
                                 (jt808_decode, j, "jt808: no unescaping")):
        bad = failures(decode, vecs, broken=broken)
        ok &= bad > 0
        print(f"  {broken:38} fails {bad} of {len(vecs)}")
    bad = failures(jt808_decode, j, sentence_length_fixed=True)
    print(f"\nWith :53's sentence length corrected, the JT808 port still fails {bad} of {len(j)}.")
    print("Every test vector sits at the start of its own buffer, where the two lengths agree.")
    print("No vector in either test puts two frames in one buffer.")
    return ok


# ---------------------------------------------------------------------------
# 2. Constructed streams. Faults are made the way traffic.py's rule R15 makes them.
# ---------------------------------------------------------------------------

def jt808_frames(rng, delimiter, n):
    terminal, clock = common.fake_terminal(rng), rng.below(common.YEAR_SECONDS)
    out = []
    for i in range(n):
        body = jt808.location_body(jt808.location_fields(rng, common.clock_digits(clock + 30 * i),
                                                         [0, 2], 18))
        out.append(jt808.frame(jt808.LOCATION, body, delimiter=delimiter, terminal=terminal,
                               index=i, version_2019=False))
    return out


def gt06_frames(rng, n):
    return [gt06.frame(gt06.STATUS, gt06.status_content(gt06.status_fields(rng)), serial)
            for serial in range(1, n + 1)]


def no_sync(rng, protocol, n):
    alphabet = bytes(b for b in range(256) if b not in traffic.SYNC_BYTES[protocol])
    return rng.bytes_from(n, alphabet)


def show(title, decode, segments, **kw):
    """segments: [(label, bytes, whole?, what it was before it was broken)]. Names each frame
    returned by the segment it equals, or by the frame a broken segment was cut from."""
    names = {}
    for label, data, whole, original in segments:
        if original is not None:
            names[frames_of(decode, original)[0][0]] = label if whole else f"{label.split()[0]}, read as whole"
    returned, left = frames_of(decode, b"".join(s[1] for s in segments), **kw)
    got = []
    for f in returned:
        if isinstance(f, IndexError):
            got.append(f"exception: {f}")
        else:
            got.append(names.get(f, f"{len(f)} bytes, no whole frame"))
    lost = [s[0] for s in segments if s[2] and s[0] not in got]
    print(f"\n{title}")
    print("  sent:     " + " | ".join(s[0] for s in segments))
    print("  returned: " + " | ".join(got) + (f"   ({left} byte{'s' * (left != 1)} left waiting)" if left else ""))
    print("  whole frames lost: " + (", ".join(lost) if lost else "none"))


def constructed():
    print("\n## 2. Constructed streams: a broken frame, then whole frames\n")
    print("F: JT808 location 0x0200, 2013 format. G: GT06 status 0x13. Made by bench/stimulus's")
    print("encoders from SplitMix64 seed 8. The words in brackets say how a frame was broken, as")
    print("rule R15 would break it. \"Left waiting\" is bytes the framer holds because it took one of")
    print("them as a frame start and no closing byte has come.")
    rng = SplitMix64(8)
    for delimiter in (jt808.STANDARD, jt808.ALTERNATIVE):
        F = jt808_frames(rng, delimiter, 7)
        d = f"{delimiter:02X}"

        def seg(i, data=None, broken=None):
            label = f"F{i + 1}" + (f" ({broken})" if broken else "")
            return (label, F[i] if data is None else data, broken is None, F[i])

        whole = [seg(i) for i in range(1, 7)]
        show(f"JT808 {d}: all whole (control)", jt808_decode, [seg(0)] + whole)
        show(f"JT808 {d}: F1 truncated to half", jt808_decode,
             [seg(0, F[0][:len(F[0]) // 2], "truncated")] + whole)
        show(f"JT808 {d}: F1 lost only its closing {d}", jt808_decode,
             [seg(0, F[0][:-1], "truncated by 1")] + whole)
        show(f"JT808 {d}: F1 and F4 truncated", jt808_decode,
             [seg(0, F[0][:len(F[0]) // 2], "truncated"), seg(1), seg(2),
              seg(3, F[3][:len(F[3]) // 2], "truncated"), seg(4), seg(5), seg(6)])
        show(f"JT808 {d}: 6 garbage bytes after F1 (no_sync, rule R16)", jt808_decode,
             [seg(0), ("garbage", no_sync(rng, "jt808", 6), False, None)] + whole)

    F = jt808_frames(rng, jt808.STANDARD, 2)
    sentence = jt808.sentence(jt808.sentence_fields(rng, "000000000000", 1))
    segments = [("F1", F[0], True, F[0]), ("sentence", sentence, True, sentence),
                ("F2", F[1], True, F[1])]
    show("JT808 7E: a ( sentence after a binary frame, one buffer", jt808_decode, segments)
    show("  the same, with :53's length corrected", jt808_decode, segments, sentence_length_fixed=True)

    G = gt06_frames(rng, 5)
    whole = [(f"G{i + 1}", G[i], True, G[i]) for i in range(1, 5)]
    content = gt06.status_content(gt06.status_fields(rng))
    show("GT06: all whole (control)", gt06_decode, [("G1", G[0], True, G[0])] + whole)
    show("GT06: 6 garbage bytes after G1 (no_sync, rule R16)", gt06_decode,
         [("G1", G[0], True, G[0]), ("garbage", no_sync(rng, "gt06", 6), False, None)] + whole)
    show("GT06: G1 truncated to 8 of its 15 bytes", gt06_decode,
         [("G1 (truncated)", G[0][:8], False, G[0])] + whole)
    long = gt06.frame(gt06.STATUS, content, 1, length=5 + len(content) + 2)
    show("GT06: G1's length field 2 too long, its CRC recomputed", gt06_decode,
         [("G1 (length +2)", long, True, long)] + whole)
    bad = gt06.frame(gt06.STATUS, content, 1, crc_error=0x1234)
    show("GT06: G1's CRC wrong", gt06_decode, [("G1 (bad CRC)", bad, True, bad)] + whole)


# ---------------------------------------------------------------------------
# 3. The coverage stimulus.
# ---------------------------------------------------------------------------

FAULT_MARK = {None: ".", "truncated": "T", "bad_checksum": "C", "length_disagreement": "L",
              "unknown_type": "U", "flag_lying": "F"}


def coverage():
    import json
    path = os.path.join(STIMULUS, "params", "coverage.json")
    with open(path) as f:
        params = json.load(f)
    conns, _ = traffic.generate(params, SplitMix64(1))
    print("\n## 3. The coverage stimulus, params/coverage.json, seed 1\n")
    print("Its fault rates are chosen so that every class occurs, and are no claim about traffic.")
    print("These counts show that the mechanism of section 2 occurs in the benchmark's own stimulus.")
    print("They are not a rate. Sentences use :53's corrected length, so that only the delimiter")
    print("pairing is counted.\n")
    print("Per connection, its frames in order: . whole, T truncated, C bad check, L length,")
    print("U unknown type, F flag-lying, g a garbage run before the next frame. A whole frame that")
    print("does not come out whole is shown in upper case as X.\n")
    totals = {}
    for conn in conns:
        decode = gt06_decode if conn.protocol == "gt06" else jt808_decode
        kw = {} if conn.protocol == "gt06" else {"sentence_length_fixed": True}
        returned, _ = frames_of(decode, conn.stream(), **kw)
        returned = [f for f in returned if not isinstance(f, IndexError)]
        marks, whole, lost = [], 0, 0
        for s in conn.segments:
            if s.record["kind"] == "garbage":
                marks.append("g")
                continue
            fault = s.record["fault"]
            if fault is None:
                whole += 1
                alone = frames_of(decode, s.data, **kw)[0][0]
                if alone in returned:
                    returned.remove(alone)
                    marks.append(".")
                else:
                    lost += 1
                    marks.append("X")
            else:
                marks.append(FAULT_MARK[fault])
        t = totals.setdefault(conn.protocol, [0, 0])
        t[0] += whole
        t[1] += lost
        extra = f" {conn.delimiter:02X}" if conn.protocol == "jt808" else ""
        print(f"  conn {conn.conn:2} {conn.protocol}{extra:3}  {''.join(marks)}")
    print()
    for protocol, (whole, lost) in sorted(totals.items()):
        print(f"{protocol}: {lost} of {whole} whole frames do not come out whole")


def main():
    print("Inputs (reference/, gitignored; Traccar at 847edd2c8c4dcc47426fb76b7800b342dea3cde6):")
    for name in SOURCES:
        path = os.path.join(REF, name)
        if not os.path.exists(path):
            print(f"  MISSING {name}: see reference/README.md to refetch")
            return 2
        with open(path, "rb") as f:
            print(f"  {hashlib.sha256(f.read()).hexdigest()}  {name}")
    print()
    if not anchors():
        print("\nANCHORS FAILED: the port is not Traccar's framer; nothing below would mean anything")
        return 1
    constructed()
    coverage()
    return 0


if __name__ == "__main__":
    sys.exit(main())
