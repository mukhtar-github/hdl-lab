# 0002 — ripple_adder: carry-out tapped one bit early (Phase 0 gate, SOLVED)

- **Date:** 2026-09-16   **Phase:** 0   **Deliberate:** yes (planted, mechanism withheld)

- **Symptom:** `make adder` reports **128 failures out of 512** exhaustive cases.
  First failing case: `FAIL: 0 + 7 + 1 -> got 24, want 8`.
  All 128 are in `stdout.txt`.

- **Signal to watch:** `u_add.g_bit[3].u_fa.cout` against the module's `cout`.
  *(Withheld while the gate was open. The method below is what found it, and it
  is the part worth keeping.)*

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
  The ripple adder computes the sum and the internal carry chain correctly —
  every full adder in the chain is honest. The fault is at the module boundary:
  `cout` is taken from `carry[WIDTH-1]`, the carry *entering* the most-significant
  bit, instead of `carry[WIDTH]`, the final carry-out. The adder publishes bit 3's
  incoming carry as the module's carry-out, and the true final carry is never
  driven anywhere.

  *(Answer written from the waveform before decoding the spoiler; confirmed
  against it afterwards.)*

  Confirming evidence at 15 ns (case `0 + 7 + 1`, the first failure):

      a                        = 0000
      b                        = 0111
      cin                      = 1
      sum                      = 1000        <- correct
      u_add.carry[4:0]         = 01111       <- correct chain: carry[4]=0, carry[3]=1
      u_add.g_bit[3].u_fa.cout = 0           <- the MSB adder's own carry-out
      cout                     = 1           <- module output, contradicts it

  `g_bit[3].u_fa.cout` *is* `carry[WIDTH]`, and it reads 0 while the module's
  `cout` reads 1. That single disagreement — a module output contradicting the
  only signal that feeds its position — is the earliest and only contradiction in
  the design. Everything upstream of it is correct.

  Why exactly a quarter of the space fails: the fault is invisible whenever
  `carry[3] == carry[4]`, which is three quarters of the 512 cases. The error is
  always exactly ±2^4 = ±16, the place value of the `cout` bit — 64 cases read 16
  too high (`carry[3]=1, carry[4]=0`, e.g. `0 + 7 + 1 -> got 24, want 8`) and 64
  read 16 too low (`carry[3]=0, carry[4]=1`, e.g. `8 + 8 + 0 -> got 0, want 16`).
  A hand-simulated `cout = carry[3]` reproduces all 128 observed failures exactly,
  with no false positives and none missed.

- **Solution:** `SPOILER-solution.patch.b64` holds the change that produced this,
  base64-encoded so it cannot be read by accident. Decode it only after writing
  your answer above:

      base64 -d -i docs/bugs/0002-adder-unknown/SPOILER-solution.patch.b64
      # BSD/macOS base64 requires -i for a file argument; GNU coreutils takes
      # the bare path. Use -i so the command works on this machine.

- **Reproduce:** decode the patch, `git apply` it, `make adder`. `git apply -R` reverts.

- **Files:** `broken.vcd`, `stdout.txt`, `SPOILER-solution.patch.b64`.
