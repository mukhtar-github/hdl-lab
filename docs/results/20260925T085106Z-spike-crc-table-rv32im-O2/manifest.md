# spike-crc-table-rv32im-O2

- **Captured (UTC):** 20260925T085106Z
- **Command:** `make -C bench/rv32 check`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 0s

## Source state

- **Commit:** 24346310085334b705d81e09398e90f8f678d513
- **Branch:** phase0/decide-0008
- **Working tree:** clean

## Tool versions

| Tool | Version |
|---|---|
| iverilog | Icarus Verilog version 13.0 (stable) (v13_0) |
| verilator | Verilator 5.050 2026-07-01 rev vUNKNOWN-built20260701 |
| yosys | not installed |
| spike | Spike RISC-V ISA Simulator 1.1.0 |
| riscv gcc | riscv64-elf-gcc (GCC) 16.2.0 |
| riscv binutils | GNU ld (GNU Binutils) 2.47.20260726 |
| host | Darwin 25.6.0 |

## Configuration

- **Overrides:** none — the Makefile defaults. Everything else is the Makefile at the commit above.
- **Recorded by the run itself** (first lines of `stdout.txt`): the compiler, the effective
  `cflags` (including `-DCRC_IMPL_*` and `-fno-optimize-crc`), and the loaded-image hash.
- **Simulator:** `spike --isa=rv32im`. Metric: `instret` over `[t0, t1)` in `main`.

## Result

`instret = 00021b99` (138,137) · `crc_ref = 0x4cd4` · `acc = 0x33cc525d` · `iters = 0x3e8` · oracle **PASS**

## Notes

- **The reference, as of `decisions/0008`.** The CRC form is stated in the source (the byte-wise reflected table), and `-fno-optimize-crc` means no compiler can substitute its own.
- Work performed = work declared: Spike's instruction log for this image shows 12,012 table loads executed — 1001 CRCs × 12 bytes.
- Not comparable with `experiments/0001`'s -O2 figure: that build ran a table GCC generated, reflecting bits on every byte. The difference between the two is a software change, and must never be quoted as a speedup.
- Result line filled from `stdout.txt` by script, not retyped.
