# ============================================================
# bench/decoder — the reference decoder's harness (decisions/0014)
#
#   make            build against the coverage stimulus
#   make run        build, then run under Spike
#   make check      both test decoders against the coverage stimulus,
#                   each held to expect.py; then one decoder image
#                   for two stimuli
#   make mutate     break the harness on purpose, 16 ways; something
#                   must catch each one. Run make check first.
#   make clean
#
#   make run STIM=<dir>       another stimulus: a directory that
#                             bench/stimulus wrote
#   make run DECODER=<name>   stub (the default) or format_test. The
#                             reference decoder is the next step.
# ============================================================

CC      := riscv64-elf-gcc
OBJCOPY := riscv64-elf-objcopy
SPIKE   := spike
PYTHON  := python3
SHA256  := shasum -a 256

# The same ISA, ABI, tuning and algorithm rule as bench/rv32 (decisions/0008).
ARCH      := rv32im
ABI       := ilp32
TUNE      := rocket
OPT       := -O2
ALGOFLAGS := -fno-optimize-crc

# Where memory ends. The connections' state and the records sit between the stimulus and here.
# Spike gives 2,048 MiB from 0x80000000 by default (spike_main/spike.cc:383); this uses 256 MiB.
MEM_TOP := 0x90000000

DECODER := stub
STIM    := ../stimulus/build/coverage-1
RV32    := ../rv32

ARCHFLAGS := -march=$(ARCH) -mabi=$(ABI) -mtune=$(TUNE) -mcmodel=medany
CFLAGS    := $(ARCHFLAGS) $(OPT) $(ALGOFLAGS) -DMEM_TOP=$(MEM_TOP) -I$(RV32) \
             -ffreestanding -fno-builtin -Wall -Wextra -Werror
LDFLAGS   := $(ARCHFLAGS) -nostdlib -nostartfiles -T link.ld -Wl,--no-warn-rwx-segments

# crt0.S and htif.c are bench/rv32's, unchanged, so the CRC reference image cannot move.
SOURCES := harness.c output.c $(DECODER).c stimulus.S $(RV32)/crt0.S $(RV32)/htif.c
HEADERS := decoder.h records.h output.h $(RV32)/htif.h
INPUTS  := $(SOURCES) $(HEADERS) link.ld $(STIM)/stimulus.bin

# Each build lives in a directory named by a hash of everything that goes into it, the
# stimulus's bytes included, as in bench/rv32 (docs/bugs/0004). One configuration cannot run
# another's binary, and one stimulus cannot run under another's name.
CC_ID     := $(shell $(CC) --version 2>/dev/null | head -n 1)
CONFIG    := $(strip $(CC_ID) | $(CFLAGS) | $(LDFLAGS) | $(DECODER))
CONFIG_ID := $(shell { printf '%s\n' '$(CONFIG)'; cat $(INPUTS); } | $(SHA256) | cut -c1-12)
BUILD     := build/$(CONFIG_ID)
ELF       := $(BUILD)/decoder.elf

.PHONY: all run check expect hashes mutate clean

all: $(ELF)

$(STIM)/stimulus.bin:
	@echo "no stimulus in $(STIM): make it with make -C ../stimulus" >&2; exit 1

$(BUILD):
	@mkdir -p $@ && printf '%s\n' '$(CONFIG)' > $@/config.txt

$(BUILD)/stimulus.bin: $(STIM)/stimulus.bin | $(BUILD)
	@cp $< $@

$(ELF): $(SOURCES) $(HEADERS) link.ld $(BUILD)/stimulus.bin | $(BUILD)
	@$(CC) $(CFLAGS) -Wa,-I$(BUILD) $(LDFLAGS) -o $@ $(SOURCES)

# Every byte Spike loads, and the same without the stimulus (decisions/0014, section 1).
$(BUILD)/image.bin: $(ELF)
	@$(OBJCOPY) -O binary $< $@

$(BUILD)/decoder.bin: $(ELF)
	@$(OBJCOPY) -O binary -R .stimulus $< $@

# Everything a result needs to say what ran is printed before it runs.
run: $(ELF) $(BUILD)/image.bin $(BUILD)/decoder.bin
	@echo "--- $(ELF)   (spike --isa=$(ARCH)) ---"
	@echo "cc       = $(CC_ID)"
	@echo "cflags   = $(strip $(CFLAGS))"
	@echo "source   = $(DECODER).c"
	@echo "image    = sha256:$$($(SHA256) $(BUILD)/image.bin | cut -d' ' -f1)"
	@echo "decoder  = sha256:$$($(SHA256) $(BUILD)/decoder.bin | cut -d' ' -f1)"
	@echo "stimulus = sha256:$$($(SHA256) $(BUILD)/stimulus.bin | cut -d' ' -f1)"
	@$(PYTHON) expect.py manifest $(STIM) $(BUILD)/stimulus.bin
	@$(SPIKE) --isa=$(ARCH) $(ELF)

expect: $(ELF) $(BUILD)/image.bin $(BUILD)/decoder.bin
	@$(MAKE) --no-print-directory run > $(BUILD)/run.out || { cat $(BUILD)/run.out; exit 1; }
	@$(PYTHON) expect.py $(DECODER) $(BUILD)/run.out $(BUILD)/stimulus.bin

hashes: $(BUILD)/image.bin $(BUILD)/decoder.bin
	@echo "$$($(SHA256) $(BUILD)/image.bin | cut -c1-64) $$($(SHA256) $(BUILD)/decoder.bin | cut -c1-64)"

check:
	@$(MAKE) --no-print-directory -C ../stimulus SEED=1
	@$(MAKE) --no-print-directory -C ../stimulus SEED=2
	@$(MAKE) --no-print-directory expect DECODER=stub STIM=../stimulus/build/coverage-1
	@$(MAKE) --no-print-directory expect DECODER=format_test STIM=../stimulus/build/coverage-1
	@one="$$($(MAKE) -s --no-print-directory hashes STIM=../stimulus/build/coverage-1)" && \
	 two="$$($(MAKE) -s --no-print-directory hashes STIM=../stimulus/build/coverage-2)" && \
	 $(PYTHON) expect.py same-decoder "$$one" "$$two"

mutate:
	@$(PYTHON) mutate.py

clean:
	rm -rf build
