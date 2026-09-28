# 0009 — No OS under the benchmark; the core takes traps from Phase 2

- **Date:** 2026-09-28
- **Status:** Accepted. Decision 3 is open on purpose, with a deadline: before Phase 3's pipeline
  design starts.
- **Phase:** 0 (policy), binding on Phases 2 and 3

## Context

On 2026-09-28 the question came up whether the project needs an RTOS. It came up as a question
about the benchmark. Most of its weight turned out to be on the core.

What the repository already said, and where it disagreed with itself:

- **The workload has no OS dependency** (`0001`), and the benchmark runs bare metal, with no OS and
  no libc (`bench/rv32/README.md`).
- **The core must boot an OS.**
  - `roadmap.md` Phase 3 adds `Zicsr` and machine-mode trap handling, and its gate includes "a real
    RTOS (Zephyr or FreeRTOS) boots in simulation".
  - `0003` lists the same boot as rung 7.
  - The roadmap already frames that boot as "an integration test, not a correctness proof, but it
    exercises trap handling and CSR behaviour in ways synthetic tests rarely do".
- **So `bench/rv32/README.md` and `htif.h` were wrong** to say that "the core we are building will
  have no OS", and the rv32 Makefile's header likewise said it would have "no libc". The benchmark
  runs without an OS; the core must be able to boot one.

Checking what riscv-tests actually needs found a sequencing problem. Phase 2's gate is riscv-tests
(`0003`: "the gate that matters"). Every test starts and ends through its standard environment,
`p/riscv_test.h`. That file is from riscv-test-env at `6de71edb`, the commit riscv-tests `bcffa2b`
pins; see `reference/README.md`. Before any test runs, the environment:

- reads `mhartid` (lines 170-172);
- writes `mie`, `mtvec`, `mstatus` and `mepc`, and ends its setup with `mret` (134-140, 219-248);
- writes registers a core may not have: `satp`, `pmpaddr0`, `pmpcfg0`, `mnstatus`, `medeleg`,
  `mideleg`. Before each write it points `mtvec` at the next instruction. So a core may trap on
  them or ignore the write: both land in the same place (109-140). `mie` is the exception. It is
  written before its guard is set, while `mtvec` still points at that write, so a core that traps
  on `mie` loops there forever (134-140);
- ends every test with `ecall`, which its trap handler identifies through `mcause` (193-218,
  262-277).

That is `Zicsr`, six machine-mode CSRs, the environment-call exception and `mret`. Phase 2's gate
needs all of them, and the roadmap added none of them until Phase 3. rv32ui does not *test* any of
this. It uses it to start each test and to report the result.

The benchmark needs a CSR too. It measures its own work with `rdinstret`
(`bench/rv32/crc_itu_ref.c:105-108`). `0004` promises that "the same program, unmodified" runs on
the core. On a core without the `instret` counter it takes an illegal-instruction trap instead.

## Options considered

### The benchmark's environment

1. **Run the benchmark under an RTOS, because tracking devices run one.** Rejected, for three
   reasons.
   - It reasons from deployment, which `0001` rules out: the commitment is "a protocol family and a
     rate — never a deployment".
   - A tick adds interrupts and context switches to every capture. `instret`, and later the cycle
     counts, would include kernel work that belongs to no hypothesis. `experiments/0001` and `0008`
     removed two hidden contributors, a stale build and hoisted work, and a tick would put one back
     on purpose. The journal had already asked what becomes of `instret` "once there are
     interrupts" (2026-09-21).
   - Connections are data, not tasks. `0007`'s amendment found that per-connection state "trades a
     branch-heavy cost for a memory-heavy one". A thread per connection would turn that
     data-structure question into a scheduling one, and bury the dispatch-cost measurement under
     context switches.
2. **Bare metal.** Accepted. If input later becomes interrupt-driven, an interrupt handler that
   fills a buffer and a loop that drains it need no kernel.

### When the core first takes a trap

1. **Keep `Zicsr` and traps in Phase 3, and give Phase 2 a hand-written test environment** that
   ends each test with a plain store to `tohost`. Rejected.
   - The instruction tests would run unchanged, since they do not test traps. What a hand-written
     environment replaces is the pass/fail reporting. That is where this project's harnesses have
     already lied, three times: the `htif_exit` race that dropped the last byte of output
     (`bench/rv32/README.md`), the stale build reported under another configuration
     (`docs/bugs/0004`), and a comparison that compared nothing (journal, 2026-09-26). Reporting
     written here would be checked by no one else. The standard environment's reporting is shared
     by every core that runs riscv-tests.
   - The pipelined core would then take the project's first trap, with nothing known-good to check
     its trap changes against.
2. **Build the whole privileged scope in Phase 2**: timer, interrupts, user mode, PMP. Rejected.
   The gate needs a fraction of it, and the rest is decided better once the pipeline's shape is
   known (Decision 3).
3. **Build in Phase 2 the minimum the standard environment needs, and run that environment
   unmodified.** Accepted. It does not spare Phase 3 the hard part: precise exceptions in a
   five-stage pipeline still have to be designed there. What it buys is a trap implementation known
   to work, and a passing suite, before pipelining starts. Phase 3's changes are then checked
   against something that already works, rather than debugged together with it.

### The RTOS boot

1. **Drop it from the Phase 3 gate, since the workload needs no OS.** Rejected. It was never a
   workload claim. `0003` has it as a conformance rung, a test of traps, interrupts and CSRs.
2. **Keep it, as a test of the privileged implementation.** Accepted, unchanged.

## Decision

1. **No OS under the benchmark.** Every reference result and every measured run is bare metal: no
   OS, no libc, no scheduler. No measured window may include an interrupt that the configuration
   does not declare. This is the rule `experiments/0001` set for compiler flags, applied to
   interrupts.
