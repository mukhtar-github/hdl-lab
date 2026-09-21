#!/usr/bin/env bash
# Prove the ALU testbench has teeth, by breaking the ALU on purpose.
#
#   scripts/mutate-alu.sh
#
# A passing testbench is evidence of nothing until you have seen it fail.
# This injects each classic ALU bug one at a time, reruns the bench, and
# checks it goes red. A mutation that survives is a hole in the bench, and
# the script exits non-zero so it cannot be ignored.
#
# The same argument as `make lint-trap`: a check that cannot go red tells
# you nothing. This is that argument applied to the golden-model bench.
#
# rtl/04_alu.sv is restored on every exit path, including Ctrl-C.

set -uo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ALU=rtl/04_alu.sv
GOOD="$(mktemp -t alu.good)"
cp "$ALU" "$GOOD"
trap 'cp "$GOOD" "$ALU"; rm -f "$GOOD"' EXIT INT TERM

survivors=0

# mutate <label> <python-literal-old> <python-literal-new>
# Python, not sed: these expressions are full of | and / and ( characters
# that every sed delimiter collides with. Learned the hard way.
mutate () {
    local label="$1" old="$2" new="$3"
    cp "$GOOD" "$ALU"
    python3 - "$ALU" "$old" "$new" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
old, new = sys.argv[2], sys.argv[3]
if old not in s:
    sys.exit(f"MUTATION DID NOT APPLY — source moved:\n  {old}")
p.write_text(s.replace(old, new, 1))
PY
    [ $? -ne 0 ] && { echo "  $label: SKIPPED (see above)"; survivors=$((survivors+1)); return; }

    printf '  %-46s ' "$label"
    local out; out="$(make alu 2>&1)"
    if grep -q '^PASS' <<<"$out"; then
        echo "SURVIVED  <-- the bench is blind to this"
        survivors=$((survivors+1))
    else
        echo "killed: $(grep '^FAIL  alu' <<<"$out" | sed 's/FAIL  alu: //')"
        grep '<--' <<<"$out" | sed 's/^/        /'
    fi
}

echo "=== ALU bench mutation test ==="
echo

mutate "shift amount not masked" \
    'assign shamt = b[SHW-1:0];' \
    'assign shamt = b[SHW-1:0] | {SHW{|b[WIDTH-1:SHW]}};'

mutate "SLT is really an unsigned compare" \
    'assign slt = sum[WIDTH-1] ^ ovf;' \
    'assign slt = sltu;'

mutate "SLT uses sign of difference, ignores overflow" \
    'assign slt = sum[WIDTH-1] ^ ovf;' \
    'assign slt = sum[WIDTH-1];'

mutate "SLTU forgets the borrow is inverted carry" \
    'assign sltu = ~carry_out;' \
    'assign sltu = carry_out;'

mutate "SRA is really a logical shift" \
    'y = $signed(a) >>> shamt;' \
    'y = a >> shamt;'

mutate "SUB omits the +1 (a + ~b only)" \
    '.cin  (use_sub),' \
    ".cin  (1'b0),"

mutate "use_sub taken from op[3]" \
    'assign use_sub = (op == ALU_SUB) | (op == ALU_SLT) | (op == ALU_SLTU);' \
    'assign use_sub = op[3];'

echo
if [ "$survivors" -eq 0 ]; then
    echo "  all mutations killed — the bench has teeth"
else
    echo "  $survivors mutation(s) SURVIVED — the bench needs work"
    exit 1
fi
