# RISC-V Project Roadmap

*Revised endpoint: a general-purpose core with a domain-specific extension, quantified.*

---

## What changed and why

The original plan's endpoint was "a documented RV32I SoC taken through FPGA and ASIC flows."
That is a completion claim, not an engineering result. Hundreds of people have implemented
RV32I. The artifact does not distinguish you and, worse, it has no natural stopping point —
you can always add another instruction, another pipeline stage, another cache level. Open-ended
learning projects die of exactly this.

The revised endpoint is:

> **I profiled a real workload, designed a custom extension to accelerate its hot path,
> integrated it into a pipelined RV32IM core I built, and measured what it cost in area and
> clock frequency to get the speedup I got.**

That is the actual job description of a computer architect. It also has a natural terminus:
the workload defines when you are done.

One honest caveat. The market observation that RISC-V wins in domain-specific silicon does
**not** mean you can compete there. Tenstorrent and Axelera have hundreds of engineers and
fab access. What the observation buys you is *project shape* — a legible scope, a measurable
outcome, and a story that isn't "I followed a tutorial."

---

## Direction versus commitment

Choose your **workload** now. Hold your **mechanism** loosely. These are different decisions and
they have very different costs.

Committing to a workload in week one is nearly free and pays immediately. It directs your
reading, gives the project a destination you can picture, and — most importantly — informs early
architectural choices that are painful to reverse:

- **Bus versus direct memory ports.** If something will eventually hang off your core, design a
  real memory interface in Phase 2, however simple. Retrofitting one means rewriting the memory
  path through every pipeline stage.
- **Register file ports.** Some operations want three sources. Finding that out after
  pipelining a two-read-port design costs you a week.
- **Datapath width and load/store granularity.** Data-hungry targets shape Phase 2, not Phase 5.
- **Area budget.** If Tiny Tapeout is on the table, that constrains every module from the first
  one.

Committing to a *mechanism* in week one is where it goes wrong. "I'm building a systolic array"
decided before you can measure anything turns Phase 4 into theatre: you will find the evidence
that ratifies the choice you already made, and you will believe it.

**Build the benchmark before the core.** "My workload" is not a benchmark. What you need is a
concrete artifact: a specific program, fixed input data, deterministic output, under version
control. Write it and run it on Spike in Phase 0, before any RTL exists. That gives you a
reference result from day one, lets you run it on your own core the moment the core executes
anything, and makes every later speedup claim reproducible rather than anecdotal.

**Synthesise the stimulus from a specification. Never commit a captured trace.** Real
operational data carries obligations a benchmark repository cannot hold — the FleetPoynt trace
that motivated this revision is the live GPS history of federal judges' vehicles, and it is
gitignored for good reason. Generate stimulus from the published protocol instead. A real trace
is *optional realism* for the arrival model — inter-arrival distribution, dark gaps, malformed
rate — and explicitly a nice-to-have, never a dependency. Borrow the shape, never the data.

**Record what kind of benchmark it is, in the README, on the day you write it.** Spec-derived
stimulus running through a decoder you wrote is a *reconstruction*, not instrumented production
code. Both are legitimate. Confusing them later is not, and the confusion is much easier to
prevent now than to detect at Phase 4.

**Record your prediction.** Before Phase 1, write down what you think the bottleneck will be
and why, and date it. Compare against the Phase 4 measurements. Right means you have documented
evidence of good instincts. Wrong is the most valuable thing this project will teach you — and
it is only available if the guess was written before the data. Reconstructed reasoning always
turns out to have been correct all along.

---

## Recorded predictions — 2026-09-01

Written before any RTL exists and before any measurement. Two positions, deliberately opposed,
so that Phase 4 can settle them rather than ratify one.

**Prediction A — frame synchronisation and per-model dispatch dominate.** Scanning a byte
stream for delimiters, resynchronising after garbage, and branching per model variant is
unpredictable control flow, and on an unpredicted five-stage pipeline every mispredicted branch
is a flush. Checksum work over a short frame is comparatively cheap.

**Prediction B — the per-byte passes dominate, and which one depends on the protocol mix.**
Frame sync and dispatch are O(1) per frame; the checksum is O(n) over it. A table-driven CRC's
"forty lookups" is forty taken loop-back branches *and* forty load-use stalls. So:

- **GT06-heavy traffic** → CRC wins, as the only O(n) pass.
- **JT/T 808-heavy traffic** → escape destuffing wins instead. Also O(n), but with a
  *data-dependent* branch per byte where the CRC loop's branch is loop-invariant.
