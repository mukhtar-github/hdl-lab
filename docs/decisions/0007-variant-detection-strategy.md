# 0007 — How does the reference decoder carry variant and version state?

- **Date:** 2026-09-21
- **Status:** Accepted
- **Phase:** 0

## Context

`bench/PROTOCOL-EVIDENCE.md` establishes from Traccar's source that decoding a frame in this
family requires resolving, per frame, at minimum:

- which of 3 JT808 framing modes applies (`(`, `0x7e`, `0xe7`) — and hence which of 2 escape
  alphabets to destuff with
- whether the JT808 version byte is present (`attribute` bit 14), which also resizes the ID field
- which of 16 GT06 variants is speaking, tested at 35 separate branch sites

None of that is free, and **where that cost is paid is an architectural choice, not an
implementation detail.** It belongs here rather than buried in benchmark code, because it may
move the profile more than any accelerator the project could later build.

The trigger for writing this down: the detection key is not trustworthy. Vendors are reported to
ship 2013-format payloads with the version bit set, so a decoder that believes the flag will
mis-parse. If the flag cannot be trusted, dispatch stops being a table lookup and becomes
*detection* — parse speculatively, validate, fall back on failure. That is among the most
expensive control-flow shapes a pipeline can face, and it is the difference between the two
options below being a minor and a major decision.

<!-- NOTE: the "vendors set the flag wrongly" claim comes from a library README, not from code
     this project has read. It is NOT in the same evidence class as PROTOCOL-EVIDENCE.md.
     Before this decision is accepted, that claim needs either a source in the reading-discipline
     class of decisions/0006, or explicit marking as an assumption the benchmark makes. -->

## Options considered

1. **Stateless — detect per frame.**
   Every frame is self-describing; the decoder reads flags, validates, and dispatches with no
   memory of what came before.
   *For:* trivially reproducible, no session model, no cache-warming effects in the measurement,
   and it is the honest worst case. *Against:* pays detection on every single frame, which may
   dominate the profile and overstate the dispatch cost relative to a deployed system.

2. **Stateful — cache the detected variant per device or connection.**
   Detect once, remember, and revalidate only on parse failure.
   *For:* closer to what a deployed decoder does; isolates steady-state per-byte cost.
   *Against:* introduces a session model and a cache into the benchmark, so results depend on
   connection count and frame-per-connection distribution — two more mandatory manifest
   parameters. A warm cache can hide exactly the dispatch cost Prediction A is about.

3. **Both, as a declared benchmark axis.**
   Implement the decoder with detection behind one interface and run the benchmark in both modes,
   reporting two numbers.
   *For:* the difference between them *is* the measurement of dispatch cost, which is the
   quantity Prediction A actually disputes. Refuses to guess. *Against:* every result manifest
   carries a mode field.
   <!-- This option originally read "roughly doubles reference-decoder work". That estimate was
        wrong and is corrected here rather than quietly dropped: detection sits behind one
        interface and the decoder body is shared, so the second mode is a session map plus a
        revalidate-on-failure path — call it 15%, not 100%. The bad estimate would have argued
        against the option that was chosen. -->

## Decision

**Option 3, with the ambiguity it left open resolved explicitly:**

> **The stateless decoder is *the* reference result. The cached decoder is a declared second
> mode, reported beside it. The difference between them is the dispatch-cost measurement.**

There is one denominator, and it is the stateless number. `0004` promises that "3× faster" has a
documented denominator; two co-equal references would not be one denominator, so the cached
figure is never quoted as "the" reference.

### Why stateless has to be the reference

**Caching the detected variant does not merely optimise the decoder — it engineers away the
precise cost Prediction A claims is dominant.**

`roadmap.md` → *Recorded predictions*:

- **A** — "frame synchronisation and **per-model dispatch** dominate."
- **B** — "frame sync and dispatch are **O(1) per frame**; the checksum is O(n) over it."

A cached decoder makes dispatch O(1) per *connection* instead of per frame. That is Prediction B's
position, implemented. Building the reference that way would bake one side of the dispute into the
artifact whose entire purpose is to settle it — the Phase 4 failure `0004` exists to prevent,
arriving a phase early and through the decoder rather than through the benchmark's selection.

Stateless does not assume A is right. It declines to optimise, and decodes the work as specified.
That asymmetry is the whole argument: **one option pre-judges the question and the other does not.**

Two supporting reasons, neither sufficient alone:

- **A cached result depends on parameters this project cannot currently source.** Its cost moves
  with the flag-lying rate and the re-detect rate, and the flag-lying claim is explicitly marked
  in this file as a weaker evidence class than `bench/PROTOCOL-EVIDENCE.md`. A reference whose
  value depends on an unsourced number is not a reference.
- **A stateless result depends only on the generator and its seed.** Anyone can reproduce it
  without a session model, a connection-count distribution, or agreement about real traffic.

### Why the cached mode is still built, in Phase 0, not deferred

Prediction A bundles **two** costs that are usually discussed as one:

```
Prediction A  =  resync          (finding frame starts after garbage)
              +  dispatch        (choosing which variant decoder runs)
```

The project already has an instrument for the first: resync rate is a declared stimulus
parameter, and `roadmap.md` names it "the discriminator." It has had no instrument for the second.

**The stateless↔cached delta is that instrument.** Running both decomposes Prediction A into two
independently measurable components instead of one lump, which is strictly more than Phase 4 could
otherwise conclude.

It is built now rather than in Phase 4 for the reason in `0004`: an artifact added after
profiling starts is shaped by what profiling has already shown. Adding a second mode later also
means changing the thing being measured, mid-measurement.

## Consequences

**Mandatory manifest parameters gained** (`bench/README.md` updated):

- `detection_mode` — `stateless` | `cached`. Required on **every** result, including the
  stateless one. A result that does not say which mode produced it is unusable.
- For `cached` runs only: **connection count** and **frames-per-connection distribution**. The
  cached number is meaningless without them, since the amortisation is over exactly that.

**Made easier.** One quotable reference number with a short dependency list. Dispatch cost becomes
a measured quantity rather than an inference from a profile. Phase 4 can report "dispatch is X% of
decode" with a subtraction behind it.

**Made harder.** The reference decoder carries a detection interface it would not otherwise need,
and two implementations behind it. Every manifest carries a mode field. The cached path needs a
revalidate-on-failure route that the stateless path does not, and that path is exercised by
frames the generator must deliberately emit.

**Forecloses** quoting a single "decoder throughput" figure without qualification. Every
throughput claim from this benchmark now names a detection mode. That is a narrower claim than
would be convenient, and it is the honest one.

**Revisit if:** the flag-lying rate is sourced and turns out to be zero, in which case the cached
path needs no revalidation and the two modes differ only in a cache lookup — much less
interesting, and the second mode may not earn its keep. Or if measurement shows the delta is
within run-to-run noise, which would settle Prediction A's dispatch half on its own.
