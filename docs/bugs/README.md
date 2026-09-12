# bugs/ — preserved evidence of wrong behaviour

**The rule: never fix an interesting bug before preserving its evidence.**

```
working RTL → introduce/find bug → run → CAPTURE HERE → diagnose → fix → rerun
```

A VCD showing wrong behaviour is destroyed the moment you fix it. It is worth more than any
diagram you could draw later, because it is what the failure actually looked like rather than
what you remember it looking like.

This layer exists separately from `journal/` because the artifacts are binary and long-lived
while journal entries are text and chronological. The journal entry *points here*; this
directory holds the thing itself.

## What goes in

One directory per bug: `NNNN-short-slug/`

```
0001-adder-cout-dropped-carry/
├── NOTES.md          what you were looking at, and what was wrong about it
├── broken.vcd        the failing waveform — this is the point
├── waveform.png      screenshot with the divergence visible
└── broken.patch      the diff that produced it, if deliberate
```

`.gitignore` excludes `*.vcd` everywhere except here. That exception is deliberate: these are
the only waveforms in the project worth keeping.

## NOTES.md — four lines is enough

```markdown
# NNNN — <what broke>

- **Date:** YYYY-MM-DD   **Phase:** 0–7   **Deliberate:** yes | no
- **Symptom:** what the testbench reported.
- **Signal to watch:** the net and time where it first goes wrong. The
  reader should be able to open the VCD and see it without hunting.
- **Cause:** filled in after diagnosis. Empty is fine while unsolved —
  an unsolved bug with evidence beats a solved one without.
```

Do not write the tutorial version. Write where to look.

## Why this is load-bearing

The Phase 0 gate is *"find a bug you deliberately introduced by reading a waveform, without
adding print statements."* This directory is the evidence that gate was actually passed, rather
than remembered as passed.
