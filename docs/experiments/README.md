# experiments/ — questions asked of the hardware

An experiment is **a question with a hypothesis written before the run**. It may produce no
reportable number at all, and a clean "no" is a successful experiment.

## How this differs from `results/`

They are easy to confuse and the distinction matters:

| | `results/` | `experiments/` |
|---|---|---|
| Holds | a number you will **report** | a question you **asked** |
| Written | mechanically, by `scripts/capture.sh` | by hand, hypothesis first |
| Success | the measurement is reproducible | the question is answered, either way |
| Typical outcome | "CPI on the hot loop is 2.4" | "no, wider loads do not help — here is why" |

An experiment usually *produces* a result; the result directory holds the provenance, this one
holds the reasoning. Link them: an experiment cites the `results/<timestamp>-<label>/` it
generated.

## The rule that makes this worth keeping

**Write the hypothesis and the discriminator before you run anything.** An experiment whose
hypothesis is recorded afterwards always turns out to have been correct all along — which is
exactly the failure mode the roadmap's dated predictions exist to prevent, applied at a smaller
scale.

If you cannot state in advance what result would change your mind, you are not running an
experiment. You are collecting support.

## Layout

One file per experiment: `NNNN-short-slug.md`, using `TEMPLATE.md`. Immutable once the outcome
is written — a wrong hypothesis, left standing, is the most valuable thing in this directory.
