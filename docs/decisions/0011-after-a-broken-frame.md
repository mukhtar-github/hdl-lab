# 0011 — After a broken frame, the reference decoder loses nothing else

- **Date:** 2026-09-29
- **Status:** Accepted
- **Phase:** 0, binding on the reference decoder and on the expected output it produces

## Context

The reference decoder is next in `0004`'s chain, and Phase 0 cannot close without it (`0010`).
`bench/stimulus/README.md` records the question it has to answer first: `intent.jsonl` says what
the generator put where, but not what a decoder prints for a broken frame, or for the frame after
one. That depends on where the decoder looks for the next frame, and SPEC does not fix it.

- **§3** lists the statuses, `ok`, `crc_fail`, `malformed`, `resync` and `unsupported`, and says a
  rejected frame still produces a record.
- **§4** lists the fault classes.
- **§5** records how Traccar resynchronises, marked verified. It does not say that the benchmark
  decoder must do the same.

The generator breaks frames in five ways (rule R15). A truncated frame keeps a prefix, and the next
frame follows it directly. A length disagreement and a bad checksum each leave the rest of the frame
intact. An unknown type is otherwise valid. A flag-lying frame sets bit 14 over a 2013 header.
Garbage appears only between frames (R16), and chunks are cut with no regard to frames (R17).

**What the de facto decoder does is now measured.** `PROTOCOL-EVIDENCE` Finding 8, from a port of
Traccar's framers that reproduces their own tests:

- After a truncated JT808 frame, Traccar's framer pairs every later delimiter wrongly. It loses
  whole frames until another missing delimiter or a stray byte re-pairs them, or until the
  connection ends.
- After garbage or a truncated fragment, its GT06 framer loses the next whole frame, because nothing
  in it looks for `78 78`.
- A GT06 frame whose length disagrees comes through whole, and reaches variant selection with the
  wrong length (Finding 7).

**`0010` requires a check that compares the decoder's records with the intent log.** So whatever
the decoder does after a fault, the check has to predict it from `intent.jsonl`.

**One constraint on how this is chosen.** Resync is the discriminator between Predictions A and B,
so the rule decides how much resync work the benchmark contains. As with `0007` and `0009`, it may
not be chosen for its effect on either prediction. That effect is stated under *Consequences*,
because it was not a criterion.

## Options considered

1. **Do what Traccar's framers do.**
   - *For:* it is the de facto decoder, and SPEC §5 describes its scans. This project already takes
     Traccar's reading of JT808 as the reference, since no JT/T 808 standard is pinned.
   - *Against, and why it lost:* it loses whole frames after broken ones (Finding 8). On JT808
     the loss is not local. Its size depends on how many frames the connection carries after the
     fault, and on stray bytes in field values (rule R6).
     - A fault's cost would then vary with frames per connection. Prediction C sweeps connection
       count, so fault rates and the connection count would interact through framing, not through
       anything the predictions are about.
     - The `0010` check would have to reproduce Traccar's pairing to know which frames are lost.
       That makes the check a second copy of the decoder, the arrangement `bench/stimulus/README`'s
       "Its limit" already warns about.
     - Nothing about Traccar's framing is a protocol requirement. The benchmark already departs
       from Traccar where the GT06 vendor document asks it to: it checks checksums (Finding 4).
2. **Skip a broken frame by its own length.** Resume where the broken frame's framing says it ends.
   - *For:* the cheapest rule, with no bytes scanned twice.
   - *Against:* after a fault, a frame's own framing is exactly what cannot be trusted. A
     truncated frame's declared end lies inside the next frame, so the next frame is lost: the
     GT06 half of Finding 8, reached by another route.
3. **A broken frame costs only its own bytes.** When a candidate frame fails its framing test,
   look again from the byte after the one it started at.
   - *For:* a whole frame is decoded whatever precedes it, with two exceptions, both stated below.
     So a fault's cost is local. The check can predict the records from `intent.jsonl` without
     modelling framing.
   - *Against:* it scans a broken frame's bytes a second time. It must hold up to one maximal frame
     of look-ahead per connection. On GT06 it departs from Traccar's resynchronisation.
