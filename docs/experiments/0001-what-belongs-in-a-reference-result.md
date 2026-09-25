# 0001 — What, exactly, is "the reference result"?

- **Date opened:** 2026-09-21
- **Phase:** 0
- **Status:** Answered 2026-09-25 — *Result, Outcome and What this changes drafted by Claude
  from the captures, for the author to edit. Immutable once merged.*

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

*Drafted by Claude on 2026-09-25 from the captures, for the author to edit. The table was generated
from each capture's `stdout.txt` by script, not retyped. All twelve passed `make check` (reference
lines matched `bench/rv32/crc_oracle.py`) from a clean tree at `de7758b`.*

| Build | `instret` | Loaded image | Capture |
|---|---:|---|---|
| `OPT=-O0` | 1,753,602 | `99dcd97e17d0` | [`20260925T084332Z-spike-crc-rv32im-O0`](../results/20260925T084332Z-spike-crc-rv32im-O0/) |
| `OPT=-O1` | 788,692 | `4ef710271a65` | [`20260925T084332Z-spike-crc-rv32im-O1`](../results/20260925T084332Z-spike-crc-rv32im-O1/) |
| defaults (`-O2`, rv32im) | 630,653 | `69f46c095e73` | [`20260925T084333Z-spike-crc-rv32im-O2`](../results/20260925T084333Z-spike-crc-rv32im-O2/) |
| `OPT=-O3` | 654,655 | `58652b14093c` | [`20260925T084333Z-spike-crc-rv32im-O3`](../results/20260925T084333Z-spike-crc-rv32im-O3/) |
| `OPT=-Os` | 649,642 | `c2b5ff5c3038` | [`20260925T084334Z-spike-crc-rv32im-Os`](../results/20260925T084334Z-spike-crc-rv32im-Os/) |
| `ARCH=rv32i` | 630,653 | `69f46c095e73` | [`20260925T084334Z-spike-crc-rv32i-O2`](../results/20260925T084334Z-spike-crc-rv32i-O2/) |
| `OPT=-O2 -fno-optimize-crc` | 942,942 | `261bb8f8d620` | [`20260925T084335Z-spike-crc-rv32im-O2-no-crc-pass`](../results/20260925T084335Z-spike-crc-rv32im-O2-no-crc-pass/) |
| `OPT=-Os -fno-optimize-crc` | 961,954 | `6e895cc45d78` | [`20260925T084336Z-spike-crc-rv32im-Os-no-crc-pass`](../results/20260925T084336Z-spike-crc-rv32im-Os-no-crc-pass/) |
| `OPT=-O3 -fno-optimize-crc` | 654,655 | `58652b14093c` | [`20260925T084336Z-spike-crc-rv32im-O3-no-crc-pass`](../results/20260925T084336Z-spike-crc-rv32im-O3-no-crc-pass/) |
| `OPT=-O3 -fdisable-tree-cunrolli` | 106,612 | `84fb3d255ca2` | [`20260925T084337Z-spike-crc-rv32im-O3-no-early-unroll`](../results/20260925T084337Z-spike-crc-rv32im-O3-no-early-unroll/) |
| `TUNE=sifive-7-series` | 618,641 | `96097952810d` | [`20260925T084337Z-spike-crc-rv32im-O2-tune-sifive7`](../results/20260925T084337Z-spike-crc-rv32im-O2-tune-sifive7/) |
| `TUNE=generic-ooo` | 630,653 | `90f1536a4b7f` | [`20260925T084338Z-spike-crc-rv32im-O2-tune-generic-ooo`](../results/20260925T084338Z-spike-crc-rv32im-O2-tune-generic-ooo/) |

`crc_ref = 0x4cd4`, `acc = 0x33cc525d` and `iters = 0x3e8` in all twelve. Step 1's capture and the
stale-build evidence, both taken at the hypothesis commit before the harness changed:
[`20260925T083727Z-spike-crc-rv32im-O2`](../results/20260925T083727Z-spike-crc-rv32im-O2/) and
[`20260925T083729Z-evidence-stale-build`](../results/20260925T083729Z-evidence-stale-build/).

What the builds actually run, read from the binaries rather than the source:

