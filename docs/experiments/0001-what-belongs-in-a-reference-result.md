# 0001 — What, exactly, is "the reference result"?

- **Date opened:** 2026-09-21
- **Phase:** 0
- **Status:** Open — **this is the Phase 0 reference-discipline exercise**

## Question

`docs/decisions/0004` requires a Spike reference result that exists before the core does, so
that every later speedup claim has a documented denominator. A reference must be *stable*: if it
changes when nothing meaningful changed, it settles no argument.

**Which parts of `make -C bench/rv32 run`'s output are the reference, and which parts are merely
this build's configuration?**

## Hypothesis

<!-- WRITE THIS BEFORE RUNNING ANYTHING. That is the whole point of the file.
     The output has four lines: crc_ref, acc, iters, instret. For each one,
     predict whether rebuilding with a different compiler flag changes it, and
     say WHY — name the mechanism, not just the direction. -->

## What would change my mind

<!-- Also before the run. What would you have to see to conclude your split of
     "reference" vs "configuration" was wrong? If you cannot answer this, you
     are not running an experiment, you are collecting support for a conclusion. -->

## Method

The toolchain is installed and the harness is tested: 20 consecutive runs of the default build
are byte-identical, including the instruction count. So any variation you see comes from what
you changed, not from run-to-run noise.

**Step 1 — freeze the default build as a candidate reference.**

Commit first. `capture.sh` records working-tree cleanliness, and a capture taken from a dirty
tree is not a reference — it cannot be reproduced from any commit.

```bash
git status --short                 # must be empty
scripts/capture.sh spike-crc-rv32im-O2 make -C bench/rv32 run
```

Then open the new `docs/results/<timestamp>-spike-crc-rv32im-O2/manifest.md` and **fill in the
Configuration and Result sections by hand.** This is the part that feels like paperwork and is
not. Ask yourself while filling it: *if I came back to this number in eight months, what would I
need in order to reproduce it exactly?* Everything that answers that question and is not already
implied by the commit hash belongs in Configuration.

**Step 2 — change exactly one thing.**

The `Makefile` exposes `OPT` and `ARCH` as overridable variables, so you do not have to edit
anything:

```bash
make -C bench/rv32 clean
make -C bench/rv32 run OPT=-O0
```

Write down all four output values. Then try the others, one at a time — `-O1`, `-O3`, `-Os`.

**Step 3 — change the instruction set instead of the optimiser.**

```bash
make -C bench/rv32 clean
make -C bench/rv32 run ARCH=rv32i          # drops the M extension: no mul, no div
```

Note that `make run` passes `--isa=$(ARCH)` to Spike, so the simulator's permitted ISA changes
with the build. Compare this result against `rv32im` carefully — and if it surprises you, work
out *why* from what `crc_itu_ref.c` actually computes. Read the inner loop before you theorise.

**Step 4 — the judgement, which is the actual exercise.**

Sort the four output lines into two groups:

```
INVARIANT — must never change, or the program is wrong
            => this is the reference result
VARIANT   — changes with the build
            => this is configuration, and must be DECLARED, not hidden
```

Then answer, in the sections below:

1. Which lines went in which group, and **why** — the mechanism, not the observation.
2. Did any flag change a value you had put in the INVARIANT group? If so, that is either a
   compiler bug or a bug in your program. Which, and how would you tell?
3. `bench/README.md` lists the parameters that must appear in every result manifest — protocol
   mix, resync rate, variant mix, frame length distribution, generator seed. **Your run just
   demonstrated at least two more that the list is missing.** Name them.
4. `docs/decisions/0004` promises that "3× faster" will have a documented denominator. Given
   what you just measured, state precisely what a denominator has to include for that claim to
   mean anything. One `instret` number alone — is it enough?

## Result

<!-- Link the captured runs: docs/results/<timestamp>-<label>/. Never retype a
     number by hand; point at the capture that contains it. -->

## Outcome

<!-- Was your hypothesis right? If not, say so plainly and leave the original
     hypothesis above untouched. That contrast is the record worth having. -->

## What this changes

<!-- Concretely: what gets added to bench/README.md's mandatory-parameter list?
     What does capture.sh need to record automatically that it currently does
     not? An experiment that changes nothing is still worth the file — but this
     one probably should change something. -->
