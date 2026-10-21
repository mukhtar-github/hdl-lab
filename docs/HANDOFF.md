# Handoff

Where the next working session starts: the state, what is next, commands, gotchas. Each handoff
overwrites this file, and git keeps every earlier one: `git log -p -- docs/HANDOFF.md`.

It is a summary, derived from the journal, the decision records and git, so it can be wrong or
stale. A new session checks it against the live state before acting on it.

---

*Written by Claude on 2026-09-28 (transcript `9a8face2`), after #19 merged. Updated the same day for
both rounds of amendments to `0009` and `0010`, on 2026-09-29 for `0011` and `0012`, and on
2026-09-30 for `experiments/0002`'s result, for the author's answers with `0013` among them, for the
pinned RISC-V manuals, and for `0014`; on 2026-10-01 for `stimulus.bin` version 2 and an amendment
to `0004`; and on 2026-10-02 for the decoder's harness.*

## hdl-lab handoff (2026-09-28)

**State:** `main` was at `34e94c6` when this was written, and at `bedf5de` when it was last updated,
with PRs #8–#31 all merged and the decoder's harness in review. **Phase 0 is open again**, for the
benchmark (`decisions/0010`). Phase 1's gate is passed. The only pushed tag is
`v0.1-alu-golden-model-passing`. The tag `sealed/0002-claude-prediction` is still local only. It has
been opened, and its text is in `experiments/0002`, so the tag is redundant now.

**If you are a second assistant reading this:** it replaces any other handoff. Where anything
disagrees with `roadmap.md` or a decision record, those win. **Freshness is by commit, not by
length.** `roadmap.md` was last changed in `35b17f5`; `git log -1 --format=%h -- roadmap.md` prints
the current one. A copy from before it is out of date. (This note once gave a line count, and it was
stale the same day.)

### Phase gates, and where each stands

