# ============================================================
# hdl-lab — Project 1
#
#   make            run every testbench
#   make mux        run one testbench
#   make wave-mux   open its waveform in GTKWave
#   make clean      remove build artefacts
#   make lint       static-check the RTL with Verilator (optional)
# ============================================================

IVERILOG := iverilog
VVP      := vvp
GTKWAVE  := gtkwave
BUILD    := build

# -g2012 selects the SystemVerilog-2012 language level.
# Without it, always_ff / always_comb / logic will not compile.
IVFLAGS  := -g2012 -Wall

.PHONY: all mux adder seq clean lint

all: mux adder seq
	@echo ""
	@echo "=========================================="
	@echo " All Project 1 testbenches complete."
	@echo " Waveforms are in $(BUILD)/ — open one with:"
	@echo "   make wave-mux | wave-adder | wave-seq"
	@echo "=========================================="

$(BUILD):
	@mkdir -p $(BUILD)

mux: | $(BUILD)
	@echo "--- mux2 ---"
	@$(IVERILOG) $(IVFLAGS) -o $(BUILD)/mux2.vvp 01_mux2.sv 01_tb_mux2.sv
	@$(VVP) $(BUILD)/mux2.vvp

adder: | $(BUILD)
	@echo "--- ripple_adder ---"
	@$(IVERILOG) $(IVFLAGS) -o $(BUILD)/adder.vvp 02_adder.sv 02_tb_adder.sv
	@$(VVP) $(BUILD)/adder.vvp

seq: | $(BUILD)
	@echo "--- sequential ---"
	@$(IVERILOG) $(IVFLAGS) -o $(BUILD)/seq.vvp 03_sequential.sv 03_tb_sequential.sv
	@$(VVP) $(BUILD)/seq.vvp

wave-mux:
	$(GTKWAVE) $(BUILD)/mux2.vcd &

wave-adder:
	$(GTKWAVE) $(BUILD)/adder.vcd &

wave-seq:
	$(GTKWAVE) $(BUILD)/sequential.vcd &

# Verilator's linter catches synthesis problems Icarus will happily ignore
# (inferred latches, width mismatches, unclocked signals). Run it often.
lint:
	verilator --lint-only -Wall --top-module counter 03_sequential.sv || true
	verilator --lint-only -Wall --top-module ripple_adder 02_adder.sv || true

clean:
	rm -rf $(BUILD)
