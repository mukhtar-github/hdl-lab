# bench/ — the Telematics Frame Decoder Benchmark

That is its name. FleetPoynt is *workload context*, never part of the artifact's name — the
engineering object and the product stay separate on the page as well as in the reasoning
(`decisions/0006`).

```
Workload context : FleetPoynt (motivation only)
Benchmark        : telematics frame decoding
Protocols        : GT06 / JT/T 808 variants
Input            : deterministic byte streams
Output           : decoded frame records
```

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

## What to read before writing any of it

Specifications and implementations. **Not domain material** — see `decisions/0006` for why that
distinction is load-bearing rather than pedantic. In order of value:

1. **Traccar's source.** `Gt06ProtocolDecoder.java`; JT808 under the Huabao decoder. The de
   facto documentation for this protocol family, because vendor specs are inconsistent,
   incomplete and often only in Chinese.
2. **Real captured hex** from Traccar's forums and hex decoder tool — for sanity-checking a
   parser before the generator exists. *Read the provenance caveat below before committing any.*
3. **Vendor specs**, skimmed for byte layout and checksum definition, then closed.

Already banked from doing this, before a line of code:

> GT06 frames start `7878` or `7979`. JT/T 808 frames start **and end** with `7e`.

Those two protocols are therefore framed differently *in kind* — length-prefixed versus
delimiter-terminated. That asymmetry is the root of the escaping difference in Prediction B,
not a detail of it.

## Three rules

**1. Stimulus is synthesised from published specifications.** GT06 and JT/T 808 are public
documents. The generator is code in this directory; its output is regenerable from a seed, so
the inputs are versioned as *a generator plus a seed*, not as a blob.

**2. No captured operational data. Ever.** A real trace supplies *optional realism for the
arrival model only* — inter-arrival distribution, dark gaps, malformed rate. Borrow the shape,
never the data. The FleetPoynt trace is live GPS history of real vehicles; it does not enter
version control, and `.gitignore` enforces this mechanically rather than relying on discipline
at 1am.

**2a. Forum hex is not automatically safe to redistribute.** It is a different provenance from
the FleetPoynt trace — strangers' test devices, publicly posted, no comparable obligation — and
it is genuinely useful for validating a parser. But GT06 identifies by **cleartext IMEI**, and
an IMEI in a forum post is still a real device identifier. Use it locally to check your decoder;
if any of it is to be committed, scrub identifiers first and record where it came from. Decide
that deliberately, not at 1am.

**3. Record the provenance the day you write it.** Spec-derived stimulus run through a decoder
you wrote is a **reconstruction**, not instrumented production code. Both are legitimate
benchmark types. Confusing them at Phase 4 is not, and the confusion is far easier to prevent
now than to detect later. State which one this is, in this file, in writing.

## Parameters that must be declared in every result manifest

Not left implicit — predictions A and B in `0001` diverge on exactly these:

- **Protocol mix** (GT06 : JT/T 808 ratio)
- **Resync rate** / malformed-frame rate
- **Variant mix** — which GT06/JT808 model variants, in what proportion
- **Frame length distribution**
- **Generator seed**

## Malformed frames are a requirement, not an edge case

The generator must emit malformed and variant frames **deliberately, at a realistic rate**. A
benchmark of 1000 well-formed packets measures the wrong thing.

Evidence, not assumption: Traccar carries open JT808 decoder pull requests and forum threads
where a device speaks a variant the existing decoder chokes on —
`readerIndex + length exceeds writerIndex`, a length-field disagreement producing a
frame-boundary error, live, in production, in a mature codebase. Handling that is a meaningful
fraction of what a real decoder does.

This is also direct evidence for the resync branch of Prediction B, which `0001` deferred as
"not on the critical path." It is now on it.
