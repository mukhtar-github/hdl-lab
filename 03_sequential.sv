`timescale 1ns/1ps

// ============================================================
// Exercise 3 — sequential logic
//
// Everything so far had no memory: outputs were a pure function
// of inputs. Now we add a clock, and the design gains state.
// This is the concept that makes a CPU possible.
// ============================================================

// The atom of all sequential design: a D flip-flop.
// On each rising clock edge, whatever was on d becomes q.
module dff (
    input  logic clk,
    input  logic rst_n,   // active-LOW asynchronous reset
    input  logic d,
    output logic q
);
    // always_ff = "this is a clocked register".
    // Inside clocked blocks use NON-blocking assignment: <=
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) q <= 1'b0;
        else        q <= d;
    end
endmodule


// A register: N flip-flops sharing a clock, with a load enable.
module reg_en #(
    parameter int WIDTH = 8
) (
    input  logic             clk,
    input  logic             rst_n,
    input  logic             en,
    input  logic [WIDTH-1:0] d,
    output logic [WIDTH-1:0] q
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)   q <= '0;
        else if (en)  q <= d;
        // no else: q holds its value. That is intentional and correct
        // in a clocked block (it infers an enable, not a latch).
    end
endmodule


// A counter. This becomes your program counter later.
module counter #(
    parameter int WIDTH = 8
) (
    input  logic             clk,
    input  logic             rst_n,
    input  logic             en,
    output logic [WIDTH-1:0] count
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)  count <= '0;
        else if (en) count <= count + 1'b1;
    end
endmodule


// ------------------------------------------------------------
// THE CLASSIC TRAP — read this block carefully.
//
// Both shift registers below look almost identical.
// They produce completely different hardware.
// ------------------------------------------------------------

// CORRECT: non-blocking <= means all three registers sample
// simultaneously on the edge. This is a real 3-stage shift register.
module shift_nonblocking (
    input  logic clk,
    input  logic rst_n,
    input  logic din,
    output logic dout
);
    logic s0, s1, s2;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) {s0, s1, s2} <= '0;
        else begin
            s0 <= din;
            s1 <= s0;
            s2 <= s1;
        end
    end
    assign dout = s2;
endmodule

// WRONG (as a shift register): blocking = executes in order,
// so din races straight through to the output in one cycle.
// The three flip-flops collapse into one.
module shift_blocking (
    input  logic clk,
    input  logic rst_n,
    input  logic din,
    output logic dout
);
    logic s0, s1, s2;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s0 = 0; s1 = 0; s2 = 0; end
        else begin
            s0 = din;
            s1 = s0;
            s2 = s1;
        end
    end
    assign dout = s2;
endmodule
