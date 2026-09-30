# gcc-optimized-crc-bitwise-pass-rv32im_zbkb-O2

- **Captured (UTC):** 20260930T025157Z
- **Command:** `riscv64-elf-gcc -march=rv32im_zbkb -mabi=ilp32 -mtune=rocket -mcmodel=medany -O2 -DCRC_IMPL_bitwise -ffreestanding -fno-builtin -Wall -Wextra -Werror -Ibench/rv32 -S -o /dev/null -fdump-tree-optimized=stdout bench/rv32/crc_itu_ref.c`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 0s

## Source state

- **Commit:** d981908e84887d19fd45adfa271d1c6118c21bde
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

- **What:** GCC's last tree-level form (`-fdump-tree-optimized`, to stdout) of build **B** of
  `experiments/0002`. The flags are B's effective `cflags`, from the first lines of its run's
  `stdout.txt`, plus `-Ibench/rv32` for `htif.h` and `-S -o /dev/null`: no object is written.
- The source and flags are the ones B was built from: nothing under `bench/` changed between
  `5333c7f`, where B was captured, and this commit.

## Result

`crc_37 = _35 ^ crc_79;` then `crc_82 = .CRC_REV (crc_37, 0, 4129);` (lines 42–43; again at 67–68): data operand `0`, polynomial 4129 = `0x1021`

## Notes

- Captured for `experiments/0002`, to check a reading of B's disassembly. B's byte loop reflects
  the constant 0 and XORs it into the table index (`li`, `brev8`, `zext.b`, `xor`). This is where
  the 0 comes from: the source XORs each byte into the CRC before its bit loop, so the CRC the
  pass recognises is handed no data of its own.
- The IR for `rv32im` (A) and `rv32im_zbc` (C) carries the same call, with the same data operand
  `0`, so only the expansion differs between builds. That check was run by hand and is not part
  of this capture.
- Result line filled from `stdout.txt` by script, not retyped.
