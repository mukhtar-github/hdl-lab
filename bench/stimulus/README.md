# bench/stimulus — the stimulus generator

**Benchmark type: specification-derived reconstruction.** Recorded on the day it was written,
2026-09-27, per `bench/README.md` rule 3 and `decisions/0004`. Every frame is laid out from the GT06
vendor document and from Traccar's decoders, both pinned in `reference/README.md`. Every field
value and identifier is drawn from a seed. No captured operational data, no forum hex, no real
IMEI.

This is the second step of `decisions/0004`'s chain:

```
protocol specification → stimulus generator → reference decoder → expected output → Spike reference
                         ^^^^^^^^^^^^^^^^^^
```

## Run it

```bash
make -C bench/stimulus                          # the coverage stimulus, then check.py on it
make -C bench/stimulus test                     # the unit tests
make -C bench/stimulus PARAMS=<file> SEED=<n>   # any parameter file, any seed
```

Each run writes three files to `build/<parameter file>-<seed>/`:

| File | What it holds |
|---|---|
| `stimulus.bin` | The decoder's input: each connection's protocol, then `(connection, chunk)` pairs in delivery order (SPEC §3). Format below. |
| `intent.jsonl` | What the generator put where: each connection, frame and garbage run, with its offset in its connection's byte stream, its fields, and its fault if it has one. |
| `manifest.json` | The seed, every parameter and rule, the generator's commit and source hashes, the output hashes, and what the run actually contains. |

A stimulus is versioned as generator + parameters + seed, and never committed (SPEC §8).

**`intent.jsonl` is not the expected output.** It records what was generated. What a decoder
should *print* for a truncated frame, or for the frame after one, depends on how it resynchronises,
and that is the reference decoder's design, fixed by `decisions/0011`. What each record contains,
and what the decoder sends back, is fixed by `decisions/0012`. In `0004`'s chain the reference
decoder produces the expected output. The intent log is what that output will be checked
against.

## Every parameter is an assumption

`bench/SPEC.md` lists the numbers that shape the traffic as unset, with no source: protocol mix,
malformed rates, resync rate, connection count and the rest. So a parameter file must state **all**
of them. Nothing has a default, and a missing key is an error that names it. Every manifest records
the whole file under `"status_of_every_parameter": "assumption"`.

| Parameter | What it sets | SPEC |
|---|---|---|
| `connections`, `frames`, `assignment` | Connections; frames per run; how frames are dealt to connections, `equal` or `uniform` | §7 |
| `protocol_weights` | GT06 : JT808, per connection | protocol mix |
| `gt06.type_weights` | location `0x12` : status `0x13` | §2 |
| `jt808.delimiter_weights`, `jt808.version_weights` | `7E` : `E7`, and 2013 : 2019, per connection | §1 |
| `jt808.type_weights` | location `0x0200` : batch `0x0704` : location 2 `0x5501` : `(` sentence | §1, §2 |
| `jt808.batch_records`, `jt808.location_items`, `jt808.auth_code_length` | `[lo, hi]`: records per batch, additional-information items per location, characters in an authentication code | frame length |
| `faults_ppm` | The probability of each §4 fault, per frame it can apply to, in parts per million | §4 |
| `garbage` | The probability of a garbage run between two frames, its length, and its alphabet, `any` or `no_sync` | §5 |
| `chunk_size` | `[lo, hi]` bytes per chunk | §3 |
| `interleave` | `sequential`, `round_robin` or `uniform` | §7 |

`params/coverage.json` is the only parameter file here. It is for tests: every frame type, framing
mode, header format, fault and garbage run occurs in a run small enough to read. **No result may be
quoted from a stimulus made with it.** Choosing a real benchmark configuration is a separate step,
and resync rate and connection count are to be swept rather than set (roadmap, Predictions A to C).

## Where each frame comes from

"Doc" is the GT06 vendor document v1.8.1, with PDF page numbers. Line numbers are Traccar's at the
pinned commit.

| Frame | Layout from | Anchored by |
|---|---|---|
| GT06 login `0x01` | doc §5.1.1, p.11; `Gt06ProtocolDecoder.java:521-526` | the doc's example, p.12, byte for byte |
| GT06 location `0x12` | doc §5.2.1, p.13-16; `decodeGps` :301-351, `decodeLbs` :353-410 | the doc's example, p.16, with the byte its own table corrects (`PROTOCOL-EVIDENCE` Finding 5) |
| GT06 status `0x13` | doc §5.4.1, p.24-25, the field table; `Gt06ProtocolDecoder.java:896-998` | no example that verifies. The p.26 example's length and CRC are for a 3-byte content (Finding 5), and the encoder reproduces that frame too. |
| JT808 header, check, escaping | `Jt808ProtocolDecoder.java:359-373` and :146; `Jt808FrameDecoder.java:61-91` | Traccar's escaping test vector; header lengths against Finding 2's formula |
| JT808 authentication `0x0102` | the 2013 body, an authentication code (rule R10) | none |
| JT808 location `0x0200` | `decodeLocation` :748-786; `decodeCoordinates` :707-739; items :791-831 | none |
| JT808 batch `0x0704` | `decodeLocationBatch` :1634-1655 | none |
| JT808 location 2 `0x5501` | `Jt600ProtocolDecoder.decodeBinaryLocation` :95-116, then :1521-1548 | none |
| `(` sentence | `Jt808FrameDecoder.java:49-54`; `Jt808ProtocolDecoder.java:345-357` | none |

**No JT/T 808 standard is pinned.** Every JT808 layout here is Traccar's reading, so a JT808 frame
is right if Traccar would read it as intended. The one check on that reading from outside it is
Finding 6's run over Traccar's own test inputs
([`20260927T062216Z-protocol-checksums`](../../docs/results/20260927T062216Z-protocol-checksums/)).
The header-length formula fits the body length of 105 of those 114 real frames, and the XOR span
verifies 103. A wrong reading would fit almost none.

