# 0002 — What does GCC's CRC pass emit when the target has Zbkb or Zbc?

- **Date opened:** 2026-09-25
- **Phase:** 0
- **Status:** Open — **joint prediction.** Neither party has built or run any configuration below.
  Both hypotheses are committed before anything is built.

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

Written and sealed on 2026-09-25, before the author wrote the section above, and before any
Zbkb or Zbc build existed. Only its hash is committed here. The text sits in a git object behind a
**local** tag, which `git push` does not send, so it cannot be read by accident. Reading it
deliberately before your own hypothesis is committed would spend the experiment.

```
sha256  13361923f43677df4e03ffd5cca81c914a3af8c477c019526c3f1a3de6a65e2f
tag     sealed/0002-claude-prediction          (local only)
open    git cat-file blob sealed/0002-claude-prediction
verify  git cat-file blob sealed/0002-claude-prediction | shasum -a 256
```

When it is opened, the text is committed into this section verbatim and the hash is checked in the
same commit. If the hash does not match, the prediction is void and that is recorded here.

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

<!-- Link the captures. Never retype a number by hand. -->

## Outcome

<!-- Both hypotheses judged, plainly. A wrong one stays standing above. -->

## What this changes

<!-- For the core's ISA: which extension earns its area on this workload's CRC? -->
