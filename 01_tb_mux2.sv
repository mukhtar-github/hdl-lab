// ============================================================
// Testbench for mux2
//
// Note what this is NOT: it is not "run it and eyeball the output".
// It drives every possible input combination, computes the expected
// answer independently, and fails loudly on mismatch.
//
// That is the habit to build from day one.
// ============================================================
`timescale 1ns/1ps

module tb_mux2;

    logic a, b, sel;
    logic y_struct, y_behav;
    logic expected;
    int   errors = 0;

    mux2_structural u_struct (.a(a), .b(b), .sel(sel), .y(y_struct));
    mux2_behavioral u_behav  (.a(a), .b(b), .sel(sel), .y(y_behav));

    initial begin
        // Dump waveforms so you can open this in GTKWave
        $dumpfile("build/mux2.vcd");
        $dumpvars(0, tb_mux2);

        // 3 inputs -> 8 combinations. Exhaustive proof, not spot-checking.
        for (int i = 0; i < 8; i++) begin
            {sel, b, a} = i[2:0];
            #10;  // let the logic settle, and make the waveform readable

            // The "golden model": what SHOULD the answer be?
            expected = sel ? b : a;

            if (y_behav !== expected) begin
                $display("FAIL behavioral: a=%b b=%b sel=%b -> got %b, want %b",
                         a, b, sel, y_behav, expected);
                errors++;
            end
            if (y_struct !== y_behav) begin
                $display("FAIL structural != behavioral: a=%b b=%b sel=%b -> %b vs %b",
                         a, b, sel, y_struct, y_behav);
                errors++;
            end
        end

        if (errors == 0) $display("PASS  mux2: 8/8 combinations correct");
        else             $display("FAIL  mux2: %0d error(s)", errors);
        $finish;
    end

endmodule
