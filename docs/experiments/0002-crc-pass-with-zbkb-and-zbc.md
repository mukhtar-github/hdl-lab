# 0002 — What does GCC's CRC pass emit when the target has Zbkb or Zbc?

- **Date opened:** 2026-09-25
- **Phase:** 0
- **Status:** Answered 2026-09-29. *Result, Outcome and What this changes drafted by Claude from the
  captures.*

## Question

In `experiments/0001`, GCC's CRC pass on rv32im replaced the bitwise loop with a table wrapped in
per-byte bit reflection. GCC uses a target-specific expander when the target has one. **When the
target has Zbkb (bit and byte reversal, rotates) or Zbc (carry-less multiply), what does the pass
emit instead, and what happens to `instret` and to the loaded image?**

This is the first measurement that bears on an ISA question the core will face: which extension, if
any, earns its area on this workload's CRC.

## Known before predicting

All captured on rv32im, `-O2`, oracle PASS. Nothing here was built with Zbkb or Zbc.

| Build | `instret` | Capture |
|---|---:|---|
| **A** — `CRC_IMPL=bitwise`, CRC pass **allowed** (`ALGOFLAGS=`) | 630,653 | [`…-bitwise-pass-rv32im-O2`](../results/20260925T085345Z-spike-crc-bitwise-pass-rv32im-O2/) |
| `CRC_IMPL=bitwise`, CRC pass pinned off | 942,942 | [`…-bitwise-rv32im-O2`](../results/20260925T085107Z-spike-crc-bitwise-rv32im-O2/) |
| the stated table, `CRC_IMPL=table` — the reference (`decisions/0008`) | 138,137 | [`…-table-rv32im-O2`](../results/20260925T085106Z-spike-crc-table-rv32im-O2/) |

**The anatomy of A**, from its disassembly: one loop iteration per byte, 51 instructions, which
breaks down as:

```
 3   lbu, addi, xor           fetch the byte, advance, fold it into the CRC
20   reflect in               byte swap (5) + three mask-and-shift rounds (3 × 5)
 7   table step               index (srli, slli, add), lhu, then or / slli / xor
20   reflect out              byte swap (5) + three mask-and-shift rounds (3 × 5)
 1   bne
```

So **40 of the 51 are bit reflection**. The 512-byte table is in `.rodata` (size `0x24c`; `0x4c`
without it). Outside the per-byte loop, each of the 1001 CRCs costs about 18 more instructions
(630,653 − 51 × 12,012 = 18,041). That includes the `acc` fold's rotate, which is three
instructions: `srli`, `slli`, `add`.

**Instruction reference** — facts about the ISA, not predictions:

| Extension | Instructions (RV32) | What they do |
|---|---|---|
| **Zbkb** | `rev8` | reverse the byte order of a register |
| | `brev8` | reverse the bit order *within each byte* |
| | `rol`, `ror`, `rori` | rotate |
| | `andn`, `orn`, `xnor` | logic with an inverted operand |
| | `pack`, `packh` | pack the low halves or low bytes of two registers |
| | `zip`, `unzip` | bit interleave and de-interleave |
| **Zbc** | `clmul` | low 32 bits of the carry-less (XOR) product |
| | `clmulh` | high 32 bits of it |
| | `clmulr` | bits 62..31 of it ("reversed") |