- **Frame sync wins only if resync is common**, which is a property of the link, not the
  protocol.

**The discriminator: resync rate.** Measurable from trace metadata — reissue flags and
inter-sample gap distribution. It is an input to the stimulus generator, not a measurement of
your core, so computing it does not spoil either prediction. Deliberately deferred until stimulus
generation is actually on the critical path; it is not one now.

**Consequence either way:** both candidate bottlenecks already have a ratified extension aimed
at them — `Zbc`'s `clmul` for CRC, `Zbb`'s `orc.b` for delimiter scanning. Rule 3 of the
standard/custom boundary fires before any custom encoding is considered. A genuinely possible
Phase 5 finding is that custom space is never needed at all.

---

## The phases

Week ranges assume roughly ten focused hours a week. Scale them to whatever you actually have;
the **sequence** matters far more than the calendar, and the gates matter more than either.

### Phase 0 — Toolchain and primitives *(weeks 1–3)*

Simulator, waveform viewer, linter. Gates, mux, adder, flip-flop, register, counter. Every
module exhaustively self-checked from the first one.

**Gate:** you can find a bug you deliberately introduced by reading a waveform, without
adding print statements.

---

### Phase 1 — Datapath components *(weeks 3–8)*

ALU (add, sub, and, or, xor, shifts, slt/sltu). Register file with two read ports and one
write port, x0 hardwired to zero. Instruction and data memory models.

**Gate:** the ALU passes randomised testing against a golden model in software, including
signed/unsigned comparison edge cases and shift-amount masking. These are where nearly
everyone's first ALU is wrong.

---

### Phase 2 — RV32I, single-cycle then multi-cycle *(weeks 8–16)*

Start with five instructions: `ADD`, `ADDI`, `LW`, `SW`, `BEQ`. Get those genuinely working
before widening to the full base set. Build or borrow an assembler path early — hand-assembly
is fine for five instructions and miserable for forty.

**Gate — the important one:** your core passes the `riscv-tests` suite for RV32I. Not your own
tests. Someone else's, written by people who knew the traps you don't yet. This is the moment
you find out whether you built a CPU or something that runs the programs you happened to write.

See **The conformance track** below — rungs 1 and 2 belong here.

---

### Phase 3 — Pipeline, M extension, traps *(weeks 16–24)*

Five stages: fetch, decode, execute, memory, writeback. Then the parts that make it real:
hazard detection, forwarding paths, load-use stalls, branch resolution and flush.

Add `M` (multiply/divide), `Zicsr`, and machine-mode trap handling.

This phase contains most of the actual computer architecture in the project. Phases 0–2 teach
you to describe hardware; this one teaches you why processors are shaped the way they are.

**Gate:** `riscv-tests` still passes on the pipelined version, the official Architectural
Certification Tests pass, differential co-simulation against Spike runs clean over a few
million instructions, and a real RTOS (Zephyr or FreeRTOS) boots in simulation. You now have
a microcontroller-class processor.

Rungs 3 through 6 of the conformance track belong here. Pipelining is where correctness bugs
stop being obvious — a forwarding path that's wrong one cycle in ten thousand will pass every
hand-written test and destroy you later.

---

### Phase 4 — Profile and choose the domain *(weeks 24–30)* ← **the new phase**

This is the phase the original plan lacked entirely, and it is what makes everything after it
mean something.

You own the RTL, which gives you an instrumentation advantage no software profiler has: you can
count anything, for free, with perfect accuracy and no observer effect. Cycles per instruction
class. Stall cycles by cause. Memory access patterns. Branch misprediction rates.

**Do this:**

1. Get your chosen workload running on your core. You picked it in Phase 0, so it should
   already be your benchmark by now.
2. Instrument the RTL. Where do the cycles actually go?
3. Find the hot loop. Establish an honest scalar baseline — cycle count, not vibes.
4. *Then* decide what hardware would help.

**What this phase decides is the mechanism, not the destination.** You already know the
workload. What you cannot know in advance is whether its bottleneck is the arithmetic, the
memory access pattern, the branch behaviour, or something you would never have guessed —
and therefore whether the right answer is a custom instruction, a wider load path, a small
lookup table, or an accelerator block. Guessing that in week one costs months.

Open your dated prediction from Phase 0 and compare.

**Also measure a commodity part.** Run the identical benchmark on an off-the-shelf
microcontroller — a Cortex-M4, an ESP32-C6, whatever your deployment would realistically use.
Your own core is slow, so measuring only against it makes almost any mechanism look like a win
and answers nothing. The question "would specialized hardware ever be justified here" is a
comparison against what you could simply buy, and you cannot answer it without that number.

