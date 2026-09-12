// ============================================================
// Testbench for ripple_adder
//
// 4 bits + 4 bits + carry = 512 cases. Small enough to test
// exhaustively — so do it. Exhaustive beats clever every time
// it is affordable.
// ============================================================
`timescale 1ns/1ps

module tb_adder;

    localparam int WIDTH = 4;

    logic [WIDTH-1:0] a, b, sum;
    logic             cin, cout;
    logic [WIDTH:0]   got;
    int               exp;
    int               errors = 0;

    ripple_adder #(.WIDTH(WIDTH)) u_add (
        .a(a), .b(b), .cin(cin), .sum(sum), .cout(cout)
    );

    initial begin
        $dumpfile("build/adder.vcd");
        $dumpvars(0, tb_adder);

        for (int ia = 0; ia < (1 << WIDTH); ia++) begin
            for (int ib = 0; ib < (1 << WIDTH); ib++) begin
                for (int ic = 0; ic < 2; ic++) begin
                    a   = ia[WIDTH-1:0];
                    b   = ib[WIDTH-1:0];
                    cin = ic[0];
                    #1;

                    // Golden model: plain integer arithmetic.
                    // Your hardware must match ordinary maths.
                    exp = ia + ib + ic;
                    got = {cout, sum};

                    if (got !== exp[WIDTH:0]) begin
                        $display("FAIL: %0d + %0d + %0d -> got %0d, want %0d",
                                 ia, ib, ic, got, exp);
                        errors++;
                    end
                end
            end
        end

        if (errors == 0) $display("PASS  ripple_adder: 512/512 cases correct");
        else             $display("FAIL  ripple_adder: %0d error(s)", errors);
        $finish;
    end

endmodule
