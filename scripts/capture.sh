#!/usr/bin/env bash
# Capture a measurement with enough provenance to reproduce it.
#
#   scripts/capture.sh <label> <command...>
#
# Example:
#   scripts/capture.sh adder-exhaustive make adder
#
# Writes docs/results/<timestamp>-<label>/ containing manifest.md,
# stdout.txt, stderr.txt and a diff of any uncommitted changes.
# Runnable from anywhere in the tree — the output path is resolved
# from the repository root, not from your current directory.
#
# Never record a measurement by hand. You will omit the one field that
# turns out to matter.

set -uo pipefail

if [ $# -lt 2 ]; then
    echo "usage: $0 <label> <command...>" >&2
    exit 1
fi

LABEL="$1"; shift
TS="$(date -u +%Y%m%dT%H%M%SZ)"

# Resolve from the repo root so the script works from any directory.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || dirname "$(dirname "$0")")"
DIR="${ROOT}/docs/results/${TS}-${LABEL}"
mkdir -p "$DIR"

# --- provenance ---------------------------------------------------------
COMMIT="$(git rev-parse HEAD 2>/dev/null || echo 'not-a-git-repo')"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '-')"
DIRTY="clean"
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    DIRTY="DIRTY — uncommitted changes present, see uncommitted.diff"
    git diff HEAD > "$DIR/uncommitted.diff" 2>/dev/null
fi

tool_version() {
    if command -v "$1" >/dev/null 2>&1; then
        # single line, pipe-escaped so it can't break the markdown table
        "$@" 2>&1 | head -1 | tr -d '\n' | sed 's/|/\\|/g'
    else
        printf 'not installed'
    fi
}

# --- run ----------------------------------------------------------------
START="$(date -u +%s)"
"$@" > "$DIR/stdout.txt" 2> "$DIR/stderr.txt"
STATUS=$?
END="$(date -u +%s)"

# --- manifest -----------------------------------------------------------
cat > "$DIR/manifest.md" << EOF
# ${LABEL}

- **Captured (UTC):** ${TS}
- **Command:** \`$*\`
- **Exit status:** ${STATUS}
- **Wall time:** $((END - START))s

## Source state

- **Commit:** ${COMMIT}
- **Branch:** ${BRANCH}
- **Working tree:** ${DIRTY}

## Tool versions

| Tool | Version |
|---|---|
| iverilog | $(tool_version iverilog -V) |
| verilator | $(tool_version verilator --version) |
| yosys | $(tool_version yosys -V) |
| spike | $(tool_version spike --help) |
| riscv gcc | $(tool_version riscv32-unknown-elf-gcc --version) |
| host | $(uname -sr) |

## Configuration

<!-- Fill in by hand: parameters, WIDTH, pipeline depth, extensions enabled,
     benchmark input set, packet mix, target rate. Anything a reader would
     need to reproduce this exactly and cannot read off the commit. -->

## Result

<!-- The number(s). One line. Interpretation goes in the journal, not here. -->

## Notes

<!-- Anything unusual about this run. Thermal state, a rebuild mid-run,
     a flaky test you re-ran. Especially: reasons to distrust it. -->
EOF

echo "captured → ${DIR#"$ROOT"/}   (exit ${STATUS})"
echo "fill in Configuration and Result in manifest.md while it is fresh"
exit $STATUS
