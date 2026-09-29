# 0012 — What the reference decoder reports, and what it sends back

- **Date:** 2026-09-29
- **Status:** Accepted
- **Phase:** 0, binding on the reference decoder, on the expected output it produces, and on the
  `0010` check

## Context

SPEC §3 fixes the shape of a record and little else:

```
<conn_id> <protocol> <msg_type> <status> <field>=<value> …
```

It gives one record per frame, in input order, a record for every rejected frame, and fields sorted
by name, as integers with no floating point. `0011` added `resync` records, and left one question
for this record: what a flag-lying frame's record says.

SPEC does not say which fields a record carries, in what units, or what its text is exactly. The
decoder cannot be written without those, and the `0010` check has nothing to compare without them.

Three more things bear on it.

- **The roadmap names a stage that SPEC leaves out.** Its workload is "frame sync over a byte stream
  → length and protocol ID → checksum → unpack BCD timestamp and packed fixed-point coordinates →
  status bitfield → identifier lookup → ACK" (`roadmap.md:467-469`). SPEC §3 has records and no
  ACK, and nothing records that the ACK was dropped, or why.
- **What the sources do is now read,** in `PROTOCOL-EVIDENCE` Finding 9:
  - Traccar turns every location into one `Position` type, in degrees, knots and a UTC instant.
  - It reads a GT06 time as UTC, a JT808 `0x0200` time as GMT+8, and a `0x5501` time as UTC. All
    three are configuration defaults. The GT06 document gives no time zone.
  - Its knots come from a ratio rounded to six places, so they are not exact.
  - It drops a frame whose latitude or longitude is out of range.
  - The GT06 document defines responses to login and heartbeat, and its two response examples
    verify. Traccar also acknowledges location frames and unknown types. It acknowledges frames
    whose check fails, because it never checks one (Finding 4).
  - JT808's general response is read from Traccar alone, like every JT808 layout here.
- **The `0010` check has to predict every record from `intent.jsonl`.** So every field must be
  computable from what the generator records, and every conversion must be one the check can do
  by a path of its own.

**The same constraint as `0007`, `0009` and `0011`.** These choices decide how much per-frame work
the benchmark contains beside the per-byte work that Predictions A and B are about. They also decide
whether transmit-side CRC and escaping exist in it at all. They may not be chosen for their effect
on either prediction. That effect is stated under *Consequences*.

## Options considered

### Units

1. **Each field in its frame's own unit.** GT06 latitude in 1/1,800,000 degree, JT808's in
   millionths, `0x5501`'s in BCD degrees and minutes.
   - *For:* nothing is converted, so nothing is rounded and nothing assumed. The check compares
     with the intent log directly.
   - *Against, and why it lost:* such a record is not decoded. Its meaning depends on which frame
     type it came from, so a consumer must dispatch on protocol and type again before using it.
     Turning a family of formats into one record type is the dispatch layer's job. The roadmap
     describes the workload as "a family of decoders behind a dispatch layer", and Traccar
     decodes both protocols into one `Position` type.
2. **Traccar's units, in fixed point:** degrees, knots, and milliseconds since 1970.
   - *For:* they are the de facto decoder's units.
   - *Against:* no source converts to them exactly. Traccar's own km/h-to-knots ratio is 0.539957
     (`UnitsConverter.java:20`), which is 1/1.852 rounded to six places. A GT06 coordinate is a count
     of 1/1,800,000 degree, which no decimal fixed point holds. Each conversion would need a rounding
     rule that no source gives, and the check would have to reproduce it.
3. **One exact unit per quantity.** For each quantity that more than one frame type carries, the
   coarsest unit into which every source converts with integer arithmetic and no remainder.
   - *For:* one record type, as with option 2, and no rounding rule to invent. The check can use
     exact fractions and a calendar library, neither of them the decoder's code.
   - *Against:* the coordinate unit is unfamiliar, 1/9,000,000 degree, and an odometer needs 64
     bits.

### Which fields

1. **What Traccar reads, for both protocols.**
   - *For:* it is the de facto decoder.
   - *Against:* for GT06 the benchmark follows the pinned vendor document where it speaks, as it
     already does for the checksum (Finding 4). The document defines two fields that Traccar never
     reads: the differential-positioning bit of a location, and the language byte of a heartbeat.
2. **Every field the generator writes.**
   - *For:* it gives the check the most to compare.
   - *Against:* it makes the generator the specification, backwards along `0004`'s chain. The
     generator's layouts come from the sources, not the other way round.
