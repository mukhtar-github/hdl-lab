# 0005 — Surfer as the waveform viewer; GTKWave is not viable on this machine

- **Date:** 2026-09-12
- **Status:** Accepted
- **Phase:** 0

## Context

`0002` settled the simulator and the linter but said nothing about the waveform viewer, because
at the time it looked like a solved problem: every tutorial says `brew install gtkwave`.

It is not solved, and it was blocking the Phase 0 gate outright. That gate is *"find a bug you
deliberately introduced by reading a waveform, without adding print statements."* Waveform
reading is not a convenience here — it is the skill the gate exists to certify, and it cannot
be substituted with `$display`.

The failure was silent and therefore cost more than it should have. `gtkwave` was on `PATH`,
`brew list` showed it installed, and every invocation exited with status **137** printing
nothing. 137 is `128 + 9` — SIGKILL. The process was not crashing; the OS was killing it.

Diagnosis:

| | |
|---|---|
| Binary | `gtkwave-bin`, Mach-O **x86_64 only**, dated **October 2020** |
| Host | arm64, macOS 26.6.2 (Darwin 25.6.0) |
| Rosetta 2 | **not installed** → x86_64 binaries are SIGKILLed on exec |
| Signature | `code object is not signed at all`, plus a `com.apple.quarantine` attribute |
| Shipped as | a Homebrew **cask** (`.app` bundle), with `/opt/homebrew/bin/gtkwave` a Perl launcher script symlinked into it |

So the packaged tool is a five-year-old unsigned x86 binary behind a Perl shim, on a machine
with no x86 emulation layer. It never ran once.

## Options considered

1. **Install Rosetta 2 and unquarantine GTKWave** — rejected. It would work: `softwareupdate
   --install-rosetta`, clear the `com.apple.quarantine` xattr, ad-hoc codesign the bundle. But
   it buys a 2020 unsigned binary running under emulation, as a permanent dependency of the one
   tool the Phase 0 gate rests on. It also normalises "strip the quarantine flag until it runs,"
   which is a bad reflex to build in week two of a project that will later pull down toolchains,
   PDKs and vendor flows.

2. **Read the VCD text directly** — rejected as a primary answer. VCD is plain text and reading
   it by hand is a genuinely useful thing to be able to do once. But the gate is about seeing
   divergence across time, which is exactly the thing a text dump is bad at. Keep it as a
   debugging trick, not as the viewer.

3. **Surfer** — accepted. Native arm64, actively developed, in Homebrew as a formula (not a
   cask), reads VCD/FST/GHW. Installed clean at 0.7.0 and parsed all three Project 1 waveforms.

## Decision

**Surfer is the waveform viewer.** `make wave-mux | wave-adder | wave-seq` launch it.

GTKWave stays installed but unused; no effort goes into reviving it. If a future tutorial or
tool assumes GTKWave specifically, revisit then — option 1 is still available and the diagnosis
above is written down so it need not be redone.

## Consequences

- **The Phase 0 gate becomes reachable.** It was not, for the entire life of the project to date.
- **Verified headlessly, not assumed.** `surfer server --file build/<x>.vcd` loads a waveform
  without opening a window, which makes "does the viewer actually parse our output" a scriptable
  check rather than a thing someone eyeballs. Used to confirm all three Project 1 VCDs parse.
- Surfer's keybindings and UI are not GTKWave's. Tutorials will not match. Accepted.
- **A tool being on `PATH` and installed by the package manager is not evidence that it runs.**
  This is the second instance in one day of a tool reporting success while doing nothing — see
  the lint target, which exited 0 for its entire existence without checking any RTL. Both were
  found only by looking at exit codes and output rather than at whether the command "worked".
  Worth generalising: in Phase 2, `riscv-tests` passing must mean tests *ran*, and the count
  must be checked, not the exit status.

## Predictions

Surfer's FST support will matter sooner than expected. VCD files from a pipelined core running
millions of instructions get large fast, and FST is the compressed format Icarus can emit with
`$dumpfile` plus a format switch. Recorded now so the moment VCD size becomes painful is
recognised as predicted rather than as a surprise.
