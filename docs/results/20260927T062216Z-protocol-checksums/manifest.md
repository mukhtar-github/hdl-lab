# protocol-checksums

- **Captured (UTC):** 20260927T062216Z
- **Command:** `python3 bench/evidence/checksums.py`
- **Run from:** `./` (relative to the repository root)
- **Exit status:** 0
- **Wall time:** 0s

## Source state

- **Commit:** d4515ce0a5238fee2179d2a6a450897b0ea7f428
- **Branch:** phase0/checksum-evidence
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
- **Inputs:** `reference/`, gitignored. Traccar files are from commit
  `847edd2c8c4dcc47426fb76b7800b342dea3cde6`; the GT06 PDF is v1.8.1. `stdout.txt` lists the SHA-256
  of each one read. The refetch recipe is in `reference/README.md`.
- **The vendor example frames are transcribed in `bench/evidence/checksums.py`,** with PDF page
  numbers. The PDF itself is hashed, not parsed.

## Result

Device-sent vendor examples verifying as printed: **1 of 3**. Traccar receive-path checksum checks:
**0**. Traccar test inputs failing their checksum: GT06 **27 of 185**, JT808 **11 of 114**.

## Notes

- Section 3's frames are the inputs to Traccar's unit tests, **not a sample of traffic**. They may
  have been edited, for example to anonymise an IMEI, without the checksum being recomputed. The
  counts say what a validating decoder would do to Traccar's tests, not how often devices send
  bad checksums.
- Result line filled from `stdout.txt` by reading it, not by a script.
