# spike-crc-table-rv32i-O2

- **Captured (UTC):** 20260928T041029Z
- **Command:** `make -C bench/rv32 check ARCH=rv32i`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 0s

## Source state

- **Commit:** da6081ac2fb0f2bc6e28a7929d32363556f6f74c
- **Branch:** phase0/amend-0009-0010
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

- **Overrides:** `ARCH=rv32i`. Everything else is the Makefile default, i.e. the `decisions/0008`
  reference built for RV32I instead of RV32IM. `make run` passes `--isa=rv32i` to Spike, so Spike
  ran it as an RV32I hart.
- **Why:** `decisions/0009`'s amendment asks whether the harness can run on a Phase 2 core, which
  has no `M` extension.
- **Recorded by the run itself** (first lines of `stdout.txt`): compiler, effective `cflags`, and
  the loaded-image hash.

## Result

image `sha256:1baf3e07…`, byte-identical to the RV32IM reference · `instret = 00021b99` (138,137) ·
oracle **PASS**

## Notes

- The reference image contains no `M` instruction. `objdump -d` on the RV32IM build found none of
  `mul`/`mulh*`/`div*`/`rem*`; that check was run by hand and is not part of this capture. The
  identical image is the stronger evidence.
- Result line filled from `stdout.txt` by reading it.
