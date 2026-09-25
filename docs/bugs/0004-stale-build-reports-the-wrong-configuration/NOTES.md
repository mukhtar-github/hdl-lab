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

- **Fix:** the next commit on the branch. The flags are written to a stamp file that the ELF depends
  on, rewritten only when they change; `make run` prints the effective flags and a SHA-256 of the
  loaded image before running, so every capture now records what actually executed.
