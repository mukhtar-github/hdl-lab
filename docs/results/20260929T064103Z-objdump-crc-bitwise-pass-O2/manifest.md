# objdump-crc-bitwise-pass-O2

- **Captured (UTC):** 20260929T064103Z
- **Command:** `riscv64-elf-objdump -h -d bench/rv32/build/3edef443630f/crc_itu_ref.elf bench/rv32/build/2295c84e56b3/crc_itu_ref.elf bench/rv32/build/c6fc43358c6e/crc_itu_ref.elf bench/rv32/build/e36625f0473e/crc_itu_ref.elf`
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

- **What:** section headers and full disassembly (`-h -d`) of `experiments/0002`'s four ELFs, in
  the order A, B, C, D. Each is the one the run just before it built at this commit. A build
  directory is named by a hash of the compiler's identity, the flags and the input bytes, and
  each matches the first line of its run's `stdout.txt`:
  - **A** `3edef443630f`, from [`20260929T064033Z-spike-crc-bitwise-pass-rv32im-O2`](../20260929T064033Z-spike-crc-bitwise-pass-rv32im-O2/)
  - **B** `2295c84e56b3`, from [`20260929T064034Z-spike-crc-bitwise-pass-rv32im_zbkb-O2`](../20260929T064034Z-spike-crc-bitwise-pass-rv32im_zbkb-O2/)
  - **C** `c6fc43358c6e`, from [`20260929T064034Z-spike-crc-bitwise-pass-rv32im_zbc-O2`](../20260929T064034Z-spike-crc-bitwise-pass-rv32im_zbc-O2/)
  - **D** `e36625f0473e`, from [`20260929T064035Z-spike-crc-bitwise-pass-rv32im_zbkb_zbc-O2`](../20260929T064035Z-spike-crc-bitwise-pass-rv32im_zbkb_zbc-O2/)

## Result

`.rodata`: A `0x24c` · B `0x24c` · C `0x4c` · D `0x4c`. Sweep byte loop: A 51 · B 23 · C 11 · D 11 instructions.

## Notes

- `0x24c − 0x4c = 0x200`: the 512-byte table.
- The byte loop is the backward branch inside the sweep. Its count, the sweep's other
  instructions and the ones run once rebuild each run's `instret` exactly:
  once + 12 × loop + 1000 × (sweep overhead + 12 × loop).
- Result line filled from `stdout.txt` by script, not retyped.