## Rules

These are choices the generator makes that are not numbers in the parameter file. Each one is an
assumption. Their exact text is `RULES` in `traffic.py`, and every manifest carries it. The reasons
are here.

| | Rule | Why |
|---|---|---|
| R1 | One protocol and one device per connection | Device identity is carried by the connection (Finding 3). A connection that changed device could not be decoded at all. |
| R2 | The session frame comes first and is never faulty | GT06 drops every non-login frame that arrives before a session exists (`Gt06ProtocolDecoder.java:501-505`). A faulty login orphans its whole connection. That is real, and it is deferred so that the other classes can be seen cleanly first. |
| R3 | One JT808 delimiter and one format per connection | A device speaks one dialect. `(` sentences appear beside binary frames in Traccar's tests. |
| R4 | At most one fault per frame, each rate per eligible frame | So that a rate means one thing. Faults that combine are a later question. |
| R5 | Device clocks start in 2026 and step 1-120 s | Only the encoding of a time reaches the decoder. |
| R6 | Field values uniform over their sourced ranges | There is no source for real distributions. How often a JT808 byte needs escaping follows from this, and destuffing work depends on it (Prediction B), so the manifest reports it. |
| R7 | Counters: GT06 from 1, JT808 from 0 | GT06 per doc §4.5. JT808 has no pinned source. |
| R8 | The 2019 version byte is 1 | Traccar reads it and never interprets it. |
| R9 | The `E7` alphabet escapes `0x3D` | It is the inverse of the decoder's table. A raw `0x3D` would decode the same. Traccar's own encoder escapes it too (`Jt808FrameEncoder.java:33-35`, `PROTOCOL-EVIDENCE` Finding 9). |
| R10 | The 2013 authentication body, in both formats | Traccar never reads it. The 2019 body has no pinned source. |
| R11 | No location whose items Traccar would read as its 20-byte vendor format | Neither Traccar nor the benchmark decoder may be handed a frame that the other reads differently. |
| R12 | The ranges no source gives | Stated so they can be found, not because they are right. |
| R13 | No trailing items on `0x5501` | Its items are vendor-specific. |
| R14 | The shape of a `(` sentence | The decoder only distinguishes whether a sentence contains `BASE,2`. |
| R15 | How each fault is made | So that the fault is the only thing wrong with the frame: a length that disagrees still has a valid check, and a bad check has the right length. |
| R16 | Garbage only between frames; what `no_sync` excludes | SPEC §5. `no_sync` excludes the bytes each framer treats as a boundary, so garbage never looks like a frame start. |
| R17 | Chunks cut without regard to frames | SPEC §3: a stream does not deliver whole frames. |

## `stimulus.bin`

Integers are little-endian, RV32's byte order. Every header starts on a 4-byte boundary, so the
decoder reads one with a single `lw`, and the harness costs one load per chunk.

```
header   "TFDS" | u16 format version (2) | u16 header bytes (20)
         | u32 chunks | u32 connections | u32 payload bytes (chunk data, no padding)
table    u8 protocol per connection: 1 GT06, 2 JT808 | zeros to a multiple of 4
chunk    u16 length | u16 connection | length bytes | zeros to a multiple of 4
```

The table stands in for the port that each connection arrived on, so the decoder knows a
connection's protocol before its first byte (`decisions/0011`). This is version 2, from
`decisions/0014`. Version 1 had no table, and `container.unpack` refuses it.

It reaches the decoder as data the compiler cannot see. It is linked into the decoder's image in a
section of its own, never compiled in as a C array (`bench/README`, `decisions/0014`).

## Checking

`check.py` rebuilds each connection's byte stream from `stimulus.bin`. Then it walks `intent.jsonl`
over the stream, parsing every frame back and comparing it with its declared fields, header values
and fault. It also checks each connection's protocol in the table, every garbage run against its
alphabet, the session-first rule, chunk sizes, the manifest's hashes, and that no identifier can be
a real device's: every IMEI must fail its Luhn check digit. It imports none of the encoders. Frames are parsed in the order
Traccar reads them, and GT06 CRCs go through `bench/rv32/crc_oracle.py`, a different path from
`gt06.py`'s table.

**Its limit:** the same person read the same sources for the encoder and for the checker. When
they agree, the two are consistent with each other, not necessarily right. What ties them to the
sources is the anchors in `test_stimulus.py`.

`test_stimulus.py` has five groups:

- **Anchors.** The GT06 vendor examples byte for byte, two CRC paths agreeing, Traccar's escaping
  vector, Traccar's Luhn digit, and 50 outputs of the SplitMix64 reference implementation.
- **Layouts.** Header lengths, STANDARD lengths, and rule R11 over a large run.
- **Parameters.** Every key is required, unknown keys are refused, and so is any batch whose
  length a 10-bit field cannot state.
- **Container.** A two-connection `stimulus.bin`, written out by hand from `decisions/0014`'s
  layout, byte for byte. Version 1, a protocol code of 0 or 3, non-zero padding and a table that
  runs past the end are refused.
- **Streams.** Same seed, same bytes. The coverage run contains every class. `check.py` passes
  the coverage run, and fails each of 14 corruptions for its own reason.

## What it does not do

- **Produce the expected output.** See above.
- **Vary the GT06 variant.** Draft 1 is `STANDARD` only (SPEC §1).
- **Model arrival times.** A stimulus is an order, not a schedule. Rate is not a benchmark
  parameter (SPEC §7).
- **Know anything about real traffic.** Every rate and range is an assumption, and every manifest
  says so.
