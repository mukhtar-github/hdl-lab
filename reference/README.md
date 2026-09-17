# reference/ — third-party source, read-only

Reference implementations, fetched for reading. **Not part of this project's build, and not
committed** — the `.java` files here are gitignored. This file records what belongs here and
how to get it back, which is the part worth keeping.

Per `docs/decisions/0006`: read implementations and specifications, not domain material.
Traccar's decoders are the de facto documentation for the GT06 / JT/T 808 family, because the
vendor specs are inconsistent, incomplete and frequently only in Chinese.

## What's here

Traccar splits each protocol into **framing** and **field decoding**. That split maps onto the
two halves of Prediction A in `decisions/0001`, so read them as separate concerns:

| | GT06 | JT/T 808 |
|---|---|---|
| **Framing** — find frame boundaries in the byte stream | `Gt06FrameDecoder.java` (2.0 KB) | `Jt808FrameDecoder.java` (3.3 KB) |
| **Fields** — dispatch, unpack, checksum | `Gt06ProtocolDecoder.java` (77 KB) | `Jt808ProtocolDecoder.java` (95 KB) |
| Wiring / registration | `Gt06Protocol.java` | `Jt808Protocol.java` |

**Read the size ratio carefully.** ~30-40x more code in field handling than framing tells you
where the *variant complexity* lives. It says nothing about where the *cycles* go — a 77 KB
decoder may execute one narrow path per frame while a 2 KB frame decoder runs over every byte.
That is exactly the O(1)-per-frame versus O(n)-per-byte distinction the predictions turn on.
Do not let a source-size observation quietly become evidence for a cycle-count claim.

## Provenance

- **Source:** https://github.com/traccar/traccar
- **Path:** `src/main/java/org/traccar/protocol/`
- **Fetched:** 2026-09-17
- **Pinned commit:** `847edd2c8c4dcc47426fb76b7800b342dea3cde6`
- **Licence:** Apache-2.0, Copyright 2012-2026 Anton Tananaev

Note the JT808 decoder was formerly `HuabaoProtocolDecoder.java` and has been renamed. Older
references to "the Huabao decoder" mean this file.

## Refetch

```bash
B=https://raw.githubusercontent.com/traccar/traccar/847edd2c8c4dcc47426fb76b7800b342dea3cde6/src/main/java/org/traccar/protocol
for f in Gt06FrameDecoder Gt06Protocol Gt06ProtocolDecoder \
         Jt808FrameDecoder Jt808Protocol Jt808ProtocolDecoder; do
    curl -sL -o "reference/$f.java" "$B/$f.java"
done
```

The URL pins the commit rather than `master`, so this fetches what was actually read, not
whatever the file has become since.

## Why the .java files are not committed

Apache-2.0 permits vendoring. Whether third-party source belongs in this repository is a
provenance decision, not a default — and nothing here is needed to build or run anything in the
project. A pinned URL reproduces it exactly. If that changes (offline work, or the benchmark
starts citing specific decoder behaviour), vendor it deliberately with the licence retained and
say so in a decision record.
