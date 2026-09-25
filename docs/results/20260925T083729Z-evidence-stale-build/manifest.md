# evidence-stale-build

- **Captured (UTC):** 20260925T083729Z
- **Command:** `make -C bench/rv32 run OPT=-O3`
- **Exit status:** 0
- **Wall time:** 0s

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

- **Same commit and same `build/` directory** as `20260925T083727Z-spike-crc-rv32im-O2`, run two
  seconds later **without** `make clean`.
- **Typed:** `OPT=-O3`. **Built:** nothing. make found `build/crc_itu_ref.elf` newer than every
  source file and re-ran the -O2 binary. The ELF rule's prerequisites were the sources, not the flags.

## Result

`instret = 0x00099f7d` (630,653) — the **-O2** number, under a command that says -O3.

## Notes

- **Preserved evidence, not a measurement.** Captured deliberately before the fix — see
  `docs/bugs/0004-stale-build-reports-the-wrong-configuration/`.
- Every field in this manifest is true: command, commit, clean tree, exit 0. The result is still
  not what the command says. Nothing in stdout records the flags, so nothing here can reveal it.
