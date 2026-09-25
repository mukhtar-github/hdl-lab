# spike-crc-rv32im-O3-no-early-unroll

- **Captured (UTC):** 20260925T084337Z
- **Command:** `make -C bench/rv32 check 'OPT=-O3 -fdisable-tree-cunrolli'`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 0s

## Source state

- **Commit:** de7758b281cb6685c7a0554340c2ec1c3a28da97
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

- **Overrides:** 'OPT=-O3 -fdisable-tree-cunrolli'. Everything else is the Makefile at the commit above.
- **Recorded by the run itself** (first lines of `stdout.txt`): the compiler, the effective
  `cflags`, and `image`, the SHA-256 of the loaded image — which identifies what executed.
- **Simulator:** `spike --isa=<ARCH>`. Metric: `instret` over `[t0, t1)` in `main`.

## Result

`instret = 0001a074` (106,612) · `crc_ref = 0x4cd4` · `acc = 0x33cc525d` · `iters = 0x3e8` · oracle **PASS**

## Notes

- Early complete unrolling disabled, so the CRC pass fires at -O3 — and the CRC of the 10 bytes that never change is hoisted out of the sweep: 2 table loads per iteration instead of 12, about a sixth of the declared CRC work. **Same reference lines as every other build.** Evidence that `acc` verifies the answer, not the work behind it.
- Result line filled from `stdout.txt` by script, not retyped.
