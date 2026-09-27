# Protocol evidence — measured from the reference implementations

Everything here was read out of Traccar's source at pinned commit
`847edd2c8c4dcc47426fb76b7800b342dea3cde6` (see `reference/README.md` to refetch). Line numbers
are from that commit. Nothing here is from vendor marketing, forum summaries or explainers — per
`docs/decisions/0006`, specifications and implementations only.

Findings 4 and 5 also read the GT06 vendor document, v1.8.1, pinned by SHA-256 in the same README.
Every number in Findings 4 to 6 comes from one capture of `bench/evidence/checksums.py`.

**Why this file exists.** The benchmark's shape depends on claims about how much these protocols
actually vary. Those claims circulate mostly in domain material of poor provenance. This file
holds only what can be checked against code, with a citation for each.

---

## Finding 1 — GT06 is not one protocol. It is 16, sharing an envelope

`Gt06ProtocolDecoder.java:130-148` declares a `Variant` enum:

```
VXT01  WANWAY_S20  SR411_MINI  GT06E_CARD  BENWAY  S5  SPACE10X  STANDARD
OBD6   WETRUST     JC400       SL4X        SEEWORLD RFID LW4G     TRX16I
```

| Measure | Count |
|---|---|
| Variants in the enum | **16** |
| Branch sites testing `variant` | **35** |
| `MSG_*` message-type constants | **71** |
| Branch sites testing message type | **110** |
| Decoder length | 1,705 lines |

`STANDARD` is one member of that list, not the norm the others deviate from.

**What this means for the benchmark.** 35 variant branches and 110 type branches in one decoder
is not incidental complexity — it *is* the decoder. A benchmark that decodes only well-formed
`STANDARD` frames exercises a small corner of the real control-flow graph and would measure the
wrong thing.

---

## Finding 2 — JT/T 808 selects its framing, escaping AND header layout at runtime

### Three framing modes, not one

`Jt808FrameDecoder.java` resynchronises by scanning byte-at-a-time for any of **three** frame
starts, then frames differently for each:

```java
if (b == '(' || b == 0x7e || b == 0xe7) break;   // else skipBytes(1)
```

- `(` … `)` — an ASCII-delimited variant outside JT808's binary framing entirely
- `0x7e` … `0x7e` — the standard
- `0xe7` … `0xe7` — the "alternative"

That scan loop is a per-byte three-way comparison hunting for a frame start. It is
**Prediction A's resynchronisation cost, in literal code**.

### Two escape alphabets, chosen by the delimiter

The destuffing loop branches on `alternative = (delimiter == 0xe7)`:

| Mode | Escape rules |
|---|---|
| standard (`0x7e`) | `7d 01`→`7d`, `7d 02`→`7e` |
| alternative (`0xe7`) | `e6 01`→`e6`, `e6 02`→`e7`, `3e 01`→`3e`, `3e 02`→`3d` |

Two introducer bytes and four pairs in the alternative mode versus one and two in the standard.
**Destuffing is per-byte work (Prediction B) with a variant dispatch inside the loop
(Prediction A).** The two predictions are not cleanly separable here, and the benchmark must not
be built as though they are.

### Three independent fields decide where the body starts

`Jt808ProtocolDecoder.java:359-373`:

```java
delimiter    = buf.readUnsignedByte();
int type     = buf.readUnsignedShort();
int attribute= buf.readUnsignedShort();
int bodyLength = BitUtil.to(attribute, 10);                                  // low 10 bits
protocolVersion = BitUtil.check(attribute, 14) ? buf.readUnsignedByte() : null;   // bit 14
ByteBuf id   = buf.readSlice(protocolVersion != null ? 10
                           : (delimiter == 0xe7 ? 7 : 6));
int index    = (type == MSG_LOCATION_REPORT_2 || type == MSG_LOCATION_REPORT_BLIND)
             ? buf.readUnsignedByte() : buf.readUnsignedShort();
```

Header length is a function of **three fields read from three different places**:

| Field | Read from | Effect on header length |
|---|---|---|
| `attribute` bit 14 | bytes 3–4 | +1 version byte, and ID 6→10 |
| `delimiter` | byte 0 | ID 6→7 when `0xe7` |
| `type` | bytes 1–2 | index 2→1 byte for two message types |

So the header is **5 + {0,1} + {6,7,10} + {1,2}** bytes. You must read and branch on three
separate fields before you know where the body begins.

---

## Finding 3 — device identity is carried by the *connection*, not the frame

This is the finding with the largest consequence for the benchmark's input contract, and it is
unconditional for GT06.

`Gt06ProtocolDecoder.java` resolves the device two different ways:

| Line | Call | When |
|---|---|---|
| 526 | `getDeviceSession(channel, remoteAddress, imei)` | **only** inside `if (type == MSG_LOGIN)` |
| 502 | `getDeviceSession(channel, remoteAddress)` | every other message type |

