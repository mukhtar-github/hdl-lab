# Handoff

Where the next working session starts: the state, what is next, commands, gotchas. Each handoff
overwrites this file, and git keeps every earlier one: `git log -p -- docs/HANDOFF.md`.

It is a summary, derived from the journal, the decision records and git, so it can be wrong or
stale. A new session checks it against the live state before acting on it.

---

*Written by Claude as the last chat reply of the session that ended 2026-09-27 06:02 UTC (transcript
`19fa6aa8`), and saved here verbatim.*

## hdl-lab handoff (2026-09-27)

**State:** Phase 0. `main` is at `cb1d711`, PRs #8–#14 are all merged, the working tree is clean, and the local checkout is on `main`.

**Done last session**
- **0001 answered (#8).**
  - The output lines sort into three groups: reference (`crc_ref`, `acc`), workload (`iters`) and measurement (`instret`).
  - Stale-build bug `docs/bugs/0004` is fixed: build directories are named by a hash of compiler + flags + source.
  - `make run` now prints the flags and the loaded-image hash, and `make check` holds the output to `crc_oracle.py`.
  - `capture.sh` now lists untracked files, quotes the command and records where it ran.
  - 12 captures.
- **0008 (#9).** The reference is the byte-wise reflected table, written in the source (`CRC_IMPL=table`), with `-fno-optimize-crc` pinned (`ALGOFLAGS`) and a memory barrier in the sweep. The reference is **138,137 instret, image `1baf3e07…`**.
  - #11 amended it: GT06 v1.8.1 Appendix A `crctab16` is identical to our table.
  - #13 tested its prediction: -O1 +3.6%, -O3 −12.3%, -Os +13.8%, so it held. The spread across levels is still about the same as the bitwise program's.
- **0002 opened (#10):** a joint prediction on Zbkb/Zbc. My prediction is sealed in the **local tag** `sealed/0002-claude-prediction`.
- **GT06 citations pinned (#11).** poppler is installed. The PDF is in `reference/`, gitignored and pinned by SHA-256.
- **Spike 1.1.0 rebuilt with `--enable-commitlog` (#12).** Output and traces were verified identical to the old build.
- **`make -C bench/rv32 anatomy` (#14)** regenerates the CRC Byte Anatomy page: https://claude.ai/artifact/5errrsAzSxXbhLwmG4RLQY

**Per-byte cost** (plus about 18 per CRC outside the loop):

| Program | Per byte | instret |
|---|---:|---:|
| Bitwise loop | 77 | 942,942 |
| GCC's substituted table | 51 (40 of them bit reversal) | 630,653 |
| Stated table | 10 | 138,137 |

**Next, in order**
1. **0002.** I write my hypothesis for B (`rv32im_zbkb`), C (`rv32im_zbc`) and D (both). For each: instret, whether the 512-byte table survives, the mechanism, whether it beats 138,137, and what would change my mind. Then:
   1. Commit my hypothesis verbatim.
   2. Open the seal and verify its hash.
   3. Commit the sealed text verbatim.
   4. Only then capture B, C and D.

   No Zbkb/Zbc builds before step 1.
2. **Loose end:** 0001 was merged exactly as drafted, and its status line still says "for the author to edit". Either leave it, or append a one-line note in the 0007 style (the file is immutable).
3. **The real Phase 0 item: the stimulus generator**, from `bench/SPEC.md` §1–5 and §8. The stimulus must be data the compiler can't see (see `bench/README`). `crc_itu_ref.c` is only a harness proof, not the benchmark.
4. **QEMU isn't planned.** Revisit it for gdb source-level debugging once the decoder exists. For a second opinion on the ISA, prefer Sail.

**Commands**
- `make -C bench/rv32 check [VARS]`
- `scripts/capture.sh <label> make -C bench/rv32 check [VARS]`
- `make -C bench/rv32 anatomy`
- `spike -d …`, or `spike -l --log-commits --log=f …`

**Gotchas**
- zsh doesn't word-split `$vars`.
- Paste only the `spike -d` line itself; debugger commands pasted with it go to zsh, which treats `until` as a loop.
- Spike's debugger misreads piped input, so use `--debug-cmd=<file>`.
- Install with Homebrew only with `HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1`, then re-check the reference image hash.
- Start every topic from a freshly fetched `origin/main`.
