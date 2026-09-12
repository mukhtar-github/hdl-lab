# 0004 — The benchmark exists before the processor

- **Date:** 2026-09-12
- **Status:** Accepted
- **Phase:** 0 (policy), binding through Phase 5

## Context

`0001` committed the project to a workload: telematics frame decoding at line rate. A workload
is not a benchmark. "Telematics frame decoding" cannot be run, cannot be diffed, and cannot
settle an argument. What Phase 4 needs is a concrete artifact — a specific program, fixed input
data, deterministic output, under version control — and it needs it to have existed *before*
the core did.

The ordering is the whole decision. A benchmark written after the core exists is written, however
unconsciously, to the core's shape: you reach for the instructions you already implemented and
avoid the paths you know are weak. The measurement then confirms the design instead of testing it.

There is a second, harder constraint. The trace that motivated this workload is live GPS history
of real vehicles. It is not a data-licensing inconvenience; it is an obligation a benchmark
repository cannot hold, and it must never become a project dependency.

## Options considered

1. **Decide the benchmark after the CPU runs** — rejected. Reverses the dependency: the
   benchmark ends up shaped by what the core happens to do well, and Phase 4 degrades into
   ratification. Also strands Phases 0–3 with no reference result, so nothing is comparable
   until week 24.

2. **Use a captured operational trace as the stimulus** — rejected. Imports an obligation into
   version control that cannot be withdrawn once pushed, makes the benchmark unreproducible by
   anyone else, and makes the project depend on continued access to someone's data. The
   reproducibility loss alone would sink the result even if the privacy question did not.

3. **Synthesise stimulus from the published protocol specifications** — accepted. GT06 and
   JT/T 808 are public documents belonging to nobody in this story. Spec-derived stimulus is
   deterministic, versionable, regenerable, and waits on no one.

4. **Establish the reference result on Spike before any core exists** — accepted, and paired
   with option 3. Gives a golden output from day one, so the core can be checked against it the
   moment it executes anything at all.

## Decision

**The benchmark is built, run, and frozen before the processor executes it.**

Concretely, and in this order:

```
protocol specification → stimulus generator → reference decoder
                       → expected output → Spike reference execution
```

then, much later:

```
same program + same inputs → your RV32IM core
```

Stimulus is **synthesised from published specifications**. A real trace is *optional realism for
the arrival model only* — inter-arrival distribution, dark gaps, malformed rate — borrowed as
shape, never as data, and never committed. `.gitignore` enforces this mechanically.

The benchmark's **provenance is recorded in `bench/README.md` on the day it is written**, not
reconstructed later. Spec-derived stimulus run through a decoder you wrote is a *reconstruction*,
not instrumented production code. Both are legitimate; confusing them at Phase 4 is not.

## Consequences

- **Every later speedup claim is reproducible rather than anecdotal.** There is a fixed reference
  result that predates the core, so "3× faster" has a documented denominator.
- **A reference result exists from week one**, years before the core can run it. This is what
  makes the commodity-MCU baseline (roadmap → *The three numbers*) obtainable at all: the same
  program, unmodified, runs on Spike, on a Cortex-M4, and eventually on our core.
- **The project waits on nobody.** No data access, no NDA, no third party's strategy.
- **Cost: real work in Phase 0 that produces no RTL.** A stimulus generator and a reference
  decoder are a genuine detour when the instinct is to go build the adder. Accepted knowingly —
  it is cheaper now than a Phase 4 with nothing to measure against.
- **Forecloses** any claim about real-world traffic characteristics unless the arrival model is
  separately justified from trace *metadata*. That is a narrower claim than the project might
  want later, and it is the honest one.

## Predictions

The stimulus generator will be harder to write than the reference decoder, because the decoder
has a specification and the generator has to invent a traffic model. Recorded so Phase 4 can
show it wrong.

The protocol mix in the generated stimulus will turn out to be a more sensitive parameter than
expected — see `0001` predictions A/B, where GT06-heavy and JT/T 808-heavy traffic point at
different bottlenecks. If so, the mix is a first-class benchmark parameter and must be declared
in every result manifest, not left implicit.
