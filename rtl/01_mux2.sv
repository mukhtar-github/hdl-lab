`timescale 1ns/1ps

// ============================================================
// Exercise 1 — mux2
// A 2-to-1 multiplexer: the single most-used building block
// in a CPU datapath. Every "choose between two values" decision
// inside a processor is one of these.
//
// Written twice on purpose:
//   mux2_structural — wired up from primitive gates
//   mux2_behavioral — described by what it DOES
// Both synthesise to the same hardware. Prove it in the waveform.
// ============================================================

// ---- Structural: you are literally drawing the circuit ----
module mux2_structural (
    input  logic a,     // input 0
    input  logic b,     // input 1
    input  logic sel,   // 0 -> a, 1 -> b
    output wire y
);
    wire nsel, a_and, b_and;

    not  u_not  (nsel,  sel);
    and  u_a    (a_and, a, nsel);
    and  u_b    (b_and, b, sel);
    or   u_out  (y,     a_and, b_and);
endmodule


// ---- Behavioral: you describe intent, the tool infers the gates ----
module mux2_behavioral (
    input  logic a,
    input  logic b,
    input  logic sel,
    output logic y
);
    // always_comb = "this block describes combinational logic".
    // Inside combinational blocks use blocking assignment: =
    always_comb begin
        if (sel) y = b;
        else     y = a;
    end
endmodule
