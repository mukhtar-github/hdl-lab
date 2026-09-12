# hdl-lab — Project 1

Everything here compiles and passes. Verified, not sketched.

## Setup (30 minutes, once)

**Linux / WSL**
```bash
sudo apt install iverilog gtkwave verilator
```

**macOS**
```bash
brew install icarus-verilog gtkwave verilator
```

**Windows** — use WSL2. Native Windows HDL tooling is not worth the pain.

Verified against **Icarus Verilog 13.0** and **Verilator 5.050**. Icarus 12 also works, with one
caveat: Icarus 13 rejects `logic` on a gate-primitive output, which is why `mux2_structural`
declares `output wire y` and its behavioral twin declares `output logic y`. They are not
interchangeable to the tool even though they read as though they are.

Two simulators on purpose:
- **Icarus** runs the testbenches. Forgiving, fast to start, good error messages.
- **Verilator** is a *linter* here (`make lint`). It catches what Icarus accepts happily but
  synthesis will not — inferred latches, width mismatches, signals assigned from two blocks,
  blocking assignment inside a clocked block. Later, when CPU testbenches get slow, Verilator
  becomes the main simulator. See `docs/decisions/0002-toolchain.md`.

## Run it

```bash
make            # all three testbenches — ends in three PASS lines
make lint       # 8 modules, must stay green
make lint-trap  # watch the linter catch the deliberate bug
make wave-seq   # open the sequential waveform in GTKWave
```

`make lint` **fails on any warning**. A lint target that cannot go red tells you nothing — this
one silently checked nothing at all until 2026-09-12, including never once looking at the
module that is wrong on purpose.

## Where things are

| | |
|---|---|
| `rtl/` | Synthesisable hardware |
| `tb/` | Testbenches |
| `scripts/` | `capture.sh` — never record a measurement by hand |
| `docs/` | `journal/` (what happened) · `decisions/` (why) · `results/` (numbers) |
| `build/` | Generated. Git-ignored |

## What is actually in here

| File | Concept |
|---|---|
| `rtl/01_mux2.sv` | Structural vs behavioral description; the mux |
| `tb/01_tb_mux2.sv` | Self-checking testbench, exhaustive over 8 cases |
| `rtl/02_adder.sv` | Full adder; `generate`; parameterised modules |
| `tb/02_tb_adder.sv` | Golden-model checking, exhaustive over 512 cases |
| `rtl/03_sequential.sv` | Flip-flop, register with enable, counter; blocking vs non-blocking |
| `tb/03_tb_sequential.sv` | Clock generation, reset sequencing, time-based checks |

## Do this before writing any new code

Run `make wave-seq` and open `build/sequential.vcd`. Find `dout_nb` and `dout_b`.
Watch the same input pulse come out of one three cycles later than the other.

Those two modules differ only in `<=` versus `=`. That difference is the single
most common bug in beginner RTL, and it will not show up as a compile error —
only as wrong behaviour in a waveform. Learning to read waveforms *is* the skill.

## Exercises (do these before Project 2)

1. **mux4** — a 4-to-1 mux with a 2-bit select. Build it two ways: from three
   `mux2` instances, and directly with a `case` statement. Write an exhaustive
   testbench. Confirm both match.

2. **Break the adder deliberately.** Change `assign cout = (a & b) | (cin & (a ^ b));`
   to `assign cout = a & b;`. Run `make adder`. Find the first failing case in the
   waveform and explain *why* it fails before you fix it. Debugging your own
   working design is the cheapest debugging practice you will ever get.

3. **Latch trap.** Write this to `scratch/latch.sv` and lint it:
   ```systemverilog
   module latch_trap (input logic sel, input logic a, output logic y);
       always_comb begin
           if (sel) y = a;   // note: no else
       end
   endmodule
   ```
   ```bash
   make lint-file FILE=scratch/latch.sv TOP=latch_trap
   ```
   Expect `%Warning-LATCH: Latch inferred for signal 'y'`. Understand exactly what hardware the
   tool thinks you asked for, and why that is almost never what you want.

4. **Shift register with parallel load** — combine `reg_en` and the shift idea:
   a module that either shifts by one or loads a whole new value, controlled by
   a `load` input. This is a real component; you will use it again.

5. **Widen the adder to 32 bits.** 2^65 cases — exhaustive testing is now
   impossible. Write a testbench that instead tries: all zeros, all ones, the
   maximum value plus one, a few hundred random pairs, and every single-bit
   value. Notice that you just invented *directed plus random* testing, which is
   what real verification teams do.

Exercise 5 is the important one. It is the moment you learn that verification is
a design problem, not a chore.

## Next

Project 2 is the ALU: your adder plus SUB, AND, OR, XOR, SLT, and the shifts,
behind a single opcode input. Straight after that, the register file. Then you
have two of the three pieces a CPU needs.
