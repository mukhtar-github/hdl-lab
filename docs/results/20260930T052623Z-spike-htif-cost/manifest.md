# spike-htif-cost

- **Captured (UTC):** 20260930T052623Z
- **Command:** `make -C bench/rv32 htif-cost`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 61s

## Source state

- **Commit:** 752930bd2e033bf9ec34a89c3f0ddf9119d95b94
- **Branch:** phase0/decide-0014
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

- **Overrides:** none. The target builds four ELFs from `bench/rv32/htif_cost.c`, each rebuilt on
  every run, with the flags printed on `stdout.txt`'s second line.
- **Modes:** `putchar`, one console command per character (`htif.c`); `write-1` and `write-4096`, the
  syscall proxy's `SYS_write` with 1 or 4,096 characters a command; `compute`, 100,000,000
  iterations of a loop with no HTIF traffic.
- **Simulator:** `spike --isa=rv32im`. Metric: `instret` over each mode's loop, `[t0, t1)` in `main`.
  Wall time: `/usr/bin/time -p`, the whole Spike run.

## Result

- `putchar` 511,991,787 instructions for 102,400 characters in 102,400 commands, 4,999.92 a command and 4,999.92 a character, 19.15 s
- `write-1` 511,996,676 instructions for 102,400 characters in 102,400 commands, 4,999.97 a command and 4,999.97 a character, 23.32 s
- `write-4096` 121,674 instructions for 102,400 characters in 25 commands, 4,866.96 a command and 1.19 a character, 0.08 s
- `compute` 400,000,005 instructions in 17.02 s, 23.5 million a second

## Notes

- The host is an Apple M2 (`sysctl machdep.cpu.brand_string`), which `capture.sh` does not record.
  Wall times depend on it. The instruction counts do not: a trial run before this capture, at the
  same source, printed the same four counts.
- The printing modes' counts are set by Spike's `INTERLEAVE` = 5,000 (`riscv/sim.h:104`): the host
  reads `tohost` once per 5,000 instructions, and the program spins until it does.
- The last line of `stdout.txt` is the target's own check that the three printing modes printed the
  same 102,400 bytes. It failed as it should when one mode flipped a bit at byte 8,193.
- Result lines filled from `stdout.txt` by script, not retyped.
