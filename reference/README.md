# reference/ — third-party source, read-only

Reference implementations and specifications, fetched for reading. **Not part of this project's
build, and not committed**: the `.java` and `.pdf` files here are gitignored. This file records
what belongs here and how to get it back, which is the part worth keeping.

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

Added 2026-09-27, from the same commit:

| File | Why it is here |
|---|---|
| `Jt600ProtocolDecoder.java` | `decodeBinaryLocation()`, which JT808 message `0x5501` delegates to (`Jt808ProtocolDecoder.java:1526`). The benchmark's `0x5501` frames are laid out from it. |
| `BcdUtil.java`, `BitUtil.java`, `Checksum.java` | Helpers the decoders call. Read for exact semantics: an odd BCD digit count peeks at the next byte without consuming it, and `CRC16_X25` is CRC-16/X-25. |
| `Gt06ProtocolDecoderTest.java`, `Jt808ProtocolDecoderTest.java`, `Jt808FrameDecoderTest.java` | Traccar's unit tests. **Their frames are real-device and forum hex** (`bench/README` rule 2a), so they are only counted, locally, by `bench/evidence/checksums.py`. None of their bytes is committed. |

Added 2026-09-28, from the same commit:

| File | Why it is here |
|---|---|
| `Gt06FrameDecoderTest.java` | Traccar's GT06 framer test. With `Jt808FrameDecoderTest.java`, it anchors the port of both framers in `bench/evidence/framing.py` (`PROTOCOL-EVIDENCE` Finding 8). Real-device hex again, so it is only used locally and none of its bytes is committed. |

Added 2026-09-29, from the same commit, for `PROTOCOL-EVIDENCE` Finding 9 and `decisions/0012`:

| File | Why it is here |
|---|---|
| `DateBuilder.java`, `BaseProtocolDecoder.java`, `DeviceSession.java` | Which time zone each decoder reads a time in, when nothing is configured: UTC for GT06 and for `0x5501`. `DateBuilder` also makes a two-digit year 2000 + YY. |
| `UnitsConverter.java` | Traccar's km/h-to-knots ratio, rounded to six places |
| `Position.java` | The only range check on a decoded location: latitude and longitude |
| `Jt808FrameEncoder.java` | How a JT808 response is escaped. Its `E7` alphabet escapes `0x3D`, which gives `bench/stimulus` rule R9 its source. |

**Read the size ratio carefully.** ~30-40x more code in field handling than framing tells you
where the *variant complexity* lives. It says nothing about where the *cycles* go — a 77 KB
decoder may execute one narrow path per frame while a 2 KB frame decoder runs over every byte.
That is exactly the O(1)-per-frame versus O(n)-per-byte distinction the predictions turn on.
Do not let a source-size observation quietly become evidence for a cycle-count claim.

## Provenance

- **Source:** https://github.com/traccar/traccar
- **Path:** `src/main/java/org/traccar/protocol/`, and since 2026-09-27 also
  `src/main/java/org/traccar/helper/` and `src/test/java/org/traccar/protocol/`. Since 2026-09-29,
  also `BaseProtocolDecoder.java` in `src/main/java/org/traccar/`, and one file each from its
  `session/` and `model/`.
- **Fetched:** 2026-09-17; the files added above on 2026-09-27, 2026-09-28 and 2026-09-29
- **Pinned commit:** `847edd2c8c4dcc47426fb76b7800b342dea3cde6`, for every file
- **Licence:** Apache-2.0, Copyright 2012-2026 Anton Tananaev

Note the JT808 decoder was formerly `HuabaoProtocolDecoder.java` and has been renamed. Older
references to "the Huabao decoder" mean this file.

## Refetch

