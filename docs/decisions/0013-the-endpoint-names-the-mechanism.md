# 0013 — The endpoint names the mechanism that the measurements choose

- **Date:** 2026-09-30
- **Status:** Accepted, **amended twice on 2026-09-30**; see the amendments at the end.
- **Phase:** all. It changes the roadmap's statement of what finishes the project.

## Context

The line numbers in this record are at `d0e6eab`, the last commit before this change.

The roadmap states the project's endpoint in one sentence (`roadmap.md:34-36`):

> **I profiled a real workload, designed a custom extension to accelerate its hot path,
> integrated it into a pipelined RV32IM core I built, and measured what it cost in area and
> clock frequency to get the speedup I got.**

The subtitle says the same (`roadmap.md:3`): "a general-purpose core with a domain-specific
extension, quantified".

Four other parts of the roadmap allow an outcome with no custom extension:

- **The question** (`roadmap.md:16-20`) asks whether the ratified extensions are enough. It calls
  *"the standard already covers it"* "a real result", and adds: "It is not a fallback."
- **Rule 3 of the standard/custom boundary** (`roadmap.md:384`) says: "When a ratified extension
  already covers your workload, implement that instead."
- **The recorded predictions** (`roadmap.md:129-131`) name a ratified extension for each candidate
  bottleneck. They end: "A genuinely possible Phase 5 finding is that custom space is never needed
  at all."
- **Phase 4** (`roadmap.md:263-267`) decides "the mechanism". It names "a custom instruction, a
  wider load path, a small lookup table, or an accelerator block".

If a ratified extension covers the workload, rule 3 makes the project implement it. The endpoint
sentence is then false, although the project followed its own rules. So the statement of done
contradicts the rules that decide it.

A second assistant found this in a review of the roadmap. Claude checked it against the text on
2026-09-29. On 2026-09-30 the author decided to reword the endpoint now, not at Phase 4.

`experiments/0002` points the same way. It measured instruction counts on Spike on 2026-09-29. On
this workload's CRC, neither Zbkb nor Zbc beats the stated table, which runs on RV32IM with no
extension. That is one kernel, and a count of instructions, not of cycles on a core.

## Options considered

1. **Keep the sentence, and read "custom extension" loosely.** This costs nothing now. It lost
   because the sentence is the project's definition of done. Under that definition, only a custom
   extension finishes the project. That is a reason to prefer one, and rule 3 says not to.
2. **Reword it at Phase 4, when the mechanism is known.** The new words could then name the actual
   result. It lost because the contradiction is in the text now. Until Phase 4, every reader of the
   roadmap reads the endpoint as a promise of a custom extension.
3. **"Chose or designed an extension"**, the second assistant's wording. It admits rule 3's case.
   It lost because it is still too narrow: Phase 4 names mechanisms that are not extensions, such
   as a wider load path.
4. **Name the choice, and let Phase 4 make it.** This is the decision.

## Decision

The endpoint sentence at `roadmap.md:34` becomes:

> **I profiled a real workload, used the measurements to choose what would accelerate its hot
> path, integrated it into a pipelined RV32IM core I built, and measured what it cost in area and
> clock frequency to get the speedup I got.**

Only the words "designed a custom extension to accelerate" change. The rest is the author's
wording, as it was.

A new paragraph after the sentence says what the choice can be:

> Phase 4 decides the mechanism. It can be a ratified extension, a custom extension, or another
> kind of hardware, such as a wider load path. Rule 3 of the standard/custom boundary decides
> between the first two, and any of the three completes the project (`decisions/0013`).

The subtitle at `roadmap.md:3` becomes "a general-purpose core with the specialisation its
workload justifies, quantified".

The question at `roadmap.md:16-17` does not change. It asks whether a custom extension is
justified, and the answer is still open.

## Consequences

- **A ratified extension is a full result.** If Phase 4 chooses one, Phase 5 implements it to its
  specification. Phase 5 reports the same three numbers: speedup, area and Fmax.
- **The rules for a custom extension still apply when the choice is one.** Rules 1, 2, 4 and 5 of
  the standard/custom boundary do not change.
- **Phase 5's text does not change.** It names two ways to integrate new hardware: instructions in
  the core, and a memory-mapped accelerator. A ratified extension uses the first way, with the
  encodings from its specification instead of the custom opcode space.
- **What would reopen this:** a change to rule 3, or to the roadmap's question.

# Amendment 1 — 2026-09-30

