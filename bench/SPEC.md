# Telematics Frame Decoder Benchmark — specification

- **Version:** draft 1 — **frozen before the reference decoder is written**, per `decisions/0004`
- **Amended 2026-09-27:** see *Amendment* at the end. Writing the stimulus generator found
  unset parameters that the list below does not name. Nothing already here changes.
- **Amended 2026-09-28 and 2026-09-29:** see the amendments at the end. §7's frame count is also
  sized for RTL simulation. §5 records Traccar's scans, and the decoder's rule is `decisions/0011`.
  §3's records get their fields, units, responses and order from `decisions/0012`.
- **Amended 2026-09-30:** §3's input carries each connection's protocol. `decisions/0014` fixes how
  the stimulus reaches the decoder, what the window counts, and how the records leave Spike.
- **Date:** 2026-09-21
- **Classification:** specification-derived reconstruction (`bench/README.md` rule 3)

Every claim below is one of three kinds, and each is marked:

| Mark | Meaning |
|---|---|
| **[V]** | **Verified** — cited to a file and line in `bench/PROTOCOL-EVIDENCE.md` |
| **[D]** | **Decided** — a decision record fixes it |
| **[ ]** | **Unset** — a parameter that must be justified before any result is quoted |

**An unset parameter is not a gap to be filled in by whoever writes the code first.** It is a
number that has no source yet. Inventing one while writing is how this project has already been
wrong twice — see `0007`'s amendment. If a value is needed to run, declare it in the manifest as
an *assumption*, not a finding.

---

## 1. Protocols and variants in scope

**[D]** Two protocol families: **GT06** and **JT/T 808**. Fixed by `decisions/0001`.

**[V]** Neither is one protocol. GT06 declares 16 variants tested at 35 branch sites; `STANDARD`
is one enum member, not a norm. JT808 selects framing, escape alphabet and header layout at
runtime from three independent fields.

**In scope for draft 1:**

| | In | Rationale |
|---|---|---|
| GT06 variants | `STANDARD` only | Variant-specific field layouts are a *breadth* axis. Draft 1 fixes breadth at one and varies the axes that change the *work shape*. |
| JT808 framing modes | all three — `(`…`)`, `0x7e`, `0xe7` | **[V]** The delimiter selects which of two escape alphabets the destuffing loop runs. Dropping any mode removes a distinct per-byte code path. |
| JT808 header versions | both — bit 14 clear and set | **[V]** Changes header length and ID width. This is the dispatch `0007` is about. |

**Deferred, with reason:** the other 15 GT06 variants. They multiply branch coverage without
adding a new *kind* of work, and the variant mix is unset **[ ]** anyway, so including them would
require inventing proportions. Revisit when a variant mix has a source.

## 2. Frame types

Chosen so that each entry exercises a **distinct work shape**, not to maximise coverage.

### GT06

| Type | Code | Work shape it exercises |
|---|---|---|
| `MSG_LOGIN` | `0x01` | **[V]** The only frame carrying the IMEI. Establishes the connection→device binding that every later frame depends on. |
| `MSG_GPS_LBS_1` | `0x12` | The bulk location path — longest body, most field extraction. |
| `MSG_STATUS` | `0x13` | Short frame. Exercises the regime where per-frame overhead dominates per-byte work. |

### JT/T 808

| Type | Code | Work shape it exercises |
|---|---|---|
| `MSG_TERMINAL_AUTH` | `0x0102` | Session establishment. |
| `MSG_LOCATION_REPORT` | `0x0200` | The bulk path. |
| `MSG_LOCATION_BATCH` | `0x0704` | Several location records in one frame — amortises header cost over N bodies, a per-frame shape none of the others has. |
| `MSG_LOCATION_REPORT_2` | `0x5501` | **[V]** The *only* way to exercise the type→header-length branch: this type reads a **1-byte** index where others read 2. A vendor extension (`0x55xx`), and the dispatch is keyed on type rather than on any version field. |

## 3. Input and output contract

### Input — **not a flat byte stream**

**[V]** `bench/PROTOCOL-EVIDENCE.md` Finding 3. `Gt06ProtocolDecoder.java:502` resolves every
non-login frame with `getDeviceSession(channel, remoteAddress)` and no id. **Non-login GT06 frames
contain no device identifier at all.** A flat stream cannot represent this workload even in
principle.

The stimulus is therefore a sequence of **(connection_id, byte_chunk)** pairs:

```
(conn, bytes) (conn, bytes) (conn, bytes) …
```

