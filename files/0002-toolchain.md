# 0002 — Icarus for simulation, Verilator for lint

- **Date:** 2026-09-01
- **Status:** Accepted
- **Phase:** 0

## Context

Starting from no prior digital-hardware knowledge. The first weeks are dominated by toolchain
friction, and a hostile simulator at this stage kills the project before any learning happens.

## Options considered

1. **Verilator as primary simulator** — fastest, and the industry choice for large designs.
   Rejected for now: stricter, less forgiving error messages, and historically a C++ testbench
   barrier. The speed advantage is irrelevant until testbenches get slow, which is Phase 3 at
   the earliest.

2. **Icarus as primary** — accepted. Forgiving, quick to start, readable errors, handles
   SystemVerilog testbenches with `-g2012`.

3. **Vendor simulator (Vivado/Questa)** — rejected. Heavyweight install, ties the project to one
   vendor before any board is chosen.

## Decision

Icarus Verilog runs the testbenches. Verilator runs as a **linter only** (`make lint`),
from day one.

## Consequences

- Verilator catches what Icarus accepts happily but synthesis will not — inferred latches, width
  mismatches, multiply-driven signals. Running it early builds the habit before the design is
  large enough for those bugs to hide.
- Migration to Verilator as primary simulator becomes a later decision, made when simulation
  speed actually hurts. Write testbenches that don't gratuitously depend on Icarus-specific
  behaviour.
- `-g2012` is required or `always_ff` / `always_comb` / `logic` will not compile.
