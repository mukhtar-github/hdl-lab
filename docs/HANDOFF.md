# Handoff

Where the next working session starts: the state, what is next, commands, gotchas. Each handoff
overwrites this file, and git keeps every earlier one: `git log -p -- docs/HANDOFF.md`.

It is a summary, derived from the journal, the decision records and git, so it can be wrong or
stale. A new session checks it against the live state before acting on it.

---

*Written by Claude on 2026-09-28 (transcript `9a8face2`), after #19 merged. Updated the same day
for both rounds of amendments to `0009` and `0010`, on 2026-09-29 for `0011` and `0012`, and on
2026-09-30 for `experiments/0002`'s result.*

## hdl-lab handoff (2026-09-28)

**State:** `main` was at `34e94c6` when this was written, and at `92b3c59` when it was last updated,
with PRs #8–#24 all merged and `experiments/0002`'s result in review. **Phase 0 is open again**,
for the benchmark (`decisions/0010`). Phase 1's gate is passed. The only pushed tag is
`v0.1-alu-golden-model-passing`. The tag `sealed/0002-claude-prediction` is still local only. It has
been opened, and its text is in `experiments/0002`, so the tag is redundant now.

**If you are a second assistant reading this:** it replaces any other handoff. Where anything
disagrees with `roadmap.md` or a decision record, those win. **Freshness is by commit, not by
length.** `roadmap.md` was last changed in `d0e6eab`; `git log -1 --format=%h -- roadmap.md` prints
the current one. A copy from before it is out of date. (This note once gave a line count, and it was
stale the same day.)

### Phase gates, and where each stands

| Phase | Gate (`roadmap.md`) | Stands |
|---|---|---|
| 0 | 1. Find a deliberately introduced bug by reading a waveform. 2. The benchmark runs on Spike, is checked against the generator's intent, is captured at every declared configuration, and is frozen and tagged (`0010`) | 1 passed 2026-09-21 (#1). **2 open.** It closes with the tag `v0.0-benchmark-frozen` |
| 1 | The ALU passes randomised testing against a golden model | Passed 2026-09-21 (#2), tagged `v0.1-alu-golden-model-passing`. The register file and memories are still to build, with no gate of their own |
| 2 | `rv32ui-p-*` passes through riscv-tests' standard environment, unmodified: its `riscv_test.h` and `link.ld`, so memory sits at `0x80000000`. That needs the trap minimum (`0009`, amended) | Not started. **The core runs no program until Phase 0 closes** (`0010`). The Privileged Architecture is pinned before any trap work |
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
- **`experiments/0002`, answered** (in review). On instruction count, neither Zbkb nor Zbc beats the
  stated table: B retires 292,293, C 150,155 and D 148,155, against 138,137. GCC 16.2.0's
  expansions carry dead instructions, 6 per byte with Zbkb and 2 with Zbc. Both hypotheses got the
  mechanism right, and both missed B's count.

**Next, in order**
1. **The reference decoder:** Phase 0's critical path now.
   - **Settled by `0011`:** what it does after a broken frame. A broken frame costs only its own
     bytes, and a GT06 length fault cannot reach variant dispatch (Findings 7 and 8).
   - **Settled by `0012`:** what it reports and sends back (Finding 9). Shared quantities have exact
     units, for example 1/9,000,000 degree and metres per hour. It answers GT06 login and heartbeat,
     and JT808 `0x0102`, `0x0200` and `0x0704`, but only frames that pass. Records are ordered by
     connection. SPEC §3 carries the full field table.
   - **Still to decide before writing any of it:** how `stimulus.bin` reaches it under Spike. That
     includes how it learns each connection's protocol (`0011` assumes it knows), and where records
     are serialised relative to the measured window (`0012`: serialising is not decoding).

   Before freezing, measure simulated cycles per second on a proxy of about the planned core's
   size, for example an open-source RV32 core under Icarus. Convert with the planned core's cycles
   per instruction, and size a small configuration from that (`0010`, amended twice).
2. **Before any Phase 2 trap work,** pin the Privileged Architecture in `reference/` (`0009`,
   amended). The pin settles the rest of the Phase 2 minimum by rule, starting with the counters:
   `minstret`, its upper halves, and `mcycle`. **Before Phase 2's gate,** decide two things, both tied to the memory-interface choice:
   `fence_i` needs Zifencei and an instruction fetch that sees earlier stores; `ma_data` needs
   misaligned loads and stores in hardware.

**Waiting on the author**
- **0001's status line** still says "for the author to edit". A one-line note is recommended; it is
  the author's call.
- **The roadmap's endpoint sentence** (`roadmap.md:34`) says "designed a custom extension". Rule 3
  has the project implement a ratified extension when one covers the workload, and an outcome
  decided that way would not satisfy the sentence. Rewording it takes a decision record. The
  author decides whether now or at Phase 4.
- **Git identity.** git cannot derive an author from the hostname `Mac`. Commit with
  `-c user.name="MacBook Pro" -c user.email="macbookpro@MacBooks-MacBook-Pro.local"`, or the author
  sets one.

**Where things are**
- **Plan and rules:** `roadmap.md`, and `docs/decisions/0001`–`0012`.
- **The benchmark:** `bench/SPEC.md`, `bench/PROTOCOL-EVIDENCE.md`, and `bench/stimulus/README.md`,
  whose `intent.jsonl` is the decoder's ground truth, not its expected output.
- **What happened and what is unresolved:** `docs/journal/2026-09.md`, latest entries at the bottom.

**Commands**
- `make -C bench/rv32 check`, `make -C bench/stimulus`, `make -C bench/stimulus test`
- `make alu` and `make mutate-alu` (the Phase 1 gate)
- `scripts/capture.sh <label> <command…>`, run from a clean tree

**Gotchas**
- **Push a tag by name, never with `--tags`,** so that no local-only tag is published by accident.
- **Merge with a merge commit, never a squash.** Captures record the branch commit they ran at, such
  as `5333c7f` for 0002's. A squash would drop that commit from `main`'s history. For the same
  reason, never rebase or amend a branch after a capture has recorded one of its commits.
- **A check that has never failed proves nothing.** Break it on purpose once.
- **Homebrew:** install only with `HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1`,
  then re-check the reference image hash.
- **zsh** does not word-split `$vars`, and it expands a word that starts with `=`.
- **Branches:** start every topic from a freshly fetched `origin/main`. The author merges within
  minutes.

**Memory:** seven notes load automatically in `~/hdl-lab`: how Claude seals a prediction, toolchain
safety, the PR workflow, the author's profile, the author's open items, git identity, and this
file's location.
