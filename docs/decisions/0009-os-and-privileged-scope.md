# 0009 — No OS under the benchmark; the core takes traps from Phase 2

- **Date:** 2026-09-28
- **Status:** Accepted, **amended twice on 2026-09-28**; see the amendments at the end. **Where
  they disagree with the body, the amendments win.** The body is left as merged, so these passages
  in it are superseded:
  - Decision 1's "interrupt": it is now any trap (Amendment 1, point 4).
  - Decision 2's list: the minimum is now a rule (Amendment 2, point 2). Amendment 1's list stands
    until the specification is pinned.
  - Decision 3's "both flush the younger instructions" (Amendment 1, point 6).
  - *Consequences*: "the benchmark can run unmodified on the Phase 2 core" (Amendment 1, point 1),
    and "six CSRs" (Amendment 1, point 5).
  - The open-items rows for the ID registers and for pinning the Privileged Architecture. Both are
    due in Phase 2 now (Amendment 1, points 2 and 5).

  Decision 3 is open on purpose, with a deadline: before Phase 3's pipeline design starts.
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

# Amendment 1 — 2026-09-28: the record as merged, reviewed

A review of this record as merged raised seven points about it. Each was checked before it went in,
against the reference build, riscv-tests' `p/link.ld`, and Spike 1.1.0's own source at `530af85`.
Spike is the model the core will be held to in lockstep (rung 4). **The four decisions stand.**
Their details were wrong or incomplete in the ways below.

## 1. The benchmark does not run on the Phase 2 core. The harness does.

*Consequences* said that "the benchmark can run unmodified on the Phase 2 core". That holds only for
an image with no `M` instruction, and `M` arrives in Phase 3.

- **Today's harness has none.** Built for `rv32i`, its image is byte-identical to the reference, and
  Spike runs it as an RV32I hart with the same count and an oracle pass
  ([`20260928T041029Z-spike-crc-table-rv32i-O2`](../results/20260928T041029Z-spike-crc-table-rv32i-O2/)).
  So it can run on the Phase 2 core.
- **The reference decoder very likely will not.** It unpacks BCD timestamps and fixed-point
  coordinates, and for `rv32im` GCC compiles division, and much multiplication, to `M` instructions.
- **So `0004`'s "same program, unmodified" is first honoured for the benchmark when `M` lands, in
  Phase 3.** `M` stays where the roadmap puts it. The gap is not bridged by a trap handler that
  emulates `M` in software: point 4 forbids an undeclared trap in a measured window.

## 2. The Privileged Architecture is pinned before Phase 2

Decision 2 implements privileged behaviour in Phase 2, and `0006` requires a specification to be
pinned before it is implemented. So this open item's deadline moves: the version is pinned in
`reference/` before Phase 2's trap minimum is written. The rules in point 3 are to be checked
against it then. Until that point, their source is Spike.

## 3. What "read-only" and "write" mean

Decision 2 raises the illegal-instruction exception "for a write to a read-only CSR". Both words
have exact definitions, and two cases in this record sit right on the line. Spike 1.1.0 implements
them as follows.

- **Read-only is a property of the address:** bits 11:10 are `11` (`riscv/csrs.cc:25`). A register
  whose bits are all hardwired is not read-only. `mie` may be all zeros, but its address is
  read/write, so writes to it are accepted and ignored. Trapping them would recreate the `mie` loop
  found above.
- **A write is a property of the encoding.** `csrrs` and `csrrc` with `rs1 = x0` do not write, and
  nor do their immediate forms with zero (`riscv/insns/csrrs.h:1`, `csrrsi.h:1`). `csrrw` always
  writes (`csrrw.h:1`). Only a write to a read-only address traps (`riscv/csrs.cc:38-39`).
- **So `rdinstret` never traps.** It is `csrrs rd, instret, x0` on a read-only address, which makes
  it a read. The benchmark's own measurement depends on this rule being implemented exactly.
- **A CSR that does not exist traps on any access** (`riscv/processor.cc:1014-1016`).

## 4. Decision 1 covers every trap

Decision 1 said that no measured window may include an undeclared *interrupt*. But a trap
handler's instructions count in `instret` whatever raised the trap. **It now reads: no measured
window may include a trap, exception or interrupt, that the configuration does not declare.** That
covers what this record leaves open: a software fix-up for misaligned accesses, and software
emulation of `M`.

## 5. The illegal-instruction trap, for one consistent reason

The record justified the trap by conformance. It cited a Phase 3 test for that, `rv32mi`'s
`illegal`, which also reads `mtval`. And it left out registers that conformance requires. Applied
consistently:

- **`misa`, `mvendorid`, `marchid` and `mimpid` join the Phase 2 minimum.** They must be readable,
  and may read as zero; confirm both in the version pinned under point 2. Spike implements all four
  (`riscv/processor.cc:366`, `545-547`). A core that traps on reading them would diverge from the
  model it will be held to. Under Decision 2 as first written, reading them would have trapped.
