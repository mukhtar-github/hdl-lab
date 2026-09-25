# 0004 — `make run OPT=-O3` re-ran the -O2 binary and reported it under the new flags

- **Date:** 2026-09-25   **Phase:** 0   **Deliberate:** no (found by `experiments/0001` step 4)

- **Symptom:** over an existing -O2 build, `make -C bench/rv32 run OPT=-O3` printed
  `instret = 00099f7d` (630,653) — the -O2 number. Exit 0, no warning, clean tree, right commit.

- **Where to look:** these two captures, side by side. Different commands, byte-identical stdout:

      docs/results/20260925T083727Z-spike-crc-rv32im-O2/      make -C bench/rv32 clean run
      docs/results/20260925T083729Z-evidence-stale-build/     make -C bench/rv32 run OPT=-O3

- **Cause:** the ELF rule in `bench/rv32/Makefile` listed the sources as prerequisites but not the
  flags, so changing a flag never forced a rebuild. And `@` hid the compile line, so the output
  carried no trace of which flags had produced the binary. `capture.sh` recorded the command it was
  given — which was true, and was not the configuration that ran.

- **Fix:** each build now lives in `build/<hash>/`, named by a hash of the compiler's identity,
  every flag and the bytes of every input, so one configuration cannot run another's binary. And
  `make run` prints the effective flags and a SHA-256 of the loaded image before running, so every
  capture records what actually executed.

- **The first fix failed the same way, more quietly.** A flags stamp that the ELF depended on,
  rewritten only when the flags changed. Switching O2 → O3 → O2 with no pause left the O3 binary
  running under the O2 command: this host's GNU make 3.81 compares mtimes to the second, and a
  stamp rewritten in the same second as the last build does not count as newer. Humans rarely
  switch configurations within a second. A capture script does it every time. Hence no
  timestamps at all.
