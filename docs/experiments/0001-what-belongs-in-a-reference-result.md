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

**Written 2026-09-24, before any of the six configurations was run.** Committed in its own commit,
ahead of the first capture, so the ordering is a matter of git history rather than recollection.

**Question:** what happens to the four output lines — `crc_ref`, `acc`, `iters`, `instret` —
across `-O0`, `-O1`, `-O2`, `-O3`, `-Os`, and when the target ISA changes from `rv32im` to `rv32i`?

### 1. `crc_ref` — unchanged in all six configurations

The deterministic CRC of the same fixed 12-byte frame. Changing compiler strategy or the available
instruction set should not change the program's mathematical result.

### 2. `acc` — unchanged in all six configurations

The compiler may implement the calculation differently, but the loop performs the same
deterministic sequence of CRC calculations and accumulator updates, so any *correct* compilation
must produce the same final value.

### 3. `iters` — unchanged, decimal 1000 (`0x000003e8` as printed)

`ITERS` is a compile-time constant `1000u`. No optimisation level or ISA choice changes that
constant or the number of iterations the source requires.

### 4. `instret` — changes significantly with optimisation level; little or no change from ISA

Optimisation levels change how GCC transforms the program: function calls, register use, loop
structure, constant propagation, inlining, unrolling. By contrast the dominant CRC operations are
XOR, AND, shifts, loads, stores, additions, comparisons and branches, so the M extension's
multiply/divide instructions are not expected to matter.

Supporting arithmetic: the inner bit loop runs 96 times per `crc_itu()` call (12 bytes × 8 bits),
so 96 × 1000 = 96,000 in the sweep plus 96 for the reference call — 96,096 inner iterations. The
hot path is therefore:

```c
crc = (crc & 1u) ? (crc >> 1) ^ 0x8408 : crc >> 1;
```

which needs only base RV32I integer and control-flow operations.

### Committed optimisation ordering

Highest retired-instruction count to lowest:

```
-O0  >  -O1  >  -Os  >  -O2  >  -O3
```

- `-O0` — least optimisation, therefore the most instruction work.
- `-O1` — removes some unnecessary work, conservative strategy.
- `-Os` — optimises beyond `-O1` but prioritises *code size* over executed-instruction count, so
  predicted to stay above the performance-oriented `-O2` and `-O3`.
- `-O2` — more extensive optimisation, reduces executed work further.
- `-O3` — **lowest**, via more aggressive transformations aimed at execution speed, including ones
  that reduce loop overhead.

### Committed ISA prediction

```
rv32im  ≈  rv32i        at every optimisation level
```

Any difference expected to be small compared with the differences caused by optimisation level.
The CRC hot path contains no obvious multiplication or division, so removing M should not force a
substantially different implementation.

## What would change my mind

Falsified, or seriously weakened, by any of:

- `crc_ref` changes between configurations.
- `acc` changes between configurations.
- `iters` is anything other than decimal 1000 (`0x000003e8`).
- **Any adjacent pair out of the committed order** `-O0 > -O1 > -Os > -O2 > -O3`. Stated as an
  exact criterion rather than "substantially different" because Spike is deterministic and has no
  timing model — 20 consecutive runs were byte-identical including instruction count — so there is
  no run-to-run scatter for an inversion to hide in. Any inversion is a real inversion.
- `rv32i` consistently producing substantially more **or fewer** retired instructions than
  `rv32im` at the same optimisation level.

**The most interesting available falsification:** finding that the compiler emits an M-extension
instruction for something that, read from the C source, appears to need no multiply or divide.
That would mean the source-level mental model is incomplete, and would send me to the generated
assembly rather than to the C.

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