- **The trap also costs almost nothing** once `ecall`'s trap path exists. Passing the gate by
  silently ignoring unimplemented instructions would be behaviour to reverse later.
- **`rv32mi`'s `illegal` test is where Phase 3 checks it,** together with `mtval`.

## 6. What a trap and a branch actually share

Decision 3 said that "a precise trap and a mispredicted branch both flush the younger instructions".
But a trap also squashes the instruction that raised it. What the two share is the pipeline's
squash-and-redirect logic, with a priority rule: an older trap must override a younger branch's
redirect. That coupling is why Decision 3's deadline stands.

Separately, **where branches resolve sets the misprediction cost that Prediction A is about.** That
choice joins the open items. Its reasons are to be recorded before pipeline design, so that Phase 3
does not settle Prediction A without anyone noticing.

## 7. What "unmodified" covers

riscv-tests' environment is `p/riscv_test.h` together with `p/link.ld`. The linker script places
code at `0x80000000`, and `tohost` on the next 4 KiB page. **"Unmodified" covers both files.** So
the core's memory map puts memory at `0x80000000`, as the benchmark already assumes
(`bench/rv32/link.ld:7`), and the testbench ends a test on the write to `tohost`.

## The Phase 2 minimum, as amended

- `Zicsr`: the six CSR instructions, with point 3's rules;
- the CSRs `mstatus`, `mtvec`, `mepc`, `mcause`, `mhartid` and `mie`, and `misa`, `mvendorid`,
  `marchid` and `mimpid`;
- the environment-call and illegal-instruction exceptions;
- `mret`;
- the `instret` counter;
- all of it written against the Privileged Architecture pinned before Phase 2 starts.

`roadmap.md` is amended to match: the Phase 2 paragraph, the trap-and-CSR bullet among the early
choices, and rung 2's heading, which still read "*(Phase 2)*" over all three test groups.

# Amendment 2 — 2026-09-28: a second review

A second review of the amended record raised six points. Each was checked against Spike's pinned
source, and the first also against a live run. All six hold. None changes a decision. Two of them
are recorded elsewhere: the superseded passages are listed in the status block, and a stale
freshness marker was fixed in `docs/HANDOFF.md`.

## 1. Lockstep needs its differences declared before bring-up

Amendment 1 held the core to Spike. But even a correct core will differ from Spike in at least
three places:

- **The ID registers' values.** Spike's `marchid` is 5, its own registered architecture ID
  (`riscv/processor.cc:545`). A core that returns zero will mismatch on every read of it.
- **`misa`.** Spike builds it from its `--isa` argument (`processor.cc:366`), so Spike must be
  launched with an ISA and a privilege configuration that match the core.
- **Spike's boot ROM.** Spike runs five instructions at `0x1000` to `0x1010` before it jumps to
  `0x80000000`. Its own log of the reference image shows them. The core starts at `0x80000000`.

So rung 4 needs two things before its bring-up: Spike's launch configuration, and a list of
expected divergences. This joins the open items. It is due before lockstep co-simulation starts, in
Phase 3.

## 2. The counters, and a rule for the minimum

`instret` is `0xC02`, a read-only view of `minstret` at `0xB02` (`processor.cc:376`). On RV32 their
upper halves are `0xC82` and `0xB82`. Two rules decide what the core must return, and lockstep
compares every read, so both must be exact:

- **A read returns the count from before the reading instruction retires.** Spike increments
  `minstret` only after each instruction has executed (`riscv/execute.cc:351`), and a read returns
  the stored value (`csrs.cc:842-844`). So `rdinstret` does not count itself. The benchmark's
  difference of two reads would cancel an off-by-one here. Lockstep would not.
- **A write takes precedence over the writing instruction's own increment.** In Spike's words, "The
  ISA mandates that if an instruction writes instret, the write takes precedence over the increment
  to instret" (`csrs.cc:855-858`).

Whether `minstret` comes with `instret` in Phase 2 is one case of a general question. Amendment 1
answered it one register at a time. It is answered now by a rule. **The Phase 2 minimum is:**

- what the standard environment needs;
- what the harness reads;
- every register that the pinned Privileged Architecture makes mandatory for a machine-mode-only
  RV32 hart.

Amendment 1's list stands until the pin, due before Phase 2, settles the third part. The counters
are its first case: `minstret`, its upper halves, and `mcycle`. Until then, both rules above come
from Spike, and the pinned specification is to confirm them.

## 3. Where branches resolve, decided on engineering grounds only

Amendment 1 made the stage where branches resolve an open item, because it sets Prediction A's
cost. **Its reasons are to be timing, area and hazards. Prediction A must not be one of them.** The
record exists so that the stage is chosen without regard to which prediction it favours. Its effect
on A is to be measured in Phase 4, not chosen in Phase 3. `roadmap.md`'s trap-and-CSR bullet gains
the same clause.
