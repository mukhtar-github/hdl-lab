# 0003 — Validate against external suites, not self-written tests

- **Date:** 2026-09-01
- **Status:** Accepted
- **Phase:** 0 (policy), enforced from Phase 2

## Context

"My core runs my code" is not a correctness claim: the same person wrote the RTL and the tests,
so both encode the same misunderstandings. This is precisely the reasoning that produced a
generation of RVV 0.7.1 silicon no upstream compiler will target.

## Options considered

1. **Self-written testbenches only** — rejected. Fast to start, but the failure mode above is
   invisible from the inside and only surfaces when someone else's binary won't run.

2. **External suites layered on top** — accepted.

## Decision

A staged validation ladder. Each rung tests something the one below structurally cannot:

1. Unit self-checking testbenches (Phase 0–1)
2. `riscv-tests` (Phase 2) — **the gate that matters**
3. Architectural Certification Tests, ACT4 framework (Phase 3)
4. Differential co-simulation against Spike (Phase 3)
5. `riscv-formal` via SymbiYosys (Phase 3, ongoing)
6. Random program generation (`riscv-dv` / `riscv-torture`)
7. RTOS boot (Phase 3 gate)

**Note the tooling change:** RISCOF is deprecated; ACT4 replaces it.

## Consequences

- Conformance is a **regression suite**, not a one-time gate. Every pipeline change in Phase 3
  and every integration change in Phase 5 can break it.
- Custom extensions must be gated behind a build parameter or CSR bit, and the full track must
  pass in the **standard-only** configuration. If it can't be switched off and still pass, the
  ISA has been forked rather than extended.
- Custom instructions go in reserved custom-0..3 opcode space. Never in reserved-but-unallocated
  standard space — colliding encodings execute wrongly rather than trapping.
- Honest caveat: the architectural suite is a *minimal filter*. RISC-V International's own
  documentation states passing it does not mean the design complies. Rungs 4 and 5 exist for
  exactly that reason.
