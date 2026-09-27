# stimulus-coverage

- **Captured (UTC):** 20260927T065053Z
- **Command:** `make -C bench/stimulus test check`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 1s

## Source state

- **Commit:** 2604e978d204618832469910efa7d3890032b2c5
- **Branch:** phase0/stimulus-generator
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

- **Interpreter:** `/usr/bin/python3`, Python 3.9.6 (not in the tool table above).
- **Parameters:** `bench/stimulus/params/coverage.json`, seed 1, the Makefile's defaults.
  **Coverage only:** every value in that file is an assumption chosen so that every class occurs.
  Nothing about traffic may be quoted from this stimulus.
- **What ran:** the unit tests (`stderr.txt`), then `generate.py` and `check.py` (`stdout.txt`).
  The generator's own `manifest.json` also recorded this commit and a clean tree.

## Result

23 tests OK · stimulus `sha256:dfd8239b…` (14,260 bytes, 484 chunks, 240 frames) · check **PASS** ·
JT808 escape pairs: 28 in 8,327 frame bytes.

## Notes

- This commit changed only the summary lines. A capture of the same command at the previous commit,
  `22ea3a1`, printed the same stimulus hash, and was discarded because it lacked the escape line.
  To see it again: check out `22ea3a1` and run `make -C bench/stimulus`.
- Result line filled from `stdout.txt` and `stderr.txt` by reading them, not by a script.
