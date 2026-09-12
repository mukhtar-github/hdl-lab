# hdl-lab — Project 1

Everything here compiles and passes with Icarus Verilog 12. Verified, not sketched.

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

Two simulators on purpose:
- **Icarus** runs your testbenches. Forgiving, fast to start, good error messages.
- **Verilator** is used here only as a *linter* (`make lint`). It catches things
  Icarus accepts happily but real synthesis will not — inferred latches, width
  mismatches, signals assigned from two blocks. Run it often. Later, when your
  CPU testbenches get slow, Verilator becomes your main simulator.

## Run it

```bash
make          # all three testbenches
make lint     # static checks
make wave-seq # open the sequential waveform in GTKWave
```

Expected output ends with three `PASS` lines.

## What is actually in here

| File | Concept |
|---|---|
| `01_mux2.sv` | Structural vs behavioral description; the mux |
| `01_tb_mux2.sv` | Self-checking testbench, exhaustive over 8 cases |
| `02_adder.sv` | Full adder; `generate`; parameterised modules |
| `02_tb_adder.sv` | Golden-model checking, exhaustive over 512 cases |
| `03_sequential.sv` | Flip-flop, register with enable, counter; blocking vs non-blocking |
| `03_tb_sequential.sv` | Clock generation, reset sequencing, time-based checks |

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

3. **Latch trap.** Write this and lint it:
   ```systemverilog
   always_comb begin
       if (sel) y = a;   // note: no else
   end
   ```
   `make lint` will complain. Understand exactly what hardware the tool thinks
   you asked for, and why that is almost never what you want.

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
