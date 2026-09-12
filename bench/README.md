# bench/ — the benchmark

Empty on purpose. Decision `docs/decisions/0004-benchmark-first.md` says what goes here and
in what order, and this file exists so the rules are in front of you on the day you start
writing rather than in a document you have to remember to reopen.

## What goes here

```
protocol specification → stimulus generator → reference decoder
                       → expected output → Spike reference execution
```

Built **before** the core executes it, not after. A benchmark written after the core exists is
written to the core's shape, and Phase 4 then ratifies the design instead of testing it.

## Three rules

**1. Stimulus is synthesised from published specifications.** GT06 and JT/T 808 are public
documents. The generator is code in this directory; its output is regenerable from a seed, so
the inputs are versioned as *a generator plus a seed*, not as a blob.

**2. No captured operational data. Ever.** A real trace supplies *optional realism for the
arrival model only* — inter-arrival distribution, dark gaps, malformed rate. Borrow the shape,
never the data. The FleetPoynt trace is live GPS history of real vehicles; it does not enter
version control, and `.gitignore` enforces this mechanically rather than relying on discipline
at 1am.

**3. Record the provenance the day you write it.** Spec-derived stimulus run through a decoder
you wrote is a **reconstruction**, not instrumented production code. Both are legitimate
benchmark types. Confusing them at Phase 4 is not, and the confusion is far easier to prevent
now than to detect later. State which one this is, in this file, in writing.

## Parameters that must be declared in every result manifest

Not left implicit — predictions A and B in `0001` diverge on exactly these:

- **Protocol mix** (GT06 : JT/T 808 ratio)
- **Resync rate** / malformed-frame rate
- **Frame length distribution**
- **Generator seed**