---

### Phase 5 — Design, integrate, measure *(weeks 30–40)*

Two integration styles, and the choice is itself a design decision worth reasoning about:

- **Custom instructions** — RISC-V reserves `custom-0` through `custom-3` encoding space
  precisely for this. Tight coupling, low latency, operands come from the register file.
  Right for fine-grained operations.
- **Memory-mapped accelerator** — a separate block the CPU configures and kicks off. Right
  for coarse-grained work where the setup cost amortises.

Then re-measure against the Phase 4 baseline.

**Gate:** three numbers, all of them, honestly reported.

---

### Phase 6 — FPGA *(weeks 40–48)*

Synthesis, timing closure, real peripherals (UART at minimum), and running your benchmark on
actual hardware rather than in simulation.

Expect this phase to force architectural changes. Synchronous block RAM does not behave like
your simulation memory model, and your first timing report will not be kind.

---

### Phase 7 — ASIC flow *(open-ended)*

Yosys, OpenROAD, a PDK, SDC constraints, DRC and LVS. Treat this as a separate discipline
you're beginning, not as the last 12% of this project. If the goal is actual silicon rather
than a layout screenshot, Tiny Tapeout is the realistic route — but note you'd be designing to
a tile area budget from the start, which is a constraint worth knowing before Phase 5.

---

## The conformance track

This runs *alongside* the phases, not after them. Each rung tests something the one below it
structurally cannot.

**1. Unit self-checking testbenches** *(Phase 0–1)* — yours. Exhaustive wherever the input
space is small enough to afford it.

**2. `riscv-tests`** *(Phase 2)* — the classic hand-written per-instruction tests
(`rv32ui-p-*`, `rv32um-p-*`, `rv32mi-p-*`). Bring-up needs a linker script, a `tohost`
termination mechanism, and an ELF loader in your testbench. Cheapest real external check
available; do it as early as it will run.

**3. Architectural Certification Tests (ACT4)** *(Phase 3)* — the official suite. **Note the
tooling changed:** RISCOF is deprecated and replaced by the ACT4 Framework, a Makefile-and-Python
tool that generates self-checking ELF tests you run on your own testbench. It needs a UDB
configuration file declaring which extensions and parameters you implement, an
`rvmodel_macros.h` defining DUT-specific hooks (console output, test termination, interrupt
generation), and a linker script for your memory map.

Declaring your configuration is itself the valuable part: it forces you to state precisely what
you claim to implement, which is the discipline the whole track exists to instil.

**4. Differential co-simulation against Spike** *(Phase 3)* — lockstep execution. Run your core
and the reference model on the same program and compare architectural state after every retired
instruction. This is what real verification teams do, and it is qualitatively stronger than any
test suite: it checks *every instruction of every program you ever run*, not only the cases
someone thought to write a test for.

**5. Formal verification with `riscv-formal`** *(Phase 3, ongoing)* — bounded model checking
against a formal ISA model via SymbiYosys, entirely open source. Underused by solo builders and
close to a superpower for one: it reasons over *all* inputs to a bounded depth rather than
sampling them. It will find the forwarding corner case that random testing needs a billion
cycles to stumble into.

**6. Random program generation** — `riscv-dv` or `riscv-torture`. Generates legal random
programs, runs them on both your core and the reference, compares. Feeds rung 4.

**7. RTOS boot** *(Phase 3 gate)* — Zephyr or FreeRTOS. An integration test, not a correctness
proof, but it exercises trap handling and CSR behaviour in ways synthetic tests rarely do.

**The honest caveat:** the architectural test suite is a *minimal filter*. RISC-V
International's own documentation states plainly that passing it does not mean your design
complies with the architecture. It is necessary, nowhere near sufficient, and that is exactly
why rungs 4 and 5 exist.

---

## The standard/custom boundary

This is where the two principles meet, and where Phase 5 could quietly undo everything Phases
2–3 established. Five rules.

**1. Use the reserved custom opcode space.** RISC-V reserves `custom-0` (0x0B), `custom-1`
(0x2B), `custom-2` (0x5B) and `custom-3` (0x7B) for exactly this purpose. Never place a custom
instruction in reserved-but-unallocated standard space, however convenient the encoding looks.
That is the T-Head failure in miniature: when the standard eventually claims that space, your
encodings collide, and colliding encodings *execute wrongly* rather than trapping — the worst
possible failure mode.

