# spike-crc-table-rv32im-O2

- **Captured (UTC):** 20260926T060728Z
- **Command:** `make -C bench/rv32 check`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 1s

## Source state

- **Commit:** 55386db8182705b948122ff66119cb7c21a046f4
- **Branch:** phase0/spike-commitlog
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
- **Simulator:** Spike 1.1.0 (`530af85`), **rebuilt 2026-09-26 with `--enable-commitlog`**. The
  version line cannot show that, so it is recorded in `bench/rv32/README.md`.

## Result

`instret = 00021b99` (138,137) · `crc_ref = 0x4cd4` · `acc = 0x33cc525d` · `iters = 0x3e8` · oracle **PASS**

## Notes

- Evidence that the rebuild moved nothing. Same image hash and the same count as
  `20260925T085106Z-spike-crc-table-rv32im-O2`, which the previous Spike binary produced.
- Result line filled from `stdout.txt` by script, not retyped.
