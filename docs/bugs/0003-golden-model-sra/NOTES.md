# 0003 — the ALU's golden model did a logical shift where SRA needs an arithmetic one

- **Date:** 2026-09-21   **Phase:** 1   **Deliberate:** no (first real bug of the project)

- **Symptom:** the first `make alu` run reported **6080 failures out of 207232**,
  every single one under op `1101` (SRA) and none under any other encoding:

      SRA  1101  6080/13026   <--

  First failure: `a=ffffffe0 b=00000001 op=1101 -> y=fffffff0 want=7ffffff0`.

- **Where it was:** `tb/04_tb_alu.sv`, in the **golden model** — not in the RTL.
  This is the bug's whole lesson. The failure was arbitrated before anything was
  edited: `0xFFFFFFE0` is −32; −32 arithmetic-shifted right by 1 is −16 =
  `0xFFFFFFF0`, which is what the ALU produced. `0x7FFFFFF0` is the *logical*
  shift. The reference was wrong and the design under test was right.

- **Cause:** the model computed `golden = (sa >>> sh) & mask;` where `sa` is
  declared `logic signed [31:0]`. `>>>` is an arithmetic shift **only while its
  left operand is signed**, and SystemVerilog resolves signedness for the whole
  expression before evaluating it: if any operand is unsigned the result is
  unsigned, and that unsignedness propagates *down into the operands*. `mask` is
  unsigned, so `sa` was converted to unsigned and `>>>` silently became `>>`.
  Nothing warns. The operator is still spelled `>>>`.

- **Solution:** land the shift in a signed variable first, and mask only after:

      logic signed [31:0] sra_v;
      sra_v  = sa >>> sh;
      golden = sra_v & mask;

  The RTL needed no change. `y = $signed(a) >>> shamt;` is a direct assignment
  with no unsigned operand in the expression, so nothing demotes it.

- **Why only 6080 of 13026 SRA cases failed:** the two shifts agree whenever the
  operand's sign bit is 0, or the shift amount is 0. Roughly half the random
  operands are negative, so roughly half the SRA cases diverge. A partial failure
  rate under exactly one opcode is the signature that localised this in one read
  of the per-op breakdown — which is why the bench prints that table.

## The lesson worth keeping

**The reference model is code, and it fails in ways the design cannot.**

The roadmap warns that signed comparison and shift masking are where first ALUs
go wrong. Both were correct here on the first try, because the warning was in
hand while writing them. The bug landed in the one file nobody thinks to doubt —
and a golden model is *more* exposed to this particular trap than RTL is, because
a model is written in expressions and RTL in assignments, and SystemVerilog's
signedness rule bites expressions.

So: when the DUT and the model disagree, **arbitrate with arithmetic before
editing either one.** Deciding by hand that −32 ≫ 1 = −16 took one line of Python
and pointed at the file that was actually wrong. Assuming the DUT is guilty
because it is the new code would have corrupted a correct ALU to satisfy a broken
reference — and it would have passed.

## Related

- `0002` taught: find the earliest signal that contradicts its own inputs.
- `0003` adds the step before it: establish which side is *supposed* to be right.