3. **The GT06 document for GT06, and Traccar for JT808.**
   - *For:* it is the split the generator's layouts already use (`bench/stimulus/README.md`, *Where
     each frame comes from*). JT808 has no pinned standard, so Traccar is its only source.
   - *Against:* the two protocols' fields are chosen by different rules, so a GT06 record can carry a
     field that no deployed decoder reads.

### Responses

1. **None, as SPEC §3 stands.**
   - *For:* the smallest decoder, and SPEC unchanged.
   - *Against:* every deployed server responds, the GT06 document requires it for login and
     heartbeat, and the roadmap names ACK as a stage. Without it, the benchmark would measure a
     receive-only decoder that nobody runs, without saying so.
2. **What Traccar sends, for both protocols.**
   - *For:* the de facto decoder's behaviour, on both.
   - *Against:* for GT06 it acknowledges location frames and unknown types, for which the document
     gives no response. It also acknowledges frames whose check fails.
3. **The GT06 document's responses, Traccar's for JT808, and only for frames that pass.**
   - *For:* the same split as the fields, and a response means the frame was received intact.
   - *Against:* it departs from Traccar in six places, each listed under *Decision*.

## Decision

**Option 3 in each group.** A record is a value. Its text, in section 7, is how the value is
serialised, and serialising is not decoding. Where serialising happens relative to the measured
window is for the next decision, on the harness.

The full per-type field table is SPEC §3's, amended with this record.

### 1. One exact unit for each shared quantity

| Quantity | Field | Unit | Width |
|---|---|---|---|
| time | `time` | seconds since 1970-01-01 00:00:00 UTC | u32 |
| latitude, longitude | `lat`, `lon` | 1/9,000,000 degree, north and east positive | i32 |
| speed | `speed` | metres per hour | u32 |
| course | `course` | degrees | u16 |
| position fixed | `valid` | 0 or 1 | — |
| satellites | `satellites` | count | u8 |
| altitude | `altitude` | metres | i16 |
| odometer | `odometer` | metres | u64 |

- **Why 1/9,000,000 degree.** The sources carry 1/1,800,000 degree (GT06), 1/1,000,000 (JT808
  `0x0200`), and ten-thousandths of a minute, 1/600,000 degree (`0x5501`). The least common
  multiple of the three denominators is 9,000,000, so the conversions are ×5, ×9 and ×15. 180° is
  1,620,000,000, which fits an i32.
- **Why metres per hour.** Km/h is ×1,000, tenths of km/h ×100, and a knot is exactly 1,852 m/h.
  Traccar stores `0x5501`'s speed unconverted, and so reads it as knots
  (`Jt600ProtocolDecoder.java:114`).
- **Why 64 bits for an odometer.** Both sources are 32-bit counts: tenths of a kilometre in item
  `0x01`, and kilometres in `0x5501`. In metres the largest is about 4.3 × 10¹². Traccar also
  computes both in 64 bits (`Jt808ProtocolDecoder.java:792`, `:1531`).
- **Time zones are Traccar's defaults, stated as assumptions.** Only Traccar's code gives any
  zone at all, and only as a default that a deployment overrides per device:
  - GT06: UTC (`BaseProtocolDecoder.java:158-160`). The GT06 document gives none.
  - JT808 `0x0200`, and each location in a `0x0704`: GMT+8 (`Jt808ProtocolDecoder.java:384-386`).
  - JT808 `0x5501`: UTC (`Jt600ProtocolDecoder.java:97`, `DateBuilder.java:26-28`).

  A two-digit year is 2000 + YY (`DateBuilder.java:44-48`).
- **Every other field is the frame's own unsigned integer.** Codes and bit fields are not split
  into flags, and not translated into names. Traccar's splits and names change with the configured
  device model (`Gt06ProtocolDecoder.java:449-481`; `Jt808ProtocolDecoder.java:193`, `:711-721`),
  so no single split is the source's, and the integer loses no bit. A raw field's meaning is given
  by its record's protocol and type. A shared field means the same in every record.

### 2. Which fields

- **GT06:** each field the vendor document defines for the frame type.
- **JT808:** each field Traccar reads on the path the frame takes, with no device model configured.
  For `0x0200`'s additional information, that is the six item IDs the generator makes
  (`jt808.ITEMS`). Any other item is skipped by its length, as Traccar skips the ones it does not
  know.
