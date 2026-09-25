# spike-crc-rv32im-O2

- **Captured (UTC):** 20260925T083727Z
- **Command:** `make -C bench/rv32 clean run`
- **Exit status:** 0
- **Wall time:** 1s

## Source state

- **Commit:** 1094b20059b62130262aa4ae27eaa248af2d427a
- **Branch:** phase0/experiment-0001
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

- **Program:** `bench/rv32/crc_itu_ref.c` — CRC-16/X-25 over one 12-byte GT06 login region, then a
  1000-iteration sweep of the serial field. Measured window: `[t0, t1)` in `main`.
- **Build:** the Makefile defaults at this commit — `ARCH=rv32im ABI=ilp32 OPT=-O2`, plus
  `-mcmodel=medany -ffreestanding -fno-builtin`. No `-mtune`, so GCC's built-in default applies
  (`rocket` — found afterwards, in `experiments/0001` step 4).
- **Simulator:** `spike --isa=rv32im`. Metric: `instret`, which on Spike equals `cycle`.
- **What this capture cannot prove:** which flags built the binary. The compile line is hidden by
  `@` and no hash of the image is recorded. Captured with the harness as it stood, on purpose.

## Result

`instret = 0x00099f7d` (630,653) · `crc_ref = 0x4cd4` · `acc = 0x33cc525d` · `iters = 0x3e8`

## Notes

- `experiments/0001` Method step 1, taken at the hypothesis commit before any harness change.
- `clean` is part of the command because `build/` still held an **rv32i** binary from the earlier
  sweep. Without it, this capture would have measured that binary under an rv32im label.
- At -O2 this compiler's `-foptimize-crc` pass is on: the CRC that runs is a 512-byte lookup table
  GCC generated, not the loop in the source. See `experiments/0001` step 4.