- `connection_id` stands in for the TCP connection. It is **transport metadata, not frame
  content** — the decoder may key state on it, and may not parse it out of the payload.
- A chunk is **not** frame-aligned. Frames may split across chunks and several may share one,
  because that is what a stream delivers and it is what forces the decoder to hold partial state.

### Output — canonical and diffable

A decoded record per frame, emitted **in input order**, serialised so two runs are comparable
with `diff`:

```
<conn_id> <protocol> <msg_type> <status> <field>=<value> …
```

- `status` ∈ `ok` | `crc_fail` | `malformed` | `resync` | `unsupported`
- Fields sorted by name; fixed-point integers only, **no floating point** — a reference result
  must not depend on FP rounding differing between Spike and the core.
- **Rejected frames still produce a record.** A decoder that silently drops malformed input is
  indistinguishable from one that mis-parses it.

## 4. Malformed and variant cases

**[D]** Required, not optional — `bench/README.md`. A benchmark of well-formed frames measures a
workload that does not exist.

| Class | What it forces |
|---|---|
| Truncated frame | Partial-state handling across chunk boundaries |
| Bad checksum | The validate-then-reject path, with full parse work already spent |
| Length-field disagreement | The `readerIndex + length exceeds writerIndex` failure Traccar hits in production |
| Garbage between frames | Resynchronisation — **[V]** the byte-at-a-time three-way scan |
| Unknown message type | The `unsupported` path |
| **Flag-lying frame** | **[ ]** bit 14 set, 2013 payload. **Assumption, not evidence** — see §8. |

Rates for every class: **[ ] unset.**

## 5. Resynchronisation model

**[V]** `Jt808FrameDecoder.java` resynchronises by scanning byte-at-a-time for any of three frame
starts, skipping one byte per miss. GT06 scans for `0x0D 0x0A`.

Garbage is injected **between** frames, never inside one — a corrupted frame is §4's business,
while resync is about the decoder's ability to find the next start.

- Resync rate: **[ ] unset.** `roadmap.md` names it *the discriminator* between Predictions A
  and B, so it is a swept axis, not a fixed value.
- Garbage-run length distribution: **[ ] unset.** Cost is per byte skipped, so mean run length
  scales resync cost linearly and must be declared separately from rate.

## 6. Detection strategy — **decided**

**[D]** `decisions/0007` and its amendment. Nothing here is open.

```
stateless   detect on every frame          ← THE reference result
cached      detect once per connection     ← declared second mode
delta       detection cost − lookup cost   ← the instrument
```

- The **stateless** figure is the denominator for platform speedup claims.
- **Workload characterisation is the stateless–cached range.** Neither endpoint is quoted alone;
  they bracket the dispatch term from opposite ends and neither is neutral.
- The cache is keyed on `connection_id`, never on a field parsed from the frame — **[V]** Finding
  3, and because a lying version flag makes an extracted ID garbage exactly when the cache matters.
- `detection_mode` is a mandatory manifest field on **every** result.

## 7. Size and rate

- Frame count per run: **[ ] unset.** Must be large enough that startup is negligible and small
  enough to run under Spike in reasonable time. To be set empirically once the decoder exists,
  then **frozen**.
- Connection count: **[ ] unset**, and **swept, not fixed** — `roadmap.md` Prediction C makes it
  the second discriminator. A single value would measure one point on a phase diagram and report
  it as the answer.
- Interleaving pattern: **[ ] unset.** At line rate connections interleave; a stimulus delivering
  each connection's frames contiguously measures a locality that does not exist.
- Frame length distribution: **[ ] unset.**
- Target rate: **not a benchmark parameter.** The benchmark counts instructions for a fixed input.
  Rate is a deployment property and belongs in Phase 4's interpretation, not here.

## 8. Provenance of every stimulus class

**[D]** `bench/README.md` rules 1, 2, 2a and `decisions/0004`.

| Class | Provenance | Evidence weight |
|---|---|---|
| Frame layouts, checksum, escaping | Published specs + Traccar at pinned `847edd2c` | **[V]** cited to line |
| Connection-keyed device identity | `Gt06ProtocolDecoder.java:502`, `:526` | **[V]** verified, unconditional |
| Header-length dispatch | `Jt808ProtocolDecoder.java:359-373` | **[V]** verified |
| Malformed-frame reality | Traccar open PRs and forum reports | Reported, not read from code |
| **Flag-lying behaviour** | A library README | **Weakest.** Not read from code by this project. |
| All rates and mixes | **none** | **[ ] unset — no source exists yet** |

