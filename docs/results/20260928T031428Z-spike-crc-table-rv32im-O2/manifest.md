# spike-crc-table-rv32im-O2

- **Captured (UTC):** 20260928T031428Z
- **Command:** `make -C bench/rv32 check`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 0s

## Source state

- **Commit:** 795d58f4db12915f1af28071ebd4b9e6503b4063
- **Branch:** phase0/decide-0009
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

- **Overrides:** none — the Makefile defaults, i.e. the `decisions/0008` reference.
- **Recorded by the run itself** (first lines of `stdout.txt`): compiler, effective `cflags`, and
  the loaded-image hash.
- **What changed since the last reference capture:** a comment in `htif.h`, one of the build's
  hashed inputs, corrected by `decisions/0009`. So the build directory is new (`eba9cb77278e`).

## Result

`instret = 00021b99` (138,137) · image `sha256:1baf3e07…` · oracle **PASS**

## Notes

- Evidence that the comment change moved nothing. The image hash and the count are the same as
  `20260926T060728Z-spike-crc-table-rv32im-O2`'s.
- Result line filled from `stdout.txt` by reading it, not retyped from memory.
