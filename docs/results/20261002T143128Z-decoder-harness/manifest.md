# decoder-harness

- **Captured (UTC):** 20261002T143128Z
- **Command:** `make -C bench/decoder check mutate`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 14s

## Source state

- **Commit:** 30948222b72bc620badfae9063467bb028c32ddf
- **Branch:** phase0/decoder-harness
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
- **What ran:** the coverage stimulus for seeds 1 and 2 (`bench/stimulus`). Then `make expect` for
  `stub.c` and for `format_test.c`, both on seed 1, and the decoder image for seeds 1 and 2. Then
  `mutate.py`'s 16 faults.
- **Parameters:** `bench/stimulus/params/coverage.json`. **Coverage only:** nothing about traffic
  may be quoted from these stimuli.
- **Simulator:** `spike --isa=rv32im`. The harness is `decisions/0014`'s, at this commit.

## Result

`stub.c`: 496 records match · `format_test.c`: 10 records match · two stimuli, one decoder image `sha256:bb1aa38a…` · `make mutate`: 16 of 16 faults caught

## Notes

- **Never quote the two `instret` lines** (98,931 for `stub.c` and 7,133 for
  `format_test.c`). They measure the test decoders, not decoding.
- **The chunk-walk fault ends with `trap: mcause 4, mepc 0x80000e78`**, a misaligned load. Before
  the harness had a trap handler, the same fault hung Spike for more than 10 minutes, until it was
  stopped by hand. That run was not captured.
- Result line filled from `stdout.txt` by script, not retyped.
