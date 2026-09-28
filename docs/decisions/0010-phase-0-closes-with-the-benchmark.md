# 0010 — Phase 0 closes when the benchmark runs on Spike

- **Date:** 2026-09-28
- **Status:** Accepted. Phase 0 is open again until its second criterion passes.
- **Phase:** 0 (policy), binding until Phase 2 starts

## Context

The roadmap's Phase 0 commits to two things and checks one of them.

- **It commits to the benchmark:** "the stimulus generator, reference decoder and Spike reference
  result are built *here*, before the core exists" (`roadmap.md`, Phase 0, lines 164-166 at
  `5439a3d`). `0004` makes that binding: "The benchmark is built, run, and frozen before the
  processor executes it."
- **Its gate checks only the waveform skill:** "you can find a bug you deliberately introduced by
  reading a waveform, without adding print statements" (line 168). That gate closed on 2026-09-21
  (#1, `docs/bugs/0002`).

Nothing checks the benchmark commitment, and the repository has been holding that gap shut by hand:

- **The journal repeated a guard three times**, twice on 2026-09-21 and once on 2026-09-25. The
  benchmark item is the benchmark *running on Spike*; a frozen specification is not that, and
  neither is `crc_itu_ref.c`. The first guard ends: "Do not let the register file start and close
  that gap by default."
- **`README.md` says it outright:** "Phase 0 is not finished, though, and the remaining item is not
  a gate."
- **The phase moved on anyway.** Phase 1's gate closed 58 seconds after Phase 0's (#2), which the
  roadmap allows, because the benchmark runs "in parallel". But nothing stops Phase 2 either.

A commitment with no check is how drift happens here. `0009` had just found the rv32 README
contradicting the roadmap for a week.

What the benchmark still lacks, in `0004`'s order:

```
specification   →  stimulus generator  →  reference decoder  →  expected output  →  Spike reference
bench/SPEC.md      bench/stimulus          not yet                not yet               not yet
```

## Options considered

1. **Leave the gate as it is, and keep the guard in the journal.** Rejected. A guard that has to be
   repeated is a gate that is not written down. Nothing would stop Phase 2's core from running a
   program before the benchmark exists, which is exactly what `0004` forbids.
2. **Add a separate benchmark gate before Phase 2, and leave Phase 0 closed.** It is plausible: it
   puts the check exactly where `0004`'s ordering bites, and reopens nothing. Rejected, because it
   keeps two meanings of "Phase 0 is done": the gate's, which was met, and the roadmap's, whose
   work is not finished. `README.md` already had to explain the difference.
3. **Add the benchmark to the Phase 0 gate, reopen Phase 0, and state the deadline.** Accepted. The
   gate then checks everything the phase commits to.
4. **Make all of Phase 1 wait for the benchmark.** Rejected. The roadmap runs the benchmark "in
   parallel" with the primitives, and nothing in Phase 1 can shape the benchmark, because no core
   executes anything yet. What must wait is the core running programs, which is Phase 2.

## Decision

**Phase 0's gate has two criteria. Phase 0 is open until both pass.**

1. **Waveform debugging:** "you can find a bug you deliberately introduced by reading a waveform,
   without adding print statements". Passed 2026-09-21 (#1).
2. **The benchmark runs on Spike, and is frozen.** All of these:
   - The reference decoder decodes the generated stimulus bare metal on Spike, and prints SPEC
     §3's records.
   - A check compares those records with the generator's intent log (`bench/stimulus`). It has
     been seen to fail on deliberately broken input, as `bench/stimulus`'s own check was
     (`test_stimulus.py`).
   - Every configuration the benchmark will be reported at is declared and captured with
     `scripts/capture.sh`. That includes its parameters, stated as assumptions (SPEC's unset
     list); the sweep points for resync rate and connection count (SPEC §5, §7); and the frame
     count per run, set and frozen (§7). Each capture records the decoder's output and its
     `instret`.
   - The benchmark is tagged `v0.0-benchmark-frozen`, in the form the roadmap asks for at every
     gate. After that, changing the generator, the decoder or a configuration takes a decision
     record, as changing the roadmap does.

**The deadline:** Phase 2's core runs no program until Phase 0 closes. That is `0004`'s ordering,
now checked.

**Phase 1 continues in parallel,** as the roadmap intends, and its gate (#2) stands.

## Consequences

- **Phase 0 is open again.** `roadmap.md` and `README.md` now say so, and why. So does
  `docs/bugs/README.md`, which described the waveform criterion as the whole gate.
- **Phase 2 cannot start early by default.** The first program the core runs will be judged
  against a benchmark that predates it, which is the property `0004` exists to protect.
- **The work left in Phase 0 is concrete:** the reference decoder, its check against the intent
  log, the configurations, and the captures. The decoder's first decision is what it does after a
  fault, and it comes before any code (journal, 2026-09-27).
- **The journal's guard retires.** The gate carries it now.
- **Harder:** Phase 2 now waits on software. The decoder may well take longer than the rest of
  Phase 1. This is the cost `0004` already accepted knowingly: "a genuine detour when the instinct
  is to go build the adder".
- **Found while writing this:** no gate had been tagged, though the roadmap asks for one at every
  gate. Phase 0's waveform criterion merged at `f4f1f33` (#1), and Phase 1's gate at `5d664db`
  (#2). Phase 1's gate is now tagged `v0.1-alu-golden-model-passing` (2026-09-28). `make alu`
  and `make mutate-alu` were re-run at that commit first, in a clean worktree, and both passed.
  Phase 0 gets its tag when it closes.
- **Revisit if** the benchmark's scope makes this gate unreachable in reasonable time. Then shrink
  the benchmark's first version, for instance to fewer frame types, and say so in a record. Do not
  drop the gate.

## Predictions

None. This record fixes what a gate checks. It does not rest on a belief that a later measurement
could test.
