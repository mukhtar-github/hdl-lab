# 0007 — How does the reference decoder carry variant and version state?

- **Date:** 2026-09-21
- **Status:** **Open — decision required before the reference decoder is written**
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
   quantity Prediction A actually disputes. Refuses to guess. *Against:* roughly doubles
   reference-decoder work and every result manifest carries a mode field.

## Decision

<!-- YOURS. State which, and why. If option 3, say explicitly whether the Spike reference result
     is one mode or two — decisions/0004 promises a documented denominator, and "the" reference
     result cannot be two numbers unless this file says it is. -->

## Consequences

<!-- Fill in with the decision. At minimum it must say what gets added to the mandatory
     manifest parameter list in bench/README.md. -->