4. **Split JT808 at every delimiter, as HDLC does with its flags.** Every delimiter both closes one
   frame and may open the next.
   - *For:* it also recovers from truncation. It also keeps the frame after a JT808 frame that lost
     exactly its closing delimiter, the one case option 3 loses.
   - *Against:* garbage between two frames becomes a candidate frame, to be framed, rejected and
     scanned again, where option 3 skips it once with the scan SPEC §5 verified. It doubles the
     work on every garbage byte to rescue one sub-case of one fault class. No pinned source frames
     JT808 this way.

## Decision

**Option 3.** The rules below apply to each connection's byte stream on its own, and in both
detection modes (`0007`).

**The decoder knows each connection's protocol before the connection's first byte,** as Traccar does. Traccar runs one
server per protocol (`Gt06Protocol.java:34-37`, `Jt808Protocol.java:52-56`). `stimulus.bin` does
not carry the protocol yet. How it will is part of the next decision, on the input contract. If the
decoder has to detect the protocol instead, its search gains the other protocol's start bytes, and
this record is revisited.

1. **Search.** Skip bytes one at a time until a frame start:
   - GT06: `78 78`, the vendor document's start bits (§4.1, p.9).
   - JT808: `(`, `7E` or `E7`, the three-way scan of SPEC §5 (`Jt808FrameDecoder.java:37`).
     Rule R3 gives each connection one delimiter, but a stateless decoder decides the framing per
     frame (`0007`), so it looks for all three.
2. **Candidate.** A candidate runs from the start to where its framing ends it:
   - GT06: length byte `L` + 5 bytes;
   - a JT808 binary frame: the next byte equal to its opening delimiter;
   - a sentence: the next `)`.

   The decoder abandons a candidate as soon as it can no longer pass rule 3, so its look-ahead is
   bounded. A GT06 candidate has at most 260 bytes. A JT808 binary candidate has at most 2,084: a 17-byte header, a 1,023-byte body and a
   check byte, every one escaped, plus two delimiters.
3. **Framing test.** A candidate is a frame when its framing holds:
   - **GT06:** `L` is at least 5, and `0D 0A` ends the candidate.
   - **JT808 binary:** every escape introducer is followed by `01` or `02`. After unescaping, the
     length is header + body length + 1, under a header layout that detection accepts for it
     (`0007`). So a flag-lying frame whose true layout is found is a frame.
   - **Sentence:** only printable ASCII other than parentheses lies between `(` and `)`. Traccar
     reads a sentence as ASCII text (`Jt808ProtocolDecoder.java:345-357`).

   **The checksum is not part of the framing test.**
4. **A frame is taken whole, and produces one record.**
   - A failed check (GT06 CRC-ITU, JT808 XOR) makes it `crc_fail`.
   - Otherwise its content decides between `ok`, `unsupported` and `malformed`.

   The search resumes at the byte after the frame.
5. **A candidate that fails its framing test is not a frame.** The search resumes at the byte after
   the candidate's first byte.
6. **Bytes outside every frame are reported.** Each maximal run of them produces one `resync`
   record, in input order, carrying its length.
7. **A connection's stream can end with a candidate still waiting.** That candidate fails rule 3,
   and rules 5 and 6 apply.
8. **Chunking changes nothing.** The records depend only on each connection's byte stream, never on
   where the chunks cut it.

What the generator's faults become:

| In `intent.jsonl` | Record | The search resumes |
|---|---|---|
| a frame with no fault | `ok` | after it |
| `bad_checksum` | `crc_fail` | after it |
| `unknown_type` | `unsupported` | after it |
| `flag_lying` | a frame. What its record says is the output decision's | after it |
| `truncated` | none of its own. Its bytes fall inside a `resync` record | at its second byte |
| `length_disagreement` | the same as `truncated` | at its second byte |
| a garbage run | inside a `resync` record | the search continues |