| Phase | Gate (`roadmap.md`) | Stands |
|---|---|---|
| 0 | 1. Find a deliberately introduced bug by reading a waveform. 2. The benchmark runs on Spike, is checked against the generator's intent, is captured at every declared configuration, and is frozen and tagged (`0010`) | 1 passed 2026-09-21 (#1). **2 open.** It closes with the tag `v0.0-benchmark-frozen` |
| 1 | The ALU passes randomised testing against a golden model | Passed 2026-09-21 (#2), tagged `v0.1-alu-golden-model-passing`. The register file and memories are still to build, with no gate of their own |
| 2 | `rv32ui-p-*` passes through riscv-tests' standard environment, unmodified: its `riscv_test.h` and `link.ld`, so memory sits at `0x80000000`. That needs the trap minimum (`0009`, amended) | Not started. **The core runs no program until Phase 0 closes** (`0010`). The Privileged Architecture is pinned at 20250508, and `0009`'s rules are checked against it before any trap work |
| 3 | riscv-tests on the pipeline (plus `rv32um`, `rv32mi`), ACT4, lockstep against Spike, and an RTOS boots | Not started. The rest of the privileged scope must be fixed before pipeline design (`0009`'s open items). Lockstep's Spike configuration and expected divergences must be declared before it starts |
| 4 | None written: profile on the core, plus a commodity-MCU baseline, judged against Predictions A–C | — |
| 5 | Three numbers, honestly reported: speedup, area, Fmax, plus versus commodity | — |
| 6, 7 | None written: FPGA, then the ASIC flow, open-ended | — |

**Done on 2026-09-28**
- **`0009` (#18), no OS under the benchmark.**
  - The core's trap minimum moves into Phase 2. Since the second amendment it is a rule: what
    riscv-tests' standard environment needs, what the harness reads, and every register the pinned
    Privileged Architecture makes mandatory for a machine-mode-only RV32 hart. Until the pin, the
    list is `Zicsr`; `mstatus`, `mtvec`, `mepc`, `mcause`, `mhartid`, `mie`, `misa`, `mvendorid`,
    `marchid`, `mimpid`; `ecall` and illegal-instruction exceptions; `mret`; and `instret`.
  - The rest of the privileged scope is listed as open items, due before Phase 3's pipeline design.
  - Revised in review before merge, then **amended after it**, from pinned sources:
    - the Privileged Architecture is pinned before Phase 2;
    - "read-only" and "write" follow Spike's rules until the Privileged Architecture is pinned, then
      the pinned text (so `rdinstret` never traps);
    - the counters: a read returns the count from before the reading instruction retires, and a
      write beats the writing instruction's own increment;
    - lockstep declares Spike's configuration and its expected divergences before it starts: the
      ID registers' values (Spike's `marchid` is 5), `misa`, and Spike's boot ROM at `0x1000`;
    - no measured window may include an undeclared trap of any kind;
    - the benchmark's decoder will need `M`, so it first runs on the core in Phase 3;
    - where branches resolve is recorded before pipeline design, because it sets Prediction A's
      cost. Its reasons are timing, area and hazards, never Prediction A.
- **`0010` (#19), Phase 0 closes when the benchmark runs on Spike.** Phase 2's core runs no program
  before that. Amended twice: the frozen configurations include one sized for RTL simulation in
  Phase 4, from simulated cycles per second on a proxy core of about the planned size.
- **Tagged Phase 1's gate,** after re-running `make alu` and `make mutate-alu` at `5d664db`.
- The rv32 README, `htif.h` and Makefile no longer say "the core will have no OS". The reference is
  unchanged: 138,137 instret, image `1baf3e07…`.

**Done on 2026-09-29 to 30**
- **`experiments/0002`, answered** (#25). On instruction count, neither Zbkb nor Zbc beats the
  stated table: B retires 292,293, C 150,155 and D 148,155, against 138,137. GCC 16.2.0's
  expansions carry dead instructions, 6 per byte with Zbkb and 2 with Zbc. Both hypotheses got the
  mechanism right, and both missed B's count.
- **The author's answers, 2026-09-30.**
  - **0001's status line.** The author accepted the write-up without changes, and the status line
    now says so.
  - **`0013`, the endpoint** (#26), with an amendment after review (#27). The endpoint
    sentence no longer requires a custom extension. Phase 4 chooses the mechanism: a ratified
    extension, a custom extension, or other hardware aimed at this workload, but never a
    general-purpose feature. A measured "not worth it" completes the project. The bar for
    "worth it" is stated before Phase 5 starts.
- **The RISC-V manuals are pinned** in `reference/README.md` (#28). Volumes I and II are at
  20250508, the newest ratified release. The author added seven PDFs, and all seven are
  byte-identical to their publishers' releases.
  - **A git identity for this repository,** in `.git/config`: `Mukhtartg`, the identity of the
    author's GitHub account and of every merge commit. `.git/config` is not in the repository, so
    a new clone needs it set again. Earlier local commits are authored `MacBook Pro`, a name that
    git derived from the hostname.
- **`0014`, the decoder's harness** (#29). It measured what printing costs first
  (`20260930T052623Z-spike-htif-cost`): one HTIF command costs about 5,000 instructions of
  spinning, whatever it carries.
  - `stimulus.bin` version 2 carries each connection's protocol, one byte per connection.
  - The stimulus is linked into the decoder's image. Each run prints three hashes: `image`,
    `decoder` and `stimulus`.
  - The window counts decoding and the stores that hand each record on, in 64 bits. Sorting,
    formatting and printing come after it.
  - Records leave through `SYS_write`, a buffer at a time. The last line repeats the number of
    records.

**Done on 2026-10-01**
- **`stimulus.bin` version 2** (#30), step 1 of the decoder's four. A table after the header
  gives each connection's protocol. `check.py` checks it against `intent.jsonl`, and three new
  tests hold the layout to `0014` byte for byte. Captured as `20261001T040355Z-stimulus-coverage`:
  26 tests pass, and the coverage stimulus is 14,272 bytes.
- **The root README's status block** no longer calls `experiments/0002` open.
- **`0004`, amended** (#31). The reference result fixes the expected output and
  the instruction count, not a speedup's time. A commodity part shares the source, the stimulus and
  the expected output lines, not the image.

**Done on 2026-10-02**
- **The decoder's harness, `bench/decoder`** (in review), step 2 of the decoder's four. It links the
  stimulus in last, checks it before the window, counts the window in 64 bits, and prints the
  records in canonical order through `SYS_write`. Any trap ends the run with `mcause` and `mepc`.
  Two test decoders hold it to text predicted or written out by hand, and `make mutate` breaks it
  16 ways. Captured as `20261002T143128Z-decoder-harness`: all checks pass, and all 16 faults are
  caught.

**Next, in order**
1. **The reference decoder:** Phase 0's critical path now.
   - **Settled by `0011`:** what it does after a broken frame. A broken frame costs only its own
     bytes, and a GT06 length fault cannot reach variant dispatch (Findings 7 and 8).
   - **Settled by `0012`:** what it reports and sends back (Finding 9). Shared quantities have exact
     units, for example 1/9,000,000 degree and metres per hour. It answers GT06 login and heartbeat,
     and JT808 `0x0102`, `0x0200` and `0x0704`, but only frames that pass. Records are ordered by
     connection. SPEC §3 carries the full field table.
   - **Settled by `0014`:** how the stimulus reaches it, what the window counts, and how its records
     leave Spike. Nothing is left to decide before its code.

   The work, in this order:
   1. ~~`stimulus.bin` version 2 in the generator~~: done on 2026-10-01, in review.
   2. ~~The harness, with a stub decoder~~: done on 2026-10-02, in review.
   3. The decoder itself, in `bench/decoder`, behind `decoder.h`. Its records go through
      `records.h`, and `make check` keeps the test decoders passing.
   4. The `0010` check against `intent.jsonl`, seen to fail on broken input.

   Before freezing, measure simulated cycles per second on a proxy of about the planned core's
   size, for example an open-source RV32 core under Icarus. Convert with the planned core's cycles
   per instruction, and size a small configuration from that (`0010`, amended twice).
2. **Before any Phase 2 trap work,** check `0009`'s rules against the Privileged Architecture,
   pinned at version 20250508 in `reference/`. The pinned text settles the rest of the Phase 2
   minimum by rule, starting with the counters: `minstret`, its upper halves, and `mcycle`.
   **Before Phase 2's gate,** decide two things, both tied to the memory-interface choice:
   `fence_i` needs Zifencei and an instruction fetch that sees earlier stores; `ma_data` needs
   misaligned loads and stores in hardware.
3. **Low priority:** sweep where `crc_itu_ref.c`'s first console command falls, to show or rule out
   the torn `tohost` store that `0014` found by reading the code.

**Waiting on the author**
- Nothing, as of 2026-09-30.

**Where things are**
- **Plan and rules:** `roadmap.md`, and `docs/decisions/0001`–`0014`.
- **The benchmark:** `bench/SPEC.md`, `bench/PROTOCOL-EVIDENCE.md`, `bench/stimulus/README.md`,
  whose `intent.jsonl` is the decoder's ground truth, not its expected output, and
  `bench/decoder/README.md`, the harness.
- **What happened and what is unresolved:** `docs/journal/`, one file a month. The latest entry is at
  the bottom of `2026-10.md`.
- **Pinned sources:** `reference/README.md`. It lists Traccar's decoders, the GT06 document,
  riscv-tests, Spike's source and the RISC-V manuals, each with its hash or commit.
- **How to write:** the author's guide, `~/epoynt/docs/platform/writing-style.md`, outside this repo.
  From 2026-09-30 it governs every document, commit message, PR body and reply.

**Commands**
- `make -C bench/rv32 check`, `make -C bench/stimulus`, `make -C bench/stimulus test`
- `make alu` and `make mutate-alu` (the Phase 1 gate)
- `make -C bench/rv32 htif-cost`: what each way of printing costs under Spike (about 60 s)
- `make -C bench/decoder check` and `make -C bench/decoder mutate`: the harness, held to its test
  decoders, then broken 16 ways (both together about 14 s)
- `scripts/capture.sh <label> <command…>`, run from a clean tree

**Gotchas**
- **Push a tag by name, never with `--tags`,** so that no local-only tag is published by accident.
- **Merge with a merge commit, never a squash.** Captures record the branch commit they ran at, such
  as `5333c7f` for 0002's. A squash would drop that commit from `main`'s history. For the same
  reason, never rebase or amend a branch after a capture has recorded one of its commits.
- **A check that has never failed proves nothing.** Break it on purpose once.
- **Before quoting a decision record, look for later records that narrow it.** Nothing links them.
  `0004`'s sentences on the denominator and on "the same program" stood after `experiments/0001`
  and `0008` had narrowed them, until an explanation quoted them on 2026-10-01.
- **A trap with no handler hangs Spike.** The trap goes wherever `mtvec` points, and Spike never
  exits. `bench/decoder`'s harness installs a handler. Nothing limits a run that loops without
  trapping, except `mutate.py`'s 180 s.
- **Never print inside a measured window under Spike.** Its host reads `tohost` once every 5,000
  instructions, so each HTIF command costs about 5,000 instructions of spinning (`0014`).
- **Homebrew:** install only with `HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1`,
  then re-check the reference image hash.
- **zsh** does not word-split `$vars`, and it expands a word that starts with `=`. It also stops a
  command whose glob matches nothing, so quote a pattern meant for another program:
  `grep --include='*.md'`.
- **Branches:** start every topic from a freshly fetched `origin/main`. The author merges within
  minutes.

**Memory:** eight notes load automatically in `~/hdl-lab`: how Claude seals a prediction, toolchain
safety, the PR workflow, the author's profile, the author's open items, the author's writing guide,
git identity, and this file's location.
