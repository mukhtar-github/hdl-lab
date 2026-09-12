// ============================================================
// Testbench for sequential logic
//
// New things here:
//   1. generating a clock
//   2. applying and releasing reset
//   3. checking behaviour ACROSS TIME rather than instantaneously
//   4. watching the blocking-vs-non-blocking bug happen for real
// ============================================================
`timescale 1ns/1ps

module tb_sequential;

    logic clk = 0;
    logic rst_n;
    logic en;
    int   errors = 0;

    // 100 MHz clock: 10 ns period, toggle every 5 ns, forever.
    always #5 clk = ~clk;

    // --- counter under test ---
    logic [7:0] count;
    counter #(.WIDTH(8)) u_cnt (
        .clk(clk), .rst_n(rst_n), .en(en), .count(count)
    );

    // --- shift registers under test ---
    logic din, dout_nb, dout_b;
    shift_nonblocking u_nb (.clk(clk), .rst_n(rst_n), .din(din), .dout(dout_nb));
    shift_blocking    u_b  (.clk(clk), .rst_n(rst_n), .din(din), .dout(dout_b));

    initial begin
        $dumpfile("build/sequential.vcd");
        $dumpvars(0, tb_sequential);

        // Reset sequence: assert, hold, release away from a clock edge.
        rst_n = 0; en = 0; din = 0;
        repeat (2) @(posedge clk);
        rst_n = 1;

        // --- Check 1: reset actually cleared the counter ---
        @(negedge clk);
        if (count !== 8'd0) begin
            $display("FAIL: counter not zero after reset (got %0d)", count);
            errors++;
        end

        // --- Check 2: with en low, the counter must hold ---
        repeat (3) @(posedge clk);
        @(negedge clk);
        if (count !== 8'd0) begin
            $display("FAIL: counter moved while disabled (got %0d)", count);
            errors++;
        end

        // --- Check 3: with en high, it increments once per cycle ---
        en = 1;
        for (int i = 1; i <= 10; i++) begin
            @(posedge clk);
            @(negedge clk);            // sample mid-cycle, away from the edge
            if (count !== i[7:0]) begin
                $display("FAIL: expected count=%0d, got %0d", i, count);
                errors++;
            end
        end
        en = 0;

        // --- Check 4: watch the two shift registers diverge ---
        // Send a single 1-cycle pulse into both.
        @(negedge clk); din = 1;
        @(negedge clk); din = 0;

        $display("");
        $display("  Shift register comparison (pulse sent at cycle 0):");
        for (int c = 0; c < 5; c++) begin
            $display("    cycle +%0d   non-blocking=%b   blocking=%b",
                     c, dout_nb, dout_b);
            @(negedge clk);
        end
        $display("  The non-blocking version delays the pulse by 3 cycles.");
        $display("  The blocking version passes it through in 1 — the three");
        $display("  flip-flops collapsed. Same-looking code, different chip.");
        $display("");

        if (errors == 0) $display("PASS  sequential: all counter checks correct");
        else             $display("FAIL  sequential: %0d error(s)", errors);
        $finish;
    end

    // Safety net: never let a testbench hang forever.
    initial begin
        #10000;
        $display("FAIL  timeout");
        $finish;
    end

endmodule
