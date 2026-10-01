# stimulus-coverage

- **Captured (UTC):** 20261001T040355Z
- **Command:** `make -C bench/stimulus test check`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 0s

## Source state

- **Commit:** 61bb911452dc3dfe88a8f58cbbbce188f752665a
- **Branch:** phase0/stimulus-v2
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
- **Format:** `stimulus.bin` version 2, which carries each connection's protocol (`decisions/0014`).
- **What ran:** the unit tests (`stderr.txt`), then `generate.py` and `check.py` (`stdout.txt`).
  The same command as [`20260927T065053Z-stimulus-coverage`](../20260927T065053Z-stimulus-coverage/).

## Result

26 tests OK · stimulus `sha256:855bf4ff…` (14,272 bytes, 484 chunks, 240 frames on 12 connections) · intent `sha256:0e93f887…` · check **PASS**

## Notes

- Against the 2026-09-27 capture of version 1: the stimulus is 12 bytes longer, one
  table byte for each of its 12 connections, and `intent.jsonl` has the same hash,
  `0e93f887…`.
- On 2026-10-01, before this capture, a script generated the coverage stimulus with the code at
  `origin/main` (`513cb2c`) and with this commit's. The two files differed only in the version field
  and the 12-byte table. That comparison is not captured.
- Result line filled from `stdout.txt` and `stderr.txt` by script, not retyped.
