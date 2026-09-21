# Telematics Frame Decoder Benchmark — specification

- **Version:** draft 1 — **frozen before the reference decoder is written**, per `decisions/0004`
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
