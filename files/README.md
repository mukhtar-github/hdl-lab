# Project record

Three layers. Each captures something that cannot be reconstructed later. Nothing here is
written for an audience — tutorials, articles and papers are *derived* from this material
months afterwards, when you know how the story ends.

**Budget: under 10% of build time.** If it costs more, it gets abandoned, and abandoned
documentation is worse than none because you will trust gaps that aren't there.

---

## Layer 1 — `journal/`

One file per month. Append-only. **Never edit a past entry.**

Five minutes at the end of a session. What you tried, what happened, what confused you.

The confusion is the point. The moment you don't understand why something behaves the way it
does is the most valuable thing in this project, and it evaporates within a day of resolving
it. It is also exactly where your future reader will be stuck, which makes it the best tutorial
material you will ever have. Write it *while you are still confused*, badly, in fragments.

Bad entries beat no entries. A line saying "spent 2h, adder still wrong, no idea why" is worth
more than a polished paragraph you never wrote.

## Layer 2 — `decisions/`

One numbered file per significant decision: `0001-short-slug.md`.

Immutable. If you change your mind, write a new record that supersedes the old one and leave
the original intact. The superseded record is more interesting than the replacement, because
it holds the reasoning you later found wrong.

The test for "significant": would you be annoyed in six months if you couldn't remember why?
Roughly 15–25 of these across the whole project — not one per commit.

This layer becomes the design-rationale section of anything you eventually publish.

## Layer 3 — `results/`

Every number you will ever report, with enough context to reproduce it.

Use `capture.sh`. It snapshots the commit hash, tool versions, the exact command, and the raw
output into a timestamped directory. Never record a measurement by hand — you will omit the one
field that turns out to matter.

This is what separates "about 3× faster" from a claim that survives someone checking.

---

## Two cheap habits that carry most of the weight

**Write commit messages that answer *why*.** The subject line says what changed; the body says
why you did it that way and what you rejected. Git history then becomes a searchable, timestamped
lab notebook for free. This is the highest-return documentation habit available to you.

**Screenshot waveforms showing bugs.** Save to `journal/img/`. A VCD showing wrong behaviour is
destroyed the moment you fix it, and it is worth more than any diagram you could draw later.

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
| 2026-09-01 | Hours per week actually available | Open — changes the calendar, not the sequence |
| 2026-09-01 | Which FPGA board | Deferred to Phase 6. Do not buy anything yet |
| 2026-09-01 | Resync rate in the trace (discriminator for predictions A/B) | Deferred. Input to stimulus generation, not on the critical path |
| 2026-09-01 | RISC-V Individual Community Membership still open? | Open — one email to info@riscv.org, low priority |
