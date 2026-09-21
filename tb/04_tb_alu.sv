// ============================================================
// Testbench for alu
//
// The Phase 1 gate names two things specifically, because they
// are where nearly every first ALU is wrong:
//
//   1. signed/unsigned comparison edge cases
//   2. shift-amount masking
//
// So this bench attacks both deliberately rather than hoping a
// random sweep stumbles into them:
//
//   A. 32-bit DIRECTED — every pair drawn from a hand-picked
//      edge-value set, crossed with all 16 op encodings. The set
//      contains 0, 1, -1, INT_MIN, INT_MAX and the shift amounts
//      31/32/33/-32, so the classic traps are hit by construction.
//   B. 4-bit EXHAUSTIVE — all 16x16x16 = 4096 combinations. The
//      repo's rule: exhaustive beats clever whenever affordable.
//   C. 32-bit RANDOMISED — seeded, so a failure is reproducible.
//
// The golden model uses SystemVerilog's own operators, which is
// the point: it shares no logic with the structural DUT.
// ============================================================
`timescale 1ns/1ps

module tb_alu;

    import alu_pkg::*;

    // ---------------- DUTs ----------------
    logic [31:0] a32, b32, y32;
    logic [3:0]  op32;
    logic        z32;

    alu #(.WIDTH(32)) u_alu32 (.a(a32), .b(b32), .op(op32), .y(y32), .zero(z32));

    logic [3:0]  a4, b4, y4, op4;
    logic        z4;

    alu #(.WIDTH(4))  u_alu4  (.a(a4),  .b(b4),  .op(op4),  .y(y4),  .zero(z4));

    // ---------------- bookkeeping ----------------
    int errors  = 0;
    int shown   = 0;
    int cases   = 0;
    int err_op [0:15];
    int cnt_op [0:15];

    localparam int NE = 14;
    logic [31:0] ev [0:NE-1];

    int seed = 32'h00C0FFEE;   // fixed: a failing random case must reproduce

    function automatic string opname(logic [3:0] o);
        case (o)
            ALU_ADD : opname = "ADD";
            ALU_SUB : opname = "SUB";
            ALU_SLL : opname = "SLL";
            ALU_SRL : opname = "SRL";
            ALU_SRA : opname = "SRA";
            ALU_SLT : opname = "SLT";
            ALU_SLTU: opname = "SLTU";
            ALU_XOR : opname = "XOR";
            ALU_OR  : opname = "OR";
            ALU_AND : opname = "AND";
            default : opname = "----";
        endcase
    endfunction

    // ---------------------------------------------------------
    // Golden model. Independent of the DUT: native operators only.
    // W is passed in so one model serves both instances; values are
    // held in 32 bits and masked, with sign-extension from bit W-1
    // so the signed comparison means the right thing at 4 bits too.
    // ---------------------------------------------------------
    function automatic logic [31:0] golden(int W, logic [3:0] o,
                                          logic [31:0] ra, logic [31:0] rb);
        logic [31:0]        mask, ua, ub;
        logic signed [31:0] sa, sb;
        logic signed [31:0] sra_v;
        int unsigned        sh;
        begin
            mask = (W >= 32) ? 32'hFFFF_FFFF : ((32'h1 << W) - 32'h1);
            ua   = ra & mask;
            ub   = rb & mask;
            sa   = ua[W-1] ? (ua | ~mask) : ua;   // sign-extend out of W bits
            sb   = ub[W-1] ? (ub | ~mask) : ub;
            sh   = ub & (W - 1);                  // W is a power of two, so AND is the mask

            case (o)
                ALU_ADD : golden = (ua + ub)   & mask;
                ALU_SUB : golden = (ua - ub)   & mask;
                ALU_SLL : golden = (ua << sh)  & mask;
                ALU_SRL : golden = (ua >> sh)  & mask;
                // `>>>` is arithmetic only while its left operand is SIGNED, and
                // SystemVerilog propagates unsignedness down into an expression:
                // writing `(sa >>> sh) & mask` makes the whole thing unsigned, which
                // converts `sa` to unsigned and silently demotes `>>>` to `>>`. The
                // shift therefore has to land in a signed variable FIRST, and only
                // then get masked. This bench had that bug; the ALU did not.
                ALU_SRA : begin
                              sra_v  = sa >>> sh;
                              golden = sra_v & mask;
                          end
                ALU_SLT : golden = (sa <  sb) ? 32'd1 : 32'd0;
                ALU_SLTU: golden = (ua <  ub) ? 32'd1 : 32'd0;
                ALU_XOR : golden = (ua ^ ub)   & mask;
                ALU_OR  : golden = (ua | ub)   & mask;
                ALU_AND : golden = (ua & ub)   & mask;
                default : golden = 32'd0;        // unused encodings must read zero
            endcase
        end
    endfunction

    task automatic report(string tag, int W, logic [3:0] o,
                          logic [31:0] va, logic [31:0] vb,
                          logic [31:0] gy, logic [31:0] wy,
                          logic gz, logic wz);
        begin
            err_op[o]++;
            errors++;
            if (shown < 25) begin
                shown++;
                $display("FAIL W%0d %-6s %-10s a=%08h b=%08h op=%04b -> y=%08h want=%08h  zero=%b want=%b",
                         W, opname(o), tag, va, vb, o, gy, wy, gz, wz);
            end
        end
    endtask

    task automatic chk32(logic [3:0] o, logic [31:0] va, logic [31:0] vb, string tag);
        logic [31:0] want;
        begin
            op32 = o; a32 = va; b32 = vb;
            #1;
            want = golden(32, o, va, vb);
            cnt_op[o]++; cases++;
            if (y32 !== want || z32 !== (want == 32'd0))
                report(tag, 32, o, va, vb, y32, want, z32, (want == 32'd0));
        end
    endtask

    task automatic chk4(logic [3:0] o, logic [3:0] va, logic [3:0] vb);
        logic [31:0] want;
        begin
            op4 = o; a4 = va; b4 = vb;
            #1;
            want = golden(4, o, {28'h0, va}, {28'h0, vb});
            cnt_op[o]++; cases++;
            if (y4 !== want[3:0] || z4 !== (want[3:0] == 4'h0))
                report("exhaustive", 4, o, {28'h0, va}, {28'h0, vb},
                       {28'h0, y4}, want, z4, (want[3:0] == 4'h0));
        end
    endtask

    initial begin
        $dumpfile("build/alu.vcd");
        $dumpvars(0, tb_alu);

        for (int i = 0; i < 16; i++) begin
            err_op[i] = 0;
            cnt_op[i] = 0;
        end

        // Edge-value set. Every classic trap is a pair from this list:
        //   (0, -1)               -> slt 0, sltu 1   <- signedness
        //   (INT_MIN, INT_MAX)    -> slt 1, sltu 0   <- signedness
        //   (x, 32) and (x, -32)  -> shift by 0      <- masking
        //   (x, 33)               -> shift by 1      <- masking
        ev[0]  = 32'h0000_0000;   // zero
        ev[1]  = 32'h0000_0001;   // one
        ev[2]  = 32'hFFFF_FFFF;   // -1 / UINT_MAX
        ev[3]  = 32'h8000_0000;   // INT_MIN
        ev[4]  = 32'h7FFF_FFFF;   // INT_MAX
        ev[5]  = 32'h0000_001F;   // 31 — largest legal shift
        ev[6]  = 32'h0000_0020;   // 32 — must mask to 0
        ev[7]  = 32'h0000_0021;   // 33 — must mask to 1
        ev[8]  = 32'hFFFF_FFE0;   // -32 — must mask to 0
        ev[9]  = 32'h5555_5555;
        ev[10] = 32'hAAAA_AAAA;
        ev[11] = 32'h0000_00FF;
        ev[12] = 32'h8000_0001;   // INT_MIN + 1
        ev[13] = 32'h0000_0010;   // 16

        // --- A. 32-bit directed: every edge pair x every encoding ---
        for (int i = 0; i < NE; i++)
            for (int j = 0; j < NE; j++)
                for (int o = 0; o < 16; o++)
                    chk32(o[3:0], ev[i], ev[j], "directed");

        // --- B. 4-bit exhaustive: all 16 x 16 x 16 ---
        for (int ia = 0; ia < 16; ia++)
            for (int ib = 0; ib < 16; ib++)
                for (int o = 0; o < 16; o++)
                    chk4(o[3:0], ia[3:0], ib[3:0]);

        // Stop dumping here. The directed and exhaustive cases are the
        // ones worth opening in a viewer; 200k random cases would make a
        // VCD too large to load and no easier to read.
        $dumpoff;

        // --- C. 32-bit randomised, seeded ---
        for (int n = 0; n < 200000; n++)
            chk32($random(seed), $random(seed), $random(seed), "random");

        // ---------------- verdict ----------------
        $display("");
        if (errors == 0) begin
            $display("PASS  alu: %0d/%0d cases correct", cases, cases);
            $display("        directed 32-bit : %0d   (edge pairs x 16 encodings)", NE*NE*16);
            $display("        exhaustive 4-bit: %0d   (16 x 16 x 16)", 16*16*16);
            $display("        randomised      : %0d   (seed %08h)", 200000, 32'h00C0FFEE);
        end else begin
            $display("FAIL  alu: %0d error(s) in %0d cases", errors, cases);
            $display("      per-op breakdown (errors/cases):");
            for (int i = 0; i < 16; i++)
                if (cnt_op[i] > 0)
                    $display("        %-4s %04b  %0d/%0d%s", opname(i[3:0]), i[3:0],
                             err_op[i], cnt_op[i], (err_op[i] > 0) ? "   <--" : "");
        end
        $finish;
    end

endmodule
