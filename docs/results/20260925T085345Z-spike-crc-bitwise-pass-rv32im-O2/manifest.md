# spike-crc-bitwise-pass-rv32im-O2

- **Captured (UTC):** 20260925T085345Z
- **Command:** `make -C bench/rv32 check CRC_IMPL=bitwise ALGOFLAGS=`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 0s

## Source state

- **Commit:** 8d1e890ba517e94e0e6ed3f7ebe3028bf1c2e7df
- **Branch:** phase0/experiment-0002
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

- **Overrides:** `CRC_IMPL=bitwise ALGOFLAGS=` — the bitwise definition, with GCC's CRC pass
  **deliberately allowed**. An experiment configuration, never a reference (`decisions/0008`).
- **Recorded by the run itself** (first lines of `stdout.txt`): the compiler, the effective
  `cflags`, and the loaded-image hash.
- **Simulator:** `spike --isa=rv32im`. Metric: `instret` over `[t0, t1)` in `main`.

## Result

`instret = 00099f7d` (630,653) · `crc_ref = 0x4cd4` · `acc = 0x33cc525d` · `iters = 0x3e8` · oracle **PASS**

## Notes

- Baseline **A** of `experiments/0002`, captured before either hypothesis was written. It is the
  rv32im point that Zbkb and Zbc are measured against.
- Same count as `experiments/0001`'s -O2 build (630,653) with a different image: the 0008 source
  changes moved code without changing what executes per byte.
- Result line filled from `stdout.txt` by script, not retyped.