```bash
B=https://raw.githubusercontent.com/traccar/traccar/847edd2c8c4dcc47426fb76b7800b342dea3cde6/src
for p in main/java/org/traccar/protocol/Gt06FrameDecoder main/java/org/traccar/protocol/Gt06Protocol \
         main/java/org/traccar/protocol/Gt06ProtocolDecoder main/java/org/traccar/protocol/Jt808FrameDecoder \
         main/java/org/traccar/protocol/Jt808Protocol main/java/org/traccar/protocol/Jt808ProtocolDecoder \
         main/java/org/traccar/protocol/Jt600ProtocolDecoder \
         main/java/org/traccar/helper/BcdUtil main/java/org/traccar/helper/BitUtil \
         main/java/org/traccar/helper/Checksum \
         test/java/org/traccar/protocol/Gt06ProtocolDecoderTest \
         test/java/org/traccar/protocol/Jt808ProtocolDecoderTest \
         test/java/org/traccar/protocol/Jt808FrameDecoderTest \
         test/java/org/traccar/protocol/Gt06FrameDecoderTest \
         main/java/org/traccar/helper/DateBuilder main/java/org/traccar/helper/UnitsConverter \
         main/java/org/traccar/BaseProtocolDecoder main/java/org/traccar/session/DeviceSession \
         main/java/org/traccar/model/Position main/java/org/traccar/protocol/Jt808FrameEncoder; do
    curl -sSfL -o "reference/${p##*/}.java" "$B/$p.java"
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

## riscv-tests — the Phase 2 gate's own harness

Read for `decisions/0009`, which decides what the core must implement for riscv-tests' standard
environment to run unmodified. Its line citations are to these files.

- **Source:** https://github.com/riscv-software-src/riscv-tests at
  `bcffa2b3188b040c611f90dc0b6e422f54775a09`. Its `env` submodule is
  https://github.com/riscv/riscv-test-env, pinned by that commit at
  `6de71edb142be36319e380ce782c3d1830c65d68`, which is not that repository's latest.
- **Fetched:** 2026-09-28
- **Licence:** BSD-style, Copyright 2012-2015 The Regents of the University of California

| File | Why it is here |
|---|---|
| `env/p/riscv_test.h` | The standard environment that starts and ends every `-p-` test: the CSRs, exceptions and `mret` it needs |
| `env/p/link.ld` | The environment's linker script: code at `0x80000000`, and `tohost` on the next page |
| `isa/rv32ui/Makefrag`, `isa/rv32mi/Makefrag` | Which tests make up each group |
| `isa/rv64ui/ma_data.S`, `isa/rv64ui/fence_i.S` | The two `rv32ui` tests that reach beyond RV32I. The `rv32ui` versions include these. |
| `isa/rv64mi/illegal.S`, `isa/rv64si/csr.S` | What `rv32mi` expects of the illegal-instruction trap. `rv32mi`'s `csr` test is `rv64si/csr.S` built for machine mode. |

```bash
T=https://raw.githubusercontent.com/riscv-software-src/riscv-tests/bcffa2b3188b040c611f90dc0b6e422f54775a09
E=https://raw.githubusercontent.com/riscv/riscv-test-env/6de71edb142be36319e380ce782c3d1830c65d68
mkdir -p reference/riscv-tests/env/p reference/riscv-tests/isa/rv32ui \
         reference/riscv-tests/isa/rv32mi reference/riscv-tests/isa/rv64ui \
         reference/riscv-tests/isa/rv64mi reference/riscv-tests/isa/rv64si
curl -sSfL -o reference/riscv-tests/env/p/riscv_test.h "$E/p/riscv_test.h"
curl -sSfL -o reference/riscv-tests/env/p/link.ld "$E/p/link.ld"
for p in isa/rv32ui/Makefrag isa/rv32mi/Makefrag isa/rv64ui/ma_data.S isa/rv64ui/fence_i.S \
         isa/rv64mi/illegal.S isa/rv64si/csr.S; do
    curl -sSfL -o "reference/riscv-tests/$p" "$T/$p"
done
```

Not committed, like the rest of `reference/`. The directory is gitignored.

## Spike's source — the model the core is held to

Read for `decisions/0009`'s amendment, which takes the exact CSR access rules from the simulator the
core will run in lockstep with (rung 4), until the Privileged Architecture itself is pinned.

- **Source:** https://github.com/riscv-software-src/riscv-isa-sim at tag `v1.1.0`, commit
  `530af85d83781a3dae31a4ace84a573ec255fefa`, the build `bench/rv32/README.md` pins
- **Fetched:** 2026-09-28
- **Licence:** BSD-3-Clause, Copyright The Regents of the University of California

| File | Why it is here |
|---|---|
| `riscv/csrs.cc` | A CSR is read-only by its address (bits 11:10 = `11`), and only a write to one traps |
| `riscv/processor.cc` | A missing CSR traps on any access; which CSRs exist, including the four ID registers |
| `riscv/insns/csrrs.h`, `csrrsi.h`, `csrrw.h` | What counts as a write: `csrrs` and `csrrsi` only when `rs1` is non-zero, `csrrw` always |

```bash
B=https://raw.githubusercontent.com/riscv-software-src/riscv-isa-sim/530af85d83781a3dae31a4ace84a573ec255fefa
mkdir -p reference/spike/riscv/insns
for p in riscv/csrs.cc riscv/processor.cc riscv/insns/csrrs.h riscv/insns/csrrsi.h riscv/insns/csrrw.h; do
    curl -sSfL -o "reference/spike/$p" "$B/$p"
