# 0001 — ripple_adder produces wrong sums whenever a carry should leave bit 0

- **Date:** 2026-09-13   **Phase:** 0   **Deliberate:** yes (README Exercise 2)

- **Symptom:** `make adder` reports **280 failures out of 512** exhaustive cases.
  First failing case: `FAIL: 0 + 1 + 1 -> got 0, want 2`.
  Note the shape of the failures — `0+1+1`, `0+3+1`, `0+5+1`, `0+7+1` … all
  short by exactly 2. Cases like `0+0+1` and `0+1+0` still pass. The design is
  not uniformly broken; something specific is being lost.

- **Signal to watch:** `tb_adder.u_add.carry[4:0]` at **t = 3 ns**.

  At 3 ns the inputs are `a=0000`, `b=0001`, `cin=1`. Work out by hand what bit 0
  must produce, then read what `carry` actually holds at that instant. The
  individual per-bit adders are dumped too — `tb_adder.u_add.g_bit[0].u_fa.cout`
  is the one feeding the value in question.

  Open with `surfer docs/bugs/0001-adder-wrong-sums/broken.vcd`. Add `a`, `b`,
  `cin`, `carry`, `sum`, `cout`. Time unit is 1 ns per case; case N sits in the
  window `[N ns, N+1 ns)`, so 3 ns is the fourth case.

- **Cause:**
  <!-- Fill this in AFTER reading the waveform, not before, and not from the
       patch. The patch says which line changed; the waveform says what that
       line does to the circuit. Those are different answers, and only the
       second one is the Phase 0 gate. -->

- **Reproduce:** `git apply docs/bugs/0001-adder-wrong-sums/broken.patch`, then
  `make adder`. Revert with `git apply -R` on the same file.

- **Files:** `broken.vcd` (the failing waveform), `stdout.txt` (all 280 failures),
  `broken.patch` (the one-line change that produced it).
