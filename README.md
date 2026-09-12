# hdl-lab

> A pipelined RV32IM processor optimised through evidence-driven hardware specialisation for
> telematics frame decoding.

The question this project exists to answer:

> **Are the already-ratified RISC-V extensions sufficient for telematics frame decoding, or does
> measured workload behaviour justify a genuinely custom extension?**

That question is open. *"The standard already covers it"* is a real result, not a fallback.

**The plan is `roadmap.md`** (canonical, adopted 2026-09-12). **The record is `docs/`** — read
`docs/README.md` before writing anything down.

The order everything follows:

```
workload → benchmark → reference result → CPU → profile → bottleneck
        → mechanism → implement → measure
```

The mechanism is chosen at the end, from evidence. Choosing it first turns profiling into
theatre.

---

## Where things are

| | |
|---|---|
| `rtl/` | Synthesisable hardware |
| `tb/` | Testbenches |
| `bench/` | The benchmark — built *before* the core. Read `bench/README.md` first |
| `scripts/` | `capture.sh` — never record a measurement by hand |
| `docs/` | `journal/` what happened · `decisions/` why · `results/` numbers · `experiments/` questions · `bugs/` evidence |
| `build/` | Generated. Git-ignored |

---

## Current status — Phase 0

```
✅ Icarus Verilog 13.0     ✅ mux2: structural + behavioral, 8/8 exhaustive
✅ Verilator 5.050         ✅ ripple_adder: 512/512 exhaustive
✅ Surfer 0.7.0            ✅ sequential: counter + shift-register pair
                           ✅ make lint — 8 modules, green and meaningful
```

**The Phase 0 gate is not "everything compiles."** It is:

> Introduce a bug deliberately and locate it by reading a waveform, without adding print
> statements.

That gate is now reachable — it was blocked until 2026-09-12 by a waveform viewer that had
never once run (`docs/decisions/0005`). Exercise 2 below *is* the gate.

Next hardware step: `rtl/02_adder.sv`, then Exercise 2.

---

## Setup

**macOS**
```bash
brew install icarus-verilog verilator surfer
```

Not `gtkwave`. The Homebrew cask ships a 2020 **x86_64-only** binary; on an arm64 Mac without
Rosetta it is SIGKILLed on launch and prints nothing at all — it exits 137 and looks like it
merely produced no output. Surfer is native, current, and reads the same VCD files.
See `docs/decisions/0005-waveform-viewer.md`.

**Linux / WSL**
```bash
sudo apt install iverilog verilator    # then: gtkwave, or surfer if packaged
```

**Windows** — use WSL2. Native Windows HDL tooling is not worth the pain.

Verified against **Icarus Verilog 13.0**, **Verilator 5.050** and **Surfer 0.7.0**. Icarus 12 also works, with one
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
make wave-seq   # open the sequential waveform in Surfer
```

To check a viewer actually parses a waveform without opening a window:

```bash
surfer server --file build/sequential.vcd
```

`make lint` **fails on any warning**. A lint target that cannot go red tells you nothing — this
one silently checked nothing at all until 2026-09-12, including never once looking at the
module that is wrong on purpose.

## What is in here

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

Send one pulse in. It leaves `shift_blocking` after a single clock edge and `shift_nonblocking`
after three — so you will see the same pulse emerge **two cycles apart**. The testbench prints
this too: blocking asserts at cycle +0, non-blocking at cycle +2.

Those two modules differ only in `<=` versus `=`. That difference is the single most common bug
in beginner RTL, it will not show up as a compile error, and Icarus runs both without a murmur.
`make lint-trap` shows Verilator finding it. Learning to read waveforms *is* the skill.

## Exercises (do these before Project 2)

1. **mux4** — a 4-to-1 mux with a 2-bit select. Build it two ways: from three `mux2` instances,
   and directly with a `case` statement. Write an exhaustive testbench. Confirm both match.

2. **Break the adder deliberately.** Change `assign cout = (a & b) | (cin & (a ^ b));` to
   `assign cout = a & b;`. Run `make adder`. **Capture the failing waveform into
   `docs/journal/img/` before you fix it** — see the bug-evidence rule in `docs/README.md`.
   Then find the first failing case and explain *why* it fails before fixing. Debugging your own
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

4. **Shift register with parallel load** — combine `reg_en` and the shift idea: a module that
   either shifts by one or loads a whole new value, controlled by a `load` input. This is a real
   component; you will use it again.

5. **Widen the adder to 32 bits.** 2^65 cases — exhaustive testing is now impossible. Write a
   testbench that instead tries: all zeros, all ones, the maximum value plus one, a few hundred
   random pairs, and every single-bit value. Notice that you just invented *directed plus random*
   testing, which is what real verification teams do.

Exercise 5 is the important one. It is the moment you learn that verification is a design
problem, not a chore.

## Next

Project 2 is the ALU: the adder plus SUB, AND, OR, XOR, SLT and the shifts, behind a single
opcode input. Then the register file. That is two of the three pieces a CPU needs.

In parallel — and this is binding, see `docs/decisions/0004-benchmark-first.md` — the benchmark
gets built now, not in Phase 4. A benchmark written after the core exists is shaped by what the
core turned out to do well.
