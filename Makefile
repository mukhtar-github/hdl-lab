# ============================================================
# hdl-lab — RV32IM + telematics decode specialisation
#
#   make              run every testbench
#   make mux          run one testbench (mux | adder | seq | alu)
#   make wave-mux     open its waveform in Surfer (wave-mux|wave-adder|wave-seq|wave-alu)
#   make lint         static-check the RTL with Verilator — must stay green
#   make lint-trap    demonstrate the linter catching the deliberate bug
#   make mutate-alu   break the ALU 7 ways, prove the bench catches each
#   make lint-file FILE=x.sv TOP=x    lint anything (Exercise 3 uses this)
#   make clean        remove build artefacts
# ============================================================

IVERILOG := iverilog
VVP      := vvp
# Surfer, not GTKWave: the GTKWave cask ships a 2020 x86_64-only binary
# that is SIGKILLed on this arm64 Mac. See docs/decisions/0005.
WAVE     := surfer
VERILATOR:= verilator
RTL      := rtl
TB       := tb
BUILD    := build

# -g2012 selects the SystemVerilog-2012 language level.
# Without it, always_ff / always_comb / logic will not compile.
IVFLAGS  := -g2012 -Wall

# DECLFILENAME is waived deliberately: this kit groups related modules
# per file (dff + reg_en + counter live together on purpose). It is a
# naming-convention warning, not a synthesis problem — and left enabled
# it is FATAL, which silently aborts the lint before any real check runs.
VLFLAGS  := --lint-only -Wall -Wno-DECLFILENAME

# Every module that must lint clean. Adding RTL? Add its top here.
LINT_CLEAN := \
	$(RTL)/01_mux2.sv:mux2_structural \
	$(RTL)/01_mux2.sv:mux2_behavioral \
	$(RTL)/02_adder.sv:full_adder \
	$(RTL)/02_adder.sv:ripple_adder \
	$(RTL)/03_sequential.sv:dff \
	$(RTL)/03_sequential.sv:reg_en \
	$(RTL)/03_sequential.sv:counter \
	$(RTL)/03_sequential.sv:shift_nonblocking \
	$(RTL)/04_alu.sv,$(RTL)/02_adder.sv:alu

.PHONY: all mux adder seq alu clean lint lint-trap lint-file mutate-alu

all: mux adder seq alu
	@echo ""
	@echo "=========================================="
	@echo " All testbenches complete."
	@echo " Waveforms are in $(BUILD)/ — open one with:"
	@echo "   make wave-mux | wave-adder | wave-seq"
	@echo "=========================================="

$(BUILD):
	@mkdir -p $(BUILD)

mux: | $(BUILD)
	@echo "--- mux2 ---"
	@$(IVERILOG) $(IVFLAGS) -o $(BUILD)/mux2.vvp $(RTL)/01_mux2.sv $(TB)/01_tb_mux2.sv
	@$(VVP) $(BUILD)/mux2.vvp

adder: | $(BUILD)
	@echo "--- ripple_adder ---"
	@$(IVERILOG) $(IVFLAGS) -o $(BUILD)/adder.vvp $(RTL)/02_adder.sv $(TB)/02_tb_adder.sv
	@$(VVP) $(BUILD)/adder.vvp

seq: | $(BUILD)
	@echo "--- sequential ---"
	@$(IVERILOG) $(IVFLAGS) -o $(BUILD)/seq.vvp $(RTL)/03_sequential.sv $(TB)/03_tb_sequential.sv
	@$(VVP) $(BUILD)/seq.vvp

# The ALU instantiates ripple_adder from 02_adder.sv — both files compile in.
alu: | $(BUILD)
	@echo "--- alu ---"
	@$(IVERILOG) $(IVFLAGS) -o $(BUILD)/alu.vvp $(RTL)/04_alu.sv $(RTL)/02_adder.sv $(TB)/04_tb_alu.sv
	@$(VVP) $(BUILD)/alu.vvp

wave-mux:
	$(WAVE) $(BUILD)/mux2.vcd &

wave-adder:
	$(WAVE) $(BUILD)/adder.vcd &

wave-seq:
	$(WAVE) $(BUILD)/sequential.vcd &

wave-alu:
	$(WAVE) $(BUILD)/alu.vcd &

# ------------------------------------------------------------
# Lint. Verilator catches what Icarus accepts happily but synthesis
# will not — inferred latches, width mismatches, multiply-driven
# signals, blocking assignment in a clocked block.
#
# This target FAILS on any warning. That is the point: a lint target
# that cannot go red tells you nothing. Keep it green.
# ------------------------------------------------------------
lint:
	@fail=0; \
	for spec in $(LINT_CLEAN); do \
		f=$$(echo "$${spec%%:*}" | tr ',' ' '); m=$${spec##*:}; \
		printf '  %-20s ' "$$m"; \
		if $(VERILATOR) $(VLFLAGS) --top-module $$m $$f 2>&1 | grep -qE '%(Warning|Error)'; then \
			echo "FAIL"; \
			$(VERILATOR) $(VLFLAGS) --top-module $$m $$f 2>&1 | sed 's/^/      /'; \
			fail=1; \
		else echo "clean"; fi; \
	done; \
	if [ $$fail -ne 0 ]; then echo ""; echo "  lint FAILED"; exit 1; \
	else echo ""; echo "  lint clean — $(words $(LINT_CLEAN)) modules"; fi

# shift_blocking is WRONG ON PURPOSE (03_sequential.sv). This target
# shows the linter finding it. Expect BLKSEQ warnings; that is success.
lint-trap:
	@echo "--- deliberate trap: shift_blocking (expect BLKSEQ warnings) ---"
	@$(VERILATOR) $(VLFLAGS) --top-module shift_blocking $(RTL)/03_sequential.sv 2>&1 \
		| grep -E 'BLKSEQ|Blocking assignment' | sed 's/^/  /' || true
	@echo ""
	@echo "  Verilator found the blocking-assignment-in-always_ff bug that"
	@echo "  Icarus compiled and ran without a murmur. That is why lint exists."

# Lint an arbitrary file — used by README Exercise 3 (the latch trap).
#   make lint-file FILE=scratch/latch.sv TOP=latch_test
lint-file:
	@test -n "$(FILE)" || { echo "usage: make lint-file FILE=x.sv TOP=modname"; exit 1; }
	@$(VERILATOR) $(VLFLAGS) --top-module $(TOP) $(FILE) || true

# A passing bench is evidence of nothing until you have watched it fail.
mutate-alu:
	@scripts/mutate-alu.sh

clean:
	rm -rf $(BUILD)
