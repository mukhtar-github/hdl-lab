# 0013 — The endpoint names the mechanism that the measurements choose

- **Date:** 2026-09-30
- **Status:** Accepted
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