**The guarantee, and its two exceptions.** Every whole frame decodes whatever comes before it,
except in two cases:

- **(a) A candidate that passes the framing test by coincidence** and overlaps a whole frame. On
  GT06 that needs `0D 0A` exactly where a false or wrong length points. On JT808 it needs a
  delimiter exactly where a false header's length points, with clean escapes in between.
- **(b) A JT808 frame truncated by exactly its closing delimiter**, and followed directly by a binary
  frame. Nothing distinguishes it from a whole frame whose closing delimiter is the next frame's
  opening one. It decodes as if whole, the next frame is lost, and the one after that is not.
  Under rule R15, this is a truncation that drops a single byte.

`intent.jsonl` identifies every case of (b). Case (a) shows up only as a mismatch against the
intent log. The check must report it as that, and never absorb it.

## Consequences

**Made easier.**
- **The `0010` check compares record by record.** Every whole frame in the intent log has its own
  record, apart from (a) and (b). Every broken frame and garbage run lies inside a `resync` record.
- **Faults are local.** A fault's cost no longer depends on how many frames follow it on its
  connection. The connection-count sweep and the fault rates do not interact through framing.
- **Finding 7's question is answered for this decoder: the two are independent.**
  - Draft 1 decodes STANDARD only (SPEC §1), so no length selects a variant.
  - A GT06 frame whose length disagrees fails the framing test before anything reads its protocol
    number. The one exception is a coincidence of kind (a).

**Made harder, or given up.**
- **Resync work now comes from faults as well as from garbage.** A candidate that fails the framing
  test costs its look-ahead and a second byte-at-a-time scan of its bytes. So the roadmap's resync
  rate is not the garbage rate alone. A sweep over resync rate (`0010`) must either hold the fault
  rates fixed or report them beside it.
- **Per-connection state carries across chunks.** It includes up to one maximal candidate of
  look-ahead: 260 bytes for GT06 and 2,084 for JT808. The core's memory will have to hold that for
  every open connection.
- **A truncated frame and a length disagreement look the same in the output.** The decoder cannot
  tell them apart without guessing, and its records do not pretend to.
- **`malformed` does not occur for any fault the generator makes today.** Each fault is the only
  thing wrong with its frame (R15). The two that break framing are reported as bytes outside a
  frame. `malformed` is left for a frame whose framing and check hold, but whose content cannot be
  decoded as its type.
- **Declared departures from Traccar.** SPEC is amended to say so, and to point here.
  - GT06 searches for `78 78` rather than resynchronising on `0D 0A`.
  - JT808 keeps Traccar's three-way scan, but not its pairing after a broken frame.
  - A GT06 frame whose length disagrees is not decoded.
  - `Jt808FrameDecoder.java:53`'s sentence length is not reproduced.
- **Both detection modes produce the same records,** except possibly in case (a). They may differ
  in work: a cached decoder can search for its connection's one delimiter instead of three.

**Effect on the predictions.** After a fault this rule does more work of both kinds than Traccar
does. It scans a broken frame's bytes again, which is Prediction A's term. It also decodes frames
that Traccar loses, running their CRC or their destuffing, which is B's. Which grows more cannot be
known before measurement, and the choice would have been the same either way.

**Revisit if:**
- a pinned JT/T 808 standard specifies how a receiver frames;
- a source shows real streams in which frames lose exactly their closing delimiter, often enough
  to make (b) matter;
- the look-ahead bound does not fit the core's memory.

## Predictions

Testable when the reference decoder runs on the coverage stimulus (`params/coverage.json`, seed 1).

1. **Whole frames.** Every frame that `intent.jsonl` lists without a fault gets its own `ok` record,
   except the frames lost to case (b). Case (a) does not occur.
2. **Broken frames and garbage.** Every broken frame and every garbage run lies inside a `resync`
   record. No `malformed` record appears.
3. **Chunking.** Cutting the same connection streams into different chunks changes no record.
