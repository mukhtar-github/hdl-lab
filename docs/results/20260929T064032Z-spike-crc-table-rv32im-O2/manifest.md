# spike-crc-table-rv32im-O2

- **Captured (UTC):** 20260929T064032Z
- **Command:** `make -C bench/rv32 check`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 1s

## Source state

- **Commit:** 5333c7f32ea433657afb3b01fe7a432bd7fe2fdf
- **Branch:** phase0/experiment-0002-result
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

- **Overrides:** none. The Makefile defaults: the stated table, the `decisions/0008` reference.
- **Recorded by the run itself** (first lines of `stdout.txt`): the compiler, the effective
  `cflags`, and the loaded-image hash.
- **Simulator:** `spike --isa=rv32im`. Metric: `instret` over `[t0, t1)` in `main`.

## Result

`instret = 00021b99` (138,137) · `crc_ref = 0x4cd4` · `acc = 0x33cc525d` · `iters = 0x3e8` · oracle **PASS**

## Notes

- A control for `experiments/0002`, run at the same commit as B, C and D (`5333c7f`). Same image
  (`1baf3e07…`) and count as the capture 0002 cites, so the toolchain has not moved:
  [`20260925T085106Z-spike-crc-table-rv32im-O2`](../20260925T085106Z-spike-crc-table-rv32im-O2/).
- Result line filled from `stdout.txt` by script, not retyped.
