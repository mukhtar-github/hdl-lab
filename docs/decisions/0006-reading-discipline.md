# 0006 — Read specifications and implementations, not domain material

- **Date:** 2026-09-17
- **Status:** Accepted
- **Phase:** 0 (policy), binding for the life of the project

## Context

`0001` committed the project to telematics frame decoding, with FleetPoynt supplying the
*interest* — why a year of evenings goes to frame decoding rather than matrix multiply. That was
then misread, by me, as an obligation to learn telematics **as a domain**: sensors, fleet
workflows, what operators do with the data, how vehicle-to-dashboard chains fit together.

The core never sees any of that. It sees **bytes**. The only questions it can answer are:

```
what bytes arrive → how are they framed → where are the fields
→ how are they decoded → how is validity checked → what consumes them
```

Knowing that a tracker can report harsh braking tells you nothing about how a harsh-braking
event is *encoded in a GT06 frame*, and only the second fact can become a comparator, a state
machine, a branch, or a CRC.

**And there is a second, sharper reason, discovered by walking into it.** A general telematics
explainer, requested in this project's context, came back containing a FleetPoynt architecture
diagram with a telematics device placed inside it. That is not coincidence. Domain material
about a space you operate in drifts toward product recommendations, because recommending is
what the genre is *for*.

A protocol specification cannot do that. It is bytes and offsets. It holds no opinion about
whether you should own the endpoint.

This is the roadmap's existing *"letting the workload search decide a business question"*
failure mode arriving through a side door — not from hunting for something to accelerate, but
from ordinary background reading.

## Options considered

1. **Study telematics as an application domain** — rejected. Produces almost nothing the RTL can
   use, costs real weeks, and carries the contamination hazard above. Motivation is not a
   curriculum.

2. **Read specifications, reference implementations and real packets** — accepted. Three
   complementary views, none of which can recommend anything:

   | Source | Answers |
   |---|---|
   | Specification | what *should* happen |
   | Reference implementation | how someone actually handles it |
   | Real captured packets | what actually turns up |

## Decision

**For the chip project, read specifications and implementations. Not domain material.**

The operational test, applied before opening anything:

> If what you are reading could plausibly contain a recommendation about FleetPoynt, it is
> product reading, and it belongs in a product session.

Reading order, by value:

1. **Traccar's source, first.** An open-source GPS platform implementing 200+ device protocols;
   its decoders are the de facto documentation for this family, because vendor specs are
   inconsistent, incomplete and frequently only in Chinese. `Gt06ProtocolDecoder.java`; JT808
   lives under the Huabao decoder. A working implementation of the thing you are about to write
   beats any spec summary.
2. **Real captured hex, second.** Traccar's forums carry raw packet logs posted by people
   debugging their own devices, plus a hex decoder tool. Useful for sanity-checking a parser
   before building a generator. See the provenance caveat in `bench/README.md` before any of it
   is committed.
3. **Vendor specs, third and briefly.** GT06 and JT/T 808 circulate freely. Skim for byte
   layout and checksum definition, then close them. Reference material, not reading material.

**Terminology, to keep the engineering artifact separate from the product:** the benchmark is
the **Telematics Frame Decoder Benchmark**. FleetPoynt is *workload context*, never part of the
artifact's name. "The FleetPoynt benchmark" is not a thing and should never be written.

## Consequences

- **Phase 0's benchmark work starts immediately and cheaply.** The wire format is roughly twenty
  pages, public, downloadable today. The domain is a field.
- **A structural finding already arrived from following this rule.** GT06 frames start `7878` or
  `7979`; JT/T 808 frames start *and end* with `7e`. So the two protocols are framed differently
  in kind — length-prefixed versus delimiter-terminated — and that asymmetry is the *root* of the
  escaping difference in Prediction B, not an incidental detail of it. One line of a
  protocol-identification table, worth more than a chapter of domain explanation.
- **Malformed frames are routine, not an edge case.** Traccar has open JT808 decoder pull
  requests and forum threads where a device speaks a variant the decoder chokes on —
  `readerIndex + length exceeds writerIndex`, a length-field disagreement causing a
  frame-boundary error, live, in production, in a mature codebase. This is direct evidence for
  the resync branch of Prediction B, and it changes a benchmark requirement: the generator must
  emit malformed and variant frames deliberately at a realistic rate. Recorded in
  `bench/README.md` and added to the declared stimulus parameters.
- **Forecloses** claims about operator behaviour, deployment practice or market shape. The
  project can say what the bytes cost to decode. It cannot say what fleets want, and must not
  write as though it can.
- Does not forbid domain reading. It relocates it — a different session, no connection to this
  repository, per the roadmap's re-derive-cold rule.

## Predictions

Reading Traccar's GT06 decoder will surface intra-vendor variance that no specification
documents — fields that are ASCII in one model and binary in another, values packed into spare
bits of an adjacent field. If so, the dispatch layer is a larger fraction of the workload than
`0001` assumed, which shifts weight toward **Prediction A**. Recorded now so that shift is
visible as a prediction changing rather than as a conclusion that was always held.
