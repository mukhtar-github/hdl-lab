# spike-crc-table-rv32im-O1

- **Captured (UTC):** 20260926T062541Z
- **Command:** `make -C bench/rv32 check OPT=-O1`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 0s

## Source state

- **Commit:** 977d061d418e6e39bd4cc0f4af3088d529d13493
- **Branch:** phase0/test-0008-prediction
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

- **Overrides:** `OPT=-O1`. Otherwise the `decisions/0008` reference: `CRC_IMPL=table`,
  `-fno-optimize-crc`, rv32im, `-mtune=rocket`.
- **Recorded by the run itself** (first lines of `stdout.txt`): compiler, effective `cflags`, and
  the loaded-image hash.
- **Simulator:** Spike 1.1.0 (`530af85`), built with `--enable-commitlog`.

## Result

`instret = 00022f27` (143,143) · `crc_ref = 0x4cd4` · `acc = 0x33cc525d` · `iters = 0x3e8` · oracle **PASS**

## Notes

- Tests the prediction in `decisions/0008`: within ±20% of the -O2 figure (138,137). This run is
  +3.6%, inside the band. The outcome is recorded at the end of 0008.
- Result line filled from `stdout.txt` by script, not retyped.
