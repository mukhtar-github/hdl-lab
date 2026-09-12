# 0001 — Workload: telematics frame decoding at line rate

- **Date:** 2026-09-01
- **Status:** Accepted
- **Phase:** 0

## Context

The project needs a Phase 0 workload commitment: a destination that gives direction and informs
early architectural choices, without pre-deciding the accelerator mechanism.

Two candidates were considered seriously. Both were reached through a search that kept returning
I/O-bound workloads, which turned out to be a property of the search, not bad luck.

## Options considered

1. **"Build an AI accelerator"** — rejected. Not a workload at all; it names a *mechanism*,
   leaving nothing for profiling to discover. Also: chosen under hype pressure, the compute array
   is the easy part while memory bandwidth and the compiler stack are the hard parts, and on a
   modest FPGA the project silently becomes a memory hierarchy project.

2. **Tracker firmware (fix loop)** — rejected. One report per ~86 seconds means the device is
   radio-bound and power-bound. Honest Phase 4 finding would be "nothing to accelerate," leaving
   Phase 5 with no hardware to build.

3. **Telematics frame decoding** — accepted. Integer-only, bit-heavy, branchy, no floating point,
   no OS dependency. Ports to bare-metal RV32IM without ceremony.

## Decision

**Telematics frame decoding at line rate.** Stated deliberately as *a protocol family and a
rate* — never a deployment.

Benchmark scale is decoupled from deployment scale. Line-rate packet decoding is a real silicon
domain (SmartNICs, DPUs); the architecture question stands at a rate no fleet deployment reaches.

## Consequences

- **Frees the project from all external dependencies.** GT06 and JT/T 808 are public documents.
  No waiting on anyone's data, access, or strategy.
- **The business case does not follow, and must never be written as though it does.** ~116
  packets/sec at 10k devices is free on any rented box.
- Stimulus is synthesised from published specs. A real trace supplies optional realism for the
  arrival model only — never committed, never a dependency.
- It is not one decoder: GT06 uses CRC-ITU, JT/T 808 uses XOR with 0x7e escaping, and variance
  is intra-vendor too. A family behind a dispatch layer, branchier than it first appears.

## Predictions

See `roadmap.md` → *Recorded predictions — 2026-09-01*. Two opposed hypotheses recorded, with
resync rate as the discriminator.
