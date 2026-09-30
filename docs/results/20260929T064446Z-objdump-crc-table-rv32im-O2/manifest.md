# objdump-crc-table-rv32im-O2

- **Captured (UTC):** 20260929T064446Z
- **Command:** `riscv64-elf-objdump -h -d bench/rv32/build/eba9cb77278e/crc_itu_ref.elf`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 0s

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

- **What:** section headers and full disassembly (`-h -d`) of the `decisions/0008` reference ELF,
  build directory `eba9cb77278e`, which matches the first line of [`20260929T064032Z-spike-crc-table-rv32im-O2`](../20260929T064032Z-spike-crc-table-rv32im-O2/), run at this commit.

## Result

`.rodata = 0x24c` (the stated 512-byte table) · sweep byte loop: 10 instructions

## Notes

- Captured for `experiments/0002`'s comparison against the stated table. The loop count rebuilds
  the run's `instret` exactly: 17 + 12 × 10 + 1000 × (18 + 12 × 10) = 138,137.
- Result line filled from `stdout.txt` by script, not retyped.
