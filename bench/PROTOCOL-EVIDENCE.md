# Protocol evidence — measured from the reference implementations

Everything here was read out of Traccar's source at pinned commit
`847edd2c8c4dcc47426fb76b7800b342dea3cde6` (see `reference/README.md` to refetch). Line numbers
are from that commit. Nothing here is from vendor marketing, forum summaries or explainers — per
`docs/decisions/0006`, specifications and implementations only.

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