**No captured operational data, ever.** Stimulus is generated from a seed; inputs are versioned as
**generator + seed**, never as a blob.

**The flag-lying assumption is load-bearing and under-evidenced.** It is why detection can't be a
table lookup, why the cached path needs revalidation, and half the reason the cache can't be
keyed on frame content. Before any result that depends on it is quoted, it needs either a source
in the `decisions/0006` class or an explicit statement that the benchmark *assumes* it. **It is
currently an assumption.** The GT06 half of the connection-keying requirement does not depend on
it and is verified independently.

---

## What this specification does not fix

Every **[ ]** above. They are collected here so they cannot be filled in by accident:

```
protocol mix (GT06 : JT808)      variant mix            resync rate
garbage-run length               flag-lying rate        malformed rates per class
frame count per run              connection count       interleaving pattern
frame length distribution
```

**None has a source.** Each is either swept (resync rate, connection count — both named
discriminators) or must be declared in the manifest as a stated assumption. A result quoting any
of them as settled is quoting an invented number.

---

# Amendment — 2026-09-27: what writing the generator found unset

The specification stands. Writing `bench/stimulus` against it found five more things that shape
the stimulus and that the list above does not name. They are unset in the same sense, with no
source, and the generator requires each one to be stated:

| Parameter | Why it is a parameter | In `bench/stimulus` |
|---|---|---|
| JT808 header-format mix, 2013 : 2019 | §1 puts both formats in scope, and gives no proportion. | `jt808.version_weights` |
| Message-type mix, per protocol | §2 lists the types, and gives no proportion. | `gt06.type_weights`, `jt808.type_weights` |
| Chunk-size distribution | §3 says chunks are not frame-aligned, and gives no size. | `chunk_size` |
| Garbage alphabet | §5 gives a rate and a run length, not the bytes. Garbage that contains a frame-start byte makes a false start, which is different work from skipping. | `garbage.alphabet` |
| Field-value distributions | They decide how often a JT808 byte must be escaped, so the destuffing work in Prediction B depends on them. | rule R6; each manifest reports the escape pairs |

"Frame length distribution" in the list above turns out to be several knobs: the type mix, the
records per batch, the additional-information items per location, and the length of an
authentication code.

The generator's structural choices are listed as rules R1 to R17 in `bench/stimulus/README.md`.
Each is an assumption, and none fills a `[ ]` above.

§3's `(connection_id, byte_chunk)` pairs now have a concrete form, `stimulus.bin`, specified in
the same README.

Two facts found while laying out the frames bear on §4. They are recorded in
`bench/PROTOCOL-EVIDENCE.md`:

- **Finding 4.** Neither Traccar decoder verifies the checksum of a frame it receives. The
  `crc_fail` status in §3 is the benchmark decoder conforming to the GT06 vendor document, not
  doing what the de facto decoder does.
- **Finding 7.** Traccar chooses the GT06 variant from the length field, so a length fault can
  change which decoder runs.

# Amendment — 2026-09-28: §7's frame count, sized for RTL simulation too

§7 says the frame count must be "small enough to run under Spike in reasonable time". `decisions/0010`,
as amended, adds RTL simulation. The frozen configurations include one small enough to run on the
core in RTL simulation in Phase 4, sized from a measured throughput.

# Amendment — 2026-09-29: §5 records Traccar's scans; the benchmark decoder's rule is `0011`

§5's two scans are Traccar's, and they are verified as Traccar's. They are not a rule for the
benchmark decoder. `decisions/0011` sets that rule.

- **JT808:** the decoder keeps the three-way scan.
- **GT06:** the decoder searches for the start bits `78 78`. Traccar realigns on the next `0D 0A`,
  and so loses the frame that follows garbage (`PROTOCOL-EVIDENCE` Finding 8).
- **After a broken frame:** the decoder looks again from the frame's second byte, so a broken frame
  costs only its own bytes.

Two consequences for this specification:

- **§5's resync rate is not the garbage rate alone.** Every candidate that fails framing is scanned
  a second time, so faults make resync work too. A sweep over resync rate must hold §4's fault rates
  fixed, or report them beside it.
- **§4's length-field disagreement never becomes a frame.** Its bytes are reported in a `resync`
  record, like a truncated frame's, so §3's `malformed` status is not produced by any fault the
  generator makes today.

# Amendment — 2026-09-29: §3's records, from `decisions/0012`

§3's record shape stands. `decisions/0012` fixes what goes in it, and why. This section is the
contract that the reference decoder and the `0010` check both implement.

