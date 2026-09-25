# spike-crc-rv32i-O2

- **Captured (UTC):** 20260925T084334Z
- **Command:** `make -C bench/rv32 check ARCH=rv32i`
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

- **Overrides:** ARCH=rv32i. Everything else is the Makefile at the commit above.
- **Recorded by the run itself** (first lines of `stdout.txt`): the compiler, the effective
  `cflags`, and `image`, the SHA-256 of the loaded image — which identifies what executed.
- **Simulator:** `spike --isa=<ARCH>`. Metric: `instret` over `[t0, t1)` in `main`.

## Result

`instret = 00099f7d` (630,653) · `crc_ref = 0x4cd4` · `acc = 0x33cc525d` · `iters = 0x3e8` · oracle **PASS**

## Notes

- `experiments/0001` Method step 3. **Same image hash as `spike-crc-rv32im-O2`**: the compiler never used the M extension. The two ELFs differ only in their ISA attribute string.
- Result line filled from `stdout.txt` by script, not retyped.