The IMEI is read at line 523 from the login packet's payload. **Every subsequent frame is
associated with its device by `channel` + `remoteAddress` alone — the transport connection.**
Non-login GT06 frames contain no device identifier at all, so there is nothing in the bytes to
key on even in principle.

For JT808 the situation differs: the terminal ID *is* in every frame, at an offset computable
from `attribute` bit 14, which sits at a fixed position (bytes 3–4). So ID-keying is possible —
**unless the version flag lies.** If bit 14 claims 2019 and the payload is 2013, the decoder
slices 10 bytes where the real ID is 6, and the extracted key is garbage. The ID is unusable as a
cache key in precisely the case a cache exists to handle.

**Consequence: the benchmark's stimulus cannot be a flat byte stream.** It must carry connection
identity, with connection count and interleaving pattern declared. That requirement is *verified
and unconditional* for GT06, and *conditional on the flag-lying claim* for JT808 — so the JT808
half inherits that claim's weaker evidence class while the GT06 half does not.

### A correction worth recording, because the reasoning changes the scope

A circulating version of this argument says the JT808 lookup is circular because "the terminal
phone number sits at offset 4 in a 2013 header and offset 5 in a 2019 header, so to read the
terminal number you need to know the version." **That reasoning is wrong.** `attribute` is at a
fixed offset and bit 14 announces the version directly; you can always locate the ID without
knowing the version in advance. Line 366 does exactly that.

The conclusion survives, but only via the flag-lying route above — and the difference matters,
because it decides the scope. On the stated reasoning, transport-layer keying would be required
always. On the real one, it is required always for GT06 (verified) and only-if-flag-lying for
JT808 (unsourced).

---

## Finding 4 — nobody checks the checksum of a received frame

Capture: [`20260927T062216Z-protocol-checksums`](../docs/results/20260927T062216Z-protocol-checksums/),
section 2.

The GT06 vendor document requires the check: "CRC error occur when the received information is
calculated, the receiver will ignore and discard the data packet" (§4.6, PDF page 10).

Traccar computes a checksum in three places, and none of them is on the receive path:

| Line | In | What it computes |
|---|---|---|
| `Gt06ProtocolDecoder.java:280` | `sendResponse()` | the CRC-ITU of a reply Traccar sends |
| `Jt808ProtocolDecoder.java:146` | `formatMessage()` | the XOR check of a message Traccar sends |
| `Jt808ProtocolDecoder.java:277` | `decodeId()` | a Luhn digit for an IMEI-form ID, not a frame check |

Neither frame decoder computes one at all. **A frame with a wrong checksum is decoded exactly like
a correct one**, in both protocols.

**Why it matters here.** Prediction B has GT06-heavy traffic making the CRC "the only O(n) pass".
In the de facto implementation, that pass does not run on receive. A well-formed GT06 frame is framed
by reading its length field and checking two bytes (`Gt06FrameDecoder.java:40-47`). After that, no
loop runs over its bytes: the decoder reads each field once, where it sits. JT808 differs. Its
destuffing loop runs over every byte whether or not anything validates
(`Jt808FrameDecoder.java:65-88`).

The benchmark decoder validates, because SPEC §3's `crc_fail` status requires it and the vendor
document says to. So in this benchmark, **the CRC's per-byte cost is the cost of conforming to the
specification, not the cost of what the de facto decoder does.** Both are legitimate to measure,
but they are different claims. If Phase 4 finds that the CRC dominates, it must say which one it
measured.

---

## Finding 5 — the GT06 vendor's own examples fail its own check

Capture: [`20260927T062216Z-protocol-checksums`](../docs/results/20260927T062216Z-protocol-checksums/),
section 1. Page numbers are the PDF's; the printed number is one lower.

The document gives three example frames sent by a device. As printed, one of them verifies:

| Example | Where | Length field | Bytes it should count | CRC printed | CRC computed |
|---|---|---:|---:|---|---|
| login | §5.1.3, p.12 | 13 | 13 | `0x8cdd` | `0x8cdd` |
| location `0x12` | §5.2.2, p.16 | 31 | 31 | `0x8081` | `0x7377` |
| heartbeat `0x13` | §5.4.3, p.26 | 8 | 10 | `0x061f` | `0xf8b5` |

The two server replies on the same pages both verify. Each failure has an explanation that the
document itself supplies, and each one checks out:

- **The location example has a one-byte typo.** Exactly one single-byte change makes its CRC verify:
  byte 10, `0xcc` to `0xcf`. The document's own field table on p.13 prints that byte as `0xCF`. With
  it, the frame verifies. That corrected frame is a byte-exact anchor for anything that encodes
  `0x12`.
- **The heartbeat's length and CRC were computed for a different frame.** No single-byte change
  repairs it. Its length field counts 8 bytes where 10 follow. Delete the two Alarm/Language bytes,
  `00 01`, which the example labels "Reserved bit (Language)", and both verify:
  `78 78 08 13 4B 04 03 00 11 06 1F 0D 0A`. So the length and the CRC describe a heartbeat whose
  information content is 3 bytes. The 2-byte Alarm/Language field was added to the example later
  without recomputing either. The field table on p.24 includes it, so the table and the example
  describe two versions of the frame.

