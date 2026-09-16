# 0002 — ripple_adder: unknown fault (Phase 0 gate, unsolved)

- **Date:** 2026-09-16   **Phase:** 0   **Deliberate:** yes (planted, mechanism withheld)

- **Symptom:** `make adder` reports **128 failures out of 512** exhaustive cases.
  First failing case: `FAIL: 0 + 7 + 1 -> got 24, want 8`.
  All 128 are in `stdout.txt`.

- **Signal to watch:** *withheld — finding it is the exercise.*

  The method, not the answer:

  1. **Read `stdout.txt` before opening any waveform.** 128 of 512 is a quarter
     of the input space, not all of it. Something specific survives and something
     specific doesn't. Compare `got` against `want` across many lines and look for
     what is constant about the difference. The failure pattern usually names the
     bit position, and the bit position names the signal.
  2. Convert the first failing case to a simulation time. The testbench loops
     `ia` outermost, then `ib`, then `ic`, one case per nanosecond:

         index = ia*32 + ib*2 + ic        time = index ns

  3. Go there in the waveform and find the **earliest signal that contradicts its
     own inputs.** Not the first signal that looks wrong — downstream signals look
     wrong too, and they are innocent. The fault is where output disagrees with
     the inputs that same signal was handed.

- **Cause:**
  <!-- Yours to write. State the mechanism — what the circuit now does and does
       not do — not which line changed. -->

- **Solution:** `SPOILER-solution.patch.b64` holds the change that produced this,
  base64-encoded so it cannot be read by accident. Decode it only after writing
  your answer above:

      base64 -d docs/bugs/0002-adder-unknown/SPOILER-solution.patch.b64

- **Reproduce:** decode the patch, `git apply` it, `make adder`. `git apply -R` reverts.

- **Files:** `broken.vcd`, `stdout.txt`, `SPOILER-solution.patch.b64`.