A second assistant reviewed this record after it merged, and Claude checked each point against the
roadmap. The line numbers in this amendment are at `c923785`, where this record merged. The endpoint
sentence stays as decided. The paragraph after it had three faults, and two paragraphs replace it.

1. **It had no place for a measured "no".** The sentence requires integrating something. Under it,
   only integrating some hardware completes the project. That is a reason to integrate something,
   rather than to find that nothing is worth its area. This record had fixed the same fault for
   custom extensions. The roadmap already allows a "no": the "Versus commodity" number exists to
   answer the build-versus-buy question (`roadmap.md:418`). So what completes the project is now
   separate from the verdict:
   - Phase 5 integrates the best candidate that Phase 4 finds, and measures it.
   - The verdict on whether it was worth its area is separate. A measured "not worth it" completes
     the project.
   - Before Phase 5 starts, the author states what speedup, for what area and Fmax, would make the
     mechanism worth it. So nobody can set the bar after the numbers are known.
   - Software changes belong to the baseline, as `0008` requires. They are not the mechanism.
2. **"Another kind of hardware" had no limit.** A branch predictor or a cache would have qualified.
   The endpoint was rewritten to prevent exactly that: a project that "can always add another
   instruction, another pipeline stage, another cache level" (`roadmap.md:29-30`). **On 2026-09-30
   the author decided that a general-purpose feature cannot complete the project.** A branch
   predictor, a cache, deeper forwarding or another pipeline stage stays part of the core's design.
   It is chosen for timing, area and hazards, as `0009` §3 chooses the stage where branches resolve.
3. **"Its hot path" assumed that there is one.** Prediction B says the winner "depends on the
   protocol mix" (`roadmap.md:118`), and Prediction C expects a phase diagram (`roadmap.md:140`).
   So Phase 4 can choose a set of mechanisms. The project is complete when Phase 5 has measured
   that set, for the configurations frozen under `0010`. Work beyond it is new work, with a record
   of its own.

The two paragraphs that replace the old one (`roadmap.md:42-44`):

> Phase 4 decides the mechanism, or a set of mechanisms, for the configurations frozen in Phase 0.
> It can be a ratified extension, a custom extension, or other hardware aimed at this workload, such
> as a wider load path. A general-purpose feature does not count: a branch predictor, a cache,
> deeper forwarding or another pipeline stage is part of the core's design. Software changes do not
> count either, because they belong to the baseline. Rule 3 of the standard/custom boundary decides
> between the two kinds of extension.
>
> Before Phase 5 starts, state what speedup, for what area and Fmax, would make the mechanism worth
> it. Phase 5 then integrates the best candidate and measures it. The verdict compares those numbers
> with the stated bar and with the commodity part. A measured "not worth it" completes the project
> as fully as a "worth it" (`decisions/0013`).

**A consequence for area.** A ratified extension is implemented whole. So rule 3 prefers the
smallest ratified extension that holds what the workload needs. For example, the Zbc loop in
`0002` uses only `clmul` and `clmulh`, and Zbkc holds those two without Zbc's `clmulr`. The area
number covers the whole extension as implemented. The used subset can be reported beside it,
labelled. The facts about Zbkc and about whole extensions come from the ratified specifications,
which are not pinned in `reference/`.

**Not adopted:** the review's claim that a measured "no" is "the likely case". The only
measurement so far is `0002`: one kernel, counted in instructions on Spike.

# Amendment 2 — 2026-09-30

This checks Amendment 1's facts about extensions against the ISA manual, version 20250508, which
is now pinned in `reference/README.md`. The section numbers are that version's. Rule 3's
preference in Amendment 1 does not change.

- **Zbc holds three instructions:** `clmul`, `clmulh` and `clmulr` (Volume I, §29.4.3). **Zbkc
  holds two:** `clmul` and `clmulh` (§29.4.6). So Zbkc holds every instruction of the Zbc loop in
  `0002`.
- **"A ratified extension is implemented whole" is not in the manual in those words.** Instead, the
  manual defines a smaller set of instructions as an extension of its own. Zmmul "implements the
  multiplication subset of the M extension" (§12.3), and Zbkc is carry-less multiply without
  `clmulr`. So a core can name Zbkc, but not an unnamed part of Zbc.
- **`misa` has no bit for Zbc or Zbkc.** Its B bit means Zba, Zbb and Zbs together, and its K bit
  is reserved (Volume II, §3.1.1).