**What this establishes.** The vendor's own material contains a bad-checksum frame and a
length-field disagreement, two of SPEC §4's malformed classes. A decoder that obeys p.10 would
discard two of the vendor's three examples as printed.

**What it does not establish.** Anything about devices. These are errors in a document. That some
devices send the 3-byte heartbeat is plausible from this, and not shown by it.

---

## Finding 6 — Traccar's test inputs would fail a validating decoder

Capture: [`20260927T062216Z-protocol-checksums`](../docs/results/20260927T062216Z-protocol-checksums/),
section 3.

Traccar's unit tests feed its decoders hex frames, mostly from real devices and forum posts. They are
counted here and never committed (`bench/README` rule 2a).

| | GT06 | JT808 |
|---|---:|---:|
| frames | 185 | 114 |
| checksum fails | 27 | 11 |
| length field disagrees with the bytes present | 15 | 9 |

The GT06 failures span 14 protocol numbers, among them 2 logins and 1 location `0x12`. 8 of the 11
JT808 failures are location reports, `0x0200`. 5 JT808 inputs contain an unescaped `0x7e` between
their delimiters, which `Jt808FrameDecoder` would have split. The tests never see that, because
they feed the protocol decoder directly.

**What this establishes.** Traccar could not start validating checksums without failing its own
tests. Whatever the original reason for Finding 4, the test suite now depends on it.

**What it does not establish: a rate.** These are unit-test inputs, chosen to cover code paths,
and some may have been edited. Anonymising an IMEI without recomputing the CRC would produce exactly
these failures. **None of these counts may be used as a malformed rate in the stimulus.** SPEC §4's
"rates for every class: unset" stands.

The same count shows one more thing, worth a sentence: **no test input uses the `0xe7` delimiter.**
Finding 2's alternative framing and its escape alphabet are implemented in Traccar, and untested
there.

---

## Finding 7 — the GT06 variant is chosen from the length field

`decodeVariant()` (`Gt06ProtocolDecoder.java:1642-1703`) runs first on every frame (`:491`). It
picks the variant from the start bytes, the protocol number and **the length field**. For the two
non-login types in SPEC §2, with start bytes `78 78`:

| Protocol number | Length | Variant |
|---|---|---|
| `0x12` | `0x21` | `BENWAY` |
| `0x12` | `0x24` | `VXT01` |
| `0x12` | `0x29` | `WETRUST` |
| `0x12` | `0x2b` | `S5` |
| `0x12` | `0x71` or more | `GT06E_CARD` |
| `0x13` | `0x13` | `OBD6` |
| either, any other length | | `STANDARD` |

So `STANDARD` means "a length that no variant rule claims". The vendor's layouts give `0x1f` for
`0x12` (p.13) and `0x0a` for `0x13` (p.24). Both are `STANDARD`.

**Consequence: a length-field error can change which decoder runs.** A `0x12` frame whose length
reads `0x21` instead of `0x1f` is decoded as `BENWAY`. So in Traccar, SPEC §4's length-disagreement
class and §1's variant dispatch are not independent. Whether they are independent in the benchmark
decoder is a property of its design, and must be stated when it is written.

---

## What the circulating explainers get wrong, and what they miss

A widely-repeated claim is that these devices "plug into almost any backend with zero code
changes." Findings 1 and 2 refute it from source. But two specific corrections matter:

**The common account of JT808 versioning is incomplete.** It is usually given as "bit 14 selects
2013 vs 2019, and the phone number grows BCD[6]→BCD[10]." That is right as far as it goes and
misses two further branches in the same six lines: the `0xe7` delimiter selects a **7-byte** ID —
neither 6 nor 10, and not a version question at all — and the **message type** independently
changes the index field width. Three dispatches, not one.

**The variance is worse than "vendors deviate."** `STANDARD` being one enum member among 16 means
there is no baseline to deviate *from*. "Speaks GT06" means approximately "starts with `7878` and
uses CRC-ITU."

---

## What this does not establish

- **Nothing here measures frequency.** 16 variants in a decoder says nothing about what fraction
  of real traffic is non-`STANDARD`. The variant mix is a benchmark *parameter* to be declared
  (`bench/README.md`), and a number this file cannot supply.
- **Nothing here is a security finding.** Whether JT808's encryption bit or authentication code
  are adequate does not affect *parsing*, so it is out of scope for the benchmark and stays out
  of its specification. Note only that Traccar reads `BitUtil.to(attribute, 10)` and so ignores
  attribute bits 10–13 entirely, encryption bit included.
- **Nothing here settles Prediction A vs B.** It sharpens both. A is now concrete — a byte-at-a-
  time three-way resync scan plus three-field header dispatch. B is now known to contain a
  variant branch inside the destuffing loop.
