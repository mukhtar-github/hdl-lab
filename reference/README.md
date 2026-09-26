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

## Vendor specification — GT06

Per `0006`, specifications as well as implementations. This is the one this project cites.

- **Document:** *GPS Tracker Communication Protocol*, GT06, v1.8.1 — Shenzhen Concox Information
  Technology Co., Ltd. 44 pages, dated 2012-07-13, watermarked CONFIDENTIAL on every page.
- **Fetched:** 2026-09-25, from the copy Traccar links in its protocol list:
  https://www.traccar.org/protocol/5023-gt06/GT06_GPS_Tracker_Communication_Protocol_v1.8.1.pdf
- **SHA-256:** `adbb99f64b3b84c2296b274d59c96f85cd316a1cfd1434ab0a2870ab72b633e8`
- **Cited for:** CRC-ITU.
  - §5.1.3 has a login example and the server's response (PDF page 12, printed 11). Both are
    anchors in `bench/rv32/crc_oracle.py`.
  - Appendix A, `crctab16` and `GetCrc16` (PDF page 37, printed 36), is the algorithm
    `decisions/0008` states. All 256 entries are identical to `crc_itu_table`.
- **Two things to know when reading it:**
  - The example's hex string reads `78 780 0D …`. That is a typo in the document: the
    byte-by-byte row directly beneath it gives `0x78 0x78 | 0x0D`.
  - A second login example (PDF page 38) carries a terminal ID that may be a real IMEI. It was
    checked locally and not committed (`bench/README` rule 2a).

```bash
curl -sSfL -o reference/GT06_GPS_Tracker_Communication_Protocol_v1.8.1.pdf \
  "https://www.traccar.org/protocol/5023-gt06/GT06_GPS_Tracker_Communication_Protocol_v1.8.1.pdf"
shasum -a 256 reference/GT06_GPS_Tracker_Communication_Protocol_v1.8.1.pdf   # must match the above
```

Not committed: it is the vendor's copyright and marked confidential. The hash pins exactly what
was read. If the linked copy changes, the hash will say so.

Reading it here needs poppler (`pdftotext`, `pdftoppm`). It was installed with
`HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1 brew install poppler`, so
that nothing already installed was upgraded. This machine's Homebrew also holds the pinned
RISC-V toolchain.

## Why the .java files are not committed

Apache-2.0 permits vendoring. Whether third-party source belongs in this repository is a
provenance decision, not a default — and nothing here is needed to build or run anything in the
project. A pinned URL reproduces it exactly. If that changes (offline work, or the benchmark
starts citing specific decoder behaviour), vendor it deliberately with the licence retained and
say so in a decision record.
