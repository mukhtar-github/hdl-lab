# Handoff

Where the next working session starts: the state, what is next, commands, gotchas. Each handoff
overwrites this file, and git keeps every earlier one: `git log -p -- docs/HANDOFF.md`.

It is a summary, derived from the journal, the decision records and git, so it can be wrong or
stale. A new session checks it against the live state before acting on it.

---

*Written by Claude at the end of the second session of 2026-09-27 (transcript `9a8face2`), after
#16 merged.*

## hdl-lab handoff (2026-09-27, evening)

**State:** Phase 0. `main` was at `d6f73a0` when this was written. PRs #8–#16 are all merged. The
local tag `sealed/0002-claude-prediction` exists and has not been pushed, as it should be.

**Done this session**
- **#15, `bench/PROTOCOL-EVIDENCE.md` Findings 4 to 7.** The numbers come from
  `bench/evidence/checksums.py`, captured as `20260927T062216Z-protocol-checksums`.
  - 4: neither Traccar decoder verifies a received checksum. The GT06 vendor document says to discard
    on CRC error. So in this benchmark the CRC's per-byte cost is the cost of *conforming*, not of
    what the de facto decoder does. Phase 4 must say which one it measured.
  - 5: one of the vendor's three device-sent examples verifies as printed. The location example is
    fixed by its own table (`0xCC` → `0xCF`). The heartbeat's length and CRC are for a frame
    without Alarm/Language.
  - 6: 27 of 185 GT06 and 11 of 114 JT808 Traccar test inputs fail their checksum. This is **not a
    rate**.
  - 7: the GT06 variant is chosen from the length field.
  - `reference/` holds 13 Traccar files now, all from the same pinned commit, and the refetch recipe
    is verified. The vendor PDF has its own recipe.
- **#16, `bench/stimulus`, the stimulus generator.** Captured as
  `20260927T065053Z-stimulus-coverage`: 23 tests pass, and `check.py` passes.
  - It writes `stimulus.bin`, `intent.jsonl` and `manifest.json`. **`intent.jsonl` is the ground
    truth, not the expected output**, which is the reference decoder's to produce.
  - Nothing has a default. `params/coverage.json` is for tests only, and nothing may be quoted from
    it. Rules R1–R17 are in its README.
  - `SPEC.md` was amended with 5 unset parameters. The one that matters most is field-value
    distributions: they set the JT808 escape density, 28 pairs in 8,327 frame bytes on the coverage
    run.

**The reference, unchanged:** the stated table, 138,137 instret, image `1baf3e07…`. Per byte:
bitwise 77, GCC's substituted table 51, stated table 10.

**Next, in order**
1. **0002.** Unchanged. The author writes the hypothesis for B, C and D, and it is committed
   verbatim. Then the seal is opened and verified, the sealed text is committed verbatim, and only
   then are B, C and D captured. **No Zbkb/Zbc builds before the first step.**
2. **Loose end.** Unchanged. 0001's status line still says "for the author to edit", but it was
   merged unedited. Claude recommends a one-line note in the 0007 style. It is the author's call.
3. **The reference decoder.** Decide these before writing any of it:
   - What it does after a fault, and where it looks for the next frame. SPEC does not fix this, and
     it decides what gets printed for every frame after a fault. Traccar's GT06 framer scans for
     `0D 0A`. Its JT808 framer scans for `(`, `7E` or `E7`.
   - The fields and units of its output records. SPEC §3 fixes their shape, not their contents.
   - How `stimulus.bin` reaches the program under Spike: linked or loaded as binary, never compiled
     in.
   - Whether a GT06 length fault can reach variant dispatch (Finding 7).
4. **Git identity.** git cannot derive an author from this Mac's hostname, now `Mac`. Commit with
   `-c user.name="MacBook Pro" -c user.email="macbookpro@MacBooks-MacBook-Pro.local"` until the
   author sets an identity with `git config --global`. Which one is the author's call.
5. **QEMU is not planned.** Revisit it for gdb once the decoder exists. Prefer Sail as a second
   opinion on the ISA.

**Commands**
- `make -C bench/rv32 check [VARS]` and `make -C bench/rv32 anatomy`
- `make -C bench/stimulus` (generate and check), `make -C bench/stimulus test`, and
  `make -C bench/stimulus PARAMS=<file> SEED=<n>`
- `scripts/capture.sh <label> <command…>`, run from a clean tree
- `python3 bench/evidence/checksums.py`
- `spike -d …` or `spike -l --log-commits --log=f …`

**Gotchas**
- zsh does not word-split `$vars`, and it expands a word that starts with `=`, so `echo ======`
  fails.
- Paste only the `spike -d` line itself. Debugger commands pasted with it go to zsh. Spike's debugger
  misreads piped input, so use `--debug-cmd=<file>`.
- Install with Homebrew only with `HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1`,
  then re-check the reference image hash.
- Start every topic from a freshly fetched `origin/main`. The author merges within minutes.
- Traccar's test files in `reference/` are real-device hex (rule 2a). Count them. Never commit or
  print their bytes.
- A check that has never failed proves nothing. Break it on purpose once.

**Memory:** six notes load automatically in `~/hdl-lab`: the 0002 protocol, toolchain safety, the PR
workflow, the author's profile, git identity, and this file's location.
