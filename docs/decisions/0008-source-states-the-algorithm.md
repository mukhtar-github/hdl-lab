# 0008 — The reference binary runs the algorithm, and the work, that its source states

- **Date:** 2026-09-25
- **Status:** Accepted
- **Phase:** 0 (policy), binding on every reference result

## Context

`experiments/0001` found that the reference binary was not running the reference program. At -O2,
the Makefile default, GCC 16's CRC-recognition pass (`-foptimize-crc`, new in GCC 15) matched
`crc_itu_ref.c`'s bitwise loop. It inferred the polynomial and replaced the loop with a 512-byte
lookup table, wrapped in bit reflection on every byte. The printed reference lines were correct.
The algorithm that ran does not appear in the source.

That breaks the promise `0004` rests on: "the same program, unmodified, runs on Spike, on a
Cortex-M4, and eventually on our core". If the compiler chooses the algorithm, the same source
runs different algorithms under different compilers:

- GCC 14 has no such pass.
- GCC 16 produces a table with reflection.
- A later compiler might produce a carry-less-multiply expansion.

The workload would change with the toolchain, and a reference whose workload moves settles no
argument.

0001 found a second, related failure. With early unrolling disabled, -O3 hoisted the CRC of the
ten bytes that never change out of the sweep. It did a sixth of the declared work and still printed
every reference line correctly. The reference lines verify answers, never work. So the source has
to state the work too, rather than leave it to the optimiser.

The numbers that frame the choice, all at -O2 on rv32im:

| What runs | `instret` | Capture |
|---|---:|---|
| the bitwise loop as written (`-fno-optimize-crc`) | 942,942 | [`…-rv32im-O2-no-crc-pass`](../results/20260925T084335Z-spike-crc-rv32im-O2-no-crc-pass/) |
| GCC's substituted table, reflecting every byte | 630,653 | [`…-rv32im-O2`](../results/20260925T084333Z-spike-crc-rv32im-O2/) |
| the textbook reflected table, stated in the source | 138,137 | [`…-table-rv32im-O2`](../results/20260925T085106Z-spike-crc-table-rv32im-O2/) |

## Options considered

1. **Keep -O2 as it was, and declare the compiler.** This is honest if GCC 16.2.0 and the pass are
   recorded, and "what a real build does" has a claim to being the realistic baseline. It lost
   because the workload then moves with the compiler version. The same source, at the same flags,
   runs different algorithms under GCC 14 and GCC 16, and a Cortex-M4 compiler would pick its own.
   0004's "same program" would shrink to "same source text", which is not the same thing.

2. **Keep the bitwise source, and pin `-fno-optimize-crc`.** This is the smallest change, and it
   makes the source true. It lost because it makes the weakest reasonable software the
   denominator. 0001 step 4 requires "the strongest baseline, named". Against the bitwise loop
   (942,942), any CRC assist on the core would look about 7× better than against ordinary table
   software (138,137), before the hardware had done anything.

3. **State the byte-wise reflected table in the source, and pin `-fno-optimize-crc`.** Chosen.
   - It is the ordinary software form of this CRC: one lookup per byte, and no bit reflection,
     because the table is built for the reflected polynomial.
   - No CRC-recognition pass matches it. Verified: with the pass allowed, the image is
     byte-identical. So the source form protects the algorithm even on compilers that have no such
     flag.
   - [ ] Search results report that the GT06 protocol document's own reference code is this
     algorithm: `GetCrc16`, with a `crctab16` table beginning `0x0000, 0x1189, 0x2312, 0x329B`.
     This project has not read that page yet, and the decision does not rest on it.

4. **Hand-written assembly.** It lost because the benchmark is C compiled for three targets.
   Assembly would need rewriting for each ISA, and it would measure its author.

5. **Both forms as two reference kernels.** This lost for the *reference*, because `0004`
   promises one documented denominator. The bitwise form stays in the source as the definition and
   as a subject for experiments. It is never quoted as the reference, the same split as `0007`'s
   stateless/cached.

## Decision

**The reference binary runs the algorithm and the work that its source states. The compiler
chooses how to compile them, never which algorithm runs or how much work it does.**

Concretely, for `bench/rv32` now and for the reference decoder later:

- **CRC-ITU is the byte-wise reflected table, stated in the source.** `crc_itu_ref.c` carries it
  as `CRC_IMPL=table`, the reference. The bitwise loop stays as `CRC_IMPL=bitwise`, the definition.
  Building without stating a form is an `#error`.
- **`-fno-optimize-crc` is part of every reference build** (`ALGOFLAGS` in the Makefile). An
  experiment that clears it must say so, and its number is never quoted as a reference.
- **Each frame arrives as memory the compiler cannot predict.** In the sweep, this is a memory
  clobber. In the benchmark, it is the rule `bench/README` already carries: stimulus is data the
  compiler cannot see at compile time.
- **The general rule.** A transformation that replaces the stated algorithm, or reduces the
  stated work, is pinned off, or the image is checked for it. A transformation that changes only
  *how* the stated algorithm is compiled is configuration, declared like any other.

## Consequences

- **The reference number changes, and the old one retires.** The table reference retires 138,137
  at -O2. 0001's -O2 build retired 630,653, running GCC's table. The ~4.6× between them is a
  *software* change. It is exactly the kind of number 0001 says must never be quoted as a speedup,
  and it now has a record saying so.
- **Work performed equals work declared, and this is checked.** Spike's instruction log for the
  reference image shows 12,012 table loads executed: 1001 CRCs × 12 bytes. 0001's hoisting build,
  rebuilt with the clobber and the pass allowed, also executes 12,012. To reproduce, run
  `spike -l --isa=rv32im <elf> 2>&1 >/dev/null | grep -c ' lhu '`, where `<elf>` is the path
  `make run` prints.
- **0004's Cortex-M4 baseline becomes meaningful.** "Same program, unmodified" now pins the
  algorithm, not just the text. The M4 compiler must accept `-fno-optimize-crc`, which requires
  GCC 15 or later. An older compiler has no such pass, so there the flag is dropped and that fact is
  recorded. Whether an older GCC rejects the flag is untested.
- **Harder:** questions about the textbook CRC on this ISA now need `CRC_IMPL=bitwise` stated
  explicitly. `experiments/0002` does this.
- **Forecloses** letting a compiler's CRC pass count as "the software baseline". If a later
  compiler's expansion beats the stated table, that is an experiment's result, not a new reference.
- **Revisit if** the core gains a CRC or carry-less-multiply instruction. The table stays the
  reference, and the accelerated build is separate and declared. Also revisit if the GT06
  document's reference code turns out to be something other than this table.

## Predictions

Recorded before any of these builds existed.

**The stated table is far less sensitive to optimisation level than the bitwise program was.**
At -O1, -O3 and -Os, its instruction count stays within 20% of the -O2 figure (138,137). For
comparison, the bitwise program's -O1 retired 25% more than its -O2, and a single pass toggle moved
its -O3 by 6×. If any of the three lands outside ±20%, stating the algorithm did less to stabilise
the reference than this decision assumes.
