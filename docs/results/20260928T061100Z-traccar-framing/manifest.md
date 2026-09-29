# traccar-framing

- **Captured (UTC):** 20260928T061100Z
- **Command:** `python3 bench/evidence/framing.py`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 1s

## Source state

- **Commit:** 61f2f9079d1d4d60b56097cb6a43e646f006553b
- **Branch:** phase0/decide-0011
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

- **Interpreter:** `/usr/bin/python3`, Python 3.9.6 (not in the tool table above).
- **Inputs:** `reference/`, gitignored: Traccar's `Gt06FrameDecoder.java`, `Jt808FrameDecoder.java`,
  `Gt06FrameDecoderTest.java` and `Jt808FrameDecoderTest.java`, at commit
  `847edd2c8c4dcc47426fb76b7800b342dea3cde6`. `stdout.txt` lists the SHA-256 of each one read. The
  refetch recipe is in `reference/README.md`.
- **Frames:** made by `bench/stimulus`'s encoders at the commit above. Section 2 from SplitMix64
  seed 8; section 3 is `params/coverage.json`, seed 1, generated in process.
- **Netty is not pinned.** The port uses its documented semantics for `getByte`, `indexOf`,
  `readRetainedSlice` and a `decode()` that returns null. They are listed in the script's docstring.

## Result

The port reproduces **12 of 12** vectors in Traccar's framer tests, and each of **3** deliberately
broken ports fails at least one. On the coverage stimulus, with `Jt808FrameDecoder.java:53`'s
sentence length corrected, **12 of 90** whole GT06 frames and **37 of 108** whole JT808 frames do not
come out whole.

## Notes

- **Section 3's counts are not a rate.** `coverage.json` chooses its fault rates so that every class
  occurs. The counts show that the mechanism of section 2 occurs in the benchmark's own stimulus, and
  nothing about how often it would in traffic.
- Traccar's test vectors are real-device and forum hex (`bench/README` rule 2a). Only counts of them
  are printed.
- Result filled from `stdout.txt` by reading it, not by a script.