What GCC documents: CRC loops are "replaced with calls to newly added internal functions", which
"use target-specific expanders if available, otherwise generating table-based CRCs"
([GCC 15 changes](https://gcc.gnu.org/gcc-15/changes.html)). How the RISC-V expanders behave is
*not* in this file. That is the question.

## Configurations

The 0001 program with the pass **deliberately allowed**. This experiment is about that pass, so
under `decisions/0008` none of these numbers is ever quoted as a reference.

```bash
make -C bench/rv32 check CRC_IMPL=bitwise ALGOFLAGS= ARCH=rv32im_zbkb       # B
make -C bench/rv32 check CRC_IMPL=bitwise ALGOFLAGS= ARCH=rv32im_zbc        # C
make -C bench/rv32 check CRC_IMPL=bitwise ALGOFLAGS= ARCH=rv32im_zbkb_zbc   # D
```

`make run` passes `--isa=$(ARCH)` to Spike, so the simulator's ISA follows the build.

## Hypothesis — the author's

None of my own for this experiment. I'm learning this material as the project goes. I asked a
second assistant to write the hypothesis, and it follows below. I read it before this section was
committed, so no blind prediction from me exists here.

## Hypothesis — second assistant

*Transcribed verbatim from the text the author pasted on 2026-09-29. Only the level of its first
heading was changed, to fit this file.*

Written after reading GCC's RISC-V CRC expander source. This is therefore **not a blind hypothesis about the mechanism**. The mechanism below is source-derived; the `instret` figures are predictions from the experiment's own measured baseline.

Compiler assumed: **GCC 16.2.0**. The CRC expander was added to GCC's RISC-V backend in November 2024. The source says that a target with ZBC uses `clmul` for CRC calculation, while a target with ZBKB uses a table-based CRC with `bswap`/`brev8` for reflection.

| Configuration             | Predicted `instret` | 512-byte table              | Predicted mechanism                                                                                                                                                            |
| ------------------------- | ------------------: | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **B — `rv32im_zbkb`**     | **221,000–224,000** | **Yes — `.rodata = 0x24c`** | GCC keeps the table-based CRC, but replaces the software reflection sequences with hardware byte/bit reversal (`rev8`/`brev8`, represented in the backend as `bswap`/`brev8`). |
| **C — `rv32im_zbc`**      | **124,000–128,000** | **No — `.rodata = 0x4c`**   | GCC uses the dedicated carry-less-multiply CRC expansion, principally `clmul`/`clmulh`, instead of a lookup table.                                                             |
| **D — `rv32im_zbkb_zbc`** | **124,000–128,000** | **No — `.rodata = 0x4c`**   | GCC selects the ZBC/CLMUL CRC path; ZBKB does not add the table/reflection path on top of it.                                                                                  |

For B, the arithmetic prediction comes from replacing the 20-instruction software reflection on each side of A's 51-instruction byte loop with approximately three instructions per reflection. That gives a predicted 17 instructions per byte, hence:

`18,041 + 17 × 12,012 = 222,245`

For C and D, the prediction is based on a roughly 9-instruction-per-byte CLMUL loop:

`18,041 + 9 × 12,012 = 126,149`

These are workload-derived predictions, not measured results.

### What would change my mind

For **B**, I would change the prediction if the built image drops the 512-byte table, if the per-byte disassembly does not show hardware reflection replacing the software reflection, or if `instret` falls materially outside the predicted range.

For **C**, I would change the prediction if the table remains in the image, if the CRC loop is still table-driven, or if the measured `instret` is materially outside the predicted CLMUL range.

For **D**, I would change the prediction if GCC chooses a different mixed strategy rather than the ZBC CLMUL path, particularly if the table reappears or the per-byte CRC operation is not based on `clmul`.

## Hypothesis — Claude's (sealed)

Written and sealed on 2026-09-25, before either section above was written and before any Zbkb or
Zbc build existed. Only its hash was committed then, in `84a2054`. The text sat in a git object
behind a **local** tag, which `git push` does not send, so it could not be read by accident.

**Opened on 2026-09-29,** after both sections above were committed (`9b7f274`). Its SHA-256 matches
the hash committed in `84a2054`:

```
sha256  13361923f43677df4e03ffd5cca81c914a3af8c477c019526c3f1a3de6a65e2f
tag     sealed/0002-claude-prediction          (local only)
open    git cat-file blob sealed/0002-claude-prediction
verify  git cat-file blob sealed/0002-claude-prediction | shasum -a 256
```

The text follows verbatim, between two comment markers. The tag stays local, so this checks it
from the file alone:

```bash
sed -n '/^<!-- sealed text begins/,/^<!-- sealed text ends/p' \
    docs/experiments/0002-crc-pass-with-zbkb-and-zbc.md | sed '1d;$d' | shasum -a 256
```

<!-- sealed text begins -->
### Claude's prediction — sealed 2026-09-25, before any Zbkb or Zbc build existed

**What it is predicted from.** My recollection of GCC's RISC-V CRC expanders, which I did not re-read
for this. The recollection: when the target has Zbc (or Zbkc), a reversed CRC is expanded with two
carry-less multiplies, using a reflected quotient and a reflected polynomial, so no bit reflection
is needed. Otherwise, when it has Zbkb, GCC uses the table again, with the reflections done by
`rev8` + `brev8`. Otherwise, the table with mask-and-shift reflection that 0001 saw. If that
recollection is wrong, this prediction fails, and finding that out is part of what it tests.

**B — `rv32im_zbkb`: 190,000 to 250,000, point estimate about 220,000. The 512-byte table stays.**
- Mechanism: the table path again, but each 16-bit reflection becomes `rev8` + `brev8` + a shift,
  about 3–4 instructions instead of 20.
- About 17–18 instructions per byte instead of 51.
- The `acc` fold's rotate becomes one `rori`, which saves 2 per iteration.

**C — `rv32im_zbc`: 130,000 to 190,000, point estimate about 160,000. The table is gone** (`.rodata`
back to `0x4c`).
- Mechanism: two `clmul`s per byte, working in the reflected domain.
- No reflection at all, about 12 instructions per byte.

**D — `rv32im_zbkb_zbc`: C's algorithm, because Zbc wins in the expander. C minus 1,000 to 15,000.**
- The rotate becomes `rori`, which saves 2,000.
- If C zero-extends to 16 bits with two shifts per byte, Zbkb's `pack` may do it in one, which saves
  up to 12,000 more.
- No table.

**Against the stated table (138,137):**
- None of the three beats it by more than 5%.
- C and D land between 0.95× and 1.4× of it.
- B lands near 1.6× of it.

In short: a carry-less multiply roughly ties an ordinary 512-byte table on this workload, and a
bit-reverse instruction alone gets nowhere near it.

**The invariants.** `crc_ref` and `acc` pass the oracle in all three builds. These are new expansion
paths in a one-release-old pass, so passing is a real check, not a formality.

**What would change my mind:**
- C keeps the table, or lands near A (above 400,000). That would mean the Zbc path reflects the
  data after all, or is not taken, and my recollection of the expander is wrong.
- B has no table. That would mean the Zbkb path is not table-based.
- D differs from C by more than 15,000. That would mean the extensions interact in a way I did not
  model.
- Any build beats the stated table by more than 5%.
- Any oracle failure. That would be a miscompile in a new expansion path, and the most interesting
  outcome available.
<!-- sealed text ends -->

## What would change my mind

None of my own, for the same reason. The second assistant's falsifiers are in its section, and
Claude's are inside the sealed text.

## Method

1. The author writes both sections above and commits them.
2. The sealed prediction is opened, verified against the hash above, and committed verbatim.
3. **Only then** are B, C and D built, each captured with `scripts/capture.sh` from a clean tree.
   Record `.rodata` for each: `riscv64-elf-objdump -h <elf> | grep rodata`.
4. Every build must pass the oracle. These are new expansion paths in a pass that is one release
   old: a failure there is a compiler bug, and 0001 step 4 says how to tell.
5. Compare each against both hypotheses and against the stated table.

## Result

*Drafted by Claude on 2026-09-30 from the captures. The table was generated from each capture's
`stdout.txt` by script, not retyped. The method ran in the order git shows: both hypotheses in
`9b7f274`, the seal opened and its hash checked in `5333c7f`, then every capture from a clean tree
at `5333c7f` or later.*

| Build | `instret` | × the stated table | Byte loop | `.rodata` | Loaded image | Capture |
|---|---:|---:|---:|---|---|---|
| the stated table, `decisions/0008` | 138,137 | 1.00 | 10 | `0x24c` | `1baf3e07a7c8` | [`…-table-rv32im-O2`](../results/20260929T064032Z-spike-crc-table-rv32im-O2/) |
| **A** — `rv32im` | 630,653 | 4.57 | 51 | `0x24c` | `d6ed6f718159` | [`…-bitwise-pass-rv32im-O2`](../results/20260929T064033Z-spike-crc-bitwise-pass-rv32im-O2/) |
| **B** — `rv32im_zbkb` | 292,293 | 2.12 | 23 | `0x24c` | `30f494056142` | [`…-bitwise-pass-rv32im_zbkb-O2`](../results/20260929T064034Z-spike-crc-bitwise-pass-rv32im_zbkb-O2/) |
| **C** — `rv32im_zbc` | 150,155 | 1.09 | 11 | `0x4c` | `b9e05c923810` | [`…-bitwise-pass-rv32im_zbc-O2`](../results/20260929T064034Z-spike-crc-bitwise-pass-rv32im_zbc-O2/) |
| **D** — `rv32im_zbkb_zbc` | 148,155 | 1.07 | 11 | `0x4c` | `8eeace23d221` | [`…-bitwise-pass-rv32im_zbkb_zbc-O2`](../results/20260929T064035Z-spike-crc-bitwise-pass-rv32im_zbkb_zbc-O2/) |

- **All five pass the oracle:** `crc_ref = 0x4cd4`, `acc = 0x33cc525d`, `iters = 0x3e8`. The new
  expansion paths computed the right CRC over all 1,001 frames.
- **The stated table and A are controls,** re-run at `5333c7f`. Each reproduces its 2026-09-25
  capture to the image hash, so the toolchain has not moved since A was measured.
- **Byte loop** is the instructions per byte in the sweep, and **`.rodata`** is that section's size.
  Both come from the disassembly:
  [`…-objdump-crc-bitwise-pass-O2`](../results/20260929T064103Z-objdump-crc-bitwise-pass-O2/) for A
  to D, and [`…-objdump-crc-table-rv32im-O2`](../results/20260929T064446Z-objdump-crc-table-rv32im-O2/)
  for the stated table. `0x24c` holds a 512-byte table, and `0x4c` holds none.

**Each count is fully accounted for by its loops:** the instructions run once, plus 12 trips of the
reference CRC's byte loop, plus 1,000 sweep iterations, each with 12 trips of its own copy of that
loop.

```
the stated table   17 + 12 × 10 + 1000 × (18 + 12 × 10) = 138,137
A                  41 + 12 × 51 + 1000 × (18 + 12 × 51) = 630,653
B                  17 + 12 × 23 + 1000 × (16 + 12 × 23) = 292,293
C                  23 + 12 × 11 + 1000 × (18 + 12 × 11) = 150,155
D                  23 + 12 × 11 + 1000 × (16 + 12 × 11) = 148,155
```

Each total is the captured `instret`, exactly. The sweep's 16 in B and D, against 18 in A and C, is
the `acc` fold's rotate: one `rori` with Zbkb, and `srli` + `slli` + `add` without it.

**What each build runs per byte,** read from the disassembly. Lines marked `·` compute nothing.

**B** keeps A's table and A's shape: reflect, look up, reflect back. Each reflection is now `rev8`,
`srli`, `brev8`, 3 instructions where A spends 20. But the loop is 23, not 17:

```
lbu     a4,0(t1)      the byte
li      a3,0          · the constant 0,
brev8   a3,a3         · reflected,
xor     a5,a5,a4      fold the byte into the CRC
rev8    a5,a5         reflect in
srli    a5,a5,0x10    reflect in
brev8   a5,a5         reflect in
slli    t3,a5,0x10    table index
srli    a4,t3,0x18    table index
zext.b  a3,a3         · zero-extended,
xor     a4,a4,a3      · and XORed into the index
slli    a4,a4,0x1     index × 2
add     a4,a1,a4      entry address
lhu     a4,0(a4)      table entry
slli    a5,a5,0x8     CRC << 8
addi    t1,t1,1       advance
xor     a5,a4,a5      the new CRC, in forward bit order
rev8    a5,a5         reflect out
srli    a5,a5,0x10    reflect out
brev8   a5,a5         reflect out
slli    a5,a5,0x10    · zero-extend,
srli    a5,a5,0x10    · already 16 bits wide
bne     a2,t1,…       next byte
```

- **4 reflect a zero.** GCC's CRC pass hands the expander a data operand of `0`, because the source
  XORs each byte into the CRC before its bit loop
  ([`…-gcc-optimized-crc-bitwise-pass-rv32im_zbkb-O2`](../results/20260930T025157Z-gcc-optimized-crc-bitwise-pass-rv32im_zbkb-O2/)).
  The expander reflects that 0 with `brev8`, zero-extends it, and XORs it into the table index, on
  every byte. A's loop has nothing like it: A gets the same call, and its shift-and-mask reflection
  of the 0 folds away.
- **2 zero-extend a value that is already 16 bits wide.** `srli` leaves 16 bits, and `brev8` only
  reverses bits within each byte, so the top two bytes are already zero. A's last shift-and-mask
  round leaves 16 bits too, and A needs no extension.

**C and D** run the same 11 instructions per byte: two carry-less multiplies and no reflection. The
multiplies are by two constants that GCC derived from the polynomial, `0x1911` and `0x10810`, loaded
once before the loop:

```
lbu     a5,0(a3)      the byte
addi    a3,a3,1       advance
xor     a4,a4,a5      fold the byte into the CRC
clmul   a5,a4,a0      × 0x1911, low half
srli    a4,a4,0x8     the CRC's top byte, moved down
slli    a5,a5,0x18    the product's low byte, moved to the top
clmulh  a5,a5,a1      × 0x10810, high half
xor     a5,a5,a4      the new CRC
slli    a4,a5,0x10    · zero-extend,
srli    a4,a4,0x10    · already 16 bits wide
bne     a3,a2,…       next byte
```

- **2 zero-extend a value that is already 16 bits wide,** as in B. The CRC enters each trip within
  16 bits and the byte within 8, so `srli` leaves at most 8 bits. `slli` leaves the product in bits
  24–31, and `0x10810` spans bits 4–16, so their carry-less product spans bits 28–47, and `clmulh`
  returns at most 16 bits of it. The XOR of the two stays within 16 bits.

**The stated table,** for comparison: 10 instructions per byte, and none of them wasted.

```
lbu     a5,0(a3)      the byte
srli    a2,a4,0x8     the CRC's top byte, moved down
addi    a3,a3,1       advance
xor     a5,a5,a4      fold the byte into the CRC
zext.b  a5,a5         table index: the low byte
slli    a5,a5,0x1     index × 2
add     a5,a0,a5      entry address
lhu     a4,0(a5)      table entry
xor     a4,a2,a4      the new CRC
bne     a3,a1,…       next byte
```

## Outcome

**Both hypotheses got the mechanism right in all three builds, and both missed B's count by the same
six instructions per byte.** Both built B from A by swapping the reflections,
51 − 2 × 20 + 2 × 3 = 17, as if the rest of A's loop carried over. It did not. Through `brev8`, GCC
keeps work that A's shifts and masks let it fold away.

### The second assistant's

| Prediction | Result |
|---|---|
| B: 221,000–224,000 | **Wrong.** 292,293, 30% above the top of the range. |
| B: the table stays | **Right.** `.rodata` is `0x24c`. |
| B: `rev8`/`brev8` replace the software reflection | **Right.** 3 instructions per reflection, as it assumed. |
| C: 124,000–128,000 | **Wrong.** 150,155, 17% above the top. |
| C: no table, and `clmul`/`clmulh` | **Right**, both. |
| D: 124,000–128,000 | **Wrong.** 148,155, 16% above the top. |
| D: the Zbc path, with no table or reflection added by Zbkb | **Right.** D runs C's loop. |

**By its own falsifiers, B and C are falsified.** Their `instret` fell "materially outside the
predicted range". D's falsifiers name only mechanism, and none of them fires, but its range was
missed like C's.

**Every mechanism was right and every count low, for one reason.** Its per-byte models count the
working instructions exactly: 3 per reflection in B, and C's loop less its zero-extension is exactly
the 9 it assumed. What they leave out is the instructions that compute nothing: 2 per byte in all
three builds, and B's reflected zero, 4 more. That accounts for the whole miss:

- B: 6 × 12,012 = 72,072, against a gap of 70,048 between its 222,245 and the measured 292,293.
- C: 2 × 12,012 = 24,024, against a gap of 24,006 between its 126,149 and the measured 150,155.

The small remainders come from the code around the loop, which it took from A as 18,041. B's is
16,017 and C's is 18,023.

### Claude's (sealed)

| Prediction | Result |
|---|---|
| B: 190,000–250,000, about 220,000 | **Wrong.** 292,293, 17% above the top of the range. |
| B: 17–18 per byte | **Wrong.** 23, with the same 6 dead instructions. |
| B: the table stays, and each reflection is `rev8` + `brev8` + a shift | **Right.** |
| B: the `acc` rotate becomes one `rori` | **Right.** |
| C: 130,000–190,000, about 160,000 | **Right.** 150,155, 6% under the point estimate. |
| C: no table, two `clmul`s, and no reflection | **Right.** One `clmul` and one `clmulh`. |
| C: about 12 per byte | **Close.** 11. |
| D: C's algorithm, and C minus 1,000 to 15,000 | **Right.** C minus 2,000 exactly. |
| D: `rori` saves 2,000, and `pack` may save up to 12,000 more | **Right** about `rori`, which is the whole difference. C does zero-extend with two shifts, but GCC used no `pack`: D keeps the same two. |
| None beats the stated table by more than 5% | **Right.** None beats it at all. |
| C and D between 0.95× and 1.4× of the table | **Right.** 1.09× and 1.07×. |
| B near 1.6× of the table | **Wrong.** 2.12×. |
| The oracle passes in all three | **Right.** |

**None of its falsifiers fired, and that is a gap in them, not a pass.** They covered C's table and
range, B's table, D against C, the stated table and the oracle. None covered B's range, which was
wrong for the same reason as the second assistant's.

**Its hits on C and D came from wide ranges.** C's was ±19% around 160,000, against the second
assistant's ±1.6%. A wide range that holds tests less than a narrow one that misses. The second
assistant's miss is the more informative of the two, because its exact per-byte model is what
isolates the dead instructions.

**The recollection it was built on held.** It predicted from memory of GCC's expanders, without
re-reading them: with Zbc, two carry-less multiplies and no reflection; with Zbkb alone, the table
with `rev8` + `brev8`; with both, Zbc wins. GCC 16.2.0 does all three. The second assistant read
the source, and says the same.

## What this changes

**For the core's ISA: on this workload's CRC, neither extension beats the stated table, which needs
no extension at all.** That is the answer on instruction count, as GCC 16.2.0 compiles it.

- **Zbkb, no.** It speeds up only GCC's own fallback, which reflects each byte into and out of its
  table. The stated table is reflected already and needs neither step, and B retires 2.12× what it
  does. Zbkb's one saving here is the harness's rotate, not the CRC.
- **Zbc roughly ties the table, and does not beat it.** Its loop is 11 instructions per byte against
  the table's 10: C retires 1.09× the stated table, and D 1.07×. What Zbc removes is the 512-byte
  table and a load per byte, and Spike charges a load like any other instruction.
- **Instruction count cannot settle Zbc against the table.** Without its dead zero-extension, C's
  loop would be 9 per byte, one under the table. But Zba's `sh1add` does the table's `slli` + `add`
  in one, which would take the table to 9 as well (untested). What would decide it is a `clmul`'s
  latency and area against a load's latency and 512 bytes of memory. Only a core can price those,
  in Phases 4 and 5, not Spike.
- **Under `decisions/0008`, a compiler's substitution never enters the benchmark.** A carry-less
  multiply CRC would have to be stated in the source, as a form of its own beside `table` and
  `bitwise`. Nothing here decides whether it should be.
- **Whether the CRC matters is still open.** Its share of the decoder's work is unknown until the
  reference decoder exists. This experiment prices the CRC's step per byte, not its weight.
- **Read the compiler's output before crediting or blaming an extension.** GCC 16.2.0's RISC-V CRC
  expansions carry dead instructions: 6 per byte with Zbkb, and 2 with Zbc. That is a fact about
  this compiler, to recheck when the pinned one changes.