2. **The trap minimum lands in Phase 2.** The Phase 2 gate runs `rv32ui-p-*` through riscv-tests'
   standard environment, unmodified. The minimum is:
   - `Zicsr`: the six CSR instructions;
   - the CSRs `mstatus`, `mtvec`, `mepc`, `mcause`, `mhartid` and `mie`. `mie` may be all zeros
     until interrupts exist;
   - the environment-call exception;
   - the illegal-instruction exception, raised for any unimplemented instruction or CSR, and for a
     write to a read-only CSR. rv32ui would pass without it. It is here because conformance
     requires it:
     - `rv32mi`'s `illegal` test executes an illegal instruction and expects this trap, and checks
       `mtval` (`isa/rv64mi/illegal.S:19-21`, `154-160`);
     - the CSR cases come from the Privileged Architecture, which is to be checked in the version
       pinned under Decision 3. `rv32mi`'s `csr` test checks them only on a core with user mode
       (`isa/rv64si/csr.S:89`, `113-125`). ACT4 will check more.

     It is also why `mie` must exist;
   - `mret`;
   - the `instret` counter, whose low 32 bits the benchmark reads.

   Bring-up may use any environment. The gate may not.
3. **The rest of the privileged scope is open, and must be fixed before Phase 3's pipeline design
   starts.** The items are listed below. ACT4's configuration file (roadmap, rung 3) will require
   every one of them to be declared anyway. The deadline is the point of this item. A precise trap
   and a mispredicted branch both flush the younger instructions, so where traps are taken belongs
   to the same design as where branches resolve (Prediction A).
4. **The RTOS boot stays in the Phase 3 gate**, as a test of Decision 3's scope, not as something
   the workload needs.

## Open items

These are due before Phase 3's pipeline design starts. The `rv32mi-p-*` tests named are the ones in
riscv-tests `bcffa2b`'s `isa/rv32mi/Makefrag`.

| Item | Why it is open |
|---|---|
| Interrupts, and the `mtime`/`mtimecmp` timer | Any RTOS tick needs them. The workload does not. |
| User mode, and PMP | Whether the chosen RTOS needs either. `pmpaddr` tests PMP. |
| Counters beyond the low half of `instret`: `cycle`, the RV32 upper halves, `time` | `zicntr` and `instret_overflow` test them, and Phase 4 will want `cycle`. |
| Misaligned addresses: handled in hardware, or trapped | `ma_addr`, `ma_fetch` and the four `*-misaligned` tests. |
| `ebreak`, `mtval`, and the rest of the exception set | `sbreak`, `breakpoint`, `illegal`, `shamt`. `illegal` accepts `mtval` as zero or the instruction word; `ma_addr` reads it too. |
| The machine information CSRs `misa`, `mvendorid`, `marchid` and `mimpid`, and `mscratch` | `mcsr` reads all four; `csr` reads `misa` and works on `mscratch`. Rule 4 of the roadmap's standard/custom boundary already requires the ID registers to be set. |
| Which RTOS: Zephyr or FreeRTOS | The roadmap names both. |
| Which version of the Privileged Architecture | To be pinned in `reference/` before it is implemented (`0006`). |

Two `rv32ui` tests go beyond RV32I itself. They bear on the Phase 2 gate, but they are not
privileged questions, so they are recorded here and not decided:

- **`fence_i`** stores instructions and then executes them. It needs `FENCE.I` (Zifencei), and an
  instruction fetch that sees earlier stores. That touches the roadmap's early choice of memory
  interface.
- **`ma_data`** checks that misaligned loads and stores return the right values. The standard
  environment has no handler to emulate them, so the core must do them in hardware or fail the test.

The roadmap's rung 2 listed `rv32um-p-*` and `rv32mi-p-*` under Phase 2 as well. `rv32um-p-*` runs
once `M` lands, and `rv32mi-p-*`, which tests the privileged architecture itself, once Decision 3's
scope does. Both land in Phase 3.

## Consequences

- **Phase 2 grows, by a known amount:** six instructions, six CSRs, two exceptions, `mret` and
  one counter.
- **The Phase 2 gate's verdicts are not reported by code written here.** riscv-tests' own
  environment starts and ends every test, through traps the core must take correctly. A bug in
  home-made reporting cannot turn a failure into a pass.
- **The benchmark can run unmodified on the Phase 2 core**, as soon as the core executes anything
  (`0004`).
- **Phase 3 starts with its privileged scope fixed**, rather than discovering it during pipeline
  design.
- **Corrected in the same change:**
  - `bench/rv32/README.md`, `htif.h` and the header of `bench/rv32/Makefile` now say that the
    benchmark runs without an OS, not that the core has none.
  - `roadmap.md` Phases 2 and 3, its rung 2, and its list of early choices that are painful to
    reverse now say what this record decides, each citing it. That list gains the trap and CSR
    path.
- **Forecloses** an OS under the benchmark, and a hand-written environment for the Phase 2 gate.
- **Revisit if** line-rate input becomes interrupt-driven. Then the interrupt handler is part of
  the workload, and is measured as a declared term. Also revisit if Decision 3's scope does not fit
  the area budget.

## Predictions

Recorded before any of it is built.

**Decision 2's list is enough for the standard environment.** No `rv32ui-p-*` test will fail for
want of a CSR, an exception or a privileged instruction that is missing from that list. `fence_i`
and `ma_data`, which need more for the reasons above, are excepted. Phase 2 shows this wrong if any
other test does.

**The trap logic built for the single-cycle core carries into the pipeline without a redesign of its
CSRs or its trap causes.** What changes is where in the pipeline a trap is taken, which Phase 3
designs in any case. If Phase 3 rewrites the CSR file or the trap-entry sequence, building them
early bought less than this record assumes.