**Records.**
- A frame produces one record. The exception is a `0x0704` batch whose status is `ok`, which
  produces one record per location it carries, each with `record=<i>` counting from 1. A batch with
  no location produces one record, without `record`.
- A run of bytes outside every frame produces one `resync` record (`0011`).
- Each response the decoder sends produces one record, with status **`sent`**. It comes immediately
  after the record or records of the frame it answers.

**Order.** The canonical order is by connection, then by stream order within each connection. It is
not the order of input: how records from different connections interleave depends on where the
chunks cut the streams, which `0011` rule 8 keeps out of the result.

**Text.** `<conn> <protocol> <type> <status> <field>=<value> …`
- `protocol` is `gt06` or `jt808`.
- `type` is lowercase hex, two digits for GT06 and four for JT808, `sentence` for a sentence, and `-`
  for a resync run. A response's type is its own: `0x01`, `0x13` or `0x8001`.
- Fields are sorted by name. Values are decimal integers, with a leading `-` when negative. Three
  are not: `device` is the hex digits of the IMEI or terminal ID, as the login or header carries
  them, and `bytes` and `text` are lowercase hex.

**Every record about received bytes** carries `at`, the offset of its first byte in its
connection's stream, and `len`, its length on the wire. `crc_fail`, `malformed`, `unsupported` and
`resync` records carry nothing else.

**`malformed`** is a frame that passes framing and its check, but where the type's fixed fields do
not fit the content, a BCD digit is above 9, a date or time does not exist (or a GT06 year byte is
above 99), or a latitude is beyond 90° or a longitude beyond 180°.

## Shared quantities

A quantity that more than one frame type carries has one name and one exact unit everywhere.

| Field | Unit | Width |
|---|---|---|
| `time` | seconds since 1970-01-01 00:00:00 UTC | u32 |
| `lat`, `lon` | 1/9,000,000 degree, north and east positive | i32 |
| `speed` | metres per hour | u32 |
| `course` | degrees | u16 |
| `valid` | 0 or 1: the position is fixed | — |
| `satellites` | count | u8 |
| `altitude` | metres | i16 |
| `odometer` | metres | u64 |

Every other field is the frame's own unsigned integer, and its meaning is given by its record's
protocol and type.

## GT06 — from the vendor document v1.8.1

Every `ok` record carries `serial`, and `device` once the connection has logged in.

| Type | Field | Source | From the frame |
|---|---|---|---|
| `0x01` login | `device` | Terminal ID, §5.1.1.4 | the last 15 of its 16 BCD digits: the IMEI |
| `0x12` location | `time` | Date Time, §5.2.1.4 | six binary bytes, YY MM DD hh mm ss, read as UTC **[assumption]** |
| | `satellites` | §5.2.1.5 | the low nibble |
| | `lat`, `lon` | §5.2.1.6, §5.2.1.7 | ×5. `lat` is negative when Course Status bit 10 is clear, `lon` when bit 11 is set (§5.2.1.9) |
| | `speed` | §5.2.1.8 | km/h ×1,000 |
| | `course` | Course Status bits 0-9 | degrees |
| | `valid` | Course Status bit 12 | |
| | `differential` | Course Status bit 13 | 1 is differential, 0 real-time |
| | `mcc`, `mnc`, `lac`, `cid` | §5.2.1.10 to §5.2.1.13 | as carried: 2, 1, 2 and 3 bytes |
| `0x13` heartbeat | `info` | Terminal Information, §5.4.1.4 | as carried |
| | `voltage`, `gsm` | §5.4.1.5, §5.4.1.6 | as carried: levels, not units |
| | `alarm`, `language` | Alarm/Language, §5.4.1.7 | the former byte, and the latter |

## JT808 — from Traccar at `847edd2c`

Every `ok` binary record carries `device` (the header's terminal ID, as hex digits), `header` (`2013`
or `2019`, the layout that detection found) and `index`. Line numbers are
`Jt808ProtocolDecoder.java`'s unless marked Jt600.