**2. Conformance must hold with your extension disabled.** Gate it behind a build-time
parameter or a CSR enable bit, and run the whole conformance track in the standard-only
configuration. If you can't switch it off and still pass, you haven't extended the ISA — you've
forked it.

**3. When a ratified extension already covers your workload, implement that instead.** Bit
manipulation has `Zbb`/`Zbs`. Scalar cryptography has `Zbk*` and `Zkn*` — if you want SHA-256
acceleration, `Zknh` *is* the standard answer. Implementing the ratified version inherits test
vectors, compiler support, and published implementations to benchmark against. Inventing your
own is strictly worse unless the standard genuinely doesn't cover what you're doing, and you
should be able to say precisely why it doesn't.

**4. Make it discoverable.** Set `mvendorid`, `marchid` and `mimpid`, and expose feature bits
through a vendor CSR. Software should be able to *detect* your extension rather than assume it.
This is the difference between an extension someone else could use and a private dialect.

**5. Trap cleanly when disabled.** Custom opcodes with the extension off must raise
illegal-instruction. Not nops, not undefined behaviour.

Follow these and your Phase 5 result reads as *"conformant RV32IM core plus a documented,
discoverable, optional accelerator."* Skip them and it reads as *"a core that runs my code"* —
which is the exact sentence this whole track exists to prevent you from writing.

---

## The three numbers

Any architect reviewing your work will ask for all three. Reporting one is a red flag.

| Number | Why it matters |
|---|---|
| **Speedup** | Cycles for the hot loop, before and after. The headline. |
| **Area cost** | LUTs and flip-flops (or gate-equivalents) added. A 10× speedup that triples core area is a different result from one that adds 8%. |
| **Fmax impact** | Maximum clock before and after. If your accelerator lands on the critical path and halves the clock, a "10× speedup" is really 5×. |
| **Versus commodity** | The same benchmark on a part you could just buy. Without this the build-versus-buy question stays unanswered. |

The third one catches more people than the first two combined. It is also the number that
proves you understand what you built.

**A fourth, if your deployment is power-constrained:** energy per operation. For a
battery or solar-powered device, joules matter more than cycles, and a mechanism that is
slower but wakes the core less often can win outright. Speed is a proxy for energy at best,
and sometimes a misleading one.

### Normalising, once benchmark scale is decoupled from deployment scale

Choosing a rate you can demonstrate rather than a rate your deployment sees makes absolute
throughput comparisons meaningless — a hobby FPGA will not saturate a 10Gbps link, and a
Cortex-M4 is not a line-rate part. Normalising is the fix, not the damage. But the two
normalisers are **not equally obtainable**, and reporting one as though it were the other is
exactly what this table exists to prevent.

| Normaliser | Obtainable? | Question it answers |
|---|---|---|
| **Joules per packet** | Yes. Wall power is measurable on your board and on a commodity part alike. | Build versus buy. This is the real answer to "would specialised hardware ever be justified." |
| **Packets/sec per LUT** | Only against other FPGA implementations. A server core or commercial NIC publishes no LUT-equivalent, and a die-shot estimate is not something to stake a claim on. | How your design compares to other open-source packet-processing designs. A good baseline — a *different* question from the row above. |

Decide which normaliser answers which question at the moment you set the rate, not when you
write up the results.

---

## Candidate domains

**Choose one now**, in Phase 0. What hardware to build for it is decided in Phase 4, after
measurement. Listed with honest trade-offs.

**Telematics frame decoding at line rate — the commitment this revision was written around.**
Note how it is stated: *a protocol family and a rate*, never a deployment. Frame sync over a
byte stream → length and protocol ID → checksum → unpack BCD timestamp and packed fixed-point
coordinates → status bitfield → identifier lookup → ACK. Integer-only, bit-heavy, branchy,
no floating point, no OS dependency. Ports to bare-metal RV32IM without ceremony.

*It is not one decoder.* GT06 uses CRC-ITU; JT/T 808 uses an XOR check with `0x7e` delimiter
escaping — completely different compute profiles. And the variance is intra-vendor too: GT06E
differs from GT06, which differs sharply from GT02, with fields sometimes ASCII, sometimes
binary, sometimes only part of two bytes, and coordinates stored unsigned with the hemisphere
stuffed into bits of the course field. So it is a family of decoders behind a dispatch layer,
which makes the workload branchier than it first appears — and makes profiling *more*
informative, not less.

### What supplies the interest, and what supplies the requirement

These are different things and the distinction is load-bearing.