done
```

Not committed. The directory is gitignored.

## The RISC-V manuals, and three study aids

Added 2026-09-30. The author downloaded each file between 2026-08-31 and 2026-09-26. Four of them
came from a Google Drive copy, not from their publisher. So on 2026-09-30 each file was compared
with its publisher's release, and all seven are byte-identical to it.

| File | Document | Version | Why it is here |
|---|---|---|---|
| `riscv-unprivileged.pdf` | *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*, 727 pages | 20250508, ratified | The ISA that the core implements, and the ratified extensions that rule 3 names. `decisions/0013`'s Amendment 2 cites it. |
| `riscv-privileged.pdf` | *The RISC-V Instruction Set Manual, Volume II: Privileged Architecture*, 221 pages | 20250508, ratified | The version that `decisions/0009` pins before Phase 2's trap minimum is written (its §2). 0009's rules are to be checked against it. |
| `riscv-spec-20191213.pdf` | *The RISC-V Instruction Set Manual, Volume I: Unprivileged ISA*, 238 pages | 20191213 | The version that GCC 16.2.0 assumes by default: `-misa-spec=20191213` reaches `cc1` (`experiments/0001`). |
| `riscv-abi.pdf` | *RISC-V ABIs Specification*, 56 pages | 1.0, ratified | The `ilp32` calling convention that `bench/rv32` builds with |
| `rvalp.pdf` | *RISC-V Assembly Language Programming*, John Winans, 91 pages | Draft v0.18.4, 2026-07-28 | A study aid. Not cited. |
| `riscv-card.pdf` | *RISC-V Reference Card*, 6 pages | v1.0 | A study aid. Not cited. |
| `greencard-20181213.pdf` | The green card of *The RISC-V Reader*, David Patterson, 2 pages | 2018-12-13 | A study aid. Not cited. It predates most of the ratified extensions. |

**Where these disagree, Volumes I and II at 20250508 win.** A record that cites another version
says so.

- **Sources:** the releases of https://github.com/riscv/riscv-isa-manual (tags `20250508` and
  `Ratified-IMAFDQC`), https://github.com/riscv-non-isa/riscv-elf-psabi-doc (tag `v1.0`),
  https://github.com/johnwinans/rvalp (tag `v0.18.4`), https://github.com/jameslzhu/riscv-card
  (tag `v1.0`), and http://riscvbook.com/greencard-20181213.pdf
- **Versions:** on 2026-09-30, 20250508 is the newest numbered release of the ISA manual. The
  releases after it are automatic builds, named `riscv-isa-release-<commit>-<date>`.
- **Licences:** CC-BY-4.0 for all but the green card, which states none

```bash
R=https://github.com/riscv/riscv-isa-manual/releases/download
curl -sSfL -o reference/riscv-unprivileged.pdf "$R/20250508/riscv-unprivileged-20250508.pdf"
curl -sSfL -o reference/riscv-privileged.pdf "$R/20250508/riscv-privileged-20250508.pdf"
curl -sSfL -o reference/riscv-spec-20191213.pdf "$R/Ratified-IMAFDQC/riscv-spec-20191213.pdf"
curl -sSfL -o reference/riscv-abi.pdf \
  https://github.com/riscv-non-isa/riscv-elf-psabi-doc/releases/download/v1.0/riscv-abi.pdf
curl -sSfL -o reference/rvalp.pdf https://github.com/johnwinans/rvalp/releases/download/v0.18.4/rvalp.pdf
curl -sSfL -o reference/riscv-card.pdf \
  https://github.com/jameslzhu/riscv-card/releases/download/v1.0/riscv-card.pdf
curl -sSfL -o reference/greencard-20181213.pdf http://riscvbook.com/greencard-20181213.pdf
shasum -a 256 -c <<'EOF'
cef2e63c08c6f82cf7acc9056a589954f5b1adf6f7dccaa38cd75278b093e984  reference/riscv-unprivileged.pdf
d0228bbecc76943aaa5685e381e0263a8c750d18b1b0c452b086b0ddd15a4955  reference/riscv-privileged.pdf
f392624cc815cd3f259413cbd9ae2f38678ee930878855a0f4673019410d7554  reference/riscv-spec-20191213.pdf
a8d06bdcaa82a6a4567a1904dc27ef1ca1043ebaa1f523558c927a9d72bc23d9  reference/riscv-abi.pdf
2fe3d9b2ce0db9ed07106fc983e71db0b79391dc07dd041e3f9c16840de7fb5d  reference/rvalp.pdf
401f90fa557cf5f501e761eb0ec17cce98eac798f65cc85acf811113dafe7aea  reference/riscv-card.pdf
8016ae4e7c3ba676b3dd927530f41e967116b56441f108c62e44c196fc39dd74  reference/greencard-20181213.pdf
EOF
```

The URLs name each release by its tag, so this fetches what was checked, not a later build. The
last command fails if any file differs. Not committed: the PDFs are gitignored, like the GT06
document.
