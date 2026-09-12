`timescale 1ns/1ps

// ============================================================
// Exercise 2 — full adder -> ripple-carry adder
//
// This is the first time you build a big thing out of small
// identical things. That pattern never stops: adder from full
// adders, ALU from adders, CPU from ALU + register file + control.
// ============================================================

module full_adder (
    input  logic a,
    input  logic b,
    input  logic cin,
    output logic sum,
    output logic cout
);
    assign sum  = a ^ b ^ cin;
    assign cout = (a & b) | (cin & (a ^ b));
endmodule


// Parameterised: WIDTH is a compile-time constant, not a runtime value.
// Change it to 32 later and this same file becomes your CPU's adder.
module ripple_adder #(
    parameter int WIDTH = 4
) (
    input  logic [WIDTH-1:0] a,
    input  logic [WIDTH-1:0] b,
    input  logic             cin,
    output logic [WIDTH-1:0] sum,
    output logic             cout
);
    logic [WIDTH:0] carry;
    assign carry[0] = cin;

    // generate: "stamp out WIDTH copies of this module at elaboration time"
    genvar i;
    generate
        for (i = 0; i < WIDTH; i++) begin : g_bit
            full_adder u_fa (
                .a    (a[i]),
                .b    (b[i]),
                .cin  (carry[i]),
                .sum  (sum[i]),
                .cout (carry[i+1])
            );
        end
    endgenerate

    assign cout = carry[WIDTH];
endmodule