- **At -O2 and -Os, GCC's CRC-recognition pass replaced the loop.** `-foptimize-crc` is new in GCC 15.
  On this compiler it is on at -O2, -O3 and -Os and off at -O0 and -O1. Its dump says *"Bit
  reversed … Polynomial's value is …"*. `.rodata` grows by exactly 512 bytes: a 256-entry table
  starting `0000 1021 2042 3063`, the MSB-first table for 0x1021, wrapped in bit-reflection code
  (masks `0x5555`, `0x3333`, `0x0f0f`).
- **At -O3 the pass never fires.** Early complete unrolling (`cunrolli`) flattens the 8-bit loop
  before the pass looks. The dump is empty, and the image is identical with `-fno-optimize-crc`.
  Disable the early unroller and the pass fires. The CRC over the 10 bytes that never change is
  then hoisted out of the sweep: 2 table loads per iteration, where -O2 does 12.
- **The gap between -O2 and -O3, ≈2 instructions per byte, is a coincidence.** Two different
  algorithms: table plus reflection at ≈52.5 instructions per byte all-in, unrolled bit-serial at
  ≈54.5. They cost nearly the same because on rv32im the reflection costs almost what the table saves.
- **Without the pass, -O2 turns the per-bit branch into a mask.** 9 instructions every bit, where
  -O1's branching loop takes 5 or 9.

## Outcome

### The hypothesis, line by line

| Prediction | Result |
|---|---|
| `crc_ref` unchanged | **Right**, in all twelve builds. |
| `acc` unchanged | **Right**, in all twelve builds. |
| `iters` is decimal 1000 | **Right**, and it could not have been otherwise (see the sort below). |
| `rv32im ≈ rv32i` | **Right, and stronger than claimed.** Same loaded image: the compiler never used M. |
| `-O0 > -O1 > -Os > -O2 > -O3` | **Falsified** at one adjacent pair. -O3 (654,655) retires more than both -Os (649,642) and -O2 (630,653). |

**Right answer, wrong mechanism.** The ordering was explained as "more extensive optimisation reduces
executed work further". The pairs it got right were carried by one pattern-matching pass it did not
name. With `-fno-optimize-crc`, -O2 (942,942) and -Os (961,954) both retire *more* than -O1
(788,692). Of the three pairs the hypothesis got right, `-O1 > -Os` holds only because of that pass,
and so does the `-O1 > -O2` it implies.

**The third falsifier was aimed at the right thing.** It asked whether the compiler would emit an M
instruction the source did not need. It did not. It emitted a 512-byte table the source does not
contain.

### Step 4 — the judgement

**1. The sort needs three groups, not two.**

```
REFERENCE    crc_ref, acc   must match any correct implementation, on any machine
WORKLOAD     iters          defines the work: change it and it is a different benchmark
MEASUREMENT  instret        meaningless without the configuration that produced it
```

- `crc_ref` is a function of the 12 frame bytes and the CRC-16/X-25 definition, nothing else.
- `acc` also depends on `ITERS` and the rotate-xor fold, so it is a reference *for this workload*.
- `instret` belongs to the binary and the machine counting it, not to the computation. It spans
  106,612 to 1,753,602 (16.4×) with the reference lines unchanged.
- `iters` fits neither of the template's two groups. It is `htif_puthex32(ITERS)`: the macro,
  printed, not a count. It cannot be wrong, so it verifies nothing. The build that did a sixth of the
  CRC work printed `000003e8` too. It is not build configuration either. It is the definition of the
  work, and the frame bytes belong beside it.

The general lesson: *invariant across the sweep* is not *reference*. `iters` held still only because
nothing that was swept touches it. Sort a line by what determines its value, not by whether it moved.

**2. No invariant moved.** What their agreement proved is narrower than it looks, and in one
place stronger:

- **It is consistency, not correctness.** Twelve compilations of a wrong CRC would agree perfectly.
  `crc_oracle.py` computes CRC-16/X-25 by a different path (CPython's `crc_hqx`, reflected by hand).
  It reproduces the RevEng catalogue check value `0x906E` and the GT06 login example's `8C DD`, and
  only then agrees with `0x4cd4` and `0x33cc525d`. The published values are what test the *reading
  of the spec*. A model written by the same hand shares that hand's misreadings.
- **It was a real test of the compiler.** -O0, -O1 and -O3 run the source's loop. -O2 and -Os run a
  table GCC built from a polynomial it *inferred*. They agree across 1,001 CRCs that touch all 256
  table entries.
- **It verifies answers, never work.** `acc` catches a deleted loop, because its result is used. It
  cannot catch a hoisted one.

Telling a compiler bug from a program bug, had one moved:

1. **The oracle names the wrong side.** If -O0 also disagrees with it, the program is wrong, or the
   reading of the spec is.
2. **If builds disagree with each other, suspect the program first.** Undefined behaviour is the
   usual cause, and the compiler is entitled to exploit it. Build for the host with
   `-fsanitize=undefined,address`, and try `-fwrapv -fno-strict-aliasing`. `crc_itu_ref.c` was read
   for undefined behaviour and none was found.
3. **A UB-free program that still disagrees points at the compiler.** Toggle the suspect pass first
   (a one-release-old pass such as `-foptimize-crc`), then reduce the test case.
4. **The harness is the fourth suspect.** This experiment found one: `docs/bugs/0004`.

**3. The manifest parameters `bench/README.md` was missing.** This run demonstrated all four:

- **The effective compiler flags, not the command that was typed.** `make run OPT=-O3` over an -O2
  build re-ran the -O2 binary
  ([`evidence-stale-build`](../results/20260925T083729Z-evidence-stale-build/)). Its manifest is true
  in every field.
- **The compiler's identity, including its defaults.** `-mtune` defaulted to `rocket`, which appears
  in neither the Makefile nor the version line. `sifive-7-series` retires 618,641. And the -O2
  result depends on a pass that older compilers do not have.
- **A hash of the loaded image.** This is what makes the others checkable. Configurations map to
  code many-to-one (rv32i and rv32im produce one image), and one flag can change the image without
  changing the count (`generic-ooo`). Hash `objcopy -O binary`: not the ELF, whose metadata differs,
  and not `.text` alone, because the table is in `.rodata`.
- **ISA and ABI, for the right reason.** The Makefile said changing either "changes the instruction
  count". For this program the ISA does not. Declare it because it bounds what the compiler may
  emit and what Spike will run.

**4. One `instret` is not a denominator.** With the reference lines unchanged, flags alone span
16.4×. A core no faster than Spike's count could show "3×" just by choosing which two builds to
compare. For "3× faster" to mean anything, the claim must carry:

1. **The same loaded image on both sides.** If the image has to change, declare both images and split
   the claim into a compiler effect and a hardware effect. Time = instructions × CPI × cycle time.
   `instret` is only the first factor, and the compiler owns most of it.
2. **The strongest baseline, named.** At -O2 the baseline was already a table. A CRC instruction
   would compete with the table, not with the loop in the source.
3. **The metric's blind spots, stated.** Spike charges every instruction 1. The branchless -O2 loop
   loses on Spike, and might win on a pipeline that mispredicts a 50/50 branch. `generic-ooo`
   reorders instructions at an identical count. `instret` sees neither effect.
4. **The work performed, not the work declared.** 106,612 reads as 8.9 instructions per byte. It is
   ~53 per byte, on the 2 bytes per iteration that changed. Only the binary shows this.
5. **Matching reference lines before any ratio.** Compare only results whose `crc_ref` and `acc`
   both pass the oracle.

## What this changes

- **`bench/README.md`** gains a *Build* block in the parameters every manifest must declare:
  compiler identity and tuning, effective flags, ISA and ABI for compiler and simulator,
  loaded-image hash, metric and window.
- **The harness now records all of this without being asked** (`de7758b`). `make run` prints the
  compiler, the effective flags and the image hash. Build directories are named by a hash of their
  inputs. `make check` holds every run to the oracle. `capture.sh` lists untracked files, quotes the
  command, and records the directory it ran from.
- **`docs/bugs/0004`** preserves the stale build from before the fix, together with the first fix
  (a flags stamp), which failed the same way.
- **`decisions/0008`: what the reference binary runs.** The -O2 build above did not run the
  source's algorithm. A reference whose workload changes with the compiler version is not a
  reference.
- **The stimulus generator inherits a rule.** Frames must reach the decoder as data the compiler
  cannot see at compile time. The 106,612 build shows what a compiler does with work it can see.
- **`experiments/0002`** is the joint prediction: what the CRC pass emits when the target has Zbkb
  or Zbc.
- **What remains implicit, stated rather than hidden.** Other compiler defaults stay unpinned:
  `-misa-spec=20191213` reaches `cc1` by default. The image hash is the backstop for everything
  that is not pinned.
