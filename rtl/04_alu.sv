`timescale 1ns/1ps

// ============================================================
// Project 2 — the ALU
//
// First module built out of an earlier module of your own:
// add and sub both come from the ripple_adder in 02_adder.sv.
// One adder, reused four ways (add, sub, slt, sltu), because
// that is what real hardware does — an adder is expensive and
// a comparison is a subtraction you throw the result away from.
//
// Phase 1 gate (roadmap): randomised testing against a golden
// model, including signed/unsigned comparison edge cases and
// shift-amount masking. Those two are named in the roadmap
// because they are where nearly every first ALU is wrong.
// ============================================================

package alu_pkg;

    localparam int ALU_OP_W = 4;

    // The encoding is not arbitrary: it is RV32I's {funct7[5], funct3}.
    //   op[2:0] = funct3      op[3] = funct7[5]
    // So ADD/SUB differ in exactly one bit, as do SRL/SRA — which is
    // precisely how the instruction set encodes them. Choosing this now
    // makes the Phase 2 decoder a wire, not a lookup table.
    localparam logic [ALU_OP_W-1:0]
        ALU_ADD  = 4'b0000,
        ALU_SLL  = 4'b0001,
        ALU_SLT  = 4'b0010,
        ALU_SLTU = 4'b0011,
        ALU_XOR  = 4'b0100,
        ALU_SRL  = 4'b0101,
        ALU_OR   = 4'b0110,
        ALU_AND  = 4'b0111,
        ALU_SUB  = 4'b1000,
        ALU_SRA  = 4'b1101;

endpackage


module alu
    import alu_pkg::*;
#(
    parameter int WIDTH = 32
) (
    input  logic [WIDTH-1:0]    a,
    input  logic [WIDTH-1:0]    b,
    input  logic [ALU_OP_W-1:0] op,
    output logic [WIDTH-1:0]    y,
    output logic                zero
);

    // Shift amounts are masked to log2(WIDTH) bits. For WIDTH=32 that is
    // b[4:0] — the RV32I rule. Using all of b is the classic bug: `sll x1,
    // x2, 32` must shift by 0, not annihilate the register.
    localparam int SHW = $clog2(WIDTH);

    // ---------------------------------------------------------
    // One shared adder
    //
    // a - b == a + ~b + 1. Invert b and force carry-in, and the
    // same ripple_adder subtracts. SLT and SLTU are subtractions
    // whose difference is discarded and whose flags are kept.
    //
    // NOTE: use_sub cannot be op[3], and the reason is the direction you
    // would not guess. SRA also has bit 3 set, but wiring it to op[3] does
    // NOT break SRA — SRA's result never comes from the adder, so inverting
    // b is merely wasted power. What op[3] breaks is SLT and SLTU: both have
    // bit 3 CLEAR yet both must subtract. (Verified by mutation: substituting
    // op[3] here fails 9728 cases, every one of them SLT or SLTU, none SRA.)
    // So enumerate the three ops that subtract.
    // ---------------------------------------------------------
    logic             use_sub;
    logic [WIDTH-1:0] b_eff;
    logic [WIDTH-1:0] sum;
    logic             carry_out;

    assign use_sub = (op == ALU_SUB) | (op == ALU_SLT) | (op == ALU_SLTU);
    assign b_eff   = use_sub ? ~b : b;

    ripple_adder #(.WIDTH(WIDTH)) u_add (
        .a    (a),
        .b    (b_eff),
        .cin  (use_sub),
        .sum  (sum),
        .cout (carry_out)
    );

    // ---------------------------------------------------------
    // Comparisons, both taken from the subtract above
    // ---------------------------------------------------------

    // Unsigned: for a + ~b + 1, carry_out == 1 means "no borrow", i.e.
    // a >= b. So the unsigned less-than IS the borrow, which is ~carry_out.
    logic sltu;
    assign sltu = ~carry_out;

    // Signed: the sign of the difference is the answer ONLY when the
    // subtraction did not overflow. Overflow on a - b happens exactly when
    // a and b have different signs and the result takes b's sign.
    // Then slt = sign(diff) XOR overflow.
    logic ovf, slt;
    assign ovf = (a[WIDTH-1] ^ b[WIDTH-1]) & (a[WIDTH-1] ^ sum[WIDTH-1]);
    assign slt = sum[WIDTH-1] ^ ovf;

    // ---------------------------------------------------------
    // Shifts
    // ---------------------------------------------------------
    logic [SHW-1:0] shamt;
    assign shamt = b[SHW-1:0];

    // ---------------------------------------------------------
    // Result mux
    // ---------------------------------------------------------
    always_comb begin
        case (op)
            ALU_ADD, ALU_SUB: y = sum;
            ALU_SLL         : y = a << shamt;
            ALU_SRL         : y = a >> shamt;
            ALU_SRA         : y = $signed(a) >>> shamt;   // >>> on a SIGNED operand, or it is just SRL
            ALU_SLT         : y = {{(WIDTH-1){1'b0}}, slt};
            ALU_SLTU        : y = {{(WIDTH-1){1'b0}}, sltu};
            ALU_XOR         : y = a ^ b;
            ALU_OR          : y = a | b;
            ALU_AND         : y = a & b;
            default         : y = '0;                     // unused encodings read as zero
        endcase
    end

    // Branch comparisons in Phase 2 use this: BEQ is SUB then test zero.
    assign zero = (y == '0);

endmodule