- **Structural fields are not reported:** lengths, counts, the GPS-information length nibble, escape
  bytes and check bytes. Framing and the check have used them up.
- **A record carries what its frame carries, never what an earlier frame did.** Traccar copies the
  last known position into a heartbeat's or a sentence's `Position` (`getLastLocation`). That is a
  lookup of stored state, not decoding. The one exception is the device, in section 3.

### 3. The device

- **GT06:** the IMEI from the connection's login, on the login's record and every later record of
  that connection. SPEC §2 says the login establishes this binding, and Finding 3 says nothing else
  carries it.
- **A JT808 binary frame:** the terminal ID from its own header, as hex digits (`decodeId`,
  `Jt808ProtocolDecoder.java:270-279`).
- **A sentence:** the device of its connection's most recent binary frame (`decodeResult`,
  `:653-663`).
- **Before any device is known on a connection,** a record has no `device` field and gets no
  response. Under rule R2 the generator never makes such a frame.

**In draft 1, the roadmap's "identifier lookup" is this binding.** Traccar also looks each
identifier up in a registry of provisioned devices. No source gives a registry's contents or its
size, so that lookup is left out, and SPEC says so.

### 4. Batches

A `0x0704` frame whose status is `ok` produces one record per location it carries, in order. Each
record carries its location's fields, the batch's `archive` byte, and `record=<i>`, counting from
1. A batch that carries no location produces one record, without `record`. This is what Traccar
returns for a batch: a list of positions (`:1634-1655`).

### 5. Rejected frames, `malformed`, `resync`, and flag-lying frames

- **`crc_fail`, `malformed` and `unsupported` records carry `at` and `len` only.** Nothing in a frame
  that failed its check is trusted. An unknown type has no field table, and a malformed frame's
  fields cannot all be decoded. A JT808 header could still be read from either, but one rule for
  every rejected frame is simpler to state and to check.
- **`malformed` means one of these, and nothing else:**
  - the type's fixed fields do not fit the frame's content;
  - a BCD digit above 9;
  - a date or time that does not exist, or a GT06 year byte above 99;
  - a latitude beyond 90°, or a longitude beyond 180°.

  Traccar drops a frame for the last of these: `Position` throws (`Position.java:237-255`). For the
  others it decodes a value nobody sent. `BcdUtil.readInteger` accepts digits above 9, and
  `DateBuilder` never makes its calendar strict, so month 13 becomes January of the next year. The
  benchmark reports them instead.
- **`resync` records carry `at` and `len`,** as `0011` says.
- **A flag-lying frame gets an ordinary record.** Its `header=2013` shows the layout that detection
  found, whatever attribute bit 14 says. That answers the question `0011` left for this record. Both
  detection modes print the same.

### 6. Responses

The decoder builds the bytes of each response its source specifies. Each response is a record of
its own, placed immediately after the record or records of the frame it answers.

| Frame | Response | Source |
|---|---|---|
| GT06 `0x01` login and `0x13` heartbeat | `78 78 05`, the frame's protocol number and serial, CRC-ITU, `0D 0A` | The document, §5.1.2 and §5.4.2. Its examples, §5.1.3 (p.12) and §5.4.3 (p.26), verify |
| JT808 `0x0102`, `0x0200`, `0x0704` | general response `0x8001` | `Jt808ProtocolDecoder.java:445-448`, `:468-470`, `:502-504` |
| anything else | none | |

- **The JT808 response is Traccar's, byte for byte** (`formatMessage`, `:126-148`;
  `sendGeneralResponse`, `:151-161`; `Jt808FrameEncoder.java:25-49`). It has:
  - the frame's own delimiter;
  - the header layout that detection found, so a flag-lying frame is answered in the 2013 layout;
  - the frame's terminal ID, and its version byte if it has one;
  - a response index of 0;
  - a body of the frame's index, its type, and result 0;
  - an XOR check, and escaping in the delimiter's alphabet.
- **Only a frame whose status is `ok` gets a response.** A response says that a frame arrived
  intact and was understood. A `crc_fail` frame did not arrive intact, and a `malformed` one was not
  understood.
