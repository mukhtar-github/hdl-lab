# Project record

**The principle: capture what disappears; derive what doesn't.**

Four things have a short shelf life and cannot be reconstructed later, and each has a layer:

```
confusion   →   rationale   →   measurement conditions   →   bug evidence
journal/        decisions/      results/ + experiments/      bugs/
```

Everything else — tutorials, polished explanations, articles, thesis material — is *derived*
from this material months afterwards, when you know how the story ends. Nothing here is written
for an audience.

**Budget: under 10% of build time.** If it costs more, it gets abandoned, and abandoned
documentation is worse than none because you will trust gaps that aren't there.

---

## Layer 1 — `journal/`

One file per month. Append-only. **Never edit a past entry.**

One `## Session — YYYY-MM-DD` heading per working session, so the monthly file stays light while
individual sessions stay searchable.

Five minutes at the end of a session. What you tried, what happened, what confused you.

The confusion is the point. The moment you don't understand why something behaves the way it
does is the most valuable thing in this project, and it evaporates within a day of resolving
it. It is also exactly where your future reader will be stuck, which makes it the best tutorial
material you will ever have. Write it *while you are still confused*, badly, in fragments.

Bad entries beat no entries. A line saying "spent 2h, adder still wrong, no idea why" is worth
more than a polished paragraph you never wrote.

## Layer 2 — `decisions/`

One numbered file per significant decision: `0001-short-slug.md`. Use `TEMPLATE.md`.

Immutable. If you change your mind, write a new record that supersedes the old one and leave
the original intact. The superseded record is more interesting than the replacement, because
it holds the reasoning you later found wrong.

The test for "significant": would you be annoyed in six months if you couldn't remember why?
Roughly 15–25 of these across the whole project — not one per commit.

This layer becomes the design-rationale section of anything you eventually publish.

| | |
|---|---|
| `0001-workload-commitment.md` | Telematics frame decoding at line rate |
| `0002-toolchain.md` | Icarus simulates, Verilator lints |
| `0003-conformance-strategy.md` | External suites, not self-written tests |
| `0004-benchmark-first.md` | The benchmark exists before the processor |
| `0005-waveform-viewer.md` | Surfer, not GTKWave — and why |
| `0006-reading-discipline.md` | Specs and implementations, not domain material |
| `0007-variant-detection-strategy.md` | Stateless is the reference; cached is the instrument |
| `0008-source-states-the-algorithm.md` | The reference runs the algorithm and the work its source states |

## Layer 3 — `results/`

Every number you will ever report, with enough context to reproduce it.

```bash
scripts/capture.sh <label> <command...>
scripts/capture.sh adder-exhaustive make adder
```

It snapshots the commit hash, tool versions, the exact command, the raw output and a diff of any
uncommitted changes into `docs/results/<timestamp>-<label>/`. Runnable from anywhere in the tree.

Never record a measurement by hand — you will omit the one field that turns out to matter. Then
fill in **Configuration** and **Result** in the manifest while it is fresh. Interpretation goes
in the journal, not the manifest.

This is what separates "about 3× faster" from a claim that survives someone checking.

## Layer 4 — `experiments/`

A question asked of the hardware, with **the hypothesis written before the run**. One file per
experiment, `NNNN-short-slug.md`, using its `TEMPLATE.md`.

`results/` holds a number you will report; `experiments/` holds the question you asked and what
would have changed your mind. An experiment usually produces a result and cites it. A clean
"no" is a successful experiment.

If you cannot state in advance what observation would falsify your hypothesis, you are not
running an experiment — you are collecting support. See `experiments/README.md`.

## Layer 5 — `bugs/`

Preserved evidence of wrong behaviour: the VCD, a screenshot, and four lines saying where to
look. One directory per bug, `NNNN-short-slug/`.

**Never fix an interesting bug before preserving its evidence.**

```
working RTL → introduce/find bug → run → CAPTURE → diagnose → fix → rerun
```

`.gitignore` excludes `*.vcd` everywhere except here — these are the only waveforms in the
project worth keeping. The journal entry points here; this directory holds the artifact. See
`bugs/README.md`.

---

## The two habits that carry most of the weight

**Write commit messages that answer *why*.** The subject line says what changed; the body says
why you did it that way and what you rejected. Git history then becomes a searchable, timestamped
lab notebook for free. This is the highest-return documentation habit available to you.

Not this:

```
fix mux
```

This:

```
fix structural mux primitive outputs for Icarus 13

Icarus 13 rejects primitive outputs connected to logic variables in
this structural implementation. Changed primitive-driven signals to
wire while leaving the behavioral twin unchanged, so the two remain
directly comparable in the waveform.
```

**Never fix an interesting bug before preserving its evidence.** Layer 5 above is where it
goes. This habit is what makes the Phase 0 gate passable at all: finding a deliberately
introduced bug from waveform evidence, with no print statements. Without the artifact, "I
passed that gate" is a memory rather than a record.

---

## What not to write yet

**No tutorials during Phases 0–2.** Journal aggressively; teach only after the concepts have
survived actual implementation and external validation. A tutorial written before `riscv-tests`
passes is a tutorial about what you assumed, not what is true.

**The repository does not become a publication before the experiment exists.** Right now we are
collecting evidence. Later:

```
journal → tutorials → technical article → research paper / thesis material
```

That order preserves the distinction between what actually happened and the clean story told
afterwards.

---

## Where this lives

Same repository as the RTL. The commit that changes the design and the entry explaining why land
together, which is the whole point.

If you later open-source the core and don't want the journal public, extract the RTL into a
clean repository at that point. Splitting later is easy; reconstructing provenance you never
captured is not.

**Tag phase gates:** `git tag v0.2-riscv-tests-passing`. Reproducible snapshots of "it worked
here."

---

## Open questions

Keep this list short and dated. Questions get answered or explicitly deferred — never left to
rot silently.

| Raised | Question | Status |
|---|---|---|
| 2026-09-12 | GTKWave installs but will not run on this Mac | **Closed same day.** x86_64-only 2020 binary, no Rosetta, arm64 host → SIGKILL. Replaced by Surfer; see `decisions/0005` |
| 2026-09-01 | Hours per week actually available | Open — changes the calendar, not the sequence |
| 2026-09-01 | Which FPGA board | Deferred to Phase 6. Do not buy anything yet |
| 2026-09-01 | Resync rate in the trace (discriminator for predictions A/B) | Deferred. Input to stimulus generation, not on the critical path |
| 2026-09-01 | RISC-V Individual Community Membership still open? | Open — one email to info@riscv.org, low priority |