| Type | Field | Source | From the frame |
|---|---|---|---|
| `0x0102` | none | `:445-448` | Traccar reads nothing of the body |
| `0x0200` | `alarm` | `:756` | as carried, 4 bytes |
| | `status` | `:709` | as carried, 4 bytes |
| | `valid` | status bit 1, `:723` | |
| | `lat`, `lon` | `:725-737` | ×9. Negative when status bit 2 (`lat`) or bit 3 (`lon`) is set |
| | `altitude` | `:760` | metres, signed |
| | `speed` | `:761` | tenths of km/h ×100 |
| | `course` | `:762` | degrees |
| | `time` | `:763`, `:259-268` | BCD YYMMDDhhmmss, read as GMT+8 **[assumption]** |
| | `odometer` | item `0x01`, `:791-793` | tenths of km ×100 |
| | `fuel` | item `0x02` | as carried, 2 bytes |
| | `inputs` | item `0x25` | as carried, 4 bytes |
| | `adc1`, `adc2` | item `0x2B` | as carried, 2 bytes each |
| | `rssi` | item `0x30` | as carried |
| | `satellites` | item `0x31` | count |
| `0x0704` | per location: `0x0200`'s fields, `archive` and `record` | `:1634-1655` | `archive` is the batch's type byte, as carried |
| `0x5501` | `time` | Jt600 `:97-103` | BCD DDMMYY hhmmss, read as UTC **[assumption]** |
| | `lat`, `lon` | Jt600 `:105-112`, `:50-54` | BCD DD(D)MMmmmm: degrees ×9,000,000, plus ten-thousandths of a minute ×15. Negative when flags bit 1 (`lat`) or bit 2 (`lon`) is clear |
| | `valid` | flags bit 0, Jt600 `:110` | the frame's own bit. Traccar then sets validity from the type instead (`:1527`) |
| | `speed` | Jt600 `:114` | BCD knots ×1,852 |
| | `course` | Jt600 `:115` | ×2, degrees |
| | `rssi`, `satellites` | `:1529`, `:1530` | as carried |
| | `odometer` | `:1531` | km ×1,000 |
| | `battery`, `cid`, `lac`, `product`, `status`, `alarm` | `:1533-1548` | as carried |
| sentence | `text` | `:345-357`, `:653-663` | the characters between the parentheses |
| | `device` | | the device of the connection's most recent binary frame |

`0x0200` items other than the six above are skipped by their length. The 20-byte vendor form that
Traccar reads instead of items (`:765-775`) is not decoded; rule R11 keeps it out of the stimulus.

## Responses

| Answers | `type` | `bytes` | Source |
|---|---|---|---|
| GT06 `0x01`, `0x13` | the frame's | `78 78 05`, protocol number, serial, CRC-ITU over length to serial, `0D 0A` | the document, §5.1.2 and §5.4.2 |
| JT808 `0x0102`, `0x0200`, `0x0704` | `0x8001` | the frame's delimiter; `80 01`; attribute 5, with bit 14 in the 2019 layout; the frame's version byte in the 2019 layout; its terminal ID; index `00 00`; its index, its type, and `00`; the XOR of everything from `80` to here; the delimiter. All but the two delimiters escaped in the delimiter's alphabet | `Jt808ProtocolDecoder.java:126-161`, `Jt808FrameEncoder.java:25-49` |

Only a frame whose status is `ok`, and whose connection has a device, gets a response.

**Out of scope in draft 1, and why:**
- **A registry of provisioned devices.** No source gives its contents or its size. The roadmap's
  "identifier lookup" is, here, the connection-to-device binding.
- **Traccar's other responses:** to a GT06 `0x12` or an unknown GT06 type, which the document gives
  none for; to a frame that fails its check, or is malformed; to a `0x5501` with attribute bit 15;
  and to a `BASE,2` sentence, which carries Traccar's wall clock.

# Amendment — 2026-09-30: §3's input carries each connection's protocol; the harness is `decisions/0014`

§3's input stands. `decisions/0014` adds one fact to it, and fixes the harness around the decoder.

**Input.** `stimulus.bin` version 2 has a table between its header and its first chunk: one byte for
each connection, 1 for GT06 and 2 for JT808. The table stands in for the port that each connection
arrived on. Like the connection id, it is transport metadata. The decoder chooses a connection's
framing from it, and may not parse a protocol out of the payload. The layout is in `0014`,
section 2.

**The window.** The harness counts retired instructions in 64 bits, over these and nothing else:
- the walk over the chunks, and each chunk's dispatch to its connection's protocol;
- everything that `0011` and `0012` require of the decoder;
- the stores that append each record's value to a buffer;
- the end of the input, which ends every connection's stream (`0011` rule 7).

The check of the file and the setup of each connection come before the window. Sorting, formatting
and printing come after it.

**Output.** The records print after the window, in canonical order, through Spike's syscall proxy,
one buffer at a time. The last line repeats the number of records. The stimulus is linked into the
decoder's image as data, never compiled in (`bench/README.md`).