- **Six departures from Traccar, declared:**
  - no response to a GT06 `0x12` location, or to an unknown GT06 type
    (`Gt06ProtocolDecoder.java:1618-1630`). The document gives none;
  - no response to a frame that fails its check. Traccar answers it, because it never checks one;
  - no response to a `malformed` frame. Traccar answers a JT808 frame before decoding its body
    (`:468-470`), so it answers some frames that this decoder calls malformed;
  - a flag-lying frame is answered in the layout that detection found. Traccar believes bit 14, and
    reads a version byte the frame does not have and a terminal ID that is partly something else.
    Unless that ID happens to name a known device, it finds no session and answers nothing
    (`:376-382`);
  - no `0x4401` response to a `0x5501` frame with attribute bit 15 set (`:482-485`), because the
    generator never sets that bit;
  - no response to a `BASE,2` sentence (`:347-353`). Traccar's carries its own wall clock, and a
    reference result cannot.

### 7. The text form

```
<conn> <protocol> <type> <status> <field>=<value> …
```

- `protocol` is `gt06` or `jt808`.
- `type` is the frame's type in lowercase hex: two digits for GT06, four for JT808. It is `sentence`
  for a sentence, and `-` for a resync run. A response's type is its own: `0x01`, `0x13` or
  `0x8001`.
- `status` is one of SPEC §3's five, or **`sent`** for a response.
- Fields are sorted by name. Every value is a decimal integer, with a leading `-` when negative,
  except three:
  - `device` is the hex digits of the IMEI or terminal ID, as the login or header carries them;
  - `bytes`, a response's bytes, and `text`, a sentence's, are lowercase hex.
- Every record about received bytes carries `at`, the offset of its first byte in its connection's
  stream, and `len`, its length on the wire.
- **The canonical order is by connection, then by stream order.** SPEC §3 said "input order", but
  under `0011` rule 8 only each connection's records are independent of chunking. How records from
  different connections interleave depends on where the chunks cut the streams. That is transport,
  not decoding, so it is not part of the reference result.

## Consequences

**Made easier.**
- **The `0010` check can be complete.** Every field of every record, and every byte of every
  response, can be computed from `intent.jsonl`. Times go through a calendar library, coordinates
  through exact fractions, and GT06 response CRCs through `crc_oracle.py`. None of them is the
  decoder's code.
- **A record means the same whatever sent it.** A GT06 location and a JT808 one can be compared
  directly.
- **No conversion has a remainder,** so there is no rounding rule to specify, get wrong, or
  reproduce.

**Made harder, or given up.**
- **SPEC §3 changes:** per-type fields, the `sent` status, response records, one record per location
  in a batch, and canonical order by connection. SPEC is amended.
- **The decoder does in integers what Traccar does in floating point:** a multiply by a small
  constant per coordinate, a calendar computation per time, and a 64-bit product per odometer. On
  RV32IM the last needs `M`'s `mulhu`, or a longer sequence without it.
- **The decoder builds responses.** That is a CRC-ITU over 4 bytes for each GT06 login and heartbeat,
  and a header, an XOR over 17 to 22 bytes, and escaping for each acknowledged JT808 frame.
- **`malformed` now has a definition,** and the decoder makes range and digit checks that Traccar
  does not make.
- **The time zones are assumptions,** and not consistent ones. Traccar's are defaults, which a
  deployment sets per device. By default Traccar reads one JT808 device's `0x0200` and `0x5501` times
  eight hours apart (Finding 9), and the records reproduce that.
- **Unexercised paths.** The generator makes no GT06 frame before a login, no empty batch, no
  malformed frame, and no attribute bit 15. No check will see what the decoder does with any of them.

**Effect on the predictions.** Responses add transmit-side work of the same kinds as Prediction B's
per-byte terms: CRC-ITU for GT06, XOR and escaping for JT808. It is per acknowledged frame, over a
few bytes. The unit conversions add per-location work that is neither A's term nor B's, so they
dilute the shares of both. None of this was a criterion. Each choice would have been the same if
either prediction were already known to be right.

**Revisit if:**
- a JT/T 808 standard is pinned: it would replace Traccar for JT808's fields and response;
- a source gives devices' time zones, or a registry's size;
- the generator starts setting attribute bit 15, or sending frames before a login.

## Predictions

Testable when the reference decoder runs on the coverage stimulus (`params/coverage.json`, seed 1),
with the `0010` check.

1. **Every field, and every response byte, that the check predicts from `intent.jsonl` matches the
   decoder's output,** apart from `0011`'s cases (a) and (b).
2. **No `malformed` record appears.** The generator's ranges (R12) and times (R5) are all valid.
3. **Neither chunking nor detection mode changes any record or response** in canonical order.