A fleet product supplies the *interest*: it is why you find telematics decoding worth a year of
evenings. It does not supply the *requirement*. Ten thousand devices reporting every ~86 seconds
is roughly 116 packets per second, which is free on any rented box. **The business case does not
follow, and you should never write as though it does.** Line-rate packet decoding is a genuine
silicon domain — it is most of what SmartNICs and DPUs exist to do — and that architecture
question stands on its own merits at a rate no fleet deployment will reach.

The freeing consequence: GT06 and JT/T 808 are public documents belonging to nobody in this
story. **You wait on nobody's data, nobody's access, and nobody's strategy to start.** Phase 0
begins the day you decide it does.

**Pick a rate you can actually demonstrate** on the board you eventually buy, report the
normalised figure, and let the higher framing be context rather than a target you would have to
fake.

**Cryptographic hashing or field arithmetic** — SHA-256, or the modular arithmetic underneath
signature schemes. *Strongest pedagogical property: NIST publishes test vectors, so your golden
model problem is solved for free.* Naturally parallel, small area, large speedups over scalar
code. RISC-V has ratified scalar crypto extensions (`Zbk*`, `Zkn*`), so you can implement a
standard and compare against published implementations rather than inventing an interface.
Downside: well-trodden ground.

**Fixed-point DSP / FIR filtering** — teaches MAC arrays, throughput-versus-latency trade-offs,
and pipelining under a real timing constraint. Modest, predictable, and the speedup story is
clean. Least glamorous of the four.

**Int8 GEMM / small systolic array** — the most market-relevant option, since edge inference is
exactly the segment RISC-V is winning. *Also the riskiest.* On a small FPGA you will hit memory
bandwidth long before you hit compute limits, and the project quietly becomes a memory
hierarchy project. That is a genuinely valuable lesson, but it is not the one you signed up
for. Only pick this if you're prepared for that pivot.

**Bit manipulation / string or pattern matching** — smallest scope, cleanest narrative. Profile
real code, find that it spends its life in a handful of bit-twiddling operations, add two or
three custom instructions, measure. Unglamorous and very defensible.

---

## Failure modes to watch

**Building the accelerator first.** People do this constantly — a beautiful systolic array with
no processor around it. It teaches dataflow and nothing about integration, which is where all
the real difficulty lives. The core comes first.

**Skipping `riscv-tests` because your own tests pass.** This is precisely the reasoning that
produced a generation of RVV 0.7.1 silicon that no upstream compiler will target. "My core runs
my code" is not a correctness claim — your tests encode the same misunderstandings as your RTL,
because the same person wrote both.

**Squatting on standard opcode space.** The tempting shortcut in Phase 5, and unrecoverable
once anyone else has your binaries. Custom space exists; use it.

**Treating conformance as a one-time gate.** It's a regression suite. Every pipeline change in
Phase 3 and every integration change in Phase 5 can break it, and you want to find that out in
the commit that caused it rather than three weeks later.

**Committing to a mechanism before measuring.** Not the same as having a destination — a
destination is good and you should pick one in Phase 0. The failure is deciding *how* you'll
accelerate it before you know where the cycles go, because then Phase 4 becomes a ritual that
confirms the answer rather than a measurement that could overturn it.

**Letting the workload search decide a business question.** The sharpest risk in this whole
document, and the hardest to notice from inside. A strategy that surfaces *while you are hunting
for something to accelerate* has contaminated provenance, however sound its reasoning looks. It
will feel like insight, because it produced a satisfying profiling target.

The discipline: any infrastructure or product decision that emerges from a chip-design session
gets re-derived cold, in a session with no connection to this project, before it influences
anything. And it does not get written into this roadmap — not as a recommendation, not as
context. The only trace it should leave here is this entry telling you to derive it elsewhere.

Price such decisions honestly when you do re-derive them. Owning infrastructure means owning
the outage, the field work with no clean rollback, and the contractual exposure. It can also
mean inheriting security obligations the protocol never had — GT06 identifies by cleartext
IMEI, so becoming an endpoint means anyone who guesses an identifier can inject rows into an
audit trail. That is a *transfer of liability*, not an operating cost, and it belongs in the
gate as a blocking condition rather than in a cost table.

**Treating Phase 7 as a finish line.** It is the start of a different discipline. Phases 0–6
are already a complete, defensible project without it.

**Optimising before measuring.** Phase 4 exists to prevent this. Any speedup claim without a
documented baseline is unfalsifiable, and an unfalsifiable claim is worse than no claim.
